"""
Step 4 - PDF Downloader
=========================
Download paper PDFs via Unpaywall, publisher URLs, or DOI redirects.
"""

import os
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def download_paper_pdf(
    paper: Dict[str, Any],
    pdf_dir: str,
    config: Dict[str, Any],
) -> Optional[str]:
    """
    Download paper PDF to pdf_dir/paper.pdf.

    Args:
        paper: Paper metadata with 'doi', 'paper_url'
        pdf_dir: Directory to save PDF
        config: Step 4 config dict

    Returns:
        Path to saved PDF, or None if failed.
    """
    doi = paper.get("doi", "")
    if not doi:
        logger.warning("    No DOI — cannot download PDF")
        return None

    pdf_path = os.path.join(pdf_dir, "paper.pdf")

    # Skip if already downloaded
    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000:
        logger.info(f"    PDF already exists ({os.path.getsize(pdf_path)//1024}KB)")
        return pdf_path

    pdf_config = config.get("pdf", {})
    http_config = config.get("http", {})
    timeout = http_config.get("timeout", 60)
    ua = http_config.get("user_agent", "UC_LEAP/1.0")
    headers = {"User-Agent": ua}

    pdf_bytes = None

    # Strategy 1: Unpaywall
    if pdf_config.get("use_unpaywall", True):
        email = pdf_config.get("unpaywall_email", "ucleap@example.com")
        pdf_bytes = _try_unpaywall(doi, email, headers, timeout)

    # Strategy 2: Publisher direct URL
    if not pdf_bytes:
        pdf_bytes = _try_publisher_pdf(doi, headers, timeout)

    # Strategy 3: DOI redirect
    if not pdf_bytes:
        pdf_bytes = _try_doi_redirect(doi, headers, timeout)

    if not pdf_bytes:
        logger.warning("    Could not download PDF from any source")
        return None

    # Save
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    size_kb = len(pdf_bytes) // 1024
    logger.info(f"    PDF downloaded ({size_kb}KB) via publisher")
    return pdf_path


def _try_unpaywall(doi: str, email: str, headers: dict, timeout: int) -> Optional[bytes]:
    """Try Unpaywall API for open-access PDF."""
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
    except Exception as e:
        logger.debug(f"    Unpaywall failed: {e}")
    return None


def _try_publisher_pdf(doi: str, headers: dict, timeout: int) -> Optional[bytes]:
    """Try direct publisher PDF URL patterns."""
    urls_to_try = []

    # Nature
    if "10.1038/" in doi:
        article_id = doi.split("/")[-1]
        urls_to_try.append(f"https://www.nature.com/articles/{article_id}.pdf")

    # Science
    if "10.1126/" in doi:
        urls_to_try.append(f"https://www.science.org/doi/pdf/{doi}")

    # APS (PRL, PRB, PRX, etc.)
    if "10.1103/" in doi:
        for journal in ["prl", "prb", "prx", "prresearch", "prmaterials"]:
            urls_to_try.append(f"https://journals.aps.org/{journal}/pdf/{doi}")

    for url in urls_to_try:
        try:
            resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            if resp.status_code == 200 and _is_pdf(resp):
                return resp.content
        except Exception:
            continue
    return None


def _try_doi_redirect(doi: str, headers: dict, timeout: int) -> Optional[bytes]:
    """Try following DOI redirect to find PDF."""
    try:
        url = f"https://doi.org/{doi}"
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200 and _is_pdf(resp):
            return resp.content
    except Exception:
        pass
    return None


def _is_pdf(resp: requests.Response) -> bool:
    """Check if response is a PDF."""
    ct = resp.headers.get("content-type", "")
    if "pdf" in ct:
        return True
    if resp.content[:5] == b"%PDF-":
        return True
    return False
