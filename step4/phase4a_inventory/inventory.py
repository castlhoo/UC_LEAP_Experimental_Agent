"""Step 4A: download, organize, and inspect dataset files."""

import os
import re
import shutil
from typing import Any, Dict, List

from step3.downloader import download_paper_datasets
from step3.file_inspector import inspect_all_files
from step4.file_router import organize_downloaded_files


GENERATED_DIRS = {"assessment", "classification_batches", "summary"}


def download_and_prepare_paper(
    paper: Dict[str, Any],
    download_dir: str,
    step3_paper_dir: str,
    http_config: Dict[str, Any],
    dl_config: Dict[str, Any],
    rate_limit_delay: float,
) -> Dict[str, Any]:
    """Download repository files, copy the main PDF, and route support files."""
    result = download_paper_datasets(
        paper, download_dir, http_config, dl_config, rate_limit_delay
    )
    _include_main_paper_pdf(paper, result, step3_paper_dir)
    return organize_downloaded_files(result)


def get_paper_download_dir(paper: Dict[str, Any], download_dir: str) -> str:
    """Return the same paper download folder name used by Step 3 downloader."""
    paper_id = paper.get("paper_id", "unknown")
    doi = paper.get("doi", "").replace("/", "_")
    safe_id = re.sub(r"[^\w\-]", "_", doi or paper_id)[:80]
    return os.path.join(download_dir, safe_id)


def has_existing_download(paper: Dict[str, Any], download_dir: str) -> bool:
    paper_dir = get_paper_download_dir(paper, download_dir)
    if not os.path.isdir(paper_dir):
        return False
    return any(_iter_existing_files(paper_dir))


def load_existing_download_result(
    paper: Dict[str, Any],
    download_dir: str,
    step3_paper_dir: str,
) -> Dict[str, Any]:
    """Rebuild a download_result manifest from files already present on disk."""
    paper_dir = get_paper_download_dir(paper, download_dir)
    os.makedirs(paper_dir, exist_ok=True)

    result = {
        "paper_id": paper.get("paper_id", "unknown"),
        "download_dir": paper_dir,
        "files": [],
        "errors": [],
        "zip_extracted": [],
        "reused_existing_download": True,
    }
    _include_main_paper_pdf(paper, result, step3_paper_dir)

    existing_paths = set()
    for item in result.get("files", []):
        if item.get("local_path"):
            existing_paths.add(os.path.abspath(item["local_path"]))

    for path in _iter_existing_files(paper_dir):
        abs_path = os.path.abspath(path)
        if abs_path in existing_paths:
            continue
        result["files"].append({
            "success": True,
            "url": "",
            "filename": os.path.basename(path),
            "local_path": path,
            "size_bytes": os.path.getsize(path),
            "size_human": "",
            "source": "existing_download",
        })

    return organize_downloaded_files(result)


def inspect_paper_files(
    download_result: Dict[str, Any],
    inspect_config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Inspect every downloaded/extracted file that Step 4 can read."""
    n_files = len(download_result.get("files", [])) + len(download_result.get("zip_extracted", []))
    if n_files == 0:
        return []
    return inspect_all_files(download_result, inspect_config)


def _iter_existing_files(paper_dir: str):
    for root, dirs, files in os.walk(paper_dir):
        dirs[:] = [d for d in dirs if d not in GENERATED_DIRS and not d.startswith("__")]
        for filename in files:
            yield os.path.join(root, filename)


def _include_main_paper_pdf(
    paper: Dict[str, Any],
    download_result: Dict[str, Any],
    step3_paper_dir: str,
) -> None:
    """Copy Step 3's main paper PDF into Step 4's pdf folder when available."""
    doi = paper.get("doi", "")
    paper_id = paper.get("paper_id", "unknown")
    doi_safe = doi.replace("/", "_") if doi else paper_id
    source_pdf = os.path.join(step3_paper_dir, doi_safe, "paper.pdf")
    if not os.path.isfile(source_pdf):
        return

    paper_dir = download_result.get("download_dir", "")
    if not paper_dir:
        return

    target_dir = os.path.join(paper_dir, "pdf")
    os.makedirs(target_dir, exist_ok=True)
    target_pdf = os.path.join(target_dir, "main_paper.pdf")
    if not os.path.exists(target_pdf):
        shutil.copy2(source_pdf, target_pdf)

    download_result.setdefault("files", []).append({
        "success": True,
        "url": paper.get("paper_url", ""),
        "filename": "main_paper.pdf",
        "local_path": target_pdf,
        "size_bytes": os.path.getsize(target_pdf),
        "size_human": "",
        "source": "step3_main_paper_pdf",
        "organized_folder": "pdf",
    })
