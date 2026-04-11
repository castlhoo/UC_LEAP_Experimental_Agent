"""
Step 2 - Inventory Collector
============================
Collect repository inventories from supported dataset hosts.
"""

import logging
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)


def collect_inventory(repo: Dict[str, Any], http_config: Dict[str, Any]) -> Dict[str, Any]:
    repo_type = repo.get("repo_type", "")
    handlers = {
        "zenodo": _collect_zenodo,
        "figshare": _collect_figshare,
        "github": _collect_github,
        "dryad": _collect_dryad,
        "mendeley": _collect_mendeley,
        "materials_cloud": _collect_materials_cloud,
        "osf": _collect_osf,
        "dataverse": _collect_dataverse,
    }
    handler = handlers.get(repo_type)
    if not handler:
        return {
            "repo_type": repo_type,
            "success": False,
            "error": f"unsupported repository type: {repo_type}",
        }
    try:
        return handler(repo, http_config)
    except Exception as exc:
        logger.debug(f"Inventory collection failed for {repo_type}: {exc}")
        return {
            "repo_type": repo_type,
            "success": False,
            "error": str(exc),
        }


def _get_json(url: str, http_config: Dict[str, Any], params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    headers = {"User-Agent": http_config.get("user_agent", "UC_LEAP_Step2/1.0")}
    timeout = http_config.get("timeout", 30)
    resp = requests.get(url, params=params, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _human_size(num_bytes: int | float | None) -> str:
    if not num_bytes:
        return "0 B"
    value = float(num_bytes)
    units = ["B", "KB", "MB", "GB", "TB"]
    idx = 0
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024
        idx += 1
    return f"{value:.1f} {units[idx]}"


def _build_success(repo_type: str, title: str, description: str, files: List[Dict[str, Any]], license_name: str = "") -> Dict[str, Any]:
    total_size = sum(f.get("size_bytes", 0) or 0 for f in files)
    return {
        "repo_type": repo_type,
        "success": True,
        "title": title,
        "description": description,
        "license": license_name,
        "file_count": len(files),
        "total_size_bytes": total_size,
        "total_size_human": _human_size(total_size),
        "files": files,
    }


def _normalize_file_entry(filename: str, size_bytes: int | float | None = None, download_url: str = "") -> Dict[str, Any]:
    return {
        "filename": filename,
        "size_bytes": int(size_bytes or 0),
        "size_human": _human_size(size_bytes or 0),
        "download_url": download_url,
        "extension": f".{filename.rsplit('.', 1)[-1].lower()}" if "." in filename else "",
    }


def _collect_zenodo(repo: Dict[str, Any], http_config: Dict[str, Any]) -> Dict[str, Any]:
    repo_id = repo.get("repo_id", "")
    data = _get_json(f"https://zenodo.org/api/records/{repo_id}", http_config)
    metadata = data.get("metadata", {})
    files = [
        _normalize_file_entry(
            f.get("key", "unknown"),
            (f.get("size") or 0),
            (f.get("links") or {}).get("self", ""),
        )
        for f in data.get("files", [])
    ]
    return _build_success(
        "zenodo",
        metadata.get("title", ""),
        metadata.get("description", ""),
        files,
        ((metadata.get("license") or {}).get("id", "") if isinstance(metadata.get("license"), dict) else ""),
    )


def _collect_figshare(repo: Dict[str, Any], http_config: Dict[str, Any]) -> Dict[str, Any]:
    repo_id = repo.get("repo_id", "")
    data = _get_json(f"https://api.figshare.com/v2/articles/{repo_id}", http_config)
    files = [
        _normalize_file_entry(
            f.get("name", "unknown"),
            f.get("size", 0),
            f.get("download_url", ""),
        )
        for f in data.get("files", [])
    ]
    return _build_success(
        "figshare",
        data.get("title", ""),
        data.get("description", ""),
        files,
        (data.get("license") or {}).get("name", "") if isinstance(data.get("license"), dict) else "",
    )


def _collect_github(repo: Dict[str, Any], http_config: Dict[str, Any]) -> Dict[str, Any]:
    repo_id = repo.get("repo_id", "")
    repo_data = _get_json(f"https://api.github.com/repos/{repo_id}", http_config)
    default_branch = repo_data.get("default_branch", "main")
    tree = _get_json(
        f"https://api.github.com/repos/{repo_id}/git/trees/{default_branch}",
        http_config,
        params={"recursive": 1},
    )
    files = []
    for item in tree.get("tree", []):
        if item.get("type") != "blob":
            continue
        path = item.get("path", "unknown")
        files.append(
            _normalize_file_entry(
                path,
                item.get("size", 0),
                f"https://raw.githubusercontent.com/{repo_id}/{default_branch}/{path}",
            )
        )
    return _build_success(
        "github",
        repo_data.get("full_name", repo_id),
        repo_data.get("description", ""),
        files,
        (repo_data.get("license") or {}).get("spdx_id", "") if isinstance(repo_data.get("license"), dict) else "",
    )


def _collect_dryad(repo: Dict[str, Any], http_config: Dict[str, Any]) -> Dict[str, Any]:
    repo_id = repo.get("repo_id", "")
    data = _get_json(f"https://datadryad.org/api/v2/datasets/{repo_id}", http_config)
    embedded = data.get("_embedded", {})
    files = []
    for f in embedded.get("stash:files", []):
        files.append(
            _normalize_file_entry(
                f.get("path", f.get("filename", "unknown")),
                f.get("size", 0),
                (f.get("_links") or {}).get("stash:download", {}).get("href", ""),
            )
        )
    return _build_success(
        "dryad",
        data.get("title", repo_id),
        data.get("abstract", ""),
        files,
        data.get("license", ""),
    )


def _collect_mendeley(repo: Dict[str, Any], http_config: Dict[str, Any]) -> Dict[str, Any]:
    repo_id = repo.get("repo_id", "")
    data = _get_json(f"https://api.datacite.org/dois/10.17632/{repo_id}", http_config)
    attrs = data.get("data", {}).get("attributes", {})
    files = []
    for content in attrs.get("contentUrl", []) or []:
        filename = content.rsplit("/", 1)[-1].split("?")[0] or repo_id
        files.append(_normalize_file_entry(filename, 0, content))
    title = repo_id
    if attrs.get("titles"):
        title = attrs["titles"][0].get("title", repo_id)
    description = ""
    if attrs.get("descriptions"):
        description = attrs["descriptions"][0].get("description", "")
    rights = ""
    if attrs.get("rightsList"):
        rights = attrs["rightsList"][0].get("rights", "")
    return _build_success("mendeley", title, description, files, rights)


def _collect_materials_cloud(repo: Dict[str, Any], http_config: Dict[str, Any]) -> Dict[str, Any]:
    repo_id = repo.get("repo_id", "")
    data = _get_json(f"https://archive.materialscloud.org/api/v1/records/{repo_id}", http_config)
    files = [
        _normalize_file_entry(
            f.get("path", f.get("filename", "unknown")),
            f.get("size", 0),
            f.get("url", ""),
        )
        for f in data.get("files", [])
    ]
    metadata = data.get("metadata", {})
    return _build_success(
        "materials_cloud",
        metadata.get("title", repo_id),
        metadata.get("description", ""),
        files,
        metadata.get("license", ""),
    )


def _collect_osf(repo: Dict[str, Any], http_config: Dict[str, Any]) -> Dict[str, Any]:
    repo_id = repo.get("repo_id", "")
    data = _get_json(f"https://api.osf.io/v2/nodes/{repo_id}/files/", http_config)
    files = []
    for provider in data.get("data", []):
        rel = ((provider.get("relationships") or {}).get("files") or {})
        provider_url = ((rel.get("links") or {}).get("related") or {}).get("href", "")
        if not provider_url:
            continue
        provider_listing = _get_json(provider_url, http_config)
        for item in provider_listing.get("data", []):
            attrs = item.get("attributes", {})
            if attrs.get("kind") != "file":
                continue
            files.append(
                _normalize_file_entry(
                    attrs.get("name", "unknown"),
                    attrs.get("size", 0),
                    (item.get("links") or {}).get("download", ""),
                )
            )
    return _build_success("osf", repo_id, "OSF project files", files, "")


def _collect_dataverse(repo: Dict[str, Any], http_config: Dict[str, Any]) -> Dict[str, Any]:
    repo_id = repo.get("repo_id", "")
    data = _get_json(
        "https://dataverse.harvard.edu/api/datasets/:persistentId/",
        http_config,
        params={"persistentId": repo_id},
    )
    latest = data.get("data", {}).get("latestVersion", {})
    files = []
    for file_entry in latest.get("files", []):
        data_file = file_entry.get("dataFile", {})
        files.append(
            _normalize_file_entry(
                data_file.get("filename", "unknown"),
                data_file.get("filesize", 0),
                "",
            )
        )
    title = repo_id
    citation = ((latest.get("metadataBlocks") or {}).get("citation") or {}).get("fields", [])
    if citation and isinstance(citation[0], dict):
        title = citation[0].get("value", title)
    return _build_success("dataverse", title, "Dataverse dataset", files, "")
