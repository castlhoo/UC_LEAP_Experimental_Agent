"""
Step 1 - Deduplicator
======================
Removes duplicate papers from raw search results.
Priority: DOI match > normalized title match.
When duplicates are found, merges metadata (prefers richer record).
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def normalize_title(title: str) -> str:
    """Normalize title for comparison: lowercase, remove punctuation, collapse whitespace."""
    if not title:
        return ""
    t = title.lower().strip()
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def normalize_doi(doi: str) -> str:
    """Normalize DOI: lowercase, strip URL prefix."""
    if not doi:
        return ""
    d = doi.strip().lower()
    d = d.replace("https://doi.org/", "").replace("http://doi.org/", "")
    d = d.replace("https://dx.doi.org/", "").replace("http://dx.doi.org/", "")
    return d


def _richness_score(paper: Dict[str, Any]) -> int:
    """Score how complete a paper record is (higher = richer)."""
    score = 0
    if paper.get("abstract"):
        score += 3
    if paper.get("doi"):
        score += 2
    if paper.get("journal") and paper["journal"] != "arXiv preprint":
        score += 2
    if paper.get("year"):
        score += 1
    if paper.get("citation_count") is not None:
        score += 1
    if paper.get("open_access_url"):
        score += 1
    if paper.get("concepts"):
        score += 1
    if paper.get("paper_url"):
        score += 1
    return score


def _merge_papers(existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two paper records, preferring the richer one but combining unique info."""
    if _richness_score(new) > _richness_score(existing):
        base, other = new.copy(), existing
    else:
        base, other = existing.copy(), new

    # Merge: fill in blanks from the other record
    for key in ["abstract", "doi", "journal", "year", "paper_url", "open_access_url"]:
        if not base.get(key) and other.get(key):
            base[key] = other[key]

    # Merge concepts
    existing_concepts = set(base.get("concepts") or [])
    for c in (other.get("concepts") or []):
        existing_concepts.add(c)
    base["concepts"] = list(existing_concepts)

    # Merge external_ids
    other_ids = other.get("external_ids") or {}
    base_ids = base.get("external_ids") or {}
    for k, v in other_ids.items():
        if k not in base_ids:
            base_ids[k] = v
    base["external_ids"] = base_ids

    # Track all source APIs
    sources = set()
    for p in [existing, new]:
        src = p.get("source_api", "")
        if src:
            sources.add(src)
    base["source_apis"] = sorted(sources)

    # Keep higher citation count
    cc_existing = existing.get("citation_count")
    cc_new = new.get("citation_count")
    if cc_existing is not None and cc_new is not None:
        base["citation_count"] = max(cc_existing, cc_new)
    elif cc_new is not None:
        base["citation_count"] = cc_new

    return base


def deduplicate(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate papers by DOI first, then by normalized title.

    Returns deduplicated list with merged metadata.
    """
    doi_map: Dict[str, int] = {}      # normalized DOI -> index in result
    title_map: Dict[str, int] = {}    # normalized title -> index in result
    result: List[Dict[str, Any]] = []

    duplicates_found = 0

    for paper in papers:
        ndoi = normalize_doi(paper.get("doi", ""))
        ntitle = normalize_title(paper.get("title", ""))

        # Skip papers with no title
        if not ntitle and not ndoi:
            continue

        matched_idx = None

        # Check DOI match first
        if ndoi and ndoi in doi_map:
            matched_idx = doi_map[ndoi]

        # Check title match
        if matched_idx is None and ntitle and ntitle in title_map:
            matched_idx = title_map[ntitle]

        if matched_idx is not None:
            # Merge with existing
            result[matched_idx] = _merge_papers(result[matched_idx], paper)
            duplicates_found += 1
            # Update maps in case merge changed DOI
            merged = result[matched_idx]
            merged_doi = normalize_doi(merged.get("doi", ""))
            merged_title = normalize_title(merged.get("title", ""))
            if merged_doi:
                doi_map[merged_doi] = matched_idx
            if merged_title:
                title_map[merged_title] = matched_idx
        else:
            # New unique paper
            idx = len(result)
            paper["source_apis"] = [paper.get("source_api", "")]
            result.append(paper)
            if ndoi:
                doi_map[ndoi] = idx
            if ntitle:
                title_map[ntitle] = idx

    logger.info(
        f"Deduplication: {len(papers)} raw -> {len(result)} unique "
        f"({duplicates_found} duplicates merged)"
    )
    return result
