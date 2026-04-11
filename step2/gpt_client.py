"""
Step 2 - GPT Client
=====================
GPT integration for Step 2 tasks:
  - Analyze paper metadata to find data availability hints
  - Summarize inventory contents and assess dataset relevance
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

from openai import OpenAI
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Reuse .env from project root
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_project_root, ".env"))

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    """Lazy-init OpenAI client."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your-api-key-here":
            raise ValueError(
                "OPENAI_API_KEY not set. Edit .env file in project root."
            )
        _client = OpenAI(api_key=api_key)
    return _client


def call_gpt_json(
    prompt: str,
    system_prompt: str = "",
    model: str = "gpt-5.4-mini",
    temperature: float = 0.2,
    max_tokens: int = 1500,
) -> Dict[str, Any]:
    """Call GPT and parse JSON response."""
    client = _get_client()
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_completion_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"GPT returned invalid JSON: {e}")
        raise
    except Exception as e:
        logger.error(f"GPT API error: {e}")
        raise


# ===================================================================
# Inventory Summary & Assessment
# ===================================================================

INVENTORY_SYSTEM = """You are an expert in condensed matter physics and materials science data.
Your task is to analyze a dataset repository's file inventory, assess its contents,
and classify the dataset type. Return structured JSON. Be concise and accurate."""

INVENTORY_PROMPT_TEMPLATE = """Analyze this dataset inventory for a condensed matter / materials science paper.

Paper title: {paper_title}
Paper abstract summary: {abstract_summary}
Repository type: {repo_type}
Repository title: {repo_title}
Repository description: {repo_description}

Files in the repository:
{file_list}

Return JSON:
{{
  "summary": "1-2 sentence description of what data is in this repository",
  "data_types": ["list of data types found, e.g. 'transport measurements', 'XRD spectra', 'STM images'"],
  "file_formats": ["list of unique file formats/extensions found"],
  "has_raw_data": {{
    "flag": true/false,
    "detail": "brief explanation"
  }},
  "has_processed_data": {{
    "flag": true/false,
    "detail": "brief explanation"
  }},
  "has_code": {{
    "flag": true/false,
    "detail": "brief explanation"
  }},
  "dataset_type": "type1" | "type2" | "both" | "unknown",
  "type1_evidence": "evidence for clean/replot-ready data, or 'none'",
  "type2_evidence": "evidence for raw measurement data, or 'none'",
  "confidence": "high" | "medium" | "low",
  "evidence_for": ["short supporting evidence"],
  "evidence_against": ["short contradictory or missing evidence"],
  "recommended_status": "verified" | "source_data_found" | "link_found" | "unclassified_link" | "no_dataset_found",
  "needs_human_review": true | false,
  "replot_feasibility": "high" | "medium" | "low" | "unknown",
  "replot_reason": "brief reason for feasibility assessment",
  "relevance_to_paper": "high" | "medium" | "low"
}}

Definitions:
- has_raw_data: Original measurement files (e.g., .dat, .nxs, .h5, raw images, instrument output)
- has_processed_data: Cleaned/analyzed data (e.g., .csv, .xlsx, .txt with columns, figure source data)
- has_code: Analysis scripts (e.g., .py, .m, .ipynb, .R)
- dataset_type:
  - "type1": Clean, figure-replot-ready dataset. Tabular data (.csv, .xlsx, .txt) with clear
    column headers, or organized figure source data. Can be directly loaded and plotted.
    Examples: FigureData/ folders, Source_Data.xlsx, plot_data.csv
  - "type2": Raw measurement dataset. Original instrument output files that need processing
    before plotting. Examples: .h5, .nxs, .dat, .spe, raw images, binary formats
  - "both": Contains both type1 and type2 data (e.g., raw/ + processed/ directories)
  - "unknown": Cannot determine from file listing alone
- replot_feasibility: How easy to re-create figures from this data
  - "high": tabular data with clear columns, can directly plot
  - "medium": data present but needs some processing
  - "low": raw instrument data, complex formats
  - "unknown": can't determine from file listing alone"""


def gpt_assess_inventory(
    paper: Dict[str, Any],
    inventory: Dict[str, Any],
    model: str = "gpt-5.4-mini",
) -> Dict[str, Any]:
    """
    Use GPT to assess an inventory's contents and relevance.

    Returns:
        Assessment dict with summary, data types, feasibility, etc.
    """
    # Build file list string
    files = inventory.get("files", [])
    if not files:
        return _empty_assessment("No files in inventory")

    file_lines = []
    for f in files[:50]:  # Limit to 50 files
        name = f.get("filename", "unknown")
        size = f.get("size_human", "?")
        file_lines.append(f"  - {name} ({size})")

    if len(files) > 50:
        file_lines.append(f"  ... and {len(files) - 50} more files")

    file_list_str = "\n".join(file_lines)

    prompt = INVENTORY_PROMPT_TEMPLATE.format(
        paper_title=paper.get("title", ""),
        abstract_summary=paper.get("abstract_summary", ""),
        repo_type=inventory.get("repo_type", "unknown"),
        repo_title=inventory.get("title", ""),
        repo_description=inventory.get("description", "")[:300],
        file_list=file_list_str,
    )

    try:
        result = call_gpt_json(
            prompt=prompt,
            system_prompt=INVENTORY_SYSTEM,
            model=model,
            temperature=0.2,
            max_tokens=800,
        )
        return result
    except Exception as e:
        logger.warning(f"GPT inventory assessment failed: {e}")
        return _empty_assessment(f"GPT error: {e}")


def _empty_assessment(reason: str) -> Dict[str, Any]:
    """Return empty assessment when GPT fails or no data."""
    return {
        "summary": reason,
        "data_types": [],
        "file_formats": [],
        "has_raw_data": {"flag": False, "detail": reason},
        "has_processed_data": {"flag": False, "detail": reason},
        "has_code": {"flag": False, "detail": reason},
        "dataset_type": "unknown",
        "type1_evidence": "none",
        "type2_evidence": "none",
        "confidence": "low",
        "evidence_for": [],
        "evidence_against": [reason],
        "recommended_status": "no_dataset_found",
        "needs_human_review": True,
        "replot_feasibility": "unknown",
        "replot_reason": reason,
        "relevance_to_paper": "unknown",
    }
