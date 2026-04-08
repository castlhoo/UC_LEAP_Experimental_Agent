"""
Step 2 - Dataset Link Resolver
=================================
Resolve dataset links for papers using multiple strategies:
  1. Existing dataset_url_candidates from Step 1
  2. CrossRef API: find related dataset DOIs via "relation" field
  3. Publisher-specific Source Data extraction (Nature, Science, APS, etc.)
  4. DOI landing page: parse Data Availability section
  5. GPT: analyze Data Availability text for dataset location clues
"""

import re
import time
import logging
import requests
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Known dataset repository URL patterns
DATASET_DOMAINS = [
    "zenodo.org", "figshare.com", "github.com", "datadryad.org",
    "data.mendeley.com", "materialscloud.org", "nomad-lab.eu",
    "osf.io", "dataverse", "pangaea.de",
]

DATASET_DOI_PREFIXES = ["10.5281", "10.6084", "10.5061", "10.17632", "10.24435"]


# ===================================================================
# Strategy 1: CrossRef API
# ===================================================================

def resolve_from_crossref(
    doi: str,
    http_config: Dict[str, Any],
) -> List[str]:
    """Query CrossRef for dataset-related links in relations and references."""
    if not doi:
        return []

    timeout = http_config.get("timeout", 30)
    user_agent = http_config.get("user_agent", "UC_LEAP_Step2/1.0")
    headers = {"User-Agent": user_agent}

    url = f"https://api.crossref.org/works/{doi}"
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return []

        data = resp.json().get("message", {})
        found_urls = []

        # Check relation fields
        relation = data.get("relation", {})
        for rel_type in ["has-related-resource", "is-supplemented-by", "references"]:
            for item in relation.get(rel_type, []):
                rel_id = item.get("id", "")
                rel_type_val = item.get("id-type", "")
                if rel_type_val == "doi":
                    found_urls.append(f"https://doi.org/{rel_id}")
                elif rel_type_val == "uri":
                    found_urls.append(rel_id)

        # Check link field for supplementary data
        for link_item in data.get("link", []):
            link_url = link_item.get("URL", "")
            if any(d in link_url.lower() for d in DATASET_DOMAINS):
                found_urls.append(link_url)

        # Check references for dataset DOIs
        for ref in data.get("reference", []):
            ref_doi = ref.get("DOI", "")
            if ref_doi:
                ref_doi_lower = ref_doi.lower()
                if any(prefix in ref_doi_lower for prefix in DATASET_DOI_PREFIXES):
                    found_urls.append(f"https://doi.org/{ref_doi}")

        return found_urls

    except Exception as e:
        logger.debug(f"CrossRef lookup failed for {doi}: {e}")
        return []


# ===================================================================
# Strategy 2: Publisher-specific Source Data extraction
# ===================================================================

def _detect_publisher(doi: str, journal: str, paper_url: str) -> str:
    """Detect publisher from DOI prefix, journal name, or URL."""
    doi_lower = (doi or "").lower()
    journal_lower = (journal or "").lower()
    url_lower = (paper_url or "").lower()

    if "10.1038/" in doi_lower or "nature.com" in url_lower:
        return "nature"
    if "10.1126/" in doi_lower or "science.org" in url_lower:
        return "science"
    if "10.1103/" in doi_lower or "aps.org" in url_lower:
        return "aps"
    if "10.1021/" in doi_lower or "acs.org" in url_lower:
        return "acs"
    if "10.1002/" in doi_lower or "wiley.com" in url_lower:
        return "wiley"
    if "10.1016/" in doi_lower or "elsevier" in url_lower or "sciencedirect" in url_lower:
        return "elsevier"
    if "arxiv" in doi_lower or "arxiv.org" in url_lower:
        return "arxiv"
    return "unknown"


def resolve_from_publisher(
    doi: str,
    journal: str,
    paper_url: str,
    http_config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Extract Source Data / Supplementary files from publisher pages.

    Returns:
        Dict with:
          - urls: list of found URLs
          - source_data_files: list of file info dicts
          - data_availability_text: extracted DA statement
          - publisher: detected publisher
    """
    publisher = _detect_publisher(doi, journal, paper_url)
    timeout = http_config.get("timeout", 30)
    user_agent = http_config.get("user_agent", "UC_LEAP_Step2/1.0")
    headers = {"User-Agent": user_agent, "Accept": "text/html"}

    result = {
        "urls": [],
        "source_data_files": [],
        "data_availability_text": "",
        "publisher": publisher,
    }

    if not doi:
        return result

    # Fetch the landing page
    try:
        resp = requests.get(
            f"https://doi.org/{doi}",
            headers=headers, timeout=timeout, allow_redirects=True,
        )
        if resp.status_code != 200:
            return result
        html = resp.text
        final_url = resp.url
    except Exception as e:
        logger.debug(f"Publisher page fetch failed for {doi}: {e}")
        return result

    # ---- Extract Data Availability text (all publishers) ----
    result["data_availability_text"] = _extract_data_availability(html)

    # ---- Extract dataset repository URLs (all publishers) ----
    repo_urls = _extract_repo_urls(html)
    result["urls"].extend(repo_urls)

    # ---- Publisher-specific extraction ----
    if publisher == "nature":
        _extract_nature(html, final_url, doi, result)
    elif publisher == "science":
        _extract_science(html, final_url, doi, result)
    elif publisher == "aps":
        _extract_aps(html, final_url, doi, result)

    return result


def _extract_data_availability(html: str) -> str:
    """Extract Data Availability statement from HTML."""
    # Strategy 1: Nature-specific - look for data-availability-content div
    nature_match = re.search(
        r'id="data-availability-content"[^>]*>\s*(.*?)\s*</div>',
        html, re.DOTALL | re.IGNORECASE,
    )
    if nature_match:
        text = nature_match.group(1)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > 10:
            return text[:1000]

    # Strategy 2: Science-specific
    science_match = re.search(
        r'(?:Data and materials availability|Data availability)[^<]*</h[2-4]>\s*<[^>]*>\s*(.*?)(?=</section|<h[2-4])',
        html[:200000], re.DOTALL | re.IGNORECASE,
    )
    if science_match:
        text = re.sub(r'<[^>]+>', ' ', science_match.group(1))
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > 10:
            return text[:1000]

    # Strategy 3: Generic - section with data-availability in id or data-title
    generic_match = re.search(
        r'(?:data-title="Data availability"|id="[^"]*data.availab[^"]*")[^>]*>.*?<p[^>]*>(.*?)</p>',
        html[:200000], re.DOTALL | re.IGNORECASE,
    )
    if generic_match:
        text = re.sub(r'<[^>]+>', ' ', generic_match.group(1))
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > 10:
            return text[:1000]

    return ""


def _extract_repo_urls(html: str) -> List[str]:
    """Extract dataset repository URLs from HTML."""
    found = []
    seen = set()

    for domain in DATASET_DOMAINS:
        pattern = rf'https?://[^\s"\'<>]*{re.escape(domain)}[^\s"\'<>]*'
        matches = re.findall(pattern, html[:100000], re.IGNORECASE)
        for match in matches:
            clean = match.rstrip('.,;:)"\'}]')
            # Skip tracking/analytics URLs
            if any(x in clean.lower() for x in ["track", "click", "redirect", "pixel"]):
                continue
            if clean not in seen:
                seen.add(clean)
                found.append(clean)

    # Also find dataset DOIs in text
    doi_matches = re.findall(r'10\.\d{4,}/[^\s"\'<>&,;)]+', html[:100000])
    for d in doi_matches:
        d_clean = d.rstrip('.,;:)"\'}]')
        if any(prefix in d_clean.lower() for prefix in DATASET_DOI_PREFIXES):
            url = f"https://doi.org/{d_clean}"
            if url not in seen:
                seen.add(url)
                found.append(url)

    return found


def _extract_nature(html: str, final_url: str, doi: str, result: Dict):
    """Extract Source Data from Nature articles.

    IMPORTANT: Nature MOESM links come in two forms:
      - Anchor links: /articles/xxx#MOESM2  (in-page refs, NOT real files)
      - File links: https://static-content.springer.com/...MOESM1_ESM.pdf (real files)
    We only count actual downloadable file URLs as source data.
    """
    seen_urls = set()

    # Pattern 1: Real downloadable MOESM/source files from Springer CDN
    real_file_pattern = r'href="(https?://static-content\.springer\.com/[^"]*)"'
    matches = re.findall(real_file_pattern, html, re.IGNORECASE)
    for url in matches:
        if url not in seen_urls:
            seen_urls.add(url)
            fname = url.rsplit("/", 1)[-1].split("?")[0]
            result["source_data_files"].append({
                "url": url,
                "filename": fname,
                "source": "nature_source_data",
            })
            if url not in result["urls"]:
                result["urls"].append(url)

    # Pattern 2: Direct data file links (.xlsx, .csv, .zip, etc.)
    data_file_pattern = r'href="([^"]*\.(?:xlsx?|csv|zip|tar\.gz|h5|hdf5|dat)[^"]*)"'
    data_matches = re.findall(data_file_pattern, html, re.IGNORECASE)
    for match in data_matches:
        if match.startswith("http"):
            url = match
        elif match.startswith("/"):
            url = f"https://www.nature.com{match}"
        else:
            continue
        # Skip anchor-only links and tracking URLs
        if "#MOESM" in url or any(x in url.lower() for x in ["track", "click", "redirect"]):
            continue
        if url not in seen_urls:
            seen_urls.add(url)
            fname = url.rsplit("/", 1)[-1].split("?")[0]
            result["source_data_files"].append({
                "url": url,
                "filename": fname,
                "source": "nature_data_file",
            })
            if url not in result["urls"]:
                result["urls"].append(url)

    # Pattern 3: "Source data provided with this paper" marker
    if "source data" in html.lower() and "provided with this paper" in html.lower():
        result["source_data_files"].append({
            "url": f"https://doi.org/{doi}",
            "filename": "source_data_with_paper",
            "source": "nature_embedded",
            "note": "Source data provided with this paper (embedded in article)",
        })

    # Pattern 4: Supplementary Information page link (for reference, not counted as data)
    si_pattern = r'href="([^"]*supplementary-information[^"]*)"'
    si_matches = re.findall(si_pattern, html[:200000], re.IGNORECASE)
    for match in si_matches[:2]:
        if match.startswith("/"):
            url = f"https://www.nature.com{match}"
        else:
            url = match
        if url not in result["urls"]:
            result["urls"].append(url)


def _extract_science(html: str, final_url: str, doi: str, result: Dict):
    """Extract Supplementary Materials from Science articles."""
    # Science.org supplementary materials
    supp_patterns = [
        r'href="([^"]*(?:suppl|supplementar)[^"]*)"',
        r'href="([^"]*science\.org[^"]*(?:\.pdf|\.xlsx?|\.csv|\.zip)[^"]*)"',
    ]
    for pattern in supp_patterns:
        matches = re.findall(pattern, html[:200000], re.IGNORECASE)
        for match in matches[:5]:
            if match.startswith("/"):
                url = f"https://www.science.org{match}"
            else:
                url = match
            fname = url.rsplit("/", 1)[-1].split("?")[0]
            if url not in result["urls"]:
                result["urls"].append(url)
                result["source_data_files"].append({
                    "url": url,
                    "filename": fname,
                    "source": "science_supplementary",
                })


def _extract_aps(html: str, final_url: str, doi: str, result: Dict):
    """Extract Supplemental Material from APS (Physical Review) articles."""
    supp_patterns = [
        r'href="([^"]*(?:supplemental|suppl)[^"]*\.(?:pdf|zip|tar|xlsx?))"',
        r'href="(/supplemental/[^"]*)"',
    ]
    for pattern in supp_patterns:
        matches = re.findall(pattern, html[:200000], re.IGNORECASE)
        for match in matches[:5]:
            if match.startswith("/"):
                url = f"https://journals.aps.org{match}"
            else:
                url = match
            if url not in result["urls"]:
                result["urls"].append(url)
                result["source_data_files"].append({
                    "url": url,
                    "filename": url.rsplit("/", 1)[-1].split("?")[0],
                    "source": "aps_supplemental",
                })


# ===================================================================
# Strategy 3: GPT Data Availability analysis
# ===================================================================

def gpt_analyze_data_availability(
    paper: Dict[str, Any],
    data_availability_text: str,
    publisher_result: Dict[str, Any],
    gpt_call_fn,
    model: str = "gpt-5.4-mini",
) -> Dict[str, Any]:
    """
    Use GPT to analyze Data Availability statement and publisher page findings.

    Returns:
        Dict with dataset_location, confidence, and any additional URLs.
    """
    title = paper.get("title", "")
    abstract = paper.get("abstract_summary", "")
    publisher = publisher_result.get("publisher", "unknown")
    source_files = publisher_result.get("source_data_files", [])
    found_urls = publisher_result.get("urls", [])

    # Build context
    source_files_str = ""
    if source_files:
        source_files_str = "\n".join(
            f"  - {f.get('filename', '?')} ({f.get('source', '?')})"
            for f in source_files[:10]
        )

    found_urls_str = "\n".join(f"  - {u}" for u in found_urls[:10]) if found_urls else "  (none)"

    prompt = f"""Analyze the data availability for this condensed matter / materials science paper.

Paper title: {title}
Abstract: {abstract}
Publisher: {publisher}

Data Availability statement from paper:
\"\"\"{data_availability_text if data_availability_text else '(not found)'}\"\"\"

Files found on publisher page:
{source_files_str if source_files_str else '  (none)'}

URLs found:
{found_urls_str}

Return JSON:
{{
  "dataset_location": "repository" | "publisher_source_data" | "supplementary" | "upon_request" | "no_data" | "unclear",
  "location_detail": "brief description of where data is",
  "confidence": "high" | "medium" | "low",
  "has_downloadable_data": true | false,
  "additional_urls": ["any dataset URLs mentioned in DA statement not yet found"],
  "data_description": "brief description of what data is available"
}}

Definitions:
- "repository": Data in external repo (Zenodo, Figshare, GitHub, Dryad, etc.)
- "publisher_source_data": Source Data files hosted on publisher site (e.g., Nature Source Data xlsx)
- "supplementary": Data in Supplementary Information/Materials
- "upon_request": Available from authors upon request only
- "no_data": No data mentioned or explicitly stated no data
- "unclear": Can't determine from available information"""

    system = "You are an expert at analyzing data availability in scientific papers. Return structured JSON."

    try:
        result = gpt_call_fn(
            prompt=prompt,
            system_prompt=system,
            model=model,
            temperature=0.2,
            max_tokens=500,
        )
        return result
    except Exception as e:
        logger.warning(f"GPT DA analysis failed: {e}")
        return {
            "dataset_location": "unclear",
            "location_detail": f"GPT error: {e}",
            "confidence": "low",
            "has_downloadable_data": False,
            "additional_urls": [],
            "data_description": "",
        }


def _search_zenodo_for_paper(
    paper: Dict[str, Any], http_config: Dict[str, Any]
) -> List[str]:
    """Search Zenodo for dataset records linked to this paper (DOI or title)."""
    timeout = http_config.get("timeout", 30)
    doi = paper.get("doi", "")
    title = paper.get("title", "")

    found_urls = []

    # Search by DOI relation first
    if doi:
        try:
            resp = requests.get(
                "https://zenodo.org/api/records",
                params={"q": f'related.identifier:"{doi}"', "size": 3},
                timeout=timeout,
            )
            if resp.ok:
                hits = resp.json().get("hits", {}).get("hits", [])
                for h in hits:
                    record_url = f"https://doi.org/10.5281/zenodo.{h['id']}"
                    found_urls.append(record_url)
                    logger.debug(f"  Zenodo DOI search hit: {h['id']}")
        except Exception as e:
            logger.debug(f"  Zenodo DOI search error: {e}")

    # If no DOI hits, try title search
    if not found_urls and title:
        # Clean title for search
        clean_title = re.sub(r'<[^>]+>', '', title)  # strip HTML tags
        clean_title = re.sub(r'[^\w\s]', ' ', clean_title)
        keywords = ' '.join(clean_title.split()[:8])  # first 8 words
        try:
            resp = requests.get(
                "https://zenodo.org/api/records",
                params={"q": keywords, "size": 5},
                timeout=timeout,
            )
            if resp.ok:
                hits = resp.json().get("hits", {}).get("hits", [])
                # Only accept if title is a close match
                for h in hits:
                    z_title_raw = h.get("metadata", {}).get("title", "")
                    # Normalize both titles: strip HTML, LaTeX, punctuation
                    z_clean = re.sub(r'<[^>]+>', '', z_title_raw)
                    z_clean = re.sub(r'\$[^$]*\$', '', z_clean)  # LaTeX
                    z_clean = re.sub(r'[^\w\s]', ' ', z_clean)
                    # Check overlap of significant words
                    title_words = set(w.lower() for w in clean_title.split() if len(w) > 2)
                    z_words = set(w.lower() for w in z_clean.split() if len(w) > 2)
                    overlap = len(title_words & z_words)
                    if overlap >= min(3, len(title_words)):
                        record_url = f"https://doi.org/10.5281/zenodo.{h['id']}"
                        found_urls.append(record_url)
                        logger.debug(f"  Zenodo title search hit: {h['id']} (overlap={overlap})")
        except Exception as e:
            logger.debug(f"  Zenodo title search error: {e}")

    return found_urls


def _extract_urls_from_da_text(da_text: str) -> List[str]:
    """Extract repository/dataset URLs from Data Availability text."""
    urls = []
    seen = set()

    # Pattern 1: Full URLs (https://...)
    url_pattern = r'https?://[^\s<>")\]},;]+'
    for m in re.finditer(url_pattern, da_text):
        url = m.group(0).rstrip(".")
        if url not in seen:
            seen.add(url)
            # Only keep dataset-relevant URLs
            if any(d in url.lower() for d in DATASET_DOMAINS + ["doi.org"]):
                urls.append(url)

    # Pattern 2: DOI references like "10.5281/zenodo.12345" without https://
    doi_pattern = r'\b(10\.(?:' + '|'.join(
        p.replace("10.", "") for p in DATASET_DOI_PREFIXES
    ) + r')/[^\s<>")\]},;]+)'
    for m in re.finditer(doi_pattern, da_text):
        doi_url = f"https://doi.org/{m.group(1).rstrip('.')}"
        if doi_url not in seen:
            seen.add(doi_url)
            urls.append(doi_url)

    # Clean up HTML entities
    urls = [u.replace("&amp;", "&").replace("&#xA;", "").strip() for u in urls]

    return urls


# ===================================================================
# Main resolver
# ===================================================================

def resolve_dataset_links(
    paper: Dict[str, Any],
    http_config: Dict[str, Any],
    rate_limit_delay: float = 1.0,
    use_gpt: bool = False,
    gpt_call_fn=None,
    gpt_model: str = "gpt-5.4-mini",
) -> Dict[str, Any]:
    """
    Resolve all dataset links for a paper using multiple strategies.

    Returns:
        Dict with:
          - discovered_urls: list of all found URLs
          - sources: dict mapping source_method -> list of URLs
          - source_data_files: list of publisher-hosted files
          - data_availability_text: DA statement from paper
          - gpt_analysis: GPT's analysis of data availability
          - has_dataset_link: bool
    """
    doi = paper.get("doi", "")
    journal = paper.get("journal", "")
    paper_url = paper.get("paper_url", "")
    existing_urls = list(paper.get("dataset_url_candidates", []))

    sources = {}
    all_urls = set()
    source_data_files = []
    da_text = ""

    # Strategy 1: Existing URLs from Step 1
    if existing_urls:
        sources["step1_candidates"] = existing_urls
        all_urls.update(existing_urls)

    # Strategy 2: CrossRef relations
    if doi:
        time.sleep(rate_limit_delay * 0.5)
        crossref_urls = resolve_from_crossref(doi, http_config)
        if crossref_urls:
            sources["crossref_relations"] = crossref_urls
            all_urls.update(crossref_urls)

    # Strategy 3: Publisher-specific extraction (includes landing page)
    if doi:
        time.sleep(rate_limit_delay * 0.5)
        pub_result = resolve_from_publisher(doi, journal, paper_url, http_config)
        if pub_result["urls"]:
            sources["publisher_page"] = pub_result["urls"]
            all_urls.update(pub_result["urls"])
        source_data_files = pub_result.get("source_data_files", [])
        da_text = pub_result.get("data_availability_text", "")

    # Strategy 3b: Extract repository URLs from DA text
    if da_text:
        da_repo_urls = _extract_urls_from_da_text(da_text)
        if da_repo_urls:
            sources["da_text_urls"] = da_repo_urls
            all_urls.update(da_repo_urls)
            logger.debug(f"  Found {len(da_repo_urls)} URLs in DA text")

    # Check if DA text indicates "upon request" (no public data)
    da_upon_request = False
    if da_text:
        da_lower = da_text.lower()
        upon_request_phrases = [
            "upon request", "on request", "reasonable request",
            "from the corresponding author", "from the authors",
        ]
        if any(phrase in da_lower for phrase in upon_request_phrases):
            # Only flag as upon_request if there are NO external repo URLs
            has_external_repo = any(
                any(d in u for d in DATASET_DOMAINS) for u in all_urls
            )
            has_dataset_doi = any(
                any(p in u for p in DATASET_DOI_PREFIXES) for u in all_urls
            )
            if not has_external_repo and not has_dataset_doi:
                da_upon_request = True
                # Clear out false-positive source data files (e.g., SI PDFs mistaken as data)
                source_data_files = [
                    f for f in source_data_files
                    if f.get("source") not in ("nature_source_data", "nature_data_file")
                    or f.get("filename", "").endswith((".xlsx", ".csv", ".zip", ".h5"))
                ]

    # Strategy 3c: Zenodo search fallback (when no data found from other strategies)
    if not all_urls and not source_data_files:
        zenodo_hits = _search_zenodo_for_paper(paper, http_config)
        if zenodo_hits:
            sources["zenodo_search"] = zenodo_hits
            all_urls.update(zenodo_hits)
            logger.debug(f"  Zenodo search found {len(zenodo_hits)} URLs")

    # Strategy 4: GPT analysis of Data Availability
    gpt_analysis = {}
    if use_gpt and gpt_call_fn and (da_text or source_data_files or all_urls):
        gpt_analysis = gpt_analyze_data_availability(
            paper, da_text,
            pub_result if doi else {"publisher": "unknown", "source_data_files": [], "urls": []},
            gpt_call_fn, gpt_model,
        )
        # Add any new URLs from GPT
        for url in gpt_analysis.get("additional_urls", []):
            if url and url not in all_urls:
                all_urls.add(url)
                sources.setdefault("gpt_discovered", []).append(url)

    return {
        "discovered_urls": list(all_urls),
        "sources": sources,
        "source_data_files": source_data_files,
        "data_availability_text": da_text,
        "da_upon_request": da_upon_request,
        "gpt_analysis": gpt_analysis,
        "has_dataset_link": len(all_urls) > 0 or len(source_data_files) > 0,
    }
