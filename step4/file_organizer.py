"""
Step 4 - File Organizer
=========================
Categorize and copy dataset files into organized folder structure:
  - type1_data/   — cleaned, figure-ready datasets
  - type2_data/   — raw instrument data
  - annotations/  — README, metadata, documentation
  - scripts/      — analysis/plotting code
"""

import os
import re
import shutil
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def make_paper_dirname(index: int, title: str, max_words: int = 5) -> str:
    """
    Create a clean directory name from paper index and title.

    Example: "001_Superconductivity_and_nematic_order_new"
    """
    # Clean title: keep alphanumeric and spaces
    clean = re.sub(r"[^\w\s]", "", title)
    words = clean.split()[:max_words]
    slug = "_".join(words)
    return f"{index:03d}_{slug}"


def organize_paper_files(
    paper: Dict[str, Any],
    paper_dir: str,
    config: Dict[str, Any],
) -> Dict[str, List[Dict[str, str]]]:
    """
    Organize a paper's dataset files into subfolders based on classification.

    Args:
        paper: Paper dict from Step 3 output (includes file_classifications, download_dir)
        paper_dir: Target directory for this paper
        config: Step 4 config dict

    Returns:
        Dict with keys: type1_data, type2_data, annotations, scripts, skip
        Each value is a list of {"original": ..., "renamed": ..., "source": ...}
    """
    result = {
        "type1_data": [],
        "type2_data": [],
        "annotations": [],
        "scripts": [],
        "skip": [],
    }

    # Get file classifications from GPT (full dicts with reasoning)
    classifications = {}
    classification_details = {}
    for fc in paper.get("file_classifications", []):
        fname = fc.get("filename", "")
        ftype = fc.get("type", "other")
        classifications[fname] = ftype
        classification_details[fname] = fc

    # Get source download directory
    download_dir = paper.get("download_dir", "")
    if not download_dir or not os.path.isdir(download_dir):
        logger.warning("    No download directory found")
        return result

    # Config for annotation/script detection
    ann_config = config.get("annotations", {})
    script_config = config.get("scripts", {})
    ann_filenames = set(ann_config.get("filenames", []))
    ann_extensions = set(ann_config.get("extensions", []))
    script_extensions = set(script_config.get("extensions", []))

    # Create subdirectories
    for subdir in ["type1_data", "type2_data", "annotations", "scripts"]:
        os.makedirs(os.path.join(paper_dir, subdir), exist_ok=True)

    # Walk through download directory
    for root, dirs, files in os.walk(download_dir):
        for filename in files:
            src_path = os.path.join(root, filename)

            # Determine category
            category = _categorize_file(
                filename, classifications,
                ann_filenames, ann_extensions, script_extensions,
            )

            if category == "skip":
                result["skip"].append({
                    "original": filename,
                    "renamed": filename,
                    "source": src_path,
                })
                continue

            # Copy file to target directory
            target_dir = os.path.join(paper_dir, category)
            target_path = os.path.join(target_dir, filename)

            # Handle duplicate filenames
            if os.path.exists(target_path):
                base, ext = os.path.splitext(filename)
                counter = 2
                while os.path.exists(target_path):
                    target_path = os.path.join(target_dir, f"{base}_{counter}{ext}")
                    counter += 1

            try:
                shutil.copy2(src_path, target_path)
                renamed = os.path.basename(target_path)
                file_entry = {
                    "original": filename,
                    "renamed": renamed,
                    "source": src_path,
                }
                # Attach GPT reasoning if available
                detail = classification_details.get(filename, {})
                if detail:
                    file_entry["classification"] = {
                        "type": detail.get("type", ""),
                        "paper_evidence": detail.get("paper_evidence", ""),
                        "file_evidence": detail.get("file_evidence", ""),
                        "reasoning": detail.get("reasoning", ""),
                        "ambiguity": detail.get("ambiguity", "none"),
                        "key_columns_or_structure": detail.get("key_columns_or_structure", ""),
                    }
                result[category].append(file_entry)
            except Exception as e:
                logger.warning(f"    Failed to copy {filename}: {e}")

    # Log summary
    for cat in ["type1_data", "type2_data", "annotations", "scripts"]:
        count = len(result[cat])
        if count > 0:
            logger.info(f"    {cat}: {count} files")

    return result


def _categorize_file(
    filename: str,
    classifications: Dict[str, str],
    ann_filenames: set,
    ann_extensions: set,
    script_extensions: set,
) -> str:
    """
    Determine file category based on GPT classification and config rules.

    Returns one of: type1_data, type2_data, annotations, scripts, skip
    """
    # Check GPT classification first
    gpt_type = classifications.get(filename, "")

    if gpt_type == "type1":
        return "type1_data"
    elif gpt_type == "type2":
        return "type2_data"
    elif gpt_type == "script":
        return "scripts"
    elif gpt_type == "documentation":
        return "annotations"

    # Fallback: config-based detection
    name_base = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1].lower()

    # Annotation files
    if name_base in ann_filenames or ext in ann_extensions:
        return "annotations"

    # Script files
    if ext in script_extensions:
        return "scripts"

    # Skip archives, PDFs, and unclassified
    skip_exts = {".zip", ".tar.gz", ".gz", ".pdf"}
    if ext in skip_exts:
        return "skip"

    # If GPT didn't classify it but it's a data file, skip it
    # (rather than misclassify)
    return "skip"
