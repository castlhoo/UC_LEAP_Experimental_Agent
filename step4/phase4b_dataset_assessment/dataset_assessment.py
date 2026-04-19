"""Step 4B: dataset-level assessment derived from Prompt B."""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from step4.gpt_client import CLASSIFY_SYSTEM, call_gpt_json, render_prompt
from step4.shared.formatters import (
    format_discovery_evidence,
    format_file_overview,
    format_paper_analysis,
)

logger = logging.getLogger(__name__)


def assess_dataset_level(
    paper: Dict[str, Any],
    file_reports: List[Dict[str, Any]],
    model: str = "gpt-5.4-mini",
    paper_analysis: Optional[Dict[str, Any]] = None,
    paper_dir: str = "",
) -> Dict[str, Any]:
    """Run Step 4B and persist the dataset-level assessment."""
    prompt = render_prompt(
        "phase4b_dataset_assessment/prompt.md",
        title=paper.get("title", ""),
        journal=paper.get("journal", ""),
        abstract=paper.get("abstract_summary", ""),
        discovery_evidence=format_discovery_evidence(paper),
        paper_analysis=format_paper_analysis(paper_analysis, include_figures=False),
        file_overview=format_file_overview(file_reports),
    )

    try:
        assessment = call_gpt_json(
            prompt=prompt,
            system_prompt=CLASSIFY_SYSTEM,
            model=model,
            temperature=0.2,
            max_tokens=4000,
        )
    except Exception as e:
        logger.warning(f"Dataset-level assessment failed: {e}")
        assessment = _failed_assessment(e)

    if paper_dir:
        _write_dataset_assessment(paper_dir, assessment)
    return assessment


def _failed_assessment(error: Exception) -> Dict[str, Any]:
    return {
        "dataset_overview": "",
        "paper_dataset_link": "",
        "scientific_context": "",
        "data_contents_summary": "",
        "data_modalities": [],
        "data_generation_or_processing": "",
        "field_match": "weak",
        "field_match_reasoning": f"Assessment failed: {error}",
        "likely_dataset_structure": "unclear",
        "type_classification_plan": {
            "likely_type1_evidence": "",
            "likely_type2_evidence": "",
            "files_or_groups_to_prioritize": [],
        },
        "out_of_scope": False,
        "out_of_scope_reason": "",
        "notes": f"Dataset-level assessment failed: {error}",
    }


def _write_dataset_assessment(paper_dir: str, assessment: Dict[str, Any]) -> None:
    assessment_dir = os.path.join(paper_dir, "assessment")
    os.makedirs(assessment_dir, exist_ok=True)
    path = os.path.join(assessment_dir, "dataset_assessment.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(assessment, f, ensure_ascii=False, indent=2)
