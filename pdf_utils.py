"""
Shared PDF download utilities for Step 3 and Step 4.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


def download_paper_pdf_bytes(
    paper: Dict[str, Any],
    http_config: Dict[str, Any],
    unpaywall_email: str = "uc_leap@research.edu",
    use_unpaywall: bool = True,
) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Download a paper PDF using the shared Step 3-preferred strategy.

    Returns:
        (pdf_bytes, source_name)
    """
    doi = paper.get("doi", "")
    if not doi:
        return None, None

    timeout = http_config.get("timeout", 60)
    ua = http_config.get("user_agent", "UC_LEAP/1.0")
    headers = {"User-Agent": ua}

    for item in paper.get("paper_pdf_urls", []):
        pdf_url = item.get("url", "") if isinstance(item, dict) else item
        pdf_bytes = _try_direct_pdf_url(pdf_url, headers, timeout)
        if pdf_bytes:
            return pdf_bytes, "step2_paper_pdf_url"

    resolved_pdf_url = paper.get("resolved_paper_pdf_url", "")
    if resolved_pdf_url:
        pdf_bytes = _try_direct_pdf_url(resolved_pdf_url, headers, timeout)
        if pdf_bytes:
            return pdf_bytes, paper.get("paper_pdf_source", "step2_resolved_pdf")

    arxiv_id = (paper.get("external_ids") or {}).get("arxiv", "") or (
        paper.get("external_ids") or {}
    ).get("ArXiv", "")
    if arxiv_id:
        pdf_bytes = _try_arxiv_pdf(arxiv_id, headers, timeout)
        if pdf_bytes:
            return pdf_bytes, "arxiv"

    if use_unpaywall:
        pdf_bytes = _try_unpaywall(doi, unpaywall_email, headers, timeout)
        if pdf_bytes:
            return pdf_bytes, "unpaywall"

    pdf_bytes = _try_publisher_pdf(doi, headers, timeout)
    if pdf_bytes:
        return pdf_bytes, "publisher"

    pdf_bytes = _try_semantic_scholar_pdf(doi, headers, timeout)
    if pdf_bytes:
        return pdf_bytes, "semantic_scholar"

    pdf_bytes = _try_doi_redirect(doi, headers, timeout)
    if pdf_bytes:
        return pdf_bytes, "doi_redirect"

    return None, None


def resolve_paper_pdf_url(
    paper: Dict[str, Any],
    http_config: Dict[str, Any],
    unpaywall_email: str = "uc_leap@research.edu",
    use_unpaywall: bool = True,
) -> Dict[str, Any]:
    """
    Resolve and lightly validate a paper PDF URL without downloading the full PDF.

    Returns metadata for Step 2 to pass downstream. Full PDF download/text
    extraction remains Step 3's job.
    """
    doi = paper.get("doi", "")
    timeout = http_config.get("timeout", 60)
    ua = http_config.get("user_agent", "UC_LEAP/1.0")
    headers = {"User-Agent": ua}

    candidates: List[Dict[str, str]] = []

    for url in paper.get("paper_pdf_urls", []):
        if isinstance(url, dict):
            raw_url = url.get("url", "")
            source = url.get("source", "step2_paper_pdf_url")
        else:
            raw_url = str(url)
            source = "step2_paper_pdf_url"
        if raw_url:
            candidates.append({"url": raw_url, "source": source})

    arxiv_id = (paper.get("external_ids") or {}).get("arxiv", "") or (
        paper.get("external_ids") or {}
    ).get("ArXiv", "")
    if arxiv_id:
        clean_id = arxiv_id.strip().replace("arXiv:", "").replace("arxiv:", "")
        candidates.append({"url": f"https://arxiv.org/pdf/{clean_id}.pdf", "source": "arxiv"})

    if use_unpaywall and doi:
        unpaywall_url = _resolve_unpaywall_pdf_url(
            doi, unpaywall_email, headers, timeout
        )
        if unpaywall_url:
            candidates.append({"url": unpaywall_url, "source": "unpaywall"})

    if doi:
        for url in _publisher_pdf_url_candidates(doi):
            candidates.append({"url": url, "source": "publisher_generated"})

        semantic_url = _resolve_semantic_scholar_pdf_url(doi, headers, timeout)
        if semantic_url:
            candidates.append({"url": semantic_url, "source": "semantic_scholar"})

        candidates.append({"url": f"https://doi.org/{doi}", "source": "doi_redirect"})

    seen = set()
    checked: List[Dict[str, Any]] = []
    for candidate in candidates:
        url = candidate["url"]
        if not url or url in seen:
            continue
        seen.add(url)
        validated = _validate_pdf_url(url, headers, timeout)
        checked.append({
            "url": url,
            "source": candidate["source"],
            "validated": bool(validated),
            "final_url": validated or "",
        })
        if validated:
            return {
                "paper_pdf_urls": checked,
                "resolved_paper_pdf_url": validated,
                "paper_pdf_source": candidate["source"],
                "pdf_resolution_status": "found",
            }

    return {
        "paper_pdf_urls": checked,
        "resolved_paper_pdf_url": "",
        "paper_pdf_source": "",
        "pdf_resolution_status": "not_found",
    }


def _try_direct_pdf_url(url: str, headers: dict, timeout: int) -> Optional[bytes]:
    try:
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200 and _is_pdf(resp):
            return resp.content
    except Exception as e:
        logger.debug(f"Direct PDF URL failed: {e}")
    return None


def _validate_pdf_url(url: str, headers: dict, timeout: int) -> Optional[str]:
    """Return final URL if a request looks like a PDF, without reading the full body."""
    try:
        resp = requests.get(
            url,
            headers=headers,
            timeout=timeout,
            allow_redirects=True,
            stream=True,
        )
        if resp.status_code != 200:
            resp.close()
            return None

        content_type = resp.headers.get("content-type", "").lower()
        if "pdf" in content_type or resp.url.lower().split("?")[0].endswith(".pdf"):
            final_url = resp.url
            resp.close()
            return final_url

        first = b""
        try:
            first = next(resp.iter_content(chunk_size=5), b"")
        finally:
            resp.close()
        if first == b"%PDF-":
            return resp.url
    except Exception as e:
        logger.debug(f"PDF URL validation failed for {url}: {e}")
    return None


def _try_arxiv_pdf(arxiv_id: str, headers: dict, timeout: int) -> Optional[bytes]:
    try:
        clean_id = arxiv_id.strip().replace("arXiv:", "").replace("arxiv:", "")
        url = f"https://arxiv.org/pdf/{clean_id}.pdf"
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200 and _is_pdf(resp):
            return resp.content
    except Exception as e:
        logger.debug(f"arXiv PDF failed: {e}")
    return None


def _try_unpaywall(
    doi: str,
    email: str,
    headers: dict,
    timeout: int,
) -> Optional[bytes]:
    try:
        url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return None

        data = resp.json()
        oa = data.get("best_oa_location") or {}
        pdf_url = oa.get("url_for_pdf")
        if not pdf_url:
            return None

        pdf_resp = requests.get(pdf_url, headers=headers, timeout=timeout)
        if pdf_resp.status_code == 200 and _is_pdf(pdf_resp):
            return pdf_resp.content
        if pdf_resp.status_code == 200 and len(pdf_resp.content) > 10000:
            return pdf_resp.content
    except Exception as e:
        logger.debug(f"Unpaywall failed: {e}")
    return None


def _resolve_unpaywall_pdf_url(
    doi: str,
    email: str,
    headers: dict,
    timeout: int,
) -> Optional[str]:
    try:
        url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return None
        data = resp.json()
        oa = data.get("best_oa_location") or {}
        return oa.get("url_for_pdf") or ""
    except Exception as e:
        logger.debug(f"Unpaywall URL resolve failed: {e}")
    return None


def _publisher_pdf_url_candidates(doi: str) -> List[str]:
    urls_to_try = []

    if "10.1038/" in doi:
        article_id = doi.split("/")[-1]
        urls_to_try.append(f"https://www.nature.com/articles/{article_id}.pdf")
    if "10.1126/" in doi:
        urls_to_try.append(f"https://www.science.org/doi/pdf/{doi}")
    if "10.1103/" in doi:
        for journal in ("prl", "prb", "prx", "prapplied", "prmaterials", "prresearch", "rmp"):
            urls_to_try.append(f"https://journals.aps.org/{journal}/pdf/{doi}")
    if "10.1002/" in doi:
        urls_to_try.append(f"https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}")
    if "10.1021/" in doi:
        urls_to_try.append(f"https://pubs.acs.org/doi/pdf/{doi}")
    if "10.1088/" in doi:
        urls_to_try.append(f"https://iopscience.iop.org/article/{doi}/pdf")
    if "10.1016/" in doi:
        urls_to_try.append(
            f"https://www.sciencedirect.com/science/article/pii/{doi.split('/')[-1]}/pdfft"
        )
    if "10.1007/" in doi:
        urls_to_try.append(f"https://link.springer.com/content/pdf/{doi}.pdf")
    if "10.1080/" in doi:
        urls_to_try.append(f"https://www.tandfonline.com/doi/pdf/{doi}")
    if "10.1039/" in doi:
        urls_to_try.append(f"https://pubs.rsc.org/en/content/articlepdf/{doi}")
    if "10.3390/" in doi:
        urls_to_try.append(f"https://www.mdpi.com/{doi.split('10.3390/')[-1]}/pdf")
    if "10.1063/" in doi:
        urls_to_try.append(f"https://pubs.aip.org/aip/apl/article-pdf/doi/{doi}")
        urls_to_try.append(f"https://pubs.aip.org/aip/jap/article-pdf/doi/{doi}")
    if "10.1073/" in doi:
        urls_to_try.append(f"https://www.pnas.org/doi/pdf/{doi}")
    if "10.48550/" in doi:
        arxiv_id = doi.split("arXiv.")[-1] if "arXiv." in doi else doi.split("/")[-1]
        urls_to_try.append(f"https://arxiv.org/pdf/{arxiv_id}.pdf")
    urls_to_try.append(f"https://doi.org/{doi}")
    return urls_to_try


def _try_publisher_pdf(doi: str, headers: dict, timeout: int) -> Optional[bytes]:
    urls_to_try = _publisher_pdf_url_candidates(doi)

    for url in urls_to_try:
        try:
            resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            if resp.status_code == 200 and _is_pdf(resp):
                return resp.content
        except Exception:
            continue
    return None


def _try_semantic_scholar_pdf(doi: str, headers: dict, timeout: int) -> Optional[bytes]:
    try:
        url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=openAccessPdf"
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return None
        data = resp.json()
        pdf_url = (data.get("openAccessPdf") or {}).get("url")
        if not pdf_url:
            return None
        pdf_resp = requests.get(pdf_url, headers=headers, timeout=timeout)
        if pdf_resp.status_code == 200 and _is_pdf(pdf_resp):
            return pdf_resp.content
    except Exception:
        pass
    return None


def _resolve_semantic_scholar_pdf_url(
    doi: str, headers: dict, timeout: int
) -> Optional[str]:
    try:
        url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=openAccessPdf"
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return None
        data = resp.json()
        return (data.get("openAccessPdf") or {}).get("url") or ""
    except Exception as e:
        logger.debug(f"Semantic Scholar URL resolve failed: {e}")
    return None


def _try_doi_redirect(doi: str, headers: dict, timeout: int) -> Optional[bytes]:
    try:
        url = f"https://doi.org/{doi}"
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200 and _is_pdf(resp):
            return resp.content
    except Exception:
        pass
    return None


def _is_pdf(resp: requests.Response) -> bool:
    ct = resp.headers.get("content-type", "")
    if "pdf" in ct:
        return True
    return resp.content[:5] == b"%PDF-"
