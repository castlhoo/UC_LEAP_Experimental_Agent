"""
Step 2 - Repository Classifier
================================
Classify dataset URLs into repository types (Zenodo, Figshare, GitHub, Dryad, etc.)
and extract repository-specific IDs for API access.
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)

# Repository URL patterns → (repo_type, id_extraction_regex)
REPO_PATTERNS: List[Tuple[str, str, int]] = [
    # Zenodo: https://zenodo.org/record/1234567 or https://zenodo.org/records/1234567
    ("zenodo", r"zenodo\.org/records?/(\d+)", 1),
    # Zenodo DOI: 10.5281/zenodo.1234567
    ("zenodo", r"10\.5281/zenodo\.(\d+)", 1),
    # Figshare: https://figshare.com/articles/dataset/Title/1234567
    ("figshare", r"figshare\.com/articles/[^/]+/[^/]+/(\d+)", 1),
    # Figshare DOI: 10.6084/m9.figshare.1234567
    ("figshare", r"10\.6084/m9\.figshare\.(\d+)", 1),
    # GitHub: https://github.com/owner/repo
    ("github", r"github\.com/([^/]+/[^/]+?)(?:\.git|/tree|/blob|/releases|/?$)", 1),
    # Dryad: https://datadryad.org/stash/dataset/doi:10.5061/dryad.xxx
    ("dryad", r"datadryad\.org/stash/dataset/doi[:%]10\.5061/(dryad\.\w+)", 1),
    # Dryad DOI: 10.5061/dryad.xxx
    ("dryad", r"(10\.5061/dryad\.\w+)", 1),
    # Mendeley Data: https://data.mendeley.com/datasets/xxx
    ("mendeley", r"data\.mendeley\.com/datasets/(\w+)", 1),
    # Materials Cloud: https://archive.materialscloud.org/record/2024.xxx
    ("materials_cloud", r"materialscloud\.org/record/([\d.]+)", 1),
    # NOMAD: https://nomad-lab.eu/prod/v1/gui/dataset/id/xxx
    ("nomad", r"nomad-lab\.eu/.*?/dataset/id/([a-zA-Z0-9_-]+)", 1),
    # Supplementary (generic publisher links)
    ("supplementary", r"(nature\.com|science\.org|aps\.org|wiley\.com|springer\.com).*suppl", 0),
]

# DOI prefixes that indicate dataset repositories
DATASET_DOI_PREFIXES = {
    "10.5281": "zenodo",
    "10.6084": "figshare",
    "10.5061": "dryad",
    "10.17632": "mendeley",
    "10.24435": "materials_cloud",
}


def classify_url(url: str) -> Optional[Dict[str, Any]]:
    """
    Classify a single URL into a repository type.

    Returns:
        Dict with 'repo_type', 'repo_id', 'url' or None if unrecognized.
    """
    if not url:
        return None

    url_lower = url.lower().strip()

    for repo_type, pattern, group_idx in REPO_PATTERNS:
        match = re.search(pattern, url_lower)
        if match:
            repo_id = match.group(group_idx) if group_idx > 0 else ""
            return {
                "repo_type": repo_type,
                "repo_id": repo_id,
                "url": url.strip(),
            }

    return None


def classify_doi(doi: str) -> Optional[Dict[str, Any]]:
    """
    Check if a DOI points to a dataset repository.

    Returns:
        Dict with 'repo_type', 'repo_id', 'url' or None.
    """
    if not doi:
        return None

    doi = doi.strip().lower()
    for prefix, repo_type in DATASET_DOI_PREFIXES.items():
        if doi.startswith(prefix):
            # Extract the full DOI as repo_id
            url = f"https://doi.org/{doi}"
            # For Zenodo, extract numeric ID
            if repo_type == "zenodo":
                match = re.search(r"zenodo\.(\d+)", doi)
                repo_id = match.group(1) if match else doi
            elif repo_type == "figshare":
                match = re.search(r"figshare\.(\d+)", doi)
                repo_id = match.group(1) if match else doi
            elif repo_type == "dryad":
                repo_id = doi
            else:
                repo_id = doi

            return {
                "repo_type": repo_type,
                "repo_id": repo_id,
                "url": url,
            }

    return None


def classify_all_links(
    paper: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Classify all potential dataset links from a paper candidate.
    Looks at dataset_url_candidates and any other URL fields.

    Returns:
        List of classified repository entries (deduplicated by repo_type + repo_id).
    """
    results = []
    seen = set()

    # 1. Check dataset_url_candidates from Step 1
    for url in paper.get("dataset_url_candidates", []):
        classified = classify_url(url)
        if classified:
            key = (classified["repo_type"], classified["repo_id"])
            if key not in seen:
                seen.add(key)
                results.append(classified)

    # 2. Check DOI-based dataset links
    doi = paper.get("doi", "")
    # Some papers have related DOIs in their metadata
    # We check the paper's own DOI prefix (unlikely to be dataset, but just in case)

    # 3. Check open_access_url
    oa_url = paper.get("open_access_url", "")
    if oa_url:
        classified = classify_url(oa_url)
        if classified and classified["repo_type"] != "supplementary":
            key = (classified["repo_type"], classified["repo_id"])
            if key not in seen:
                seen.add(key)
                results.append(classified)

    return results
