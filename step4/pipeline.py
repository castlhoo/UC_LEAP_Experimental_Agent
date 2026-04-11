"""
Step 4 - Pipeline
===================
Orchestrates local storage and organization:
  Phase 1: Load Step 3 classification results
  Phase 2: Select papers (both_types or all)
  Phase 3: Download paper PDFs
  Phase 4: Organize dataset files (T1/T2/annotations/scripts)
  Phase 5: Generate summary manifest
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

import yaml

from step4.pdf_downloader import download_paper_pdf
from step4.file_organizer import organize_paper_files, make_paper_dirname
from utils import save_with_latest

logger = logging.getLogger(__name__)


def _load_config() -> Dict[str, Any]:
    """Load Step 4 configuration."""
    config_path = os.path.join(
        os.path.dirname(__file__), "config", "step4_config.yaml"
    )
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_step4() -> Dict[str, Any]:
    """Execute the full Step 4 pipeline."""
    config = _load_config()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # ---- Phase 1: Load Step 3 results ----
    logger.info("=" * 60)
    logger.info("Phase 1: Loading Step 3 classification results...")

    input_path = os.path.join(project_root, config.get("input_file", ""))
    with open(input_path, "r", encoding="utf-8") as f:
        step3_data = json.load(f)

    all_papers = step3_data.get("all_papers", [])
    both_papers = step3_data.get("both_types_papers", [])

    logger.info(f"  Total papers: {len(all_papers)}")
    logger.info(f"  Both Type 1+2: {len(both_papers)}")

    # ---- Phase 2: Select papers ----
    logger.info("=" * 60)
    logger.info("Phase 2: Selecting papers to organize...")

    sel_config = config.get("selection", {})
    mode = sel_config.get("mode", "both_types")
    max_papers = sel_config.get("max_papers", 30)

    if mode == "both_types":
        selected = both_papers[:max_papers]
    elif mode == "has_any":
        selected = [p for p in all_papers if p.get("has_type1") or p.get("has_type2")][:max_papers]
    else:
        selected = all_papers[:max_papers]

    if not selected:
        logger.warning("No papers selected for organization!")
        return {"status": "empty", "papers_organized": 0}

    logger.info(f"  Selected {len(selected)} papers (mode={mode})")
    for p in selected:
        logger.info(f"    [{p.get('priority_score', 0):5.1f}] {p['title'][:55]}")

    # ---- Phase 3 & 4: Download PDFs + Organize files ----
    output_dir = os.path.join(project_root, config.get("output_dir", "step4/organized"))
    os.makedirs(output_dir, exist_ok=True)

    # Create Type-based subdirectories
    for type_dir in ["Both", "Type1", "Type2", "Neither"]:
        os.makedirs(os.path.join(output_dir, type_dir), exist_ok=True)

    rename_config = config.get("rename", {})
    max_title_words = rename_config.get("max_title_words", 5)

    manifests = []
    for i, paper in enumerate(selected):
        # Determine type group folder
        has_t1 = paper.get("has_type1", False)
        has_t2 = paper.get("has_type2", False)
        if has_t1 and has_t2:
            type_group = "Both"
        elif has_t1:
            type_group = "Type1"
        elif has_t2:
            type_group = "Type2"
        else:
            type_group = "Neither"

        dirname = make_paper_dirname(i + 1, paper["title"], max_title_words)
        paper_dir = os.path.join(output_dir, type_group, dirname)
        os.makedirs(paper_dir, exist_ok=True)

        logger.info("=" * 60)
        logger.info(f"Paper {i+1}/{len(selected)}: {paper['title'][:55]}")
        logger.info(f"  DOI: {paper.get('doi', 'N/A')}")
        logger.info(f"  Type: {type_group}")
        logger.info(f"  Dir: {type_group}/{dirname}")

        # Phase 3: Download PDF
        logger.info("  Downloading PDF...")
        pdf_dir = os.path.join(paper_dir, "pdf")
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_path = download_paper_pdf(paper, pdf_dir, config)

        # Phase 4: Organize dataset files
        logger.info("  Organizing dataset files...")
        org_result = organize_paper_files(paper, paper_dir, config)

        # Build manifest entry
        manifest = {
            "paper_index": i + 1,
            "type_group": type_group,
            "directory": f"{type_group}/{dirname}",
            "title": paper["title"],
            "doi": paper.get("doi", ""),
            "journal": paper.get("journal", ""),
            "year": paper.get("year", ""),
            "paper_url": paper.get("paper_url", ""),
            "priority_score": paper.get("priority_score", 0),
            "has_pdf": pdf_path is not None,
            "type1_summary": paper.get("type1_summary", ""),
            "type2_summary": paper.get("type2_summary", ""),
            "has_type1": paper.get("has_type1", False),
            "has_type2": paper.get("has_type2", False),
            "has_both_types": paper.get("has_both_types", False),
            "classification_confidence": paper.get("classification_confidence", ""),
            "files": {
                "type1_data": _build_file_list(org_result.get("type1_data", [])),
                "type2_data": _build_file_list(org_result.get("type2_data", [])),
                "annotations": [f["renamed"] for f in org_result.get("annotations", [])],
                "scripts": [f["renamed"] for f in org_result.get("scripts", [])],
            },
            "counts": {
                "type1": len(org_result.get("type1_data", [])),
                "type2": len(org_result.get("type2_data", [])),
                "annotations": len(org_result.get("annotations", [])),
                "scripts": len(org_result.get("scripts", [])),
                "skipped": len(org_result.get("skip", [])),
            },
        }
        manifests.append(manifest)

    # ---- Phase 5: Save manifest ----
    logger.info("=" * 60)
    logger.info("Phase 5: Saving manifest...")

    output = {
        "metadata": {
            "step": 4,
            "description": "Local Storage & Organization",
            "generated_at": datetime.now().isoformat(),
            "selection_mode": mode,
            "total_organized": len(manifests),
        },
        "summary": {
            "papers_organized": len(manifests),
            "both_count": sum(1 for m in manifests if m["type_group"] == "Both"),
            "type1_only_count": sum(1 for m in manifests if m["type_group"] == "Type1"),
            "type2_only_count": sum(1 for m in manifests if m["type_group"] == "Type2"),
            "neither_count": sum(1 for m in manifests if m["type_group"] == "Neither"),
            "pdfs_downloaded": sum(1 for m in manifests if m["has_pdf"]),
            "total_type1_files": sum(m["counts"]["type1"] for m in manifests),
            "total_type2_files": sum(m["counts"]["type2"] for m in manifests),
            "total_annotation_files": sum(m["counts"]["annotations"] for m in manifests),
            "total_script_files": sum(m["counts"]["scripts"] for m in manifests),
        },
        "papers": manifests,
    }

    latest_path = save_with_latest(output, output_dir, "manifest")

    _print_summary(output)

    logger.info(f"Manifest saved to {latest_path}")

    return {
        "status": "complete",
        "output_path": latest_path,
        "papers_organized": len(manifests),
    }


def _build_file_list(file_entries: List[Dict]) -> List[Dict]:
    """Build file list with classification reasoning for the manifest."""
    result = []
    for f in file_entries:
        entry = {"renamed": f["renamed"]}
        cls = f.get("classification", {})
        if cls:
            entry["classification"] = {
                "type": cls.get("type", ""),
                "reasoning": cls.get("reasoning", ""),
                "paper_evidence": cls.get("paper_evidence", ""),
                "file_evidence": cls.get("file_evidence", ""),
                "ambiguity": cls.get("ambiguity", "none"),
                "key_columns": cls.get("key_columns_or_structure", ""),
            }
        result.append(entry)
    return result


def _print_summary(output: Dict[str, Any]):
    """Print formatted summary."""
    s = output["summary"]
    logger.info("=" * 60)
    logger.info("STEP 4 RESULTS SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Papers organized:      {s['papers_organized']}")
    logger.info(f"  Both (T1+T2):        {s['both_count']}")
    logger.info(f"  Type 1 only:         {s['type1_only_count']}")
    logger.info(f"  Type 2 only:         {s['type2_only_count']}")
    logger.info(f"  Neither:             {s['neither_count']}")
    logger.info(f"PDFs downloaded:        {s['pdfs_downloaded']}")
    logger.info(f"Type 1 data files:     {s['total_type1_files']}")
    logger.info(f"Type 2 data files:     {s['total_type2_files']}")
    logger.info(f"Annotation files:      {s['total_annotation_files']}")
    logger.info(f"Script files:          {s['total_script_files']}")

    logger.info("-" * 60)
    for p in output["papers"]:
        c = p["counts"]
        pdf = "✓" if p["has_pdf"] else "✗"
        tg = p.get("type_group", "?")
        logger.info(
            f"  {p['paper_index']:3d}. [{tg:>5}] [PDF:{pdf}] T1:{c['type1']:2d} T2:{c['type2']:2d} "
            f"| {p['title'][:45]}"
        )
