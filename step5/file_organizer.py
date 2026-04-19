"""
Step 4 - File Organizer
=========================
Categorize and copy dataset files into organized folder structure:
  - type1/        — cleaned, figure-ready datasets
  - type2/        — raw instrument data
  - annotations/  — original README, metadata, documentation
  - scripts/      — analysis/plotting code
  - pdf/          — paper PDFs, supplementary PDFs, peer-review PDFs
  - paper_dataset_summary.json — generated paper/dataset dossier file
"""

import os
import re
import shutil
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

SUPPLEMENTARY_DOC_EXTENSIONS = {".pdf", ".doc", ".docx"}
SUPPLEMENTARY_DOC_PATTERNS = (
    "supplementary",
    "supp_info",
    "supp info",
    "supporting_information",
    "supporting information",
    "peer_review",
    "peer review",
    "reviewer",
    "response_to_review",
    "response to review",
    "response_to_reviewer",
    "response to reviewer",
)

ARCHIVE_EXTENSIONS = {
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
}

FIGURE_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".bmp", ".gif"}

FIGURE_PDF_PATTERNS = (
    "fig",
    "figure",
)


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
        Dict with keys: type1, type2, annotations, scripts, pdf, summary, skip
        Each value is a list of {"original": ..., "renamed": ..., "source": ...}
    """
    result = {
        "type1": [],
        "type2": [],
        "annotations": [],
        "scripts": [],
        "pdf": [],
        "summary": [],
        "skip": [],
    }

    # Get file classifications from GPT (full dicts with reasoning)
    classifications = {}
    classification_details = {}
    filename_counts = {}
    for fc in paper.get("file_classifications", []):
        fname = fc.get("filename", "")
        rel_path = (fc.get("relative_path", "") or "").replace("\\", "/")
        ftype = fc.get("type", "other")
        if rel_path:
            classifications[rel_path] = ftype
            classification_details[rel_path] = fc
        if fname:
            filename_counts[fname] = filename_counts.get(fname, 0) + 1
            if filename_counts[fname] == 1:
                classifications[fname] = ftype
                classification_details[fname] = fc
            else:
                classifications.pop(fname, None)
                classification_details.pop(fname, None)

    # Get source download directory
    download_dir = paper.get("download_dir", "")
    if not download_dir or not os.path.isdir(download_dir):
        logger.warning("    No download directory found")
        return result

    # Config for annotation/script detection
    ann_config = config.get("annotation", config.get("annotations", {}))
    script_config = config.get("scripts", {})
    ann_filenames = set(ann_config.get("filenames", []))
    ann_extensions = set(ann_config.get("extensions", []))
    script_extensions = set(script_config.get("extensions", []))

    # Create subdirectories. Generated Step 5 sidecars live at paper root so
    # they do not get confused with original README/annotation files.
    for subdir in ["type1", "type2", "annotations", "scripts", "pdf"]:
        os.makedirs(os.path.join(paper_dir, subdir), exist_ok=True)

    seen_targets = set()

    # Walk through download directory
    for root, dirs, files in os.walk(download_dir):
        for filename in files:
            src_path = os.path.join(root, filename)
            rel_path = os.path.relpath(src_path, download_dir).replace("\\", "/")

            # Determine category
            category = _categorize_file(
                filename, rel_path, classifications,
                ann_filenames, ann_extensions, script_extensions,
            )

            if category == "skip":
                result["skip"].append({
                    "original": filename,
                    "renamed": filename,
                    "source": src_path,
                })
                continue

            target_rel = _target_relative_path(category, filename, rel_path)
            if category == "summary":
                target_path = os.path.join(paper_dir, target_rel)
            else:
                target_path = os.path.join(paper_dir, category, target_rel)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)

            # Handle duplicate filenames
            if target_path in seen_targets and os.path.exists(target_path):
                target_dir = os.path.dirname(target_path)
                base, ext = os.path.splitext(os.path.basename(target_path))
                counter = 2
                while os.path.exists(target_path):
                    target_path = os.path.join(target_dir, f"{base}_{counter}{ext}")
                    counter += 1

            try:
                shutil.copy2(src_path, target_path)
                seen_targets.add(target_path)
                if category == "summary":
                    renamed = os.path.relpath(target_path, paper_dir).replace("\\", "/")
                    final_relative_path = renamed
                else:
                    renamed = os.path.relpath(target_path, os.path.join(paper_dir, category)).replace("\\", "/")
                    final_relative_path = f"{category}/{renamed}"
                file_entry = {
                    "original": filename,
                    "renamed": renamed,
                    "final_relative_path": final_relative_path,
                    "source": src_path,
                }
                # Attach GPT reasoning if available
                detail = classification_details.get(rel_path) or classification_details.get(filename, {})
                if detail:
                    file_entry["classification"] = {
                        "relative_path": detail.get("relative_path", rel_path),
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
    for cat in ["type1", "type2", "annotations", "scripts", "pdf", "summary"]:
        count = len(result[cat])
        if count > 0:
            logger.info(f"    {cat}: {count} files")

    return result


def _categorize_file(
    filename: str,
    relative_path: str,
    classifications: Dict[str, str],
    ann_filenames: set,
    ann_extensions: set,
    script_extensions: set,
) -> str:
    """
    Determine file category based on GPT classification and config rules.

    Returns one of: type1, type2, annotations, scripts, pdf, summary, skip
    """
    normalized_rel = relative_path.replace("\\", "/").lower()
    ext = os.path.splitext(filename)[1].lower()
    name_base = os.path.splitext(filename)[0].lower()

    if (
        normalized_rel.startswith("assessment/")
        or normalized_rel.startswith("classification_batches/")
    ):
        return "skip"

    if normalized_rel.startswith("summary/") or filename == "paper_dataset_summary.json":
        return "summary"

    # Archive files must not appear in the final type1/type2 folders. Step 4
    # extracts archives before classification; Step 5 copies extracted contents.
    if _is_archive_file(filename):
        return "skip"

    if normalized_rel.startswith("pdf/") or ext == ".pdf":
        if _is_figure_pdf(filename):
            return "annotations"
        if _is_pdf_folder_document(filename, relative_path):
            return "pdf"
        return "annotations"

    if normalized_rel.startswith("annotation/") or normalized_rel.startswith("annotations/"):
        return "annotations"

    if normalized_rel.startswith("scripts/"):
        return "scripts"

    # Figure images (fig*.png, figure*.jpg, etc.) are paper artifacts, not data.
    if _is_figure_image(filename):
        return "annotations"

    # Check GPT classification first
    gpt_type = classifications.get(relative_path, "") or classifications.get(filename, "")

    if gpt_type == "type1":
        return "type1"
    elif gpt_type == "type2":
        return "type2"
    elif gpt_type == "script":
        return "scripts"
    elif gpt_type == "documentation":
        return "annotations"

    # Fallback: config-based detection
    # Annotation files
    if name_base in ann_filenames or ext in ann_extensions:
        return "annotations"

    # Script files
    if ext in script_extensions:
        return "scripts"

    # If GPT didn't classify it but it's a data file, skip it
    # (rather than misclassify)
    return "skip"


def _target_relative_path(category: str, filename: str, relative_path: str) -> str:
    """Build the path under a final category while preserving useful structure."""
    normalized = relative_path.replace("\\", "/")
    lower = normalized.lower()

    for prefix in ("pdf/", "summary/", "annotation/", "annotations/", "scripts/"):
        if lower.startswith(prefix):
            normalized = normalized[len(prefix):]
            break

    # Strip extraction-artifact prefixes so final paths are clean.
    lower = normalized.lower()
    for prefix in ("zip_contents/", "archive_contents/"):
        if lower.startswith(prefix):
            normalized = normalized[len(prefix):]
            break

    if category == "summary" and filename == "paper_dataset_summary.json":
        return "paper_dataset_summary.json"

    if category == "pdf":
        return _pdf_target_name(filename)

    return normalized or filename


def _pdf_target_name(filename: str) -> str:
    """Use stable names for main/supplementary/peer-review PDFs."""
    lower = filename.lower()
    if lower == "main_paper.pdf" or lower == "paper_main.pdf":
        return "paper_main.pdf"
    if "peer" in lower or "review" in lower or "referee" in lower:
        return "paper_peer_review.pdf"
    if _is_supplementary_document(filename, filename):
        return "paper_supplementary.pdf"
    return filename


def _is_supplementary_document(filename: str, relative_path: str) -> bool:
    """Detect supplementary information / peer review documents that should be kept as annotations."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in SUPPLEMENTARY_DOC_EXTENSIONS:
        return False

    normalized = f"{relative_path} {filename}".replace("\\", "/").lower()
    return any(pattern in normalized for pattern in SUPPLEMENTARY_DOC_PATTERNS)


def _is_archive_file(filename: str) -> bool:
    """Detect archive originals that should not be copied into final data folders."""
    lower = filename.lower()
    return any(lower.endswith(ext) for ext in ARCHIVE_EXTENSIONS)


def _is_figure_pdf(filename: str) -> bool:
    """Detect figure-level PDFs that are artifacts, not paper/supplement PDFs."""
    lower = os.path.basename(filename).lower()
    stem = os.path.splitext(lower)[0]
    return stem.startswith(FIGURE_PDF_PATTERNS) or stem.startswith("figapp")


def _is_figure_image(filename: str) -> bool:
    """Detect figure-level images (fig*.png, figure*.jpg, etc.) that are paper artifacts."""
    lower = os.path.basename(filename).lower()
    stem, ext = os.path.splitext(lower)
    if ext not in FIGURE_IMAGE_EXTENSIONS:
        return False
    return stem.startswith(FIGURE_PDF_PATTERNS) or stem.startswith("figapp")


def _is_pdf_folder_document(filename: str, relative_path: str) -> bool:
    """Keep only main/supplementary/peer-review style documents in pdf/."""
    lower = os.path.basename(filename).lower()
    normalized = f"{relative_path} {filename}".replace("\\", "/").lower()
    if lower in {"main_paper.pdf", "paper_main.pdf", "paper_supplementary.pdf", "paper_peer_review.pdf"}:
        return True
    if any(pattern in normalized for pattern in ("peer", "review", "referee")):
        return True
    if _is_supplementary_document(filename, relative_path):
        return True
    return False
