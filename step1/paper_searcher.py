"""
Step 1 - Paper Searcher
========================
Searches multiple academic APIs to collect paper candidates.
APIs used:
  1. Semantic Scholar (free, rich metadata)
  2. OpenAlex (free, broad coverage, open access focus)
  3. CrossRef (DOI-centric, journal metadata)
  4. arXiv (preprints, cond-mat category)

Goal: maximize recall by combining results from all sources.
"""

import os
import re
import time
import random
import logging
import requests
from typing import List, Dict, Any, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Raw paper record (unified across APIs)
# ---------------------------------------------------------------------------

def _empty_raw_paper() -> Dict[str, Any]:
    return {
        "title": "",
        "abstract": "",
        "journal": "",
        "year": None,
        "doi": "",
        "paper_url": "",
        "authors": [],
        "source_api": "",
        "external_ids": {},
        "open_access_url": "",
        "citation_count": None,
        "concepts": [],
        "raw_metadata": {},
    }


# ===================================================================
# 1. Semantic Scholar
# ===================================================================

SEMANTIC_SCHOLAR_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_FIELDS = (
    "title,abstract,journal,year,externalIds,url,authors,citationCount,"
    "openAccessPdf,fieldsOfStudy,publicationTypes"
)


_s2_key_warned = False


def _semantic_scholar_headers() -> Dict[str, str]:
    global _s2_key_warned
    headers = {"User-Agent": "UC_LEAP_Step1/1.0"}
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()
    if api_key:
        headers["x-api-key"] = api_key
    elif not _s2_key_warned:
        logger.warning(
            "SEMANTIC_SCHOLAR_API_KEY not set. Rate limit is very low (~100 req/5min). "
            "Get a FREE key at https://www.semanticscholar.org/product/api#api-key-form "
            "and add it to your .env file."
        )
        _s2_key_warned = True
    return headers


def _retry_after_seconds(resp: requests.Response, fallback: int) -> int:
    retry_after = resp.headers.get("Retry-After")
    if retry_after:
        try:
            return max(int(retry_after), 1)
        except ValueError:
            pass
    return fallback


def search_semantic_scholar(
    query: str,
    max_results: int = 30,
    year_start: int = 2021,
    year_end: int = 2026,
    rate_delay: float = 1.0,
    retry_backoffs: Optional[List[int]] = None,
    max_attempts: int = 6,
) -> List[Dict[str, Any]]:
    """Search Semantic Scholar API."""
    papers = []
    offset = 0
    limit = min(max_results, 100)
    retry_backoffs = retry_backoffs or [15, 30, 60, 120, 180]
    headers = _semantic_scholar_headers()

    has_api_key = bool(os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip())
    pre_delay = rate_delay if has_api_key else max(rate_delay, 6.0)
    time.sleep(pre_delay)

    try:
        params = {
            "query": query,
            "offset": offset,
            "limit": limit,
            "fields": SEMANTIC_SCHOLAR_FIELDS,
            "year": f"{year_start}-{year_end}",
        }
        resp = None

        for attempt in range(max_attempts):
            resp = requests.get(
                SEMANTIC_SCHOLAR_SEARCH_URL,
                params=params,
                timeout=30,
                headers=headers,
            )

            if resp.status_code == 200:
                break

            if resp.status_code == 429:
                fallback = retry_backoffs[min(attempt, len(retry_backoffs) - 1)]
                backoff = _retry_after_seconds(resp, fallback)
                jitter = random.uniform(0, backoff * 0.3)
                wait = backoff + jitter
                logger.warning(
                    f"Semantic Scholar 429 for '{query[:60]}', "
                    f"waiting {wait:.0f}s (attempt {attempt + 1}/{max_attempts})..."
                )
                time.sleep(wait)
                continue

            if resp.status_code >= 500 and attempt < max_attempts - 1:
                fallback = retry_backoffs[min(attempt, len(retry_backoffs) - 1)]
                jitter = random.uniform(0, fallback * 0.3)
                wait = fallback + jitter
                logger.warning(
                    f"Semantic Scholar {resp.status_code} for '{query[:60]}', "
                    f"waiting {wait:.0f}s (attempt {attempt + 1}/{max_attempts})..."
                )
                time.sleep(wait)
                continue

            break

        if resp is None:
            raise RuntimeError("Semantic Scholar request did not produce a response")

        if resp.status_code == 429:
            logger.warning(
                f"Semantic Scholar rate limit persisted after {max_attempts} attempts "
                f"for query: {query[:60]}. Skipping — other APIs will compensate."
            )
            return papers

        if resp.status_code != 200:
            logger.warning(
                f"Semantic Scholar returned {resp.status_code} for query: {query[:60]}"
            )
            return papers

        data = resp.json()
        for item in data.get("data", []):
            p = _empty_raw_paper()
            p["title"] = item.get("title", "") or ""
            p["abstract"] = item.get("abstract", "") or ""
            journal_info = item.get("journal") or {}
            p["journal"] = journal_info.get("name", "") if isinstance(journal_info, dict) else str(journal_info)
            p["year"] = item.get("year")
            ext_ids = item.get("externalIds") or {}
            p["doi"] = ext_ids.get("DOI", "") or ""
            p["paper_url"] = item.get("url", "") or ""
            p["authors"] = [
                a.get("name", "") for a in (item.get("authors") or [])
            ]
            p["citation_count"] = item.get("citationCount")
            p["source_api"] = "semantic_scholar"
            p["external_ids"] = ext_ids
            oa_pdf = item.get("openAccessPdf") or {}
            p["open_access_url"] = oa_pdf.get("url", "") if isinstance(oa_pdf, dict) else ""
            p["concepts"] = item.get("fieldsOfStudy") or []
            p["raw_metadata"] = {
                "publicationTypes": item.get("publicationTypes") or [],
            }
            papers.append(p)

    except requests.RequestException as e:
        logger.error(f"Semantic Scholar request error: {e}")
    except Exception as e:
        logger.error(f"Semantic Scholar parse error: {e}")

    return papers


# ===================================================================
# 2. OpenAlex
# ===================================================================

OPENALEX_WORKS_URL = "https://api.openalex.org/works"


def search_openalex(
    query: str,
    max_results: int = 30,
    year_start: int = 2021,
    year_end: int = 2026,
    rate_delay: float = 0.2,
) -> List[Dict[str, Any]]:
    """Search OpenAlex API."""
    papers = []

    try:
        params = {
            "search": query,
            "filter": f"from_publication_date:{year_start}-01-01,to_publication_date:{year_end}-12-31",
            "per_page": min(max_results, 50),
            "sort": "relevance_score:desc",
            "mailto": "ucleap.research@gmail.com",
        }
        resp = requests.get(
            OPENALEX_WORKS_URL,
            params=params,
            timeout=30,
        )

        if resp.status_code != 200:
            logger.warning(
                f"OpenAlex returned {resp.status_code} for query: {query[:60]}"
            )
            return papers

        data = resp.json()
        for item in data.get("results", []):
            p = _empty_raw_paper()
            p["title"] = item.get("title", "") or ""

            # Abstract: OpenAlex returns inverted index
            abstract_inv = item.get("abstract_inverted_index")
            if abstract_inv and isinstance(abstract_inv, dict):
                p["abstract"] = _reconstruct_abstract(abstract_inv)

            # Journal / source
            primary_loc = item.get("primary_location") or {}
            source = primary_loc.get("source") or {}
            p["journal"] = source.get("display_name", "") or ""
            p["year"] = item.get("publication_year")
            p["doi"] = (item.get("doi") or "").replace("https://doi.org/", "")
            p["paper_url"] = item.get("id", "") or ""

            authorships = item.get("authorships") or []
            p["authors"] = [
                (a.get("author") or {}).get("display_name", "")
                for a in authorships[:20]
            ]
            p["citation_count"] = item.get("cited_by_count")
            p["source_api"] = "openalex"

            oa = item.get("open_access") or {}
            p["open_access_url"] = oa.get("oa_url", "") or ""

            concepts = item.get("concepts") or []
            p["concepts"] = [c.get("display_name", "") for c in concepts[:10]]

            p["raw_metadata"] = {
                "type": item.get("type", ""),
                "is_oa": oa.get("is_oa", False),
                "has_fulltext": item.get("has_fulltext", False),
            }
            papers.append(p)

    except requests.RequestException as e:
        logger.error(f"OpenAlex request error: {e}")
    except Exception as e:
        logger.error(f"OpenAlex parse error: {e}")

    time.sleep(rate_delay)
    return papers


def _reconstruct_abstract(inverted_index: Dict[str, List[int]]) -> str:
    """Reconstruct abstract from OpenAlex inverted index format."""
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return " ".join(w for _, w in word_positions)


# ===================================================================
# 3. CrossRef
# ===================================================================

CROSSREF_WORKS_URL = "https://api.crossref.org/works"


def search_crossref(
    query: str,
    max_results: int = 20,
    year_start: int = 2021,
    year_end: int = 2026,
    rate_delay: float = 0.5,
) -> List[Dict[str, Any]]:
    """Search CrossRef API."""
    papers = []

    try:
        params = {
            "query": query,
            "rows": min(max_results, 50),
            "filter": f"from-pub-date:{year_start},until-pub-date:{year_end}",
            "sort": "relevance",
            "order": "desc",
            "mailto": "ucleap.research@gmail.com",
        }
        resp = requests.get(
            CROSSREF_WORKS_URL,
            params=params,
            timeout=30,
        )

        if resp.status_code != 200:
            logger.warning(
                f"CrossRef returned {resp.status_code} for query: {query[:60]}"
            )
            return papers

        data = resp.json()
        items = data.get("message", {}).get("items", [])

        for item in items:
            p = _empty_raw_paper()

            title_list = item.get("title") or []
            p["title"] = title_list[0] if title_list else ""

            abstract = item.get("abstract", "") or ""
            # CrossRef abstract sometimes has XML tags
            p["abstract"] = re.sub(r"<[^>]+>", "", abstract)

            container = item.get("container-title") or []
            p["journal"] = container[0] if container else ""

            published = item.get("published") or item.get("published-print") or {}
            date_parts = published.get("date-parts", [[None]])[0]
            p["year"] = date_parts[0] if date_parts else None

            p["doi"] = item.get("DOI", "") or ""
            p["paper_url"] = item.get("URL", "") or ""

            authors_raw = item.get("author") or []
            p["authors"] = [
                f"{a.get('given', '')} {a.get('family', '')}".strip()
                for a in authors_raw[:20]
            ]
            p["citation_count"] = item.get("is-referenced-by-count")
            p["source_api"] = "crossref"

            # Links might contain dataset references
            links = item.get("link") or []
            p["raw_metadata"] = {
                "type": item.get("type", ""),
                "subject": item.get("subject") or [],
                "links": [l.get("URL", "") for l in links],
                "license": [l.get("URL", "") for l in (item.get("license") or [])],
            }
            papers.append(p)

    except requests.RequestException as e:
        logger.error(f"CrossRef request error: {e}")
    except Exception as e:
        logger.error(f"CrossRef parse error: {e}")

    time.sleep(rate_delay)
    return papers


# ===================================================================
# 4. arXiv
# ===================================================================

ARXIV_API_URL = "http://export.arxiv.org/api/query"


def search_arxiv(
    query: str,
    max_results: int = 20,
    year_start: int = 2021,
    year_end: int = 2026,
    rate_delay: float = 3.0,
) -> List[Dict[str, Any]]:
    """Search arXiv API (Atom feed). Filters to cond-mat category."""
    papers = []

    try:
        # arXiv search: combine query words with AND + category filter
        # Each word gets its own all: prefix joined by AND
        words = query.strip().split()
        if len(words) > 1:
            query_part = " AND ".join(f"all:{w}" for w in words)
        else:
            query_part = f"all:{words[0]}"
        search_query = f"{query_part} AND cat:cond-mat.*"
        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": min(max_results, 50),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        resp = requests.get(ARXIV_API_URL, params=params, timeout=30)

        if resp.status_code != 200:
            logger.warning(
                f"arXiv returned {resp.status_code} for query: {query[:60]}"
            )
            return papers

        # Parse Atom XML
        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.content)
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

        for entry in root.findall("atom:entry", ns):
            p = _empty_raw_paper()

            p["title"] = (entry.findtext("atom:title", "", ns) or "").strip().replace("\n", " ")
            p["abstract"] = (entry.findtext("atom:summary", "", ns) or "").strip().replace("\n", " ")

            # Year from published date
            published = entry.findtext("atom:published", "", ns)
            if published and len(published) >= 4:
                try:
                    pub_year = int(published[:4])
                    if pub_year < year_start or pub_year > year_end:
                        continue
                    p["year"] = pub_year
                except ValueError:
                    pass

            # Links
            for link in entry.findall("atom:link", ns):
                href = link.get("href", "")
                link_type = link.get("type", "")
                if link.get("rel") == "alternate":
                    p["paper_url"] = href
                elif "pdf" in link_type or href.endswith(".pdf"):
                    p["open_access_url"] = href

            # DOI
            doi_elem = entry.find("arxiv:doi", ns)
            if doi_elem is not None and doi_elem.text:
                p["doi"] = doi_elem.text.strip()

            # Authors
            for author in entry.findall("atom:author", ns):
                name = author.findtext("atom:name", "", ns)
                if name:
                    p["authors"].append(name)

            # Categories
            categories = []
            for cat in entry.findall("atom:category", ns):
                term = cat.get("term", "")
                if term:
                    categories.append(term)
            p["concepts"] = categories

            p["source_api"] = "arxiv"
            p["journal"] = "arXiv preprint"

            # arXiv ID
            arxiv_id = entry.findtext("atom:id", "", ns)
            if arxiv_id:
                p["external_ids"]["arxiv"] = arxiv_id.split("/abs/")[-1] if "/abs/" in arxiv_id else arxiv_id

            papers.append(p)

    except requests.RequestException as e:
        logger.error(f"arXiv request error: {e}")
    except Exception as e:
        logger.error(f"arXiv parse error: {e}")

    time.sleep(rate_delay)
    return papers


# ===================================================================
# 5. Europe PMC
# ===================================================================

EUROPE_PMC_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def search_europe_pmc(
    query: str,
    max_results: int = 30,
    year_start: int = 2021,
    year_end: int = 2026,
    rate_delay: float = 0.3,
) -> List[Dict[str, Any]]:
    """Search Europe PMC API (free, no key required)."""
    papers = []

    try:
        params = {
            "query": f"{query} (PUB_YEAR:[{year_start} TO {year_end}])",
            "format": "json",
            "pageSize": min(max_results, 25),
            "resultType": "core",
            "sort": "RELEVANCE",
        }
        resp = requests.get(
            EUROPE_PMC_SEARCH_URL,
            params=params,
            timeout=30,
        )

        if resp.status_code != 200:
            logger.warning(
                f"Europe PMC returned {resp.status_code} for query: {query[:60]}"
            )
            return papers

        data = resp.json()
        for item in data.get("resultList", {}).get("result", []):
            p = _empty_raw_paper()
            p["title"] = item.get("title", "") or ""
            p["abstract"] = item.get("abstractText", "") or ""
            p["journal"] = item.get("journalTitle", "") or ""
            p["year"] = item.get("pubYear")
            if p["year"]:
                try:
                    p["year"] = int(p["year"])
                except (ValueError, TypeError):
                    p["year"] = None
            p["doi"] = item.get("doi", "") or ""
            pmid = item.get("pmid", "")
            pmcid = item.get("pmcid", "")
            p["paper_url"] = (
                f"https://europepmc.org/article/MED/{pmid}" if pmid
                else f"https://europepmc.org/article/PMC/{pmcid}" if pmcid
                else ""
            )
            p["authors"] = []
            author_list = item.get("authorList", {}).get("author", [])
            for a in author_list:
                full = a.get("fullName", "")
                if full:
                    p["authors"].append(full)
            p["citation_count"] = item.get("citedByCount")
            p["source_api"] = "europe_pmc"
            p["external_ids"] = {}
            if pmid:
                p["external_ids"]["pmid"] = pmid
            if pmcid:
                p["external_ids"]["pmcid"] = pmcid
            if p["doi"]:
                p["external_ids"]["DOI"] = p["doi"]
            p["open_access_url"] = ""
            if item.get("isOpenAccess") == "Y" and pmcid:
                p["open_access_url"] = f"https://europepmc.org/article/PMC/{pmcid}"
            p["concepts"] = item.get("meshHeadingList", {}).get("meshHeading", []) if isinstance(item.get("meshHeadingList"), dict) else []
            p["raw_metadata"] = {
                "publicationTypes": [item.get("pubType", "")],
            }
            papers.append(p)

    except requests.RequestException as e:
        logger.error(f"Europe PMC request error: {e}")
    except Exception as e:
        logger.error(f"Europe PMC parse error: {e}")

    time.sleep(rate_delay)
    return papers


# ===================================================================
# Unified search dispatcher
# ===================================================================

def search_all_apis(
    queries_by_api: Dict[str, List[str]],
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Run searches across all APIs and return combined raw results.

    Args:
        queries_by_api: dict mapping API name -> list of query strings
        config: search configuration dict

    Returns:
        List of raw paper records from all APIs.
    """
    all_papers = []
    year_start = config.get("year_range", {}).get("start", 2021)
    year_end = config.get("year_range", {}).get("end", 2026)
    max_per_query = config.get("max_results_per_query", 30)
    rate_limits = config.get("rate_limits", {})
    retry_policy = config.get("retry_policy", {})

    api_functions = {
        "semantic_scholar": search_semantic_scholar,
        "openalex": search_openalex,
        "crossref": search_crossref,
        "arxiv": search_arxiv,
        "europe_pmc": search_europe_pmc,
    }

    enabled_apis = config.get("enabled_apis", {})

    for api_name, queries in queries_by_api.items():
        # Skip disabled APIs
        if not enabled_apis.get(api_name, True):
            logger.info(f"Skipping {api_name} (disabled in config)")
            continue

        search_fn = api_functions.get(api_name)
        if not search_fn:
            logger.warning(f"Unknown API: {api_name}")
            continue

        rate_delay = rate_limits.get(api_name, 1.0)
        logger.info(f"Searching {api_name} with {len(queries)} queries...")

        # Limit queries per API from config (or defaults)
        config_max_queries = config.get("max_queries_per_api", {})
        default_limits = {
            "semantic_scholar": 12,
            "openalex": 20,
            "crossref": 12,
            "arxiv": 15,
            "europe_pmc": 12,
        }
        query_limit = config_max_queries.get(api_name, default_limits.get(api_name, 15))
        selected_queries = queries[:query_limit]

        consecutive_empty = 0
        for i, query in enumerate(selected_queries):
            # If Semantic Scholar gave 0 results twice in a row, likely rate-limited — skip rest
            if api_name == "semantic_scholar" and consecutive_empty >= 2:
                logger.warning(
                    f"  [{api_name}] Skipping remaining {len(selected_queries) - i} queries "
                    f"(consecutive empty results — likely rate-limited). "
                    f"OpenAlex/CrossRef/arXiv will compensate."
                )
                break

            logger.info(
                f"  [{api_name}] Query {i+1}/{len(selected_queries)}: {query[:60]}..."
            )
            try:
                if api_name == "semantic_scholar":
                    results = search_fn(
                        query=query,
                        max_results=max_per_query,
                        year_start=year_start,
                        year_end=year_end,
                        rate_delay=rate_delay,
                        retry_backoffs=retry_policy.get(
                            "semantic_scholar_backoffs", [15, 30, 60, 120, 180]
                        ),
                        max_attempts=retry_policy.get(
                            "semantic_scholar_max_attempts", 6
                        ),
                    )
                else:
                    results = search_fn(
                        query=query,
                        max_results=max_per_query,
                        year_start=year_start,
                        year_end=year_end,
                        rate_delay=rate_delay,
                    )

                if api_name == "semantic_scholar" and len(results) == 0:
                    consecutive_empty += 1
                else:
                    consecutive_empty = 0

                all_papers.extend(results)
                logger.info(f"    -> {len(results)} results")
            except Exception as e:
                logger.error(f"  [{api_name}] Error for query '{query[:40]}': {e}")
                if api_name == "semantic_scholar":
                    consecutive_empty += 1

    logger.info(f"Total raw results from all APIs: {len(all_papers)}")
    return all_papers
