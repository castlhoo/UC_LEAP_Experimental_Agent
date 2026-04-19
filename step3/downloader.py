"""
Step 3 - Dataset Downloader
==============================
Download actual dataset files from various sources:
  - Zenodo API
  - Figshare API
  - Nature Source Data (static-content.springer.com)
  - Direct URL downloads
"""

import os
import re
import time
import logging
import gzip
import shutil
import tarfile
import zipfile
import requests
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, unquote

logger = logging.getLogger(__name__)


def download_paper_datasets(
    paper: Dict[str, Any],
    download_dir: str,
    http_config: Dict[str, Any],
    dl_config: Dict[str, Any],
    rate_limit_delay: float = 1.0,
) -> Dict[str, Any]:
    """
    Download all dataset files for a single paper.

    Returns:
        Dict with:
          - paper_id: str
          - download_dir: str (path to paper's download folder)
          - files: list of downloaded file info dicts
          - errors: list of error messages
          - zip_extracted: list of extracted ZIP contents
    """
    paper_id = paper.get("paper_id", "unknown")
    doi = paper.get("doi", "").replace("/", "_")
    safe_id = re.sub(r'[^\w\-]', '_', doi or paper_id)[:80]

    paper_dir = os.path.join(download_dir, safe_id)
    os.makedirs(paper_dir, exist_ok=True)

    max_size_bytes = dl_config.get("max_file_size_mb", 500) * 1024 * 1024
    max_files = dl_config.get("max_files_per_paper", 50)
    allowed_ext = {e.lower() for e in dl_config.get("allowed_extensions", [])}
    skip_ext = {e.lower() for e in dl_config.get("skip_extensions", [])}

    timeout = http_config.get("timeout", 60)
    user_agent = http_config.get("user_agent", "UC_LEAP_Step3/1.0")
    headers = {"User-Agent": user_agent}

    result = {
        "paper_id": paper_id,
        "download_dir": paper_dir,
        "files": [],
        "errors": [],
        "zip_extracted": [],
    }

    # Collect all downloadable URLs
    download_targets = _collect_download_targets(paper, headers, timeout)

    if not download_targets:
        result["errors"].append("No downloadable URLs found")
        return result

    logger.info(f"    Found {len(download_targets)} download targets")

    # Download each target
    downloaded = 0
    for target in download_targets:
        if downloaded >= max_files:
            logger.info(f"    Reached max files limit ({max_files})")
            break

        url = target["url"]
        fname = target.get("filename", "")
        source = target.get("source", "unknown")

        # Check extension
        ext = _get_extension(fname or url)
        if skip_ext and ext in skip_ext:
            continue
        if allowed_ext and ext and ext not in allowed_ext:
            continue

        time.sleep(rate_limit_delay * 0.3)

        file_info = _download_single_file(
            url, fname, paper_dir, headers, timeout, max_size_bytes, source
        )

        if file_info.get("success"):
            result["files"].append(file_info)
            downloaded += 1

            # Extract archives
            if file_info["local_path"].endswith(".zip"):
                zip_fname = file_info.get("filename", "")
                extracted = _extract_zip(
                    file_info["local_path"], paper_dir, max_files - downloaded
                )
                for ex in extracted:
                    ex["from_zip"] = zip_fname
                result["zip_extracted"].extend(extracted)
                downloaded += len(extracted)
            elif file_info["local_path"].endswith((".tar.gz", ".tgz", ".tar", ".gz")):
                archive_fname = file_info.get("filename", "")
                extracted = _extract_archive(
                    file_info["local_path"], paper_dir, max_files - downloaded
                )
                for ex in extracted:
                    ex["from_zip"] = archive_fname
                result["zip_extracted"].extend(extracted)
                downloaded += len(extracted)
        else:
            result["errors"].append(
                f"{fname or url[:60]}: {file_info.get('error', 'unknown')}"
            )

    logger.info(
        f"    Downloaded {len(result['files'])} files, "
        f"{len(result['zip_extracted'])} extracted from ZIPs, "
        f"{len(result['errors'])} errors"
    )

    return result


def _collect_download_targets(
    paper: Dict[str, Any],
    headers: Dict[str, str] = None,
    timeout: int = 60,
) -> List[Dict[str, str]]:
    """Collect all downloadable URLs from paper's Step 2 data."""
    targets = []
    seen_urls = set()

    # 1. Direct data/supplementary candidates from Step 2.
    direct_candidates = paper.get("data_url_candidates")
    if direct_candidates is None:
        direct_candidates = paper.get("source_data_files", [])

    for f in direct_candidates:
        url = f.get("url", "")
        if not url or url in seen_urls:
            continue
        # Skip generic DOI self-links; Step 3 consumes article PDFs separately.
        if f.get("source") == "nature_embedded":
            continue
        seen_urls.add(url)
        targets.append({
            "url": url,
            "filename": f.get("filename", ""),
            "source": f.get("source", "direct_data_candidate"),
        })

    # 2. Repository files from inventory
    for repo in paper.get("repositories", []):
        inv = repo.get("inventory", {})
        if not inv.get("success"):
            continue
        repo_type = repo.get("repo_type", "unknown")

        for finfo in inv.get("files", []):
            url = finfo.get("download_url", "") or finfo.get("url", "")
            fname = finfo.get("filename", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                targets.append({
                    "url": url,
                    "filename": fname,
                    "source": repo_type,
                })

    # 3. Discovered URLs — resolve repo DOIs to file lists
    for url in paper.get("discovered_urls", []):
        if url in seen_urls:
            continue

        # 3a. Zenodo DOI → resolve via API
        zenodo_id = _extract_zenodo_id(url)
        if zenodo_id:
            seen_urls.add(url)
            zenodo_files = _resolve_zenodo_files(zenodo_id, headers, timeout)
            for zf in zenodo_files:
                if zf["url"] not in seen_urls:
                    seen_urls.add(zf["url"])
                    targets.append(zf)
            continue

        # 3b. Figshare DOI → resolve via API
        figshare_id = _extract_figshare_id(url)
        if figshare_id:
            seen_urls.add(url)
            fig_files = _resolve_figshare_files(figshare_id, headers, timeout)
            for ff in fig_files:
                if ff["url"] not in seen_urls:
                    seen_urls.add(ff["url"])
                    targets.append(ff)
            continue

        # 3c. Direct file download URL
        if _is_direct_file_url(url):
            seen_urls.add(url)
            targets.append({
                "url": url,
                "filename": url.rsplit("/", 1)[-1].split("?")[0],
                "source": "discovered",
            })

    return targets


def _extract_zenodo_id(url: str) -> Optional[str]:
    """Extract Zenodo record ID from URL or DOI."""
    # https://doi.org/10.5281/zenodo.12345 → 12345
    m = re.search(r'10\.5281/zenodo\.(\d+)', url)
    if m:
        return m.group(1)
    # https://zenodo.org/records/12345 or /record/12345
    m = re.search(r'zenodo\.org/records?/(\d+)', url)
    if m:
        return m.group(1)
    return None


def _resolve_zenodo_files(
    record_id: str, headers: Dict[str, str] = None, timeout: int = 60
) -> List[Dict[str, str]]:
    """Resolve Zenodo record ID to file download URLs via API."""
    api_url = f"https://zenodo.org/api/records/{record_id}"
    try:
        resp = requests.get(api_url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        files = []
        for f in data.get("files", []):
            fname = f.get("key", "")
            dl_url = f.get("links", {}).get("self", "")
            if not dl_url:
                # Fallback: construct URL
                dl_url = f"https://zenodo.org/records/{record_id}/files/{fname}?download=1"
            files.append({
                "url": dl_url,
                "filename": fname,
                "source": "zenodo",
                "size_bytes": f.get("size", 0),
            })
        logger.info(f"    Zenodo {record_id}: {len(files)} files found")
        return files
    except Exception as e:
        logger.warning(f"    Zenodo API error for {record_id}: {e}")
        return []


def _extract_figshare_id(url: str) -> Optional[str]:
    """Extract Figshare article ID from URL or DOI."""
    # https://doi.org/10.6084/m9.figshare.12345
    m = re.search(r'10\.6084/m9\.figshare\.(\d+)', url)
    if m:
        return m.group(1)
    # https://figshare.com/articles/.../12345
    m = re.search(r'figshare\.com/articles/[^/]+/(\d+)', url)
    if m:
        return m.group(1)
    return None


def _resolve_figshare_files(
    article_id: str, headers: Dict[str, str] = None, timeout: int = 60
) -> List[Dict[str, str]]:
    """Resolve Figshare article ID to file download URLs via API."""
    api_url = f"https://api.figshare.com/v2/articles/{article_id}"
    try:
        resp = requests.get(api_url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        files = []
        for f in data.get("files", []):
            fname = f.get("name", "")
            dl_url = f.get("download_url", "")
            if dl_url:
                files.append({
                    "url": dl_url,
                    "filename": fname,
                    "source": "figshare",
                    "size_bytes": f.get("size", 0),
                })
        logger.info(f"    Figshare {article_id}: {len(files)} files found")
        return files
    except Exception as e:
        logger.warning(f"    Figshare API error for {article_id}: {e}")
        return []


def _is_direct_file_url(url: str) -> bool:
    """Check if URL looks like a direct file download."""
    data_extensions = {
        ".csv", ".xlsx", ".xls", ".zip", ".tar.gz", ".gz",
        ".h5", ".hdf5", ".nxs", ".dat", ".txt", ".json",
        ".npz", ".npy", ".mat",
    }
    parsed = urlparse(url)
    path = parsed.path.lower()
    return any(path.endswith(ext) for ext in data_extensions)


def _get_extension(name: str) -> str:
    """Get file extension from filename or URL."""
    name = name.lower().split("?")[0]
    if name.endswith(".tar.gz"):
        return ".tar.gz"
    if name.endswith(".tgz"):
        return ".tgz"
    _, ext = os.path.splitext(name)
    return ext


def _download_single_file(
    url: str,
    filename: str,
    paper_dir: str,
    headers: Dict[str, str],
    timeout: int,
    max_size_bytes: int,
    source: str,
) -> Dict[str, Any]:
    """Download a single file."""
    try:
        # Stream download to check size before committing
        resp = requests.get(
            url, headers=headers, timeout=timeout,
            stream=True, allow_redirects=True,
        )

        if resp.status_code != 200:
            return {"success": False, "error": f"HTTP {resp.status_code}"}

        # Check content-length
        content_length = int(resp.headers.get("content-length", 0))
        if content_length > max_size_bytes:
            return {
                "success": False,
                "error": f"Too large: {content_length / 1024 / 1024:.1f}MB",
            }

        # Determine filename
        if not filename or filename in ("unknown", "source_data_with_paper"):
            # Try from Content-Disposition header
            cd = resp.headers.get("content-disposition", "")
            if "filename=" in cd:
                filename = re.findall(r'filename="?([^";]+)', cd)[0]
            else:
                # From URL
                filename = unquote(url.rsplit("/", 1)[-1].split("?")[0])

        if not filename:
            filename = "download"

        # Sanitize filename
        filename = re.sub(r'[^\w\-.]', '_', filename)[:150]

        local_path = os.path.join(paper_dir, filename)

        # Avoid overwriting
        if os.path.exists(local_path):
            base, ext = os.path.splitext(filename)
            i = 1
            while os.path.exists(local_path):
                local_path = os.path.join(paper_dir, f"{base}_{i}{ext}")
                i += 1

        # Write file
        total_bytes = 0
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                total_bytes += len(chunk)
                if total_bytes > max_size_bytes:
                    f.close()
                    os.remove(local_path)
                    return {
                        "success": False,
                        "error": f"Exceeded max size during download",
                    }
                f.write(chunk)

        return {
            "success": True,
            "url": url,
            "filename": os.path.basename(local_path),
            "local_path": local_path,
            "size_bytes": total_bytes,
            "size_human": _human_size(total_bytes),
            "source": source,
            "content_type": resp.headers.get("content-type", ""),
        }

    except Exception as e:
        return {"success": False, "error": str(e)[:200]}


def _extract_zip(
    zip_path: str,
    paper_dir: str,
    max_extract: int = 50,
) -> List[Dict[str, Any]]:
    """Extract ZIP file contents."""
    extracted = []
    extract_dir = os.path.join(paper_dir, "zip_contents")
    os.makedirs(extract_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            entries = zf.namelist()
            logger.info(f"      ZIP contains {len(entries)} entries")

            count = 0
            for entry in entries:
                if count >= max_extract:
                    break
                # Skip directories and hidden files
                if entry.endswith("/") or "/__MACOSX" in entry or "/." in entry:
                    continue
                if _is_unsafe_archive_path(entry):
                    continue

                try:
                    zf.extract(entry, extract_dir)
                    local_path = os.path.join(extract_dir, entry)
                    size = os.path.getsize(local_path) if os.path.isfile(local_path) else 0
                    extracted.append({
                        "filename": os.path.basename(entry),
                        "archive_path": entry,
                        "local_path": local_path,
                        "size_bytes": size,
                        "size_human": _human_size(size),
                    })
                    count += 1
                except Exception as e:
                    logger.debug(f"      Failed to extract {entry}: {e}")

    except zipfile.BadZipFile:
        logger.warning(f"      Not a valid ZIP file: {zip_path}")
    except Exception as e:
        logger.warning(f"      ZIP extraction failed: {e}")

    return extracted


def _extract_archive(
    archive_path: str,
    paper_dir: str,
    max_extract: int = 50,
) -> List[Dict[str, Any]]:
    """Extract TAR/TAR.GZ/TGZ/GZ archive contents."""
    lower = archive_path.lower()
    if lower.endswith((".tar.gz", ".tgz", ".tar")):
        return _extract_tar(archive_path, paper_dir, max_extract)
    if lower.endswith(".gz"):
        return _extract_gzip_file(archive_path, paper_dir)
    return []


def _extract_tar(
    tar_path: str,
    paper_dir: str,
    max_extract: int = 50,
) -> List[Dict[str, Any]]:
    extracted = []
    extract_dir = os.path.join(paper_dir, "archive_contents")
    os.makedirs(extract_dir, exist_ok=True)

    try:
        with tarfile.open(tar_path, "r:*") as tf:
            members = [m for m in tf.getmembers() if m.isfile()]
            logger.info(f"      TAR contains {len(members)} file entries")
            count = 0
            for member in members:
                if count >= max_extract:
                    break
                if _is_unsafe_archive_path(member.name):
                    continue
                try:
                    tf.extract(member, extract_dir)
                    local_path = os.path.join(extract_dir, member.name)
                    if not os.path.isfile(local_path):
                        continue
                    size = os.path.getsize(local_path)
                    extracted.append({
                        "filename": os.path.basename(member.name),
                        "archive_path": member.name,
                        "local_path": local_path,
                        "size_bytes": size,
                        "size_human": _human_size(size),
                    })
                    count += 1
                except Exception as e:
                    logger.debug(f"      Failed to extract {member.name}: {e}")
    except Exception as e:
        logger.warning(f"      TAR extraction failed: {e}")

    return extracted


def _extract_gzip_file(
    gzip_path: str,
    paper_dir: str,
) -> List[Dict[str, Any]]:
    extract_dir = os.path.join(paper_dir, "archive_contents")
    os.makedirs(extract_dir, exist_ok=True)

    base = os.path.basename(gzip_path)
    out_name = base[:-3] if base.lower().endswith(".gz") else f"{base}.out"
    out_path = os.path.join(extract_dir, out_name)

    try:
        with gzip.open(gzip_path, "rb") as src, open(out_path, "wb") as dst:
            shutil.copyfileobj(src, dst)
        size = os.path.getsize(out_path)
        return [{
            "filename": os.path.basename(out_path),
            "archive_path": base,
            "local_path": out_path,
            "size_bytes": size,
            "size_human": _human_size(size),
        }]
    except Exception as e:
        logger.warning(f"      GZIP extraction failed: {e}")
        return []


def _is_unsafe_archive_path(path: str) -> bool:
    norm = os.path.normpath(path)
    return norm.startswith("..") or os.path.isabs(norm)


def _human_size(nbytes: int) -> str:
    """Convert bytes to human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} TB"
