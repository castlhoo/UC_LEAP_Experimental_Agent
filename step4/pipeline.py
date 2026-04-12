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


def _partition_papers(all_papers: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Partition papers by paper-level dataset type."""
    groups = {"both": [], "type1": [], "type2": [], "neither": []}
    for paper in all_papers:
        has_t1 = paper.get("has_type1", False)
        has_t2 = paper.get("has_type2", False)
        if has_t1 and has_t2:
            groups["both"].append(paper)
        elif has_t1:
            groups["type1"].append(paper)
        elif has_t2:
            groups["type2"].append(paper)
        else:
            groups["neither"].append(paper)
    return groups


def _select_balanced_has_any(
    all_papers: List[Dict[str, Any]],
    max_papers: int,
) -> List[Dict[str, Any]]:
    """
    Select papers with any dataset signal while balancing Both / Type1-only / Type2-only.

    Selection preserves the incoming order within each group, which is already sorted by
    Step 3 priority. Empty groups are ignored.
    """
    groups = _partition_papers(all_papers)
    active_group_names = [name for name in ("both", "type1", "type2") if groups[name]]
    if not active_group_names or max_papers <= 0:
        return []

    allocations = {name: 0 for name in active_group_names}
    selected_by_group = {name: [] for name in active_group_names}

    base_quota = max_papers // len(active_group_names)
    remainder = max_papers % len(active_group_names)

    # First pass: equal-size quota per available group.
    for name in active_group_names:
        take = min(base_quota, len(groups[name]))
        selected_by_group[name].extend(groups[name][:take])
        allocations[name] = take

    # Second pass: distribute remaining slots round-robin, preferring Both then Type1 then Type2.
    remaining = max_papers - sum(allocations.values())
    while remaining > 0:
        progressed = False
        for name in active_group_names:
            if allocations[name] < len(groups[name]):
                selected_by_group[name].append(groups[name][allocations[name]])
                allocations[name] += 1
                remaining -= 1
                progressed = True
                if remaining == 0:
                    break
        if not progressed:
            break

    selected = []
    for name in ("both", "type1", "type2"):
        selected.extend(selected_by_group.get(name, []))
    return selected[:max_papers]


def _select_papers(
    all_papers: List[Dict[str, Any]],
    both_papers: List[Dict[str, Any]],
    mode: str,
    max_papers: int | None,
) -> List[Dict[str, Any]]:
    """Select papers for Step 4 organization according to mode."""
    if max_papers in (None, 0):
        max_papers = None

    if mode == "both_types":
        return both_papers if max_papers is None else both_papers[:max_papers]
    if mode == "has_any":
        if max_papers is None:
            return [p for p in all_papers if p.get("has_type1") or p.get("has_type2")]
        return _select_balanced_has_any(all_papers, max_papers)
    return all_papers if max_papers is None else all_papers[:max_papers]


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
    max_papers = sel_config.get("max_papers")

    selected = _select_papers(
        all_papers=all_papers,
        both_papers=both_papers,
        mode=mode,
        max_papers=max_papers,
    )

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
        _write_reasoning_file(paper=paper, paper_dir=paper_dir, org_result=org_result)

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


def _write_reasoning_file(
    paper: Dict[str, Any],
    paper_dir: str,
    org_result: Dict[str, List[Dict[str, Any]]],
):
    """Write a human-readable reasoning summary into each organized paper folder."""
    lines: List[str] = []

    title = paper.get("title", "")
    doi = paper.get("doi", "")
    journal = paper.get("journal", "")
    year = paper.get("year", "")
    confidence = paper.get("classification_confidence", "")
    has_t1 = paper.get("has_type1", False)
    has_t2 = paper.get("has_type2", False)
    has_both = paper.get("has_both_types", False)

    if has_both:
        label = "Both"
    elif has_t1:
        label = "Type1 only"
    elif has_t2:
        label = "Type2 only"
    else:
        label = "Neither"

    lines.append(f"Title: {title}")
    lines.append(f"DOI: {doi or 'N/A'}")
    lines.append(f"Journal: {journal or 'N/A'}")
    lines.append(f"Year: {year or 'N/A'}")
    lines.append(f"Final label: {label}")
    lines.append(f"Classification confidence: {confidence or 'unknown'}")
    lines.append("")

    lines.append("Paper-level reasoning")
    lines.append(f"- Type1 summary: {paper.get('type1_summary', '') or 'none'}")
    lines.append(f"- Type2 summary: {paper.get('type2_summary', '') or 'none'}")
    lines.append("")

    for section, entries in (
        ("Type1 files", org_result.get("type1_data", [])),
        ("Type2 files", org_result.get("type2_data", [])),
        ("Annotation files", org_result.get("annotations", [])),
        ("Script files", org_result.get("scripts", [])),
    ):
        lines.append(section)
        if not entries:
            lines.append("- none")
            lines.append("")
            continue

        for entry in entries:
            cls = entry.get("classification", {})
            lines.append(f"- {entry.get('renamed', entry.get('original', 'unknown'))}")
            rel_path = cls.get("relative_path", "")
            if rel_path:
                lines.append(f"  original path: {rel_path}")
            if cls.get("type"):
                lines.append(f"  classified as: {cls.get('type')}")
            if cls.get("reasoning"):
                lines.append(f"  reasoning: {cls.get('reasoning')}")
            if cls.get("paper_evidence"):
                lines.append(f"  paper evidence: {cls.get('paper_evidence')}")
            if cls.get("file_evidence"):
                lines.append(f"  file evidence: {cls.get('file_evidence')}")
            if cls.get("key_columns_or_structure"):
                lines.append(f"  structure: {cls.get('key_columns_or_structure')}")
            ambiguity = cls.get("ambiguity", "")
            if ambiguity and ambiguity != "none":
                lines.append(f"  ambiguity: {ambiguity}")
        lines.append("")

    reasoning_path = os.path.join(paper_dir, "reasoning.txt")
    with open(reasoning_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).strip() + "\n")


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
