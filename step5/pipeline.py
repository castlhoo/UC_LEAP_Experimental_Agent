"""
Step 5 - Pipeline
===================
Orchestrates local storage and organization:
  Phase 1: Load Step 4 classification results
  Phase 2: Select papers (both_types or all)
  Phase 3: Download/copy paper PDFs
  Phase 4: Organize dataset files (type1/type2/annotations/scripts/pdf/summary)
  Phase 5: Generate summary manifest
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

import yaml

from step5.file_organizer import organize_paper_files, make_paper_dirname

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
    """Select papers for Step 5 organization according to mode."""
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
    """Load Step 5 configuration."""
    config_path = os.path.join(
        os.path.dirname(__file__), "config", "step5_config.yaml"
    )
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_step5() -> Dict[str, Any]:
    """Execute the full Step 5 pipeline."""
    config = _load_config()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # ---- Phase 1: Load Step 4 results ----
    logger.info("=" * 60)
    logger.info("Phase 1: Loading Step 4 classification results...")

    input_path = os.path.join(project_root, config.get("input_file", ""))
    with open(input_path, "r", encoding="utf-8") as f:
        step4_data = json.load(f)

    all_papers = step4_data.get("all_papers", [])
    both_papers = step4_data.get("both_types_papers", [])

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
        logger.info(f"    {p['title'][:55]}")

    # ---- Phase 3 & 4: Download PDFs + Organize files ----
    output_dir = os.path.join(project_root, config.get("output_dir", "step5/organized"))
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

        # Phase 3-4: Organize Step 4 dataset files, PDFs, annotations, scripts, and summaries.
        logger.info("  Organizing dataset files...")
        org_result = organize_paper_files(paper, paper_dir, config)
        _write_reasoning_file(paper=paper, paper_dir=paper_dir, org_result=org_result)
        has_pdf = bool(org_result.get("pdf"))
        has_summary = bool(org_result.get("summary"))

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
            "resolved_paper_pdf_url": paper.get("resolved_paper_pdf_url", ""),
            "data_url_candidates": paper.get("source_urls", {}).get("data_url_candidates", []),
            "repository_urls": paper.get("source_urls", {}).get("repository_urls", []),
            "has_pdf": has_pdf,
            "has_paper_dataset_summary": has_summary,
            "has_reasoning": bool(org_result.get("reasoning")),
            "type1_summary": paper.get("type1_summary", ""),
            "type2_summary": paper.get("type2_summary", ""),
            "has_type1": paper.get("has_type1", False),
            "has_type2": paper.get("has_type2", False),
            "has_both_types": paper.get("has_both_types", False),
            "classification_confidence": paper.get("classification_confidence", ""),
            "files": {
                "type1": _build_file_list(org_result.get("type1", [])),
                "type2": _build_file_list(org_result.get("type2", [])),
                "annotations": _build_file_list(org_result.get("annotations", [])),
                "scripts": [f["renamed"] for f in org_result.get("scripts", [])],
                "pdf": [f["renamed"] for f in org_result.get("pdf", [])],
                "summary": [f["renamed"] for f in org_result.get("summary", [])],
                "reasoning": [f["renamed"] for f in org_result.get("reasoning", [])],
            },
            "counts": {
                "type1": len(org_result.get("type1", [])),
                "type2": len(org_result.get("type2", [])),
                "annotations": len(org_result.get("annotations", [])),
                "scripts": len(org_result.get("scripts", [])),
                "pdf": len(org_result.get("pdf", [])),
                "summary": len(org_result.get("summary", [])),
                "reasoning": len(org_result.get("reasoning", [])),
                "skipped": len(org_result.get("skip", [])),
            },
        }
        manifests.append(manifest)

    # ---- Phase 5: Save manifest ----
    logger.info("=" * 60)
    logger.info("Phase 5: Saving manifest...")

    output = {
        "metadata": {
            "step": 5,
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
            "papers_with_pdf": sum(1 for m in manifests if m["has_pdf"]),
            "papers_with_dataset_summary": sum(1 for m in manifests if m["has_paper_dataset_summary"]),
            "total_type1_files": sum(m["counts"]["type1"] for m in manifests),
            "total_type2_files": sum(m["counts"]["type2"] for m in manifests),
            "total_annotation_files": sum(m["counts"]["annotations"] for m in manifests),
            "total_script_files": sum(m["counts"]["scripts"] for m in manifests),
            "total_pdf_files": sum(m["counts"]["pdf"] for m in manifests),
            "total_summary_files": sum(m["counts"]["summary"] for m in manifests),
            "total_reasoning_files": sum(m["counts"]["reasoning"] for m in manifests),
        },
        "papers": manifests,
    }

    latest_path = _save_manifest(output, output_dir)

    _print_summary(output)

    logger.info(f"Manifest saved to {latest_path}")

    return {
        "status": "complete",
        "output_path": latest_path,
        "papers_organized": len(manifests),
    }


def _save_manifest(output: Dict[str, Any], output_dir: str) -> str:
    """Save timestamped and latest Step 5 manifests without deleting older runs."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ts_path = os.path.join(output_dir, f"manifest_{timestamp}.json")
    latest_path = os.path.join(output_dir, "manifest_latest.json")

    for path in (ts_path, latest_path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False, default=str)

    return latest_path


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
        ("Type1 files", org_result.get("type1", [])),
        ("Type2 files", org_result.get("type2", [])),
        ("Annotation files", org_result.get("annotations", [])),
        ("Script files", org_result.get("scripts", [])),
        ("PDF files", org_result.get("pdf", [])),
        ("Summary files", org_result.get("summary", [])),
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

    reasoning_json_path = os.path.join(paper_dir, "reasoning.json")
    reasoning_path = os.path.join(paper_dir, "reasoning.txt")

    reasoning_payload = _build_reasoning_payload(paper, org_result, label)
    with open(reasoning_json_path, "w", encoding="utf-8") as f:
        json.dump(reasoning_payload, f, ensure_ascii=False, indent=2)

    with open(reasoning_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).strip() + "\n")

    org_result.setdefault("reasoning", []).append({
        "original": "reasoning.json",
        "renamed": "reasoning.json",
        "final_relative_path": "reasoning.json",
        "source": reasoning_json_path,
    })
    org_result.setdefault("reasoning", []).append({
        "original": "reasoning.txt",
        "renamed": "reasoning.txt",
        "final_relative_path": "reasoning.txt",
        "source": reasoning_path,
    })


def _build_reasoning_payload(
    paper: Dict[str, Any],
    org_result: Dict[str, List[Dict[str, Any]]],
    label: str,
) -> Dict[str, Any]:
    """Build a machine-readable Step 5 reasoning sidecar."""
    paper_analysis = paper.get("paper_analysis", {}) or {}
    dataset_assessment = paper.get("dataset_assessment", {}) or {}

    return {
        "paper": {
            "paper_id": paper.get("paper_id", ""),
            "title": paper.get("title", ""),
            "doi": paper.get("doi", ""),
            "journal": paper.get("journal", ""),
            "year": paper.get("year", ""),
            "paper_url": paper.get("paper_url", ""),
            "resolved_paper_pdf_url": paper.get("resolved_paper_pdf_url", ""),
        },
        "why_selected": {
            "screening_decision": paper.get("screening_decision", ""),
            "dataset_status": paper.get("dataset_status", ""),
            "verification_reasons": paper.get("verification_reasons", []),
            "needs_human_review": paper.get("needs_human_review", False),
        },
        "source_urls": paper.get("source_urls", {}),
        "topic_and_dataset_meaning": {
            "scientific_summary": paper_analysis.get("summary", ""),
            "measurement_types": paper_analysis.get("measurement_types", []),
            "dataset_characterization": paper_analysis.get("dataset_characterization", {}),
            "classification_prior": paper_analysis.get("classification_prior", {}),
            "dataset_assessment": dataset_assessment,
        },
        "final_decision": {
            "label": label,
            "has_type1": paper.get("has_type1", False),
            "has_type2": paper.get("has_type2", False),
            "has_both_types": paper.get("has_both_types", False),
            "final_classification": paper.get("final_classification", ""),
            "confidence": paper.get("classification_confidence", ""),
            "notes": paper.get("classification_notes", ""),
            "type1_summary": paper.get("type1_summary", ""),
            "type2_summary": paper.get("type2_summary", ""),
        },
        "files": {
            "type1": _build_file_list(org_result.get("type1", [])),
            "type2": _build_file_list(org_result.get("type2", [])),
            "annotations": _build_file_list(org_result.get("annotations", [])),
            "scripts": _build_plain_file_list(org_result.get("scripts", [])),
            "pdf": _build_plain_file_list(org_result.get("pdf", [])),
            "summary": _build_plain_file_list(org_result.get("summary", [])),
            "reasoning": _build_plain_file_list(org_result.get("reasoning", [])),
            "skipped": _build_plain_file_list(org_result.get("skip", [])),
        },
        "counts": {
            "type1": len(org_result.get("type1", [])),
            "type2": len(org_result.get("type2", [])),
            "annotations": len(org_result.get("annotations", [])),
            "scripts": len(org_result.get("scripts", [])),
            "pdf": len(org_result.get("pdf", [])),
            "summary": len(org_result.get("summary", [])),
            "reasoning": len(org_result.get("reasoning", [])),
            "skipped": len(org_result.get("skip", [])),
        },
    }


def _build_file_list(file_entries: List[Dict]) -> List[Dict]:
    """Build file list with classification reasoning for the manifest."""
    result = []
    for f in file_entries:
        entry = {
            "renamed": f["renamed"],
            "final_relative_path": f.get("final_relative_path", f["renamed"]),
            "source": f.get("source", ""),
        }
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


def _build_plain_file_list(file_entries: List[Dict]) -> List[Dict]:
    """Build a simple file list for non-data sections."""
    return [
        {
            "renamed": f.get("renamed", ""),
            "final_relative_path": f.get("final_relative_path", f.get("renamed", "")),
            "source": f.get("source", ""),
        }
        for f in file_entries
    ]


def _print_summary(output: Dict[str, Any]):
    """Print formatted summary."""
    s = output["summary"]
    logger.info("=" * 60)
    logger.info("STEP 5 RESULTS SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Papers organized:      {s['papers_organized']}")
    logger.info(f"  Both (T1+T2):        {s['both_count']}")
    logger.info(f"  Type 1 only:         {s['type1_only_count']}")
    logger.info(f"  Type 2 only:         {s['type2_only_count']}")
    logger.info(f"  Neither:             {s['neither_count']}")
    logger.info(f"Papers with PDF:        {s['papers_with_pdf']}")
    logger.info(f"Papers with summary:    {s['papers_with_dataset_summary']}")
    logger.info(f"Type 1 data files:     {s['total_type1_files']}")
    logger.info(f"Type 2 data files:     {s['total_type2_files']}")
    logger.info(f"Annotation files:      {s['total_annotation_files']}")
    logger.info(f"Script files:          {s['total_script_files']}")
    logger.info(f"PDF files:             {s['total_pdf_files']}")
    logger.info(f"Summary files:         {s['total_summary_files']}")
    logger.info(f"Reasoning files:       {s['total_reasoning_files']}")

    logger.info("-" * 60)
    for p in output["papers"]:
        c = p["counts"]
        pdf = "Y" if p["has_pdf"] else "N"
        tg = p.get("type_group", "?")
        logger.info(
            f"  {p['paper_index']:3d}. [{tg:>5}] [PDF:{pdf}] T1:{c['type1']:2d} T2:{c['type2']:2d} "
            f"| {p['title'][:45]}"
        )
