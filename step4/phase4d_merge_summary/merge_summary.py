"""Step 4D: merge classifications and write summary dossiers."""

import copy
import json
import os
from datetime import datetime
from typing import Any, Dict, List

from step4.phase4c_file_classification.file_classification import (
    final_classification_label,
    normalize_classification,
)


def build_output(
    results: List[Dict[str, Any]],
    skipped_missing_analysis: List[Dict[str, Any]],
) -> Dict[str, Any]:
    papers = []

    for entry in results:
        paper = entry["paper"]
        dl = entry["download"]
        inspections = entry["inspections"]
        classification = normalize_classification(entry["classification"] or {})
        has_both = classification.get("has_both", False)
        final_classification = final_classification_label(classification)

        papers.append({
            "paper_id": paper.get("paper_id", ""),
            "title": paper.get("title", ""),
            "doi": paper.get("doi", ""),
            "journal": paper.get("journal", ""),
            "year": paper.get("year", ""),
            "paper_url": paper.get("paper_url", ""),
            "resolved_paper_pdf_url": paper.get("resolved_paper_pdf_url", ""),
            "paper_pdf_source": paper.get("paper_pdf_source", ""),
            "priority_score": paper.get("priority_score", 0),
            "screening_decision": paper.get("screening_decision", ""),
            "dataset_status": paper.get("dataset_status", ""),
            "verification_reasons": paper.get("verification_reasons", []),
            "needs_human_review": paper.get("needs_human_review", False),
            "source_urls": {
                "paper_pdf_urls": paper.get("paper_pdf_urls", []),
                "data_url_candidates": paper.get("data_url_candidates", []),
                "repository_urls": paper.get("repository_urls", []),
                "ambiguous_url_candidates": paper.get("ambiguous_url_candidates", []),
                "ignored_urls": paper.get("ignored_urls", []),
            },
            "files_downloaded": len(dl.get("files", [])),
            "files_extracted": len(dl.get("zip_extracted", [])),
            "file_organization": dl.get("organization", {}),
            "organized_files": dl.get("organized_files", []),
            "download_errors": dl.get("errors", []),
            "download_dir": dl.get("download_dir", ""),
            "files_inspected": len(inspections),
            "file_types_found": list(set(r.get("file_type", "?") for r in inspections)),
            "has_type1": classification.get("has_type1", False),
            "has_type2": classification.get("has_type2", False),
            "has_both_types": has_both,
            "final_classification": final_classification,
            "type1_summary": classification.get("type1_summary", "none"),
            "type2_summary": classification.get("type2_summary", "none"),
            "type1_files": classification.get("type1_files", []),
            "type2_files": classification.get("type2_files", []),
            "classification_confidence": classification.get("confidence", "low"),
            "classification_notes": classification.get("notes", ""),
            "classification_has_gpt_error": classification.get("classification_has_gpt_error", False),
            "dataset_assessment": classification.get("dataset_assessment", {}),
            "file_classifications": classification.get("file_classifications", []),
            "paper_analysis": entry.get("paper_analysis"),
            "inspection_reports": inspections,
        })

    papers.sort(key=_sort_key)

    both_count = sum(1 for p in papers if p["has_both_types"])
    t1_only = sum(1 for p in papers if p["has_type1"] and not p["has_type2"])
    t2_only = sum(1 for p in papers if p["has_type2"] and not p["has_type1"])
    neither = sum(1 for p in papers if not p["has_type1"] and not p["has_type2"])

    return {
        "metadata": {
            "step": 4,
            "description": "Prompt B Dataset Type Classification",
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
            "skipped_missing_step3_analysis": len(skipped_missing_analysis),
        },
        "both_types_papers": [p for p in papers if p["has_both_types"]],
        "all_papers": papers,
        "skipped_missing_step3_analysis": skipped_missing_analysis,
    }


def write_paper_dataset_summary(entry: Dict[str, Any]) -> None:
    """Write one per-paper dossier with discovery, inspection, and classification."""
    dl = entry.get("download", {})
    paper_dir = dl.get("download_dir", "")
    if not paper_dir:
        return

    summary_dir = os.path.join(paper_dir, "summary")
    os.makedirs(summary_dir, exist_ok=True)
    path = os.path.join(summary_dir, "paper_dataset_summary.json")

    payload = build_paper_dataset_summary(entry)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    dl.setdefault("organized_files", []).append({
        "from": "generated_paper_dataset_summary",
        "to": "summary/paper_dataset_summary.json",
        "folder": "summary",
    })
    org = dl.setdefault("organization", {"pdf": 0, "scripts": 0, "annotation": 0})
    org["summary"] = org.get("summary", 0) + 1


def build_paper_dataset_summary(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Build a single human-readable JSON dossier for one paper/dataset."""
    paper = entry.get("paper", {})
    download = entry.get("download", {})
    inspections = entry.get("inspections", [])
    classification = normalize_classification(entry.get("classification", {}) or {})
    paper_analysis = entry.get("paper_analysis", {}) or {}
    dataset_char = paper_analysis.get("dataset_characterization", {}) or {}
    classification_prior = paper_analysis.get("classification_prior", {}) or {}

    return {
        "paper": {
            "paper_id": paper.get("paper_id", ""),
            "title": paper.get("title", ""),
            "doi": paper.get("doi", ""),
            "journal": paper.get("journal", ""),
            "year": paper.get("year", ""),
            "paper_url": paper.get("paper_url", ""),
            "resolved_paper_pdf_url": paper.get("resolved_paper_pdf_url", ""),
            "paper_pdf_source": paper.get("paper_pdf_source", ""),
        },
        "why_selected": {
            "screening_decision": paper.get("screening_decision", ""),
            "priority_score": paper.get("priority_score", 0),
            "dataset_status": paper.get("dataset_status", ""),
            "verification_reasons": paper.get("verification_reasons", []),
            "needs_human_review": paper.get("needs_human_review", False),
            "abstract_summary": paper.get("abstract_summary", ""),
        },
        "source_urls": {
            "paper_pdf_urls": paper.get("paper_pdf_urls", []),
            "data_url_candidates": paper.get("data_url_candidates", []),
            "repository_urls": paper.get("repository_urls", []),
            "ambiguous_url_candidates": paper.get("ambiguous_url_candidates", []),
            "ignored_urls": paper.get("ignored_urls", []),
        },
        "paper_topic_and_dataset_semantics": {
            "scientific_summary": paper_analysis.get("summary", ""),
            "measurement_types": paper_analysis.get("measurement_types", []),
            "data_availability_statement": dataset_char.get("data_availability_statement", ""),
            "data_provided_types": dataset_char.get("data_provided_types", []),
            "raw_data_description": dataset_char.get("raw_data_description", ""),
            "processed_data_description": dataset_char.get("processed_data_description", ""),
            "figure_data_description": dataset_char.get("figure_data_description", ""),
            "scripts_description": dataset_char.get("scripts_description", ""),
            "expected_raw_file_extensions": dataset_char.get("expected_raw_file_extensions", []),
            "classification_prior": classification_prior,
        },
        "download_and_organization": {
            "download_dir": download.get("download_dir", ""),
            "files_downloaded": len(download.get("files", [])),
            "files_extracted": len(download.get("zip_extracted", [])),
            "download_errors": download.get("errors", []),
            "organization": download.get("organization", {}),
            "organized_files": download.get("organized_files", []),
        },
        "dataset_contents": summarize_inspections(inspections),
        "type_classification": {
            "dataset_assessment": classification.get("dataset_assessment", {}),
            "has_type1": classification.get("has_type1", False),
            "has_type2": classification.get("has_type2", False),
            "has_both": classification.get("has_both", False),
            "final_classification": final_classification_label(classification),
            "type1_summary": classification.get("type1_summary", "none"),
            "type2_summary": classification.get("type2_summary", "none"),
            "type1_files": classification.get("type1_files", []),
            "type2_files": classification.get("type2_files", []),
            "data_organization": classification.get("data_organization", ""),
            "replot_ready_data_present": classification.get("replot_ready_data_present", False),
            "replot_reason": classification.get("replot_reason", ""),
            "confidence": classification.get("confidence", "low"),
            "notes": classification.get("notes", ""),
            "classification_has_gpt_error": classification.get("classification_has_gpt_error", False),
            "file_classifications": classification.get("file_classifications", []),
        },
    }


def summarize_inspections(inspections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize inspected files without embedding bulky samples or local paths."""
    type_counts: Dict[str, int] = {}
    files = []

    for report in inspections:
        file_type = report.get("file_type", "unknown")
        type_counts[file_type] = type_counts.get(file_type, 0) + 1
        item = {
            "relative_path": report.get("relative_path", ""),
            "filename": report.get("filename", ""),
            "file_type": file_type,
            "size_human": report.get("size_human", ""),
            "download_source": report.get("download_source", ""),
            "from_zip": report.get("from_zip", ""),
        }
        if report.get("columns"):
            item["columns"] = report.get("columns", [])[:30]
            item["row_count"] = report.get("row_count", "")
            item["has_header"] = report.get("has_header", "")
            item["has_numeric_data"] = report.get("has_numeric_data", "")
        if report.get("sheet_names"):
            item["sheet_names"] = report.get("sheet_names", [])[:30]
            item["sheet_count"] = report.get("sheet_count", "")
        if report.get("groups"):
            item["hdf5_groups"] = report.get("groups", [])[:30]
        if report.get("datasets"):
            item["hdf5_datasets"] = [
                {
                    "path": ds.get("path", ""),
                    "shape": ds.get("shape", ""),
                    "dtype": ds.get("dtype", ""),
                }
                for ds in report.get("datasets", [])[:30]
            ]
        if report.get("keys"):
            item["json_keys"] = report.get("keys", [])[:30]
        if report.get("note"):
            item["note"] = report.get("note", "")
        if report.get("error"):
            item["error"] = report.get("error", "")
        files.append(item)

    return {
        "files_inspected": len(inspections),
        "file_type_counts": type_counts,
        "files": files,
    }


def clean_for_json(output: Dict[str, Any]) -> Dict[str, Any]:
    clean = copy.deepcopy(output)

    for collection_name in ("all_papers", "both_types_papers"):
        for paper in clean.get(collection_name, []):
            for report in paper.get("inspection_reports", []):
                report.pop("sample_rows", None)
                report.pop("local_path", None)
                for sheet in report.get("sheets", []):
                    sheet.pop("sample_rows", None)

    return clean


def _sort_key(p: Dict[str, Any]):
    if p["has_both_types"]:
        tier = 0
    elif p["has_type1"]:
        tier = 1
    elif p["has_type2"]:
        tier = 2
    else:
        tier = 3
    return (tier, -p.get("priority_score", 0))
