"""
Step 3 - GPT Client for Dataset Type Classification
======================================================
Classify datasets based on actual file contents:
  - Type 1: Cleaned, annotated, figure-replot-ready data
  - Type 2: Raw/unprocessed measurement data
Uses file inspection reports (headers, shapes, samples) NOT just filenames.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

from openai import OpenAI
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    """Get or create OpenAI client."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not found in .env")
        _client = OpenAI(api_key=api_key)
    return _client


def call_gpt_json(
    prompt: str,
    system_prompt: str = "",
    model: str = "gpt-5.4-mini",
    temperature: float = 0.2,
    max_tokens: int = 2000,
) -> Dict[str, Any]:
    """Call GPT and parse JSON response."""
    client = _get_client()
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_completion_tokens=max_tokens,
        response_format={"type": "json_object"},
    )

    text = resp.choices[0].message.content
    if not text:
        raise ValueError("GPT returned empty response")
    text = text.strip()
    # Handle cases where GPT wraps JSON in markdown code blocks
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return json.loads(text)


# ===================================================================
# Paper Analysis Prompt (1st GPT call — read the paper)
# ===================================================================

PAPER_ANALYSIS_SYSTEM = """You are an expert in condensed matter physics and materials science.
You carefully read scientific papers and extract BOTH scientific understanding and dataset semantics.
You must distinguish between raw data, processed data, figure data, and scripts based on the paper.
Return structured JSON."""

PAPER_ANALYSIS_PROMPT = """Read this condensed matter / materials science paper and extract BOTH:

(1) Scientific understanding of the paper
(2) Dataset semantics (how data is generated, processed, and provided)

Paper title: {title}
Paper journal: {journal}

=== PAPER TEXT ===
{paper_text}

=== TASK ===

Provide:

1. Scientific summary
2. Measurement types
3. Figure-level descriptions
4. Dataset semantics (VERY IMPORTANT)

=== OUTPUT FORMAT ===

Return JSON:

{{
  "summary": "2-3 sentence summary: material, technique, key findings",

  "measurement_types": [
    "e.g. STM topography",
    "transport",
    "ARPES",
    "XRD"
  ],

  "figures": [
    {{
      "figure_id": "Fig1a",
      "description": "what this figure shows",
      "data_type": "image / spectrum / transport curve / diffraction pattern",
      "likely_source": "raw measurement / processed data / derived"
    }}
  ],

  "has_raw_measurements": true/false,
  "raw_measurement_details": "what raw data was collected (e.g. STM scans, neutron spectra)",

  "has_processed_plots": true/false,
  "processed_plot_details": "what processed data is plotted",

  "dataset_characterization": {{
    "data_availability_statement": "summarize any statement about data availability in the paper",

    "data_provided_types": [
      "raw",
      "processed",
      "source_data",
      "scripts",
      "unknown"
    ],

    "raw_data_description": "how raw data is described in the paper (files, instruments, formats)",

    "processed_data_description": "how processed data is described (tables, extracted values, etc.)",

    "figure_data_description": "whether figure-specific data is provided (e.g. source data per figure)",

    "scripts_description": "whether analysis scripts or notebooks are mentioned",

    "data_organization": "e.g. figure-based folders / raw folders / mixed / not specified",

    "replot_ready_data_present": true/false,

    "replot_reason": "why the data is or is not directly usable for replotting",

    "notes": "any important observations about how data is structured or described"
  }},

  "classification_prior": {{
    "raw_data_expected": true/false,
    "source_data_expected": true/false,
    "both_expected": true/false,
    "raw_data_evidence": "brief evidence from the paper",
    "source_data_evidence": "brief evidence from the paper",
    "both_evidence": "brief evidence if both are implied, else 'none'",
    "data_availability_section_relevant": "important phrases from data availability / methods / figure captions",
    "priority_modalities": ["measurement or file modalities likely to appear in dataset"],
    "review_notes": "anything the classifier should be careful about"
  }}
}}

=== IMPORTANT RULES ===

1. Do NOT assume based only on general knowledge.
2. Use only evidence from the paper text.
3. Distinguish clearly between:
   - raw measurement data
   - processed/cleaned data
   - figure/source data
   - scripts
4. "Source data" usually means processed figure data, NOT raw data.
5. If unclear, say "unknown" instead of guessing.
6. Be concise but precise.
7. Focus especially on dataset semantics — this will be used for downstream classification.

Be thorough with figures (include supplementary if mentioned).
"""

def analyze_paper_text(
    paper: Dict[str, Any],
    paper_text: str,
    model: str = "gpt-5.4",
) -> Dict[str, Any]:
    """
    Analyze paper text to extract summary and figure descriptions.

    Args:
        paper: Paper metadata dict
        paper_text: Full text extracted from PDF
        model: GPT model to use

    Returns:
        Paper analysis dict with summary, figures, measurement types
    """
    if not paper_text or len(paper_text) < 200:
        return _empty_paper_analysis("Paper text too short or missing")

    # Retry with decreasing text length
    for max_text in [50000, 30000, 15000]:
        text_to_send = paper_text[:max_text]
        if len(paper_text) > max_text:
            text_to_send += "\n\n[... truncated ...]"

        prompt = PAPER_ANALYSIS_PROMPT.format(
            title=paper.get("title", ""),
            journal=paper.get("journal", ""),
            paper_text=text_to_send,
        )

        try:
            result = call_gpt_json(
                prompt=prompt,
                system_prompt=PAPER_ANALYSIS_SYSTEM,
                model=model,
                temperature=0.2,
                max_tokens=4000,
            )
            logger.info(f"  Paper analysis: {len(result.get('figures', []))} figures found")
            return result
        except ValueError as e:
            if "empty response" in str(e).lower():
                logger.info(f"  Empty response with {max_text} chars, retrying shorter...")
                continue
            logger.warning(f"  Paper analysis GPT failed: {e}")
            return _empty_paper_analysis(f"GPT error: {e}")
        except Exception as e:
            err_str = str(e)
            if "context_length_exceeded" in err_str or "too many tokens" in err_str.lower():
                logger.info(f"  Token overflow with {max_text} chars, retrying shorter...")
                continue
            logger.warning(f"  Paper analysis GPT failed: {e}")
            return _empty_paper_analysis(f"GPT error: {e}")

    logger.warning("  Paper analysis failed after all retries")
    return _empty_paper_analysis("Failed after retries with decreasing text length")


def _empty_paper_analysis(reason: str) -> Dict[str, Any]:
    """Return empty paper analysis."""
    return {
        "summary": "",
        "measurement_types": [],
        "figures": [],
        "has_raw_measurements": False,
        "raw_measurement_details": "",
        "has_processed_plots": False,
        "processed_plot_details": "",
        "dataset_characterization": {
            "data_availability_statement": "",
            "data_provided_types": [],
            "raw_data_description": "",
            "processed_data_description": "",
            "figure_data_description": "",
            "scripts_description": "",
            "data_organization": "",
            "replot_ready_data_present": False,
            "replot_reason": "",
            "notes": reason,
        },
        "classification_prior": {
            "raw_data_expected": False,
            "source_data_expected": False,
            "both_expected": False,
            "raw_data_evidence": "",
            "source_data_evidence": "",
            "both_evidence": "none",
            "data_availability_section_relevant": "",
            "priority_modalities": [],
            "review_notes": reason,
        },
        "notes": reason,
    }


# ===================================================================
# Type Classification Prompt (2nd GPT call — classify files)
# ===================================================================

CLASSIFY_SYSTEM = """You are an expert in condensed matter physics and materials science datasets.
Your task is to classify dataset files into Type 1 and Type 2 based on BOTH paper evidence and file evidence.
You must follow a structured reasoning process and be precise, conservative, and evidence-based. Return structured JSON."""

CLASSIFY_PROMPT = """Analyze these dataset files from a condensed matter / materials science paper and classify each file.

Paper title: {title}
Paper journal: {journal}
Paper abstract: {abstract}

=== PAPER ANALYSIS (from reading the full publication) ===
{paper_analysis}

=== RULE-BASED PRIOR ===
{rule_prior}

=== FILE INSPECTION REPORTS ===
{file_reports}

=== CLASSIFICATION DEFINITIONS ===

Type 1 (Cleaned, replot-ready):
- Tabular data (CSV, XLSX, TXT) with column headers naming physical variables
- Organized as figure-specific data (e.g., "Fig1", "Figure_3e", "FigS4")
- Small-to-moderate file sizes appropriate for figure data
- Can be directly loaded and plotted with minimal processing
- "Source Data" deposits organized by figure = Type 1 (source data ≠ raw data)

Type 2 (Raw/unprocessed):
- Instrument output: binary/proprietary formats, microscopy images, HDF5, etc.
- Files named after scans, experiments, or instrument runs
- Files requiring processing scripts to generate figures
- Files explicitly described as raw in the paper
- Large files significantly bigger than typical figure datasets
- Data requiring significant preprocessing before plotting

=== IMPORTANT REASONING RULES ===

1. Do NOT classify based on file extension alone.
2. Do NOT classify based on filename alone.
3. Use BOTH:
   - Paper evidence (statements from the publication)
   - File evidence (structure, format, content)
4. If paper evidence and file evidence conflict:
   - Explicitly describe the conflict
   - Resolve conservatively
5. If the paper explicitly states data is raw → prioritize that (Type 2)
6. If the paper explicitly states data is figure/source data → prioritize that (Type 1)

=== REASONING PROCEDURE ===

For each file, follow this step-by-step reasoning:

Step A. Paper Evidence
- Identify any statements about whether the dataset is raw, processed, or figure data

Step B. File Evidence
- Inspect filename, extension, size, structure, headers, sheet names

Step C. Functional Role
- Determine if the file is:
  - figure-ready data
  - raw measurement data
  - script
  - documentation
  - other

Step D. Replot Test
- Can this file be directly plotted with minimal processing?
  → Yes → supports Type 1
  → No → supports Type 2

Step E. Conflict Handling
- If ambiguous, explain why
- Do NOT silently guess

Step F. Final Decision
- Assign type only after completing reasoning

=== OUTPUT FORMAT ===

Return JSON:
{{
  "file_classifications": [
    {{
      "relative_path": "...",
      "filename": "...",
      "type": "type1" | "type2" | "script" | "documentation" | "other",
      "paper_evidence": "brief paper-based evidence",
      "file_evidence": "brief file-based evidence",
      "reasoning": "how the final decision was made",
      "ambiguity": "none or explanation if uncertain",
      "key_columns_or_structure": "e.g., Temperature(K), Magnetization(emu/g)"
    }}
  ],
  "has_type1": true/false,
  "has_type2": true/false,
  "has_both": true/false,
  "type1_summary": "...",
  "type2_summary": "...",
  "rule_based_alignment": "whether the final decision agrees with the rule-based prior, and why",
  "type1_files": ["..."],
  "type2_files": ["..."],
  "confidence": "high" | "medium" | "low",
  "notes": "important observations"
}}
"""


def classify_dataset_types(
    paper: Dict[str, Any],
    file_reports: List[Dict[str, Any]],
    model: str = "gpt-5.4",
    paper_analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Classify dataset files into Type 1 / Type 2 based on actual file content
    and paper analysis.

    Args:
        paper: Paper metadata dict
        file_reports: List of file inspection reports from file_inspector
        model: GPT model to use
        paper_analysis: Optional paper analysis from analyze_paper_text()

    Returns:
        Classification result dict
    """
    if not file_reports:
        return _empty_classification("No files to classify")

    rule_prior = _compute_rule_based_prior(file_reports, paper_analysis)
    selected_reports = _select_balanced_reports(file_reports, rule_prior)
    rule_prior_str = _format_rule_prior(rule_prior)

    # Try with up to 20 files first, then retry with fewer on token overflow
    for max_files in [20, 10, 5]:
        truncated_reports = selected_reports[:max_files]
        reports_str = _format_file_reports(truncated_reports)
        if len(selected_reports) > max_files:
            reports_str += f"\n\n(Showing {max_files} of {len(selected_reports)} selected files; {len(file_reports)} total inspected)"

        # Format paper analysis section
        analysis_str = _format_paper_analysis(paper_analysis)

        prompt = CLASSIFY_PROMPT.format(
            title=paper.get("title", ""),
            journal=paper.get("journal", ""),
            abstract=paper.get("abstract_summary", ""),
            paper_analysis=analysis_str,
            rule_prior=rule_prior_str,
            file_reports=reports_str,
        )

        try:
            result = call_gpt_json(
                prompt=prompt,
                system_prompt=CLASSIFY_SYSTEM,
                model=model,
                temperature=0.2,
                max_tokens=3000,
            )
            for fc in result.get("file_classifications", []):
                if "relative_path" not in fc:
                    fc["relative_path"] = ""
            result.setdefault("rule_based_alignment", "")
            result.setdefault("rule_prior", rule_prior)
            result = _reconcile_rule_and_gpt(result, rule_prior)
            return result
        except ValueError as e:
            # Empty response — retry with fewer files
            if "empty response" in str(e).lower():
                logger.info(f"Empty GPT response with {max_files} files, retrying with fewer...")
                continue
            logger.warning(f"GPT classification failed: {e}")
            return _empty_classification(f"GPT error: {e}")
        except Exception as e:
            err_str = str(e)
            if "context_length_exceeded" in err_str or "too many tokens" in err_str.lower():
                logger.info(f"Token overflow with {max_files} files, retrying with fewer...")
                continue
            logger.warning(f"GPT classification failed: {e}")
            return _empty_classification(f"GPT error: {e}")

    logger.warning("GPT classification failed after all retries")
    return _empty_classification("Token limit exceeded even with 5 files")


def _format_paper_analysis(analysis: Optional[Dict[str, Any]]) -> str:
    """Format paper analysis dict into a readable string for the classification prompt."""
    if not analysis or not analysis.get("summary"):
        return "(Paper analysis not available — classify based on file inspection only)"

    lines = []
    lines.append(f"Summary: {analysis.get('summary', '')}")

    mtypes = analysis.get("measurement_types", [])
    if mtypes:
        lines.append(f"Measurement types: {', '.join(mtypes)}")

    if analysis.get("has_raw_measurements"):
        lines.append(f"Raw measurements: {analysis.get('raw_measurement_details', '')}")
    if analysis.get("has_processed_plots"):
        lines.append(f"Processed plots: {analysis.get('processed_plot_details', '')}")

    dataset_char = analysis.get("dataset_characterization", {}) or {}
    if dataset_char.get("data_availability_statement"):
        lines.append(f"Data availability: {dataset_char.get('data_availability_statement', '')}")
    provided_types = dataset_char.get("data_provided_types", [])
    if provided_types:
        lines.append(f"Data provided types: {', '.join(provided_types)}")
    if dataset_char.get("data_organization"):
        lines.append(f"Data organization: {dataset_char.get('data_organization', '')}")

    prior = analysis.get("classification_prior", {}) or {}
    if prior:
        lines.append("Classification prior:")
        lines.append(f"  raw_data_expected: {prior.get('raw_data_expected', False)}")
        lines.append(f"  source_data_expected: {prior.get('source_data_expected', False)}")
        lines.append(f"  both_expected: {prior.get('both_expected', False)}")
        if prior.get("raw_data_evidence"):
            lines.append(f"  raw_data_evidence: {prior.get('raw_data_evidence', '')}")
        if prior.get("source_data_evidence"):
            lines.append(f"  source_data_evidence: {prior.get('source_data_evidence', '')}")
        if prior.get("both_evidence"):
            lines.append(f"  both_evidence: {prior.get('both_evidence', '')}")
        if prior.get("priority_modalities"):
            lines.append(f"  priority_modalities: {', '.join(prior.get('priority_modalities', []))}")

    figures = analysis.get("figures", [])
    if figures:
        lines.append(f"\nFigures ({len(figures)}):")
        for fig in figures:
            fid = fig.get("figure_id", "?")
            desc = fig.get("description", "?")
            dtype = fig.get("data_type", "?")
            src = fig.get("likely_source", "?")
            lines.append(f"  {fid}: {desc} [{dtype}] (source: {src})")

    return "\n".join(lines)


def _compute_rule_based_prior(
    file_reports: List[Dict[str, Any]],
    paper_analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    type1_score = 0
    type2_score = 0
    type1_signals: List[str] = []
    type2_signals: List[str] = []

    for report in file_reports:
        ext = (report.get("extension") or "").lower()
        file_type = report.get("file_type", "")
        rel = (report.get("relative_path") or report.get("filename") or "").lower()

        if ext in {".csv", ".tsv", ".xlsx", ".xls"}:
            type1_score += 2
            type1_signals.append(f"{rel}: tabular extension")
        if file_type in {"tabular_text", "excel"}:
            type1_score += 2
            type1_signals.append(f"{rel}: structured tabular file")
        if any(token in rel for token in ("fig", "figure", "source", "plot")):
            type1_score += 2
            type1_signals.append(f"{rel}: figure/source-like naming")
        if report.get("has_header") or any(sheet.get("has_header") for sheet in report.get("sheets", [])):
            type1_score += 1
            type1_signals.append(f"{rel}: header-like structure")

        if ext in {".h5", ".hdf5", ".nxs", ".mat", ".sxm", ".ibw", ".spe"}:
            type2_score += 3
            type2_signals.append(f"{rel}: raw/instrument extension")
        if file_type in {"instrument_raw", "microscopy_image", "hdf5"}:
            type2_score += 3
            type2_signals.append(f"{rel}: raw/instrument file type")
        if ext in {".zip", ".tar.gz", ".gz"}:
            type2_score += 1
            type2_signals.append(f"{rel}: archive may contain raw data")
        if (report.get("size_bytes") or 0) > 10_000_000:
            type2_score += 1
            type2_signals.append(f"{rel}: large file size")

    prior = (paper_analysis or {}).get("classification_prior", {}) or {}
    if prior.get("raw_data_expected"):
        type2_score += 2
        type2_signals.append(f"paper prior: {prior.get('raw_data_evidence', 'raw data expected')}")
    if prior.get("source_data_expected"):
        type1_score += 2
        type1_signals.append(f"paper prior: {prior.get('source_data_evidence', 'source/processed data expected')}")
    if prior.get("both_expected"):
        type1_score += 1
        type2_score += 1
        type1_signals.append(f"paper prior both: {prior.get('both_evidence', 'both expected')}")
        type2_signals.append(f"paper prior both: {prior.get('both_evidence', 'both expected')}")

    both_candidate = type1_score >= 4 and type2_score >= 4
    return {
        "type1_score": type1_score,
        "type2_score": type2_score,
        "both_candidate": both_candidate,
        "type1_signals": type1_signals[:12],
        "type2_signals": type2_signals[:12],
    }


def _bucket_report(report: Dict[str, Any]) -> str:
    ext = (report.get("extension") or "").lower()
    file_type = report.get("file_type", "")
    rel = (report.get("relative_path") or report.get("filename") or "").lower()

    if file_type in {"tabular_text", "excel"} or ext in {".csv", ".tsv", ".xlsx", ".xls"}:
        return "type1"
    if any(token in rel for token in ("fig", "figure", "source", "plot")):
        return "type1"
    if file_type in {"instrument_raw", "microscopy_image", "hdf5"} or ext in {".h5", ".hdf5", ".nxs", ".mat", ".sxm", ".ibw", ".spe", ".tif", ".tiff"}:
        return "type2"
    if file_type in {"script", "pdf"} or ext in {".py", ".ipynb", ".m", ".r", ".jl", ".sh", ".pdf"}:
        return "support"
    return "unclear"


def _select_balanced_reports(
    file_reports: List[Dict[str, Any]],
    rule_prior: Dict[str, Any],
) -> List[Dict[str, Any]]:
    buckets = {"type1": [], "type2": [], "support": [], "unclear": []}
    for report in file_reports:
        buckets[_bucket_report(report)].append(report)

    selected: List[Dict[str, Any]] = []
    selected.extend(buckets["type1"][:6])
    selected.extend(buckets["type2"][:6])
    selected.extend(buckets["support"][:2])
    selected.extend(buckets["unclear"][:4])

    if rule_prior.get("both_candidate"):
        selected.extend(buckets["type1"][6:8])
        selected.extend(buckets["type2"][6:8])

    # Preserve original order for readability while deduplicating.
    seen = set()
    ordered = []
    selected_keys = {
        (r.get("relative_path") or r.get("filename") or "")
        for r in selected
    }
    for report in file_reports:
        key = report.get("relative_path") or report.get("filename") or ""
        if key in selected_keys and key not in seen:
            seen.add(key)
            ordered.append(report)
    return ordered


def _format_rule_prior(rule_prior: Dict[str, Any]) -> str:
    lines = [
        f"type1_score: {rule_prior.get('type1_score', 0)}",
        f"type2_score: {rule_prior.get('type2_score', 0)}",
        f"both_candidate: {rule_prior.get('both_candidate', False)}",
    ]
    t1 = rule_prior.get("type1_signals", [])
    t2 = rule_prior.get("type2_signals", [])
    if t1:
        lines.append("type1_signals:")
        lines.extend(f"  - {signal}" for signal in t1[:8])
    if t2:
        lines.append("type2_signals:")
        lines.extend(f"  - {signal}" for signal in t2[:8])
    return "\n".join(lines)


def _reconcile_rule_and_gpt(
    result: Dict[str, Any],
    rule_prior: Dict[str, Any],
) -> Dict[str, Any]:
    has_t1 = result.get("has_type1", False)
    has_t2 = result.get("has_type2", False)
    both = result.get("has_both", False)

    if rule_prior.get("both_candidate") and has_t1 and not has_t2:
        result["notes"] = f"{result.get('notes', '')} Rule-based prior suggests hidden Type 2 evidence; review recommended.".strip()
        result["confidence"] = "medium" if result.get("confidence") == "high" else result.get("confidence", "medium")
    if rule_prior.get("both_candidate") and has_t2 and not has_t1:
        result["notes"] = f"{result.get('notes', '')} Rule-based prior suggests hidden Type 1 evidence; review recommended.".strip()
        result["confidence"] = "medium" if result.get("confidence") == "high" else result.get("confidence", "medium")
    if rule_prior.get("both_candidate") and both:
        result["rule_based_alignment"] = "Rule-based prior and GPT both indicate both-type data."
    elif rule_prior.get("both_candidate") and not both:
        result["rule_based_alignment"] = "Rule-based prior indicates both-type evidence, but GPT did not fully confirm both."
    else:
        result["rule_based_alignment"] = "Rule-based prior is broadly consistent with GPT output."
    return result


def _format_file_reports(reports: List[Dict[str, Any]]) -> str:
    """Format file inspection reports into a readable string for GPT."""
    parts = []
    for i, r in enumerate(reports[:30]):  # Limit to 30 files
        display_name = r.get("relative_path") or r.get("filename", "?")
        lines = [f"--- File {i+1}: {display_name} ---"]
        if r.get("relative_path"):
            lines.append(f"  Relative path: {r['relative_path']}")
        lines.append(f"  Type: {r.get('file_type', '?')}")
        lines.append(f"  Size: {r.get('size_human', '?')}")
        lines.append(f"  Source: {r.get('download_source', '?')}")
        if r.get("from_zip"):
            lines.append(f"  Extracted from ZIP: {r['from_zip']}")

        if r.get("error"):
            lines.append(f"  Error: {r['error']}")

        # Tabular text
        if r.get("file_type") == "tabular_text":
            lines.append(f"  Columns ({r.get('column_count', '?')}): {r.get('columns', [])}")
            lines.append(f"  Rows: {r.get('row_count', '?')}")
            lines.append(f"  Has header: {r.get('has_header', '?')}")
            lines.append(f"  Has numeric: {r.get('has_numeric_data', '?')}")
            lines.append(f"  Dtypes: {r.get('dtypes', {})}")
            if r.get("sample_rows"):
                lines.append(f"  Sample row: {r['sample_rows'][0]}")

        # Excel
        elif r.get("file_type") == "excel":
            snames = r.get('sheet_names', [])[:10]
            lines.append(f"  Sheets ({r.get('sheet_count', '?')}): {snames}")
            for sheet in r.get("sheets", [])[:5]:
                if sheet.get("error"):
                    lines.append(f"    Sheet '{sheet.get('sheet_name','?')}': ERROR {sheet['error'][:80]}")
                    continue
                ncols = sheet.get('column_count', '?')
                nrows = sheet.get('row_count', '?')
                lines.append(f"    Sheet '{sheet.get('sheet_name','?')}': {ncols} cols x {nrows} rows")
                # Prefer named_columns (excludes 'Unnamed') for concise output
                cols = sheet.get('named_columns') or sheet.get('columns', [])
                cols_display = cols[:15]
                extra = len(cols) - 15 if len(cols) > 15 else 0
                cols_str = str(cols_display)
                if extra > 0:
                    cols_str += f" ... +{extra} more"
                lines.append(f"    Key columns: {cols_str}")
                lines.append(f"    Has header: {sheet.get('has_header', '?')}")

        # HDF5
        elif r.get("file_type") == "hdf5":
            lines.append(f"  Groups ({r.get('group_count', '?')}): {r.get('groups', [])[:10]}")
            lines.append(f"  Datasets ({r.get('dataset_count', '?')}):")
            for ds in r.get("datasets", [])[:10]:
                lines.append(f"    {ds['path']}: shape={ds['shape']}, dtype={ds['dtype']}")

        # JSON
        elif r.get("file_type") == "json":
            lines.append(f"  Structure: {r.get('structure', '?')}")
            if r.get("keys"):
                lines.append(f"  Keys: {r['keys']}")

        # Numpy
        elif r.get("file_type") == "numpy":
            if r.get("arrays"):
                for k, v in r["arrays"].items():
                    lines.append(f"  Array '{k}': shape={v.get('shape')}, dtype={v.get('dtype')}")
            elif r.get("shape"):
                lines.append(f"  Shape: {r['shape']}, dtype: {r.get('dtype')}")

        # Microscopy / instrument raw / script
        elif r.get("file_type") in ("microscopy_image", "instrument_raw", "script"):
            if r.get("note"):
                lines.append(f"  Note: {r['note']}")

        parts.append("\n".join(lines))

    return "\n\n".join(parts)


def _empty_classification(reason: str) -> Dict[str, Any]:
    """Return empty classification when GPT fails or no data."""
    return {
        "file_classifications": [],
        "has_type1": False,
        "has_type2": False,
        "has_both": False,
        "type1_summary": "none",
        "type2_summary": "none",
        "rule_based_alignment": "",
        "rule_prior": {},
        "type1_files": [],
        "type2_files": [],
        "confidence": "low",
        "notes": reason,
    }
