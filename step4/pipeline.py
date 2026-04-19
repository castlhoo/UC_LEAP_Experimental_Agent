"""
Step 4 - Dataset Type Classification
====================================
Runs Prompt B only:
  Phase 1: Load Step 2 dataset evidence and Step 3 paper analyses
  Phase 2: Download dataset files
  Phase 3: Inspect file contents
  Phase 4: Classify files with Prompt B using paper_analysis
  Phase 5: Save classification output
"""

import json
import logging
import os
from typing import Any, Dict, List

import yaml

from utils import save_with_latest
from step4.phase4a_inventory.inventory import (
    download_and_prepare_paper,
    get_paper_download_dir,
    has_existing_download,
    inspect_paper_files,
    load_existing_download_result,
)
from step4.phase4b_dataset_assessment.dataset_assessment import assess_dataset_level
from step4.phase4c_file_classification.file_classification import classify_dataset_files
from step4.phase4c_file_classification.file_classification import normalize_classification
from step4.phase4d_merge_summary.merge_summary import (
    build_output,
    clean_for_json,
    write_paper_dataset_summary,
)

logger = logging.getLogger(__name__)


def _load_config() -> Dict[str, Any]:
    """Load Step 4 configuration."""
    config_path = os.path.join(
        os.path.dirname(__file__), "config", "step4_config.yaml"
    )
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_step4() -> Dict[str, Any]:
    """Execute Prompt B dataset type classification."""
    config = _load_config()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    gpt_config = config.get("gpt", {})
    use_gpt = gpt_config.get("enabled", True)
    gpt_model = gpt_config.get("model", "gpt-5.4-mini")
    gpt_batch_size = gpt_config.get("batch_size", 8)

    http_config = config.get("http", {})
    dl_config = config.get("download", {})
    inspect_config = config.get("inspection", {})
    resume_config = config.get("resume", {})
    reuse_existing_downloads = resume_config.get("reuse_existing_downloads", True)
    skip_completed_papers = resume_config.get("skip_completed_papers", True)
    reprocess_failed = resume_config.get("reprocess_failed_classifications", True)
    reprocess_neither_with_data = resume_config.get("reprocess_neither_with_data_files", True)
    rate_limit_delay = http_config.get("rate_limit_delay", 1.0)

    # ---- Phase 1: Load inputs ----
    logger.info("=" * 60)
    logger.info("Phase 1: Loading Step 2 evidence and Step 3 paper analyses...")

    step2_path = os.path.join(project_root, config.get("step2_input_file", ""))
    step3_path = os.path.join(project_root, config.get("step3_input_file", ""))

    with open(step2_path, "r", encoding="utf-8") as f:
        step2_data = json.load(f)
    with open(step3_path, "r", encoding="utf-8") as f:
        step3_data = json.load(f)

    analyses_by_id = {
        p.get("paper_id"): p
        for p in step3_data.get("analyzed_papers", [])
        if p.get("paper_id")
    }

    candidates = []
    skipped_missing_analysis = []
    for paper in step2_data.get("papers", []):
        paper_id = paper.get("paper_id")
        analysis_record = analyses_by_id.get(paper_id)
        if not analysis_record:
            if paper.get("dataset_status") in ("verified", "source_data_found"):
                skipped_missing_analysis.append({
                    "paper_id": paper_id,
                    "title": paper.get("title", ""),
                    "reason": "missing_step3_paper_analysis",
                })
            continue
        candidates.append({
            "paper": paper,
            "paper_analysis": analysis_record.get("paper_analysis", {}),
        })

    if not candidates:
        logger.warning("No papers have both confirmed datasets and Step 3 paper analysis.")
        return {"status": "empty", "total_processed": 0, "both_type_count": 0}

    logger.info(f"Loaded {len(candidates)} papers for Prompt B classification")
    if skipped_missing_analysis:
        logger.info(f"Skipped {len(skipped_missing_analysis)} dataset papers missing Step 3 analysis")

    # ---- Phase 2: Download dataset files ----
    logger.info("=" * 60)
    logger.info("Phase 2: Downloading dataset files...")

    download_dir = os.path.join(project_root, config.get("download_dir", "step4/downloads"))
    step3_paper_dir = os.path.join(project_root, config.get("step3_paper_dir", "step3/papers"))
    os.makedirs(download_dir, exist_ok=True)

    results = []
    for i, item in enumerate(candidates, start=1):
        paper = item["paper"]
        title = paper.get("title", "")[:60]
        logger.info(f"  [{i}/{len(candidates)}] {title}...")

        completed = _load_completed_summary_if_available(
            paper=paper,
            download_dir=download_dir,
            reprocess_failed=reprocess_failed,
            reprocess_neither_with_data=reprocess_neither_with_data,
        ) if skip_completed_papers else None
        if completed:
            logger.info("    Reusing completed Step 4 summary")
            reused_entry = {
                "paper": paper,
                "paper_analysis": item["paper_analysis"],
                "download": completed["download"],
                "inspections": completed["inspections"],
                "classification": completed["classification"],
                "completed_reused": True,
            }
            write_paper_dataset_summary(reused_entry)
            results.append(reused_entry)
            continue

        if reuse_existing_downloads and has_existing_download(paper, download_dir):
            logger.info("    Reusing existing downloaded files")
            dl_result = load_existing_download_result(
                paper=paper,
                download_dir=download_dir,
                step3_paper_dir=step3_paper_dir,
            )
        else:
            dl_result = download_and_prepare_paper(
                paper=paper,
                download_dir=download_dir,
                step3_paper_dir=step3_paper_dir,
                http_config=http_config,
                dl_config=dl_config,
                rate_limit_delay=rate_limit_delay,
            )

        results.append({
            "paper": paper,
            "paper_analysis": item["paper_analysis"],
            "download": dl_result,
            "inspections": [],
            "classification": None,
        })

    total_files = sum(
        len(r["download"].get("files", [])) + len(r["download"].get("zip_extracted", []))
        for r in results
    )
    logger.info(f"  Total files downloaded/extracted: {total_files}")

    # ---- Phase 4A: Inspect file contents ----
    logger.info("=" * 60)
    logger.info("Phase 4A: Inspecting file contents...")

    for entry in results:
        if entry.get("completed_reused"):
            continue
        dl = entry["download"]
        n_files = len(dl.get("files", [])) + len(dl.get("zip_extracted", []))
        if n_files == 0:
            continue

        title = entry["paper"].get("title", "")[:50]
        reports = inspect_paper_files(dl, inspect_config)
        entry["inspections"] = reports

        types_found = set(r.get("file_type", "?") for r in reports)
        logger.info(f"  {title}: {len(reports)} files inspected ({types_found})")

    # ---- Phase 4B/4C: Dataset assessment, file classification, and merge ----
    if use_gpt:
        logger.info("=" * 60)
        logger.info("Phase 4B/4C: Dataset assessment, file classification, and merge...")

        classified = 0
        for entry in results:
            if entry.get("completed_reused"):
                classified += 1
                title = entry["paper"].get("title", "")[:50]
                classification = entry["classification"] or {}
                both = classification.get("has_both", False)
                has_t1 = classification.get("has_type1", False)
                has_t2 = classification.get("has_type2", False)
                status = "BOTH" if both else ("T1" if has_t1 else ("T2" if has_t2 else "NONE"))
                logger.info(f"  [{status:>4}] {title} (reused)")
                continue
            if not entry["inspections"]:
                continue

            title = entry["paper"].get("title", "")[:50]
            paper_dir = entry.get("download", {}).get("download_dir", "")

            dataset_assessment = assess_dataset_level(
                paper=entry["paper"],
                file_reports=entry["inspections"],
                model=gpt_model,
                paper_analysis=entry["paper_analysis"],
                paper_dir=paper_dir,
            )
            classification = classify_dataset_files(
                paper=entry["paper"],
                file_reports=entry["inspections"],
                dataset_assessment=dataset_assessment,
                model=gpt_model,
                paper_analysis=entry["paper_analysis"],
                batch_size=gpt_batch_size,
                paper_dir=paper_dir,
            )
            entry["classification"] = classification
            write_paper_dataset_summary(entry)
            classified += 1

            both = classification.get("has_both", False)
            has_t1 = classification.get("has_type1", False)
            has_t2 = classification.get("has_type2", False)
            status = "BOTH" if both else ("T1" if has_t1 else ("T2" if has_t2 else "NONE"))
            logger.info(f"  [{status:>4}] {title} ({classification.get('confidence', '?')})")

        logger.info(f"  Classified {classified} papers")
    else:
        logger.info("Phase 4: Skipped (GPT disabled)")

    # ---- Phase 5: Build and save output ----
    logger.info("=" * 60)
    logger.info("Phase 5: Saving classification output...")

    output = build_output(results, skipped_missing_analysis)
    output_clean = clean_for_json(output)

    output_dir = os.path.join(project_root, config.get("output_dir", "step4/output"))
    os.makedirs(output_dir, exist_ok=True)
    latest_path = save_with_latest(output_clean, output_dir, "step4_classification")

    _print_summary(output_clean)
    logger.info(f"Results saved to {latest_path}")

    return {
        "status": "complete",
        "output_path": latest_path,
        "total_processed": len(results),
        "both_type_count": output["summary"]["both_types_count"],
    }


def _print_summary(output: Dict[str, Any]):
    summary = output["summary"]
    logger.info("=" * 60)
    logger.info("STEP 4 CLASSIFICATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total papers processed:   {summary['total_processed']}")
    logger.info(f"Both Type 1+2:            {summary['both_types_count']}")
    logger.info(f"Type 1 only:              {summary['type1_only_count']}")
    logger.info(f"Type 2 only:              {summary['type2_only_count']}")
    logger.info(f"Neither type:             {summary['neither_count']}")
    logger.info(f"Files downloaded:         {summary['total_files_downloaded']}")
    logger.info(f"Files inspected:          {summary['total_files_inspected']}")
    logger.info(f"Missing Step 3 analysis:  {summary['skipped_missing_step3_analysis']}")


def _load_completed_summary_if_available(
    paper: Dict[str, Any],
    download_dir: str,
    reprocess_failed: bool = True,
    reprocess_neither_with_data: bool = True,
) -> Dict[str, Any] | None:
    paper_dir = get_paper_download_dir(paper, download_dir)
    summary_path = os.path.join(paper_dir, "summary", "paper_dataset_summary.json")
    if not os.path.isfile(summary_path):
        return None

    try:
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)
    except Exception as e:
        logger.warning(f"    Could not reuse completed summary: {e}")
        return None

    dataset_contents = summary.get("dataset_contents", {})
    classification = normalize_classification(summary.get("type_classification", {}) or {})
    inspections = dataset_contents.get("files", []) or []
    if _should_reprocess_completed_summary(
        classification=classification,
        inspections=inspections,
        reprocess_failed=reprocess_failed,
        reprocess_neither_with_data=reprocess_neither_with_data,
    ):
        logger.info("    Reprocessing completed summary because classification looks incomplete")
        return None

    download_info = summary.get("download_and_organization", {}) or {}
    return {
        "download": {
            "paper_id": paper.get("paper_id", "unknown"),
            "download_dir": paper_dir,
            "files": [],
            "zip_extracted": [],
            "errors": download_info.get("download_errors", []),
            "organization": download_info.get("organization", {}),
            "organized_files": download_info.get("organized_files", []),
            "reused_completed_summary": True,
        },
        "inspections": inspections,
        "classification": classification,
    }


def _should_reprocess_completed_summary(
    classification: Dict[str, Any],
    inspections: List[Dict[str, Any]],
    reprocess_failed: bool,
    reprocess_neither_with_data: bool,
) -> bool:
    notes = str(classification.get("notes", ""))
    if reprocess_failed and "GPT error" in notes:
        return True

    has_type1 = classification.get("has_type1", False)
    has_type2 = classification.get("has_type2", False)
    if not reprocess_neither_with_data or has_type1 or has_type2:
        return False

    data_like_types = {
        "tabular_text",
        "excel",
        "hdf5",
        "numpy",
        "matlab",
        "json",
        "binary",
        "instrument_raw",
        "microscopy_image",
        "optical_image",
    }
    return any(report.get("file_type") in data_like_types for report in inspections)
