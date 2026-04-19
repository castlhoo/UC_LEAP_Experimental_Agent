"""
Step 4 - PDF Downloader
=========================
Download paper PDFs via Unpaywall, publisher URLs, or DOI redirects.
"""

import os
import logging
from typing import Dict, Any, Optional

from pdf_utils import download_paper_pdf_bytes

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

    # Skip if already downloaded in Step 4
    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000:
        logger.info(f"    PDF already exists ({os.path.getsize(pdf_path)//1024}KB)")
        return pdf_path

    # Reuse PDF from Step 3 if available
    download_dir = paper.get("download_dir", "")
    if download_dir:
        step3_pdf = os.path.join(download_dir, "paper.pdf")
        if os.path.exists(step3_pdf) and os.path.getsize(step3_pdf) > 1000:
            import shutil
            shutil.copy2(step3_pdf, pdf_path)
            logger.info(f"    PDF reused from Step 3 ({os.path.getsize(step3_pdf)//1024}KB)")
            return pdf_path

    pdf_config = config.get("pdf", {})
    http_config = config.get("http", {})
    pdf_bytes, source = download_paper_pdf_bytes(
        paper=paper,
        http_config=http_config,
        unpaywall_email=pdf_config.get("unpaywall_email", "ucleap@example.com"),
        use_unpaywall=pdf_config.get("use_unpaywall", True),
    )

    if not pdf_bytes:
        logger.warning("    Could not download PDF from any source")
        return None

    # Save
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    size_kb = len(pdf_bytes) // 1024
    logger.info(f"    PDF downloaded ({size_kb}KB) via {source or 'unknown'}")
    return pdf_path
