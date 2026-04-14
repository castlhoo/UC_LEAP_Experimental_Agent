"""
Step 3 - PDF Reader
=====================
Download paper PDF and extract text for GPT analysis.
Uses PyMuPDF (fitz) for text extraction.
"""

import os
import re
import logging
from typing import Dict, Any, Optional

import fitz  # PyMuPDF
from pdf_utils import download_paper_pdf_bytes

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

    pdf_bytes, source = download_paper_pdf_bytes(
        paper=paper,
        http_config=http_config,
        unpaywall_email=http_config.get("unpaywall_email", "uc_leap@research.edu"),
        use_unpaywall=http_config.get("use_unpaywall", True),
    )

    if not pdf_bytes:
        logger.warning("  Could not download PDF")
        return None

    # Save PDF
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)
    logger.info(f"  PDF downloaded ({len(pdf_bytes)//1024}KB) via {source or 'unknown'}")

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

