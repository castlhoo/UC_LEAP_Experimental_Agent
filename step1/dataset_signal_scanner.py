"""
Step 1 - Dataset Signal Scanner
=================================
Scans paper metadata for dataset availability signals.
Does NOT download any files or inspect dataset contents.
Only detects signals: high / medium / low.
"""

import re
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


# ---- Dataset signal patterns ----

# Repository URL patterns
REPO_URL_PATTERNS = [
    r"zenodo\.org/record",
    r"zenodo\.org/doi",
    r"figshare\.com",
    r"github\.com/[\w-]+/[\w-]+",
    r"gitlab\.com/[\w-]+/[\w-]+",
    r"materialscloud\.org",
    r"nomad-lab\.eu",
    r"dataverse\.\w+",
    r"dryad\.org",
    r"osf\.io",
    r"data\.mendeley\.com",
    r"archive\.materialscloud\.org",
    r"iochem-bd\.bsc\.es",
    r"torina\.fe\.infn\.it",
    r"doi\.org/10\.\d+/zenodo",
    r"doi\.org/10\.\d+/figshare",
]

# High signal phrases
HIGH_SIGNAL_PHRASES = [
    "source data are available",
    "source data is available",
    "source data available",
    "data are available at",
    "data is available at",
    "data available at",
    "data have been deposited",
    "data has been deposited",
    "deposited in zenodo",
    "deposited in figshare",
    "deposited at",
    "data repository",
    "data are deposited",
    "open data",
    "data availability statement",
    "data availability:",
    "code and data availability",
    "all data are available",
    "all data is available",
    "data that support the findings",
    "data supporting the findings",
    "publicly available at",
    "publicly available on",
    "source data for figures",
    "source data for fig",
    "source data file",
    "supplementary dataset",
    "accompanying dataset",
    "raw data available",
    "processed data available",
]

# Medium signal phrases
MEDIUM_SIGNAL_PHRASES = [
    "supplementary information",
    "supplementary material",
    "supporting information",
    "supplementary data",
    "extended data",
    "data availability",
    "code availability",
    "data and code",
    "additional data",
    "see supplementary",
]

# Low / negative signal phrases
NEGATIVE_SIGNAL_PHRASES = [
    "data available upon request",
    "data available on request",
    "available upon reasonable request",
    "available from the corresponding author",
    "data not publicly available",
    "no additional data",
]


def _find_urls(text: str) -> List[str]:
    """Extract URLs from text."""
    url_pattern = r'https?://[^\s<>"\')\],;]+'
    urls = re.findall(url_pattern, text)
    # Clean trailing punctuation
    cleaned = []
    for u in urls:
        u = u.rstrip(".,;:)")
        if len(u) > 10:
            cleaned.append(u)
    return cleaned


def _find_repo_urls(text: str) -> List[str]:
    """Find repository URLs matching known dataset hosting patterns."""
    all_urls = _find_urls(text)
    repo_urls = []
    for url in all_urls:
        for pattern in REPO_URL_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                repo_urls.append(url)
                break
    return repo_urls


# DOI patterns that are NOT datasets (publisher policies, journal homepages, etc.)
NOISE_DOI_PREFIXES = [
    "10.15223/policy",   # Elsevier policies
    "10.1016/j.",        # Journal article DOIs (not datasets)
    "10.1038/s41",       # Nature article DOIs
    "10.1103/phys",      # APS article DOIs
    "10.1126/sci",       # Science article DOIs
    "10.1021/acs",       # ACS article DOIs
    "10.1088/",          # IOP article DOIs
]

DATASET_DOI_PREFIXES = [
    "10.5281/zenodo",    # Zenodo
    "10.6084/m9.figshare",  # Figshare
    "10.5061/dryad",     # Dryad
    "10.17632/",         # Mendeley Data
    "10.7910/DVN",       # Harvard Dataverse
    "10.24435/materialscloud",  # Materials Cloud
    "10.17172/NOMAD",    # NOMAD
]


def _is_noise_doi(doi_url: str) -> bool:
    """Check if a DOI URL is a publisher policy or article DOI, not a dataset."""
    lower = doi_url.lower()
    for prefix in NOISE_DOI_PREFIXES:
        if prefix.lower() in lower:
            return True
    return False


def _is_dataset_doi(doi_url: str) -> bool:
    """Check if a DOI URL matches a known dataset repository DOI prefix."""
    lower = doi_url.lower()
    for prefix in DATASET_DOI_PREFIXES:
        if prefix.lower() in lower:
            return True
    return False


def _find_doi_links(text: str) -> List[str]:
    """Find DOI links that might point to datasets."""
    doi_pattern = r'10\.\d{4,}/[^\s<>"\')\],;]+'
    dois = re.findall(doi_pattern, text)
    results = []
    for d in dois:
        url = f"https://doi.org/{d.rstrip('.,;:)')}"
        if not _is_noise_doi(url):
            results.append(url)
    return results


def scan_dataset_signal(paper: Dict[str, Any]) -> Dict[str, Any]:
    """
    Scan a paper's metadata for dataset availability signals.

    Returns:
        Dict with:
          - level: "high", "medium", "low"
          - evidence: list of evidence strings
          - url_candidates: list of dataset URL candidates
          - details: dict with match details
    """
    title = paper.get("title", "")
    abstract = paper.get("abstract", "")
    raw_meta = paper.get("raw_metadata") or {}

    # Combine all available text
    combined_text = f"{title} {abstract}"

    # Check raw metadata links separately (filter noise)
    # Only look for known dataset repository URLs in metadata links
    meta_links = raw_meta.get("crossref_links", [])
    meta_repo_urls = []
    for link in meta_links:
        link_str = str(link)
        for pattern in REPO_URL_PATTERNS:
            if re.search(pattern, link_str, re.IGNORECASE):
                meta_repo_urls.append(link_str)
                break
        if _is_dataset_doi(link_str):
            meta_repo_urls.append(link_str)
    combined_text_full = f"{combined_text} {' '.join(meta_repo_urls)}"

    evidence = []
    url_candidates = []
    score = 0

    # 1. Check for repository URLs
    repo_urls = _find_repo_urls(combined_text_full)
    if repo_urls:
        evidence.append(f"Repository URLs found: {', '.join(repo_urls[:3])}")
        url_candidates.extend(repo_urls)
        score += 5

    # 2. Check for dataset DOI links (beyond paper's own DOI)
    paper_doi = paper.get("doi", "")
    doi_links = _find_doi_links(combined_text_full)
    dataset_dois = [d for d in doi_links if paper_doi not in d]
    if dataset_dois:
        evidence.append(f"Dataset DOI links: {', '.join(dataset_dois[:3])}")
        url_candidates.extend(dataset_dois)
        score += 4

    # 3. Check high signal phrases
    high_matched = []
    for phrase in HIGH_SIGNAL_PHRASES:
        if phrase.lower() in combined_text.lower():
            high_matched.append(phrase)
    if high_matched:
        evidence.append(f"High signal phrases: {', '.join(high_matched[:4])}")
        score += 3

    # 4. Check medium signal phrases
    medium_matched = []
    for phrase in MEDIUM_SIGNAL_PHRASES:
        if phrase.lower() in combined_text.lower():
            medium_matched.append(phrase)
    if medium_matched:
        evidence.append(f"Medium signal phrases: {', '.join(medium_matched[:3])}")
        score += 1

    # 5. Check negative signals
    negative_matched = []
    for phrase in NEGATIVE_SIGNAL_PHRASES:
        if phrase.lower() in combined_text.lower():
            negative_matched.append(phrase)
    if negative_matched:
        evidence.append(f"Negative signals: {', '.join(negative_matched[:2])}")
        score -= 2

    # 6. Check open access metadata
    is_oa = raw_meta.get("is_oa", False)
    has_fulltext = raw_meta.get("has_fulltext", False)
    if is_oa:
        evidence.append("Open access paper")
        score += 0.5
    if has_fulltext:
        score += 0.5

    # Determine level
    if score >= 4:
        level = "high"
    elif score >= 1:
        level = "medium"
    else:
        level = "low"

    if not evidence:
        evidence.append("No dataset signals detected")

    # Deduplicate URL candidates
    url_candidates = list(dict.fromkeys(url_candidates))

    return {
        "level": level,
        "evidence": evidence,
        "url_candidates": url_candidates,
        "details": {
            "repo_urls": repo_urls,
            "dataset_dois": dataset_dois if 'dataset_dois' in dir() else [],
            "high_phrases": high_matched if 'high_matched' in dir() else [],
            "medium_phrases": medium_matched if 'medium_matched' in dir() else [],
            "negative_phrases": negative_matched if 'negative_matched' in dir() else [],
            "signal_score": score,
        },
    }
