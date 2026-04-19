"""
Step 4 - File Router
====================
Organize downloaded dataset files before Prompt B classification.

The routing is intentionally mechanical:
  - PDFs -> pdf/
  - scripts -> scripts/
  - README/metadata/descriptions -> annotation/
  - data files remain in place for inspection/classification
"""

import os
import re
import shutil
from typing import Any, Dict, List


PDF_EXTENSIONS = {".pdf"}
FIGURE_PDF_PATTERNS = ("fig", "figure")
FIGURE_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".bmp", ".gif"}
SCRIPT_EXTENSIONS = {".py", ".m", ".ipynb", ".r"}
ANNOTATION_EXTENSIONS = {".md", ".rst", ".yaml", ".yml"}
ANNOTATION_FILENAMES = {
    "readme", "license", "licence", "citation", "manifest",
    "metadata", "description", "data_description", "dataset_description",
}
ANNOTATION_TOKENS = (
    "readme", "metadata", "description", "data-description",
    "dataset-description", "manifest", "codebook", "column", "license",
)


def organize_downloaded_files(download_result: Dict[str, Any]) -> Dict[str, Any]:
    """Move non-data support files into Prompt B folders and update local paths."""
    base_dir = download_result.get("download_dir", "")
    if not base_dir or not os.path.isdir(base_dir):
        download_result["organization"] = {"pdf": 0, "scripts": 0, "annotation": 0}
        return download_result

    counts = {"pdf": 0, "scripts": 0, "annotation": 0}
    moves: List[Dict[str, str]] = []

    for collection_name in ("files", "zip_extracted"):
        for item in download_result.get(collection_name, []):
            path = item.get("local_path", "")
            if not path or not os.path.isfile(path):
                continue

            folder = _target_folder(path)
            if not folder:
                continue

            new_path = _move_preserving_relative_path(path, base_dir, folder)
            if new_path == path:
                continue

            item["local_path"] = new_path
            item["filename"] = os.path.basename(new_path)
            item["organized_folder"] = folder
            counts[folder] += 1
            moves.append({
                "from": _rel(path, base_dir),
                "to": _rel(new_path, base_dir),
                "folder": folder,
            })

    download_result["organization"] = counts
    download_result["organized_files"] = moves
    return download_result


def _target_folder(path: str) -> str:
    name = os.path.basename(path)
    lower = name.lower()
    stem, ext = _split_extension(lower)

    if ext in PDF_EXTENSIONS:
        if stem.startswith(FIGURE_PDF_PATTERNS) or stem.startswith("figapp"):
            return "annotation"
        return "pdf"
    if ext in FIGURE_IMAGE_EXTENSIONS:
        if stem.startswith(FIGURE_PDF_PATTERNS) or stem.startswith("figapp"):
            return "annotation"
    if ext in SCRIPT_EXTENSIONS:
        return "scripts"
    if ext in ANNOTATION_EXTENSIONS:
        return "annotation"
    if stem in ANNOTATION_FILENAMES:
        return "annotation"
    if any(token in lower for token in ANNOTATION_TOKENS):
        if ext in ("", ".txt", ".json", ".xml", ".csv", ".tsv"):
            return "annotation"
    return ""


def _move_preserving_relative_path(path: str, base_dir: str, folder: str) -> str:
    rel = _rel(path, base_dir)
    parts = rel.split("/")
    if parts and parts[0] in {"pdf", "scripts", "annotation"}:
        return path

    destination = os.path.join(base_dir, folder, *parts)
    destination = _unique_path(destination)
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    try:
        shutil.move(path, destination)
    except PermissionError:
        shutil.copy2(path, destination)
        try:
            os.remove(path)
        except OSError:
            pass
    return destination


def _unique_path(path: str) -> str:
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 1
    while True:
        candidate = f"{base}_{i}{ext}"
        if not os.path.exists(candidate):
            return candidate
        i += 1


def _split_extension(name: str):
    if name.endswith(".tar.gz"):
        return name[:-7], ".tar.gz"
    stem, ext = os.path.splitext(name)
    return stem, ext


def _rel(path: str, base_dir: str) -> str:
    try:
        return os.path.relpath(path, base_dir).replace("\\", "/")
    except ValueError:
        return re.sub(r"[^A-Za-z0-9_.-]", "_", os.path.basename(path))
