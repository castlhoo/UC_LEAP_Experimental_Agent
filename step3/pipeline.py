"""
Step 3 - Pipeline
===================
Orchestrates Dataset Download, Inspection & Type Classification:
  Phase 1: Load Step 2 results (papers with data)
  Phase 2: Download paper PDFs + GPT paper analysis
  Phase 3: Download dataset files
  Phase 4: Inspect file contents
  Phase 5: GPT Type 1/Type 2 classification (with paper context)
  Phase 6: Filter papers with BOTH types + save results
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List

import yaml

from utils import save_with_latest

from step3.downloader import download_paper_datasets
from step3.file_inspector import inspect_all_files
from step3.gpt_client import classify_dataset_types, analyze_paper_text
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
    """Execute the full Step 3 pipeline."""
    config = _load_config()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    gpt_config = config.get("gpt", {})
    use_gpt = gpt_config.get("enabled", False)
    gpt_model = gpt_config.get("model", "gpt-5.4-mini")

    http_config = config.get("http", {})
    dl_config = config.get("download", {})
    inspect_config = config.get("inspection", {})
    rate_limit_delay = http_config.get("rate_limit_delay", 1.0)

    # ---- Phase 1: Load Step 2 results ----
    logger.info("=" * 60)
    logger.info("Phase 1: Loading Step 2 results...")

    input_path = os.path.join(project_root, config.get("input_file", ""))
    with open(input_path, "r", encoding="utf-8") as f:
        step2_data = json.load(f)

    include_statuses = set(config.get("include_statuses", ["verified", "source_data_found"]))
    candidates = [
        p for p in step2_data.get("papers", [])
        if p.get("dataset_status") in include_statuses
    ]

    if not candidates:
        logger.warning("No candidates with downloadable data!")
        return {"status": "empty", "candidates_processed": 0}

    logger.info(f"Loaded {len(candidates)} papers with data to process")
    for p in candidates:
        logger.info(f"  [{p.get('priority_score', 0):5.1f}] [{p['dataset_status']}] {p['title'][:55]}")

    # ---- Phase 2: Download paper PDFs + GPT paper analysis ----
    logger.info("=" * 60)
    logger.info("Phase 2: Downloading paper PDFs & analyzing content...")

    download_dir = os.path.join(project_root, config.get("download_dir", "step3/downloads"))
    os.makedirs(download_dir, exist_ok=True)

    paper_analyses = {}  # doi -> analysis dict
    if use_gpt:
        for i, paper in enumerate(candidates):
            title = paper.get("title", "")[:50]
            doi = paper.get("doi", "")
            logger.info(f"  [{i+1}/{len(candidates)}] {title}...")

            # Download PDF and extract text
            doi_safe = doi.replace("/", "_") if doi else f"paper_{i}"
            pdf_dir = os.path.join(download_dir, doi_safe)
            paper_text = download_and_extract_text(paper, pdf_dir, http_config)

            if paper_text:
                # 1st GPT call: analyze paper
                analysis = analyze_paper_text(paper, paper_text, model=gpt_model)
                paper_analyses[doi] = analysis
            else:
                logger.info("    No PDF text available, will classify without paper context")
                paper_analyses[doi] = None

            time.sleep(rate_limit_delay)
    else:
        logger.info("  Skipped (GPT disabled)")

    # ---- Phase 3: Download dataset files ----
    logger.info("=" * 60)
    logger.info("Phase 3: Downloading dataset files...")

    results = []
    for i, paper in enumerate(candidates):
        title = paper.get("title", "")[:50]
        logger.info(f"  [{i+1}/{len(candidates)}] {title}...")

        dl_result = download_paper_datasets(
            paper, download_dir, http_config, dl_config, rate_limit_delay
        )

        results.append({
            "paper": paper,
            "download": dl_result,
            "inspections": [],
            "classification": None,
        })

    total_files = sum(
        len(r["download"].get("files", [])) + len(r["download"].get("zip_extracted", []))
        for r in results
    )
    logger.info(f"  Total files downloaded/extracted: {total_files}")

    # ---- Phase 4: Inspect file contents ----
    logger.info("=" * 60)
    logger.info("Phase 4: Inspecting file contents...")

    for entry in results:
        dl = entry["download"]
        n_files = len(dl.get("files", [])) + len(dl.get("zip_extracted", []))
        if n_files == 0:
            continue

        title = entry["paper"].get("title", "")[:50]
        reports = inspect_all_files(dl, inspect_config)
        entry["inspections"] = reports

        # Summary
        types_found = set(r.get("file_type", "?") for r in reports)
        logger.info(f"  {title}: {len(reports)} files inspected ({types_found})")

    # ---- Phase 5: GPT Type Classification (with paper context) ----
    if use_gpt:
        logger.info("=" * 60)
        logger.info("Phase 5: GPT Type 1/Type 2 classification (with paper context)...")

        classified = 0
        for entry in results:
            if not entry["inspections"]:
                continue

            title = entry["paper"].get("title", "")[:50]
            doi = entry["paper"].get("doi", "")
            analysis = paper_analyses.get(doi)

            classification = classify_dataset_types(
                entry["paper"], entry["inspections"], model=gpt_model,
                paper_analysis=analysis,
            )
            entry["classification"] = classification
            classified += 1

            has_t1 = classification.get("has_type1", False)
            has_t2 = classification.get("has_type2", False)
            both = classification.get("has_both", False)
            conf = classification.get("confidence", "?")
            t1_count = len(classification.get("type1_files", []))
            t2_count = len(classification.get("type2_files", []))

            status = "BOTH" if both else ("T1" if has_t1 else ("T2" if has_t2 else "NONE"))
            logger.info(f"  [{status:>4}] {title} (T1:{t1_count} T2:{t2_count} conf:{conf})")

        logger.info(f"  Classified {classified} papers")
    else:
        logger.info("Phase 5: Skipped (GPT disabled)")

    # ---- Phase 6: Build output + filter ----
    logger.info("=" * 60)
    logger.info("Phase 6: Building output & filtering...")

    output = _build_output(results, config, paper_analyses)
    _print_summary(output)

    # Save
    output_dir = os.path.join(project_root, config.get("output_dir", "step3/output"))
    os.makedirs(output_dir, exist_ok=True)

    # Remove large fields for JSON output (local_path, sample_rows)
    output_clean = _clean_for_json(output)

    # Save per-paper individual JSONs
    papers_dir = os.path.join(output_dir, "papers")
    os.makedirs(papers_dir, exist_ok=True)
    # Clean old per-paper JSONs
    for old in os.listdir(papers_dir):
        if old.endswith(".json"):
            os.remove(os.path.join(papers_dir, old))

    for i, paper_data in enumerate(output_clean.get("all_papers", [])):
        doi_slug = paper_data.get("doi", "").replace("/", "_").replace(".", "_")
        paper_filename = f"{i+1:03d}_{doi_slug}.json"
        paper_path = os.path.join(papers_dir, paper_filename)
        with open(paper_path, "w", encoding="utf-8") as f:
            json.dump(paper_data, f, indent=2, ensure_ascii=False, default=str)

    logger.info(f"  Saved {len(output_clean.get('all_papers', []))} individual paper JSONs to {papers_dir}")

    # Save combined manifest (latest only)
    latest_path = save_with_latest(output_clean, output_dir, "step3_classification")
    logger.info(f"Results saved to {latest_path}")

    return {
        "status": "complete",
        "output_path": latest_path,
        "total_processed": len(results),
        "both_type_count": output["summary"]["both_types_count"],
    }


def _build_output(results: List[Dict], config: Dict[str, Any], paper_analyses: Dict[str, Any] = None) -> Dict[str, Any]:
    """Build the final output structure."""
    papers = []

    for entry in results:
        paper = entry["paper"]
        dl = entry["download"]
        inspections = entry["inspections"]
        classification = entry["classification"] or {}

        has_both = classification.get("has_both", False)

        papers.append({
            "paper_id": paper.get("paper_id", ""),
            "title": paper.get("title", ""),
            "doi": paper.get("doi", ""),
            "journal": paper.get("journal", ""),
            "year": paper.get("year", ""),
            "paper_url": paper.get("paper_url", ""),
            "priority_score": paper.get("priority_score", 0),
            "dataset_status": paper.get("dataset_status", ""),
            # Download info
            "files_downloaded": len(dl.get("files", [])),
            "files_extracted": len(dl.get("zip_extracted", [])),
            "download_errors": dl.get("errors", []),
            "download_dir": dl.get("download_dir", ""),
            # Inspection summary
            "files_inspected": len(inspections),
            "file_types_found": list(set(r.get("file_type", "?") for r in inspections)),
            # Classification
            "has_type1": classification.get("has_type1", False),
            "has_type2": classification.get("has_type2", False),
            "has_both_types": has_both,
            "type1_summary": classification.get("type1_summary", "none"),
            "type2_summary": classification.get("type2_summary", "none"),
            "type1_files": classification.get("type1_files", []),
            "type2_files": classification.get("type2_files", []),
            "classification_confidence": classification.get("confidence", "low"),
            "classification_notes": classification.get("notes", ""),
            "file_classifications": classification.get("file_classifications", []),
            # Paper analysis (from reading the PDF)
            "paper_analysis": (paper_analyses or {}).get(paper.get("doi", ""), None),
            # Raw inspection data (for verification)
            "inspection_reports": inspections,
        })

    # Sort: both_types first, then type1_only, then type2_only, by priority
    def sort_key(p):
        if p["has_both_types"]:
            tier = 0
        elif p["has_type1"]:
            tier = 1
        elif p["has_type2"]:
            tier = 2
        else:
            tier = 3
        return (tier, -p.get("priority_score", 0))

    papers.sort(key=sort_key)

    # Stats
    both_count = sum(1 for p in papers if p["has_both_types"])
    t1_only = sum(1 for p in papers if p["has_type1"] and not p["has_type2"])
    t2_only = sum(1 for p in papers if p["has_type2"] and not p["has_type1"])
    neither = sum(1 for p in papers if not p["has_type1"] and not p["has_type2"])

    return {
        "metadata": {
            "step": 3,
            "description": "Dataset Download, Inspection & Type Classification",
            "generated_at": datetime.now().isoformat(),
            "total_papers": len(papers),
        },
        "summary": {
            "total_processed": len(papers),
            "both_types_count": both_count,
            "type1_only_count": t1_only,
            "type2_only_count": t2_only,
            "neither_count": neither,
            "total_files_downloaded": sum(p["files_downloaded"] for p in papers),
            "total_files_inspected": sum(p["files_inspected"] for p in papers),
        },
        "both_types_papers": [p for p in papers if p["has_both_types"]],
        "all_papers": papers,
    }


def _print_summary(output: Dict[str, Any]):
    """Print formatted summary."""
    summary = output["summary"]

    logger.info("=" * 60)
    logger.info("STEP 3 RESULTS SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total papers processed:   {summary['total_processed']}")
    logger.info(f"Both Type 1+2:            {summary['both_types_count']}  ← TARGET")
    logger.info(f"Type 1 only:              {summary['type1_only_count']}")
    logger.info(f"Type 2 only:              {summary['type2_only_count']}")
    logger.info(f"Neither type:             {summary['neither_count']}")
    logger.info(f"Files downloaded:         {summary['total_files_downloaded']}")
    logger.info(f"Files inspected:          {summary['total_files_inspected']}")

    both = output["both_types_papers"]
    if both:
        logger.info("-" * 60)
        logger.info("PAPERS WITH BOTH TYPE 1 + TYPE 2:")
        for p in both:
            logger.info(f"  [{p['priority_score']:5.1f}] {p['title'][:55]}")
            logger.info(f"         T1: {p['type1_summary'][:60]}")
            logger.info(f"         T2: {p['type2_summary'][:60]}")
    else:
        logger.info("-" * 60)
        logger.info("No papers found with BOTH Type 1 and Type 2 datasets.")
        logger.info("Consider relaxing requirements or expanding the search.")


def _clean_for_json(output: Dict[str, Any]) -> Dict[str, Any]:
    """Remove large/non-serializable fields for JSON output."""
    import copy
    clean = copy.deepcopy(output)

    for paper in clean.get("all_papers", []):
        for report in paper.get("inspection_reports", []):
            # Remove sample_rows (can be large)
            report.pop("sample_rows", None)
            report.pop("local_path", None)
            # Clean sheet sample rows
            for sheet in report.get("sheets", []):
                sheet.pop("sample_rows", None)

    for paper in clean.get("both_types_papers", []):
        for report in paper.get("inspection_reports", []):
            report.pop("sample_rows", None)
            report.pop("local_path", None)
            for sheet in report.get("sheets", []):
                sheet.pop("sample_rows", None)

    return clean
