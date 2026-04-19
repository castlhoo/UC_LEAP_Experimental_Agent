"""
Step 3 - Paper Analysis
=======================
Runs Prompt A only:
  Phase 1: Load Step 2 papers with confirmed datasets
  Phase 2: Download/extract paper PDF text
  Phase 3: Analyze paper text with Prompt A
  Phase 4: Save analyzed and skipped records
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List

import yaml

from utils import save_with_latest
from step3.gpt_client import analyze_paper_text
from step3.pdf_reader import download_and_extract_text

logger = logging.getLogger(__name__)


def _load_config() -> Dict[str, Any]:
    """Load Step 3 configuration."""
    config_path = os.path.join(
        os.path.dirname(__file__), "config", "step3_config.yaml"
    )
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_step3() -> Dict[str, Any]:
    """Execute Prompt A paper analysis for papers with confirmed datasets and PDFs."""
    config = _load_config()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    gpt_config = config.get("gpt", {})
    use_gpt = gpt_config.get("enabled", True)
    gpt_model = gpt_config.get("model", "gpt-5.4-mini")
    if not use_gpt:
        logger.warning("Step 3 requires GPT for Prompt A; no paper analysis will run.")

    http_config = config.get("http", {})
    rate_limit_delay = http_config.get("rate_limit_delay", 1.0)

    # ---- Phase 1: Load Step 2 results ----
    logger.info("=" * 60)
    logger.info("Phase 1: Loading Step 2 dataset-presence results...")

    input_path = os.path.join(project_root, config.get("input_file", ""))
    with open(input_path, "r", encoding="utf-8") as f:
        step2_data = json.load(f)

    include_statuses = set(config.get("include_statuses", ["verified", "source_data_found"]))
    dataset_candidates = [
        p for p in step2_data.get("papers", [])
        if p.get("dataset_status") in include_statuses
    ]
    candidates = [
        p for p in dataset_candidates
        if p.get("pdf_resolution_status") == "found"
        and p.get("resolved_paper_pdf_url")
    ]
    skipped_no_pdf = [
        {
            "paper_id": p.get("paper_id", ""),
            "title": p.get("title", ""),
            "doi": p.get("doi", ""),
            "journal": p.get("journal", ""),
            "year": p.get("year", ""),
            "dataset_status": p.get("dataset_status", ""),
            "step3_status": "skipped",
            "skip_reason": "pdf_url_unavailable",
        }
        for p in dataset_candidates
        if p.get("pdf_resolution_status") != "found"
        or not p.get("resolved_paper_pdf_url")
    ]

    if not candidates:
        logger.warning("No Step 2 papers with both confirmed datasets and PDFs to analyze.")
        return {
            "status": "empty",
            "dataset_eligible_count": len(dataset_candidates),
            "pdf_eligible_count": 0,
            "analyzed_count": 0,
            "skipped_count": len(skipped_no_pdf),
        }

    logger.info(
        f"Loaded {len(candidates)} papers with confirmed datasets and resolved PDFs "
        f"({len(skipped_no_pdf)} dataset candidates skipped because PDF was unavailable)"
    )

    # ---- Phase 2/3: Download PDF text + Prompt A ----
    logger.info("=" * 60)
    logger.info("Phase 2-3: Extracting PDF text and running Prompt A...")

    download_dir = os.path.join(project_root, config.get("download_dir", "step3/papers"))
    os.makedirs(download_dir, exist_ok=True)

    analyzed: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = list(skipped_no_pdf)

    for i, paper in enumerate(candidates, start=1):
        title = paper.get("title", "")[:60]
        doi = paper.get("doi", "")
        logger.info(f"  [{i}/{len(candidates)}] {title}...")

        doi_safe = doi.replace("/", "_") if doi else paper.get("paper_id", f"paper_{i}")
        pdf_dir = os.path.join(download_dir, doi_safe)
        paper_text = download_and_extract_text(paper, pdf_dir, http_config)

        if not paper_text or len(paper_text.strip()) < 200:
            skipped.append({
                "paper_id": paper.get("paper_id", ""),
                "title": paper.get("title", ""),
                "doi": doi,
                "journal": paper.get("journal", ""),
                "year": paper.get("year", ""),
                "dataset_status": paper.get("dataset_status", ""),
                "step3_status": "skipped",
                "skip_reason": "pdf_text_unavailable",
            })
            logger.info("    Skipped: PDF text unavailable")
            continue

        if not use_gpt:
            skipped.append({
                "paper_id": paper.get("paper_id", ""),
                "title": paper.get("title", ""),
                "doi": doi,
                "journal": paper.get("journal", ""),
                "year": paper.get("year", ""),
                "dataset_status": paper.get("dataset_status", ""),
                "step3_status": "skipped",
                "skip_reason": "gpt_disabled",
            })
            continue

        analysis = analyze_paper_text(paper, paper_text, model=gpt_model)
        analyzed.append({
            "paper_id": paper.get("paper_id", ""),
            "title": paper.get("title", ""),
            "doi": doi,
            "journal": paper.get("journal", ""),
            "year": paper.get("year", ""),
            "paper_url": paper.get("paper_url", ""),
            "priority_score": paper.get("priority_score", 0),
            "screening_decision": paper.get("screening_decision", ""),
            "dataset_status": paper.get("dataset_status", ""),
            "step3_status": "analyzed",
            "pdf_text_available": True,
            "paper_analysis": analysis,
        })

        time.sleep(rate_limit_delay)

    # ---- Phase 4: Save output ----
    logger.info("=" * 60)
    logger.info("Phase 4: Saving paper analyses...")

    output = {
        "metadata": {
            "step": 3,
            "description": "Prompt A Paper Analysis",
            "generated_at": datetime.now().isoformat(),
            "input_file": config.get("input_file", ""),
            "eligible_statuses": sorted(include_statuses),
            "dataset_eligible_count": len(dataset_candidates),
            "pdf_eligible_count": len(candidates),
            "total_eligible": len(candidates),
            "analyzed_count": len(analyzed),
            "skipped_count": len(skipped),
        },
        "summary": {
            "dataset_eligible_count": len(dataset_candidates),
            "pdf_eligible_count": len(candidates),
            "total_eligible": len(candidates),
            "analyzed_count": len(analyzed),
            "skipped_count": len(skipped),
            "skip_reasons": _count_by(skipped, "skip_reason"),
        },
        "analyzed_papers": analyzed,
        "skipped_papers": skipped,
    }

    output_dir = os.path.join(project_root, config.get("output_dir", "step3/output"))
    os.makedirs(output_dir, exist_ok=True)
    latest_path = save_with_latest(output, output_dir, "step3_paper_analysis")

    _print_summary(output)
    logger.info(f"Results saved to {latest_path}")

    return {
        "status": "complete",
        "output_path": latest_path,
        "analyzed_count": len(analyzed),
        "skipped_count": len(skipped),
    }


def _count_by(records: List[Dict[str, Any]], key: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for record in records:
        value = record.get(key, "unknown")
        counts[value] = counts.get(value, 0) + 1
    return counts


def _print_summary(output: Dict[str, Any]):
    summary = output["summary"]
    logger.info("=" * 60)
    logger.info("STEP 3 PAPER ANALYSIS SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Dataset-eligible papers:      {summary['dataset_eligible_count']}")
    logger.info(f"PDF + data eligible papers:   {summary['pdf_eligible_count']}")
    logger.info(f"Analyzed:                     {summary['analyzed_count']}")
    logger.info(f"Skipped:                      {summary['skipped_count']}")
    logger.info(f"Skip reasons:                 {summary['skip_reasons']}")
