"""
Step 3 - PDF Reader
=====================
Download paper PDF and extract text for GPT analysis.
Uses PyMuPDF (fitz) for text extraction.
"""

import os
import re
import logging
import requests
from typing import Dict, Any, Optional

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Max characters to send to GPT (roughly ~30 pages of text)
MAX_TEXT_CHARS = 80000


def download_and_extract_text(
    paper: Dict[str, Any],
    download_dir: str,
    http_config: Dict[str, Any],
) -> Optional[str]:
    """
    Download paper PDF and extract text.

    Args:
        paper: Paper metadata with 'doi', 'paper_url'
        download_dir: Directory to save PDF
        http_config: HTTP settings (timeout, user_agent)

    Returns:
        Extracted text string, or None if failed.
    """
    doi = paper.get("doi", "")
    if not doi:
        logger.warning("  No DOI — cannot download PDF")
        return None

    os.makedirs(download_dir, exist_ok=True)
    pdf_path = os.path.join(download_dir, "paper.pdf")

    # Skip download if already exists
    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000:
        logger.info("  PDF already downloaded, extracting text...")
        return _extract_text(pdf_path)

    # Try downloading
    timeout = http_config.get("timeout", 60)
    ua = http_config.get("user_agent", "UC_LEAP/1.0")
    headers = {"User-Agent": ua}

    pdf_bytes = None

    # Strategy 1: Unpaywall (open access PDF)
    pdf_bytes = _try_unpaywall(doi, headers, timeout)

    # Strategy 2: Publisher direct URL
    if not pdf_bytes:
        pdf_bytes = _try_publisher_pdf(doi, headers, timeout)

    if not pdf_bytes:
        logger.warning("  Could not download PDF")
        return None

    # Save PDF
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)
    logger.info(f"  PDF downloaded ({len(pdf_bytes)//1024}KB)")

    return _extract_text(pdf_path)


def _extract_text(pdf_path: str) -> Optional[str]:
    """Extract text from PDF using PyMuPDF."""
    try:
        doc = fitz.open(pdf_path)
        pages = []
        for page in doc:
            text = page.get_text()
            if text.strip():
                pages.append(text)
        doc.close()

        full_text = "\n\n".join(pages)

        if len(full_text) < 100:
            logger.warning("  PDF text extraction yielded very little text")
            return None

        # Truncate if too long
        if len(full_text) > MAX_TEXT_CHARS:
            full_text = full_text[:MAX_TEXT_CHARS] + "\n\n[... truncated ...]"

        logger.info(f"  Extracted {len(full_text)} chars from PDF ({len(pages)} pages)")
        return full_text

    except Exception as e:
        logger.warning(f"  PDF text extraction failed: {e}")
        return None


def _try_unpaywall(doi: str, headers: dict, timeout: int) -> Optional[bytes]:
    """Try Unpaywall API for open-access PDF."""
    try:
        url = f"https://api.unpaywall.org/v2/{doi}?email=uc_leap@research.edu"
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return None

        data = resp.json()
        oa = data.get("best_oa_location") or {}
        pdf_url = oa.get("url_for_pdf")
        if not pdf_url:
            return None

        pdf_resp = requests.get(pdf_url, headers=headers, timeout=timeout)
        if pdf_resp.status_code == 200 and pdf_resp.headers.get("content-type", "").startswith("application/pdf"):
            return pdf_resp.content
        # Sometimes PDF URL returns HTML redirect
        if pdf_resp.status_code == 200 and len(pdf_resp.content) > 10000:
            return pdf_resp.content

    except Exception as e:
        logger.debug(f"  Unpaywall failed: {e}")
    return None


def _try_publisher_pdf(doi: str, headers: dict, timeout: int) -> Optional[bytes]:
    """Try direct publisher PDF URL patterns."""
    doi_lower = doi.lower()

    urls_to_try = []

    # Nature
    if "10.1038/" in doi:
        article_id = doi.split("/")[-1]
        urls_to_try.append(f"https://www.nature.com/articles/{article_id}.pdf")

    # Science
    if "10.1126/" in doi:
        urls_to_try.append(f"https://www.science.org/doi/pdf/{doi}")

    # APS
    if "10.1103/" in doi:
        urls_to_try.append(f"https://journals.aps.org/prl/pdf/{doi}")
        urls_to_try.append(f"https://journals.aps.org/prb/pdf/{doi}")
        urls_to_try.append(f"https://journals.aps.org/prx/pdf/{doi}")

    # Generic DOI redirect
    urls_to_try.append(f"https://doi.org/{doi}")

    for url in urls_to_try:
        try:
            resp = requests.get(
                url, headers=headers, timeout=timeout, allow_redirects=True
            )
            ct = resp.headers.get("content-type", "")
            if resp.status_code == 200 and ("pdf" in ct or resp.content[:5] == b"%PDF-"):
                return resp.content
        except Exception:
            continue

    return None
