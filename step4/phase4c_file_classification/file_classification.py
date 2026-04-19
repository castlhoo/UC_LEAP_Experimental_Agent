"""Step 4C: file-level Prompt B classification."""

import json
import logging
import os
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional

from step4.gpt_client import CLASSIFY_SYSTEM, call_gpt_json, render_prompt
from step4.shared.formatters import (
    brief_structure,
    format_dataset_assessment,
    format_discovery_evidence,
    format_file_reports,
    format_paper_analysis,
)

logger = logging.getLogger(__name__)


def classify_dataset_files(
    paper: Dict[str, Any],
    file_reports: List[Dict[str, Any]],
    dataset_assessment: Dict[str, Any],
    model: str = "gpt-5.4-mini",
    paper_analysis: Optional[Dict[str, Any]] = None,
    batch_size: int = 8,
    paper_dir: str = "",
) -> Dict[str, Any]:
    """Classify dataset files into Type 1 / Type 2 with Prompt B batches."""
    if not file_reports:
        return empty_classification("No files to classify")

    if dataset_assessment.get("out_of_scope") or dataset_assessment.get("field_match") == "none":
        classification = out_of_scope_classification(dataset_assessment, file_reports)
        if paper_dir:
            _write_batch_result(paper_dir, "out_of_scope", classification)
        return classification

    batch_size = max(1, batch_size)
    batches = [
        file_reports[i:i + batch_size]
        for i in range(0, len(file_reports), batch_size)
    ]

    batch_results: List[Dict[str, Any]] = []
    for idx, batch in enumerate(batches, start=1):
        logger.info(
            f"  Prompt B batch {idx}/{len(batches)}: "
            f"{len(batch)} files ({len(file_reports)} total inspected)"
        )
        batch_result = _classify_report_batch(
            paper=paper,
            reports=batch,
            model=model,
            paper_analysis=paper_analysis,
            dataset_assessment=dataset_assessment,
            batch_label=f"{idx}/{len(batches)}",
        )
        batch_results.append(batch_result)
        if paper_dir:
            _write_batch_result(paper_dir, f"batch_{idx:03d}", batch_result)

    merged = merge_batch_classifications(batch_results)
    merged["dataset_assessment"] = dataset_assessment
    return merged


def _classify_report_batch(
    paper: Dict[str, Any],
    reports: List[Dict[str, Any]],
    model: str,
    paper_analysis: Optional[Dict[str, Any]],
    dataset_assessment: Dict[str, Any],
    batch_label: str = "",
) -> Dict[str, Any]:
    """Run Prompt B on one batch; split recursively if JSON is invalid."""
    if not reports:
        return empty_classification("Empty batch")

    reports_str = format_file_reports(reports)
    if batch_label:
        reports_str += f"\n\n(Batch {batch_label}; classify only the files shown in this batch.)"

    prompt = render_prompt(
        "phase4c_file_classification/prompt.md",
        title=paper.get("title", ""),
        journal=paper.get("journal", ""),
        abstract=paper.get("abstract_summary", ""),
        discovery_evidence=format_discovery_evidence(paper),
        paper_analysis=format_paper_analysis(paper_analysis, include_figures=False),
        dataset_assessment=format_dataset_assessment(dataset_assessment),
        file_reports=reports_str,
    )

    try:
        result = call_gpt_json(
            prompt=prompt,
            system_prompt=CLASSIFY_SYSTEM,
            model=model,
            temperature=0.2,
            max_tokens=6000,
        )
        for fc in result.get("file_classifications", []):
            fc.setdefault("relative_path", "")
        return result
    except ValueError as e:
        err = str(e).lower()
        if _is_retryable_json_error(err) and len(reports) > 1:
            mid = max(1, len(reports) // 2)
            logger.info(
                f"Invalid/truncated GPT JSON for batch {batch_label}; "
                f"splitting {len(reports)} files into {mid}+{len(reports)-mid}"
            )
            left = _classify_report_batch(
                paper, reports[:mid], model, paper_analysis, dataset_assessment, f"{batch_label}a"
            )
            right = _classify_report_batch(
                paper, reports[mid:], model, paper_analysis, dataset_assessment, f"{batch_label}b"
            )
            return merge_batch_classifications([left, right])
        logger.warning(f"GPT classification failed: {e}")
        return empty_classification(f"GPT error: {e}")
    except Exception as e:
        err_str = str(e)
        if ("context_length_exceeded" in err_str or "too many tokens" in err_str.lower()) and len(reports) > 1:
            mid = max(1, len(reports) // 2)
            logger.info(
                f"Token overflow for batch {batch_label}; "
                f"splitting {len(reports)} files into {mid}+{len(reports)-mid}"
            )
            left = _classify_report_batch(
                paper, reports[:mid], model, paper_analysis, dataset_assessment, f"{batch_label}a"
            )
            right = _classify_report_batch(
                paper, reports[mid:], model, paper_analysis, dataset_assessment, f"{batch_label}b"
            )
            return merge_batch_classifications([left, right])
        logger.warning(f"GPT classification failed: {e}")
        return empty_classification(f"GPT error: {e}")


def _is_retryable_json_error(err: str) -> bool:
    return (
        "empty response" in err
        or "unterminated string" in err
        or "expecting value" in err
        or "expecting ',' delimiter" in err
        or "expecting property name" in err
        or "truncated" in err
    )


def merge_batch_classifications(batch_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge Prompt B JSON outputs into one paper-level classification."""
    file_classifications: List[Dict[str, Any]] = []
    notes: List[str] = []
    data_orgs: List[str] = []
    replot_reasons: List[str] = []
    confidences: List[str] = []

    for result in batch_results:
        file_classifications.extend(result.get("file_classifications", []))
        if result.get("notes"):
            notes.append(result.get("notes", ""))
        if result.get("data_organization"):
            data_orgs.append(result.get("data_organization", ""))
        if result.get("replot_reason"):
            replot_reasons.append(result.get("replot_reason", ""))
        confidences.append(result.get("confidence", "low"))

    return normalize_classification({
        "file_classifications": file_classifications,
        "data_organization": _join_unique(data_orgs) or "not specified",
        "replot_reason": _join_unique(replot_reasons),
        "confidence": _merge_confidence(confidences),
        "notes": _join_unique(notes),
    })


def out_of_scope_classification(
    dataset_assessment: Dict[str, Any],
    file_reports: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build a Prompt-B-shaped result when 4B determines out-of-scope."""
    reason = (
        dataset_assessment.get("out_of_scope_reason")
        or dataset_assessment.get("field_match_reasoning")
        or "Dataset-level assessment marked this paper/data out of project scope."
    )
    file_classifications = []
    for report in file_reports:
        file_type = report.get("file_type", "")
        if file_type == "script":
            label = "script"
        elif file_type in ("documentation", "pdf"):
            label = "documentation"
        else:
            label = "other"
        file_classifications.append({
            "relative_path": report.get("relative_path", ""),
            "filename": report.get("filename", ""),
            "type": label,
            "paper_evidence": dataset_assessment.get("field_match_reasoning", ""),
            "file_evidence": "Dataset-level assessment used inspected file evidence and marked the dataset out of target scope.",
            "reasoning": reason,
            "ambiguity": "none",
            "key_columns_or_structure": brief_structure(report),
        })
    return {
        "file_classifications": file_classifications,
        "has_type1": False,
        "has_type2": False,
        "has_both": False,
        "type1_summary": "none",
        "type2_summary": "none",
        "type1_files": [],
        "type2_files": [],
        "data_organization": dataset_assessment.get("likely_dataset_structure", "out-of-scope"),
        "replot_ready_data_present": False,
        "replot_reason": "Out of project scope after reviewing paper and file evidence.",
        "confidence": "high",
        "notes": reason,
        "dataset_assessment": dataset_assessment,
    }


def empty_classification(reason: str) -> Dict[str, Any]:
    return {
        "file_classifications": [],
        "has_type1": False,
        "has_type2": False,
        "has_both": False,
        "type1_summary": "none",
        "type2_summary": "none",
        "type1_files": [],
        "type2_files": [],
        "data_organization": "",
        "replot_ready_data_present": False,
        "replot_reason": "",
        "confidence": "low",
        "notes": reason,
    }


def normalize_classification(classification: Dict[str, Any]) -> Dict[str, Any]:
    """Apply deterministic non-data routing and recompute paper-level flags."""
    normalized = dict(classification or {})
    file_classifications = []

    for item in normalized.get("file_classifications", []) or []:
        fc = dict(item or {})
        coerced_type = _deterministic_non_data_type(fc)
        if coerced_type and fc.get("type") in ("type1", "type2"):
            fc["type"] = coerced_type
            fc.setdefault("reasoning", "")
            reason = (
                "Deterministic Step 4 validation: this artifact is not a "
                "Type 1/Type 2 data file and was removed from data-type counts."
            )
            fc["reasoning"] = _append_note(fc.get("reasoning", ""), reason)
        file_classifications.append(fc)

    type1_files = [
        fc.get("relative_path") or fc.get("filename", "")
        for fc in file_classifications
        if fc.get("type") == "type1"
    ]
    type2_files = [
        fc.get("relative_path") or fc.get("filename", "")
        for fc in file_classifications
        if fc.get("type") == "type2"
    ]
    type1_files = [f for f in type1_files if f]
    type2_files = [f for f in type2_files if f]
    has_type1 = bool(type1_files)
    has_type2 = bool(type2_files)

    normalized["file_classifications"] = file_classifications
    normalized["has_type1"] = has_type1
    normalized["has_type2"] = has_type2
    normalized["has_both"] = has_type1 and has_type2
    normalized["type1_files"] = type1_files
    normalized["type2_files"] = type2_files
    normalized["type1_summary"] = (
        f"{len(type1_files)} Type 1 file(s): cleaned/replot-ready, figure, processed, or simulation data."
        if has_type1 else "none"
    )
    normalized["type2_summary"] = (
        f"{len(type2_files)} Type 2 file(s): raw/unprocessed, instrument, run, or preprocessing-required data."
        if has_type2 else "none"
    )
    normalized["replot_ready_data_present"] = has_type1
    normalized["final_classification"] = final_classification_label(normalized)
    normalized["classification_has_gpt_error"] = _has_gpt_error(normalized)
    return normalized


def final_classification_label(classification: Dict[str, Any]) -> str:
    has_type1 = bool(classification.get("has_type1"))
    has_type2 = bool(classification.get("has_type2"))
    if has_type1 and has_type2:
        return "Both"
    if has_type1:
        return "Type1 only"
    if has_type2:
        return "Type2 only"
    return "Neither"


def _deterministic_non_data_type(fc: Dict[str, Any]) -> str:
    path = str(fc.get("relative_path") or fc.get("filename") or "")
    filename = str(fc.get("filename") or PurePosixPath(path.replace("\\", "/")).name)
    lower_path = path.replace("\\", "/").lower()
    lower_name = filename.lower()
    ext = os.path.splitext(lower_name)[1]

    if ext == ".pdf" or lower_path.startswith("pdf/"):
        return "documentation"
    if ext in {".py", ".m", ".ipynb", ".r", ".sh", ".nb"}:
        return "script"
    if (
        lower_name.startswith("readme")
        or "readme" in lower_name
        or "description" in lower_name
        or "manifest" in lower_name
        or ext in {".md", ".rst", ".yaml", ".yml"}
    ):
        return "documentation"
    return ""


def _append_note(existing: Any, note: str) -> str:
    text = " | ".join(_as_text_items(existing))
    if not text:
        return note
    if note in text:
        return text
    return f"{text} | {note}"


def _has_gpt_error(classification: Dict[str, Any]) -> bool:
    haystack = [
        classification.get("notes", ""),
        classification.get("replot_reason", ""),
    ]
    for fc in classification.get("file_classifications", []) or []:
        haystack.extend([
            fc.get("reasoning", ""),
            fc.get("file_evidence", ""),
            fc.get("paper_evidence", ""),
        ])
    text = " ".join(_as_text_items(haystack)).lower()
    return "gpt error" in text or "json parse error" in text or "unterminated string" in text


def _write_batch_result(paper_dir: str, name: str, result: Dict[str, Any]) -> None:
    batch_dir = os.path.join(paper_dir, "classification_batches")
    os.makedirs(batch_dir, exist_ok=True)
    path = os.path.join(batch_dir, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


def _join_unique(values: List[Any]) -> str:
    seen = set()
    unique = []
    for value in values:
        for item in _as_text_items(value):
            item = item.strip()
            if item and item not in seen:
                unique.append(item)
                seen.add(item)
    return " | ".join(unique)


def _as_text_items(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        items: List[str] = []
        for item in value:
            items.extend(_as_text_items(item))
        return items
    if isinstance(value, dict):
        return [json.dumps(value, ensure_ascii=False)]
    return [str(value)]


def _merge_confidence(confidences: List[str]) -> str:
    values = {c for c in confidences if c}
    if "low" in values:
        return "low"
    if "medium" in values:
        return "medium"
    if "high" in values:
        return "high"
    return "low"
