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
      "likely_source": "theoretical calculations or simulations / experimental data"
    }}
  ],

  "has_raw_measurements": true/false,
  "raw_measurement_details": "what raw data was collected (e.g. STM scans, neutron spectra)",

  "dataset_characterization": {{
    "data_availability_statement": "summarize any statement about data availability, downloadable data, or data uploaded to an open-access repository",

    "data_provided_types": [
      "raw",
      "processed",
      "theoretical_or_simulated",
      "scripts",
      "unknown"
    ],

    "raw_data_description": "how raw data is described in the paper (files, instruments, formats)",

    "processed_data_description": "how processed data is described (tables, extracted values, etc.)",

    "figure_data_description": "whether figure-specific data is provided (e.g. source data per figure)",

    "scripts_description": "whether analysis scripts or notebooks are mentioned",

    "notes": "any important observations about how data is structured or described"
  }},

  "classification_prior": {{
    "raw_data_expected": true/false,
    "source_data_expected": true/false,
    "raw_data_evidence": "brief evidence from the paper",
    "source_data_evidence": "brief evidence from the paper",
    "data_availability_section_relevant": "important phrases from data availability / methods / figure captions",
    "priority_modalities": ["measurement or file modalities likely to appear in dataset"]
  }}
}}

=== IMPORTANT RULES ===

1. Do NOT assume based only on general knowledge.
2. Use only evidence from the paper text.
3. Distinguish clearly between:
   - raw measurement data
   - processed/cleaned data
   - scripts
4. "Source data" often refers to processed figure-ready data, but it can also include raw data depending on the paper and repository context.
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
        "dataset_characterization": {
            "data_availability_statement": "",
            "data_provided_types": [],
            "raw_data_description": "",
            "processed_data_description": "",
            "figure_data_description": "",
            "scripts_description": "",
            "notes": reason,
        },
        "classification_prior": {
            "raw_data_expected": False,
            "source_data_expected": False,
            "raw_data_evidence": "",
            "source_data_evidence": "",
            "data_availability_section_relevant": "",
            "priority_modalities": [],
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

=== FILE INSPECTION REPORTS ===
{file_reports}

=== CLASSIFICATION DEFINITIONS ===

Type 1 (Cleaned, replot-ready):
- Tabular data (CSV, XLSX, TXT) with column headers naming variables, especially processed variables (e.g. R/resistance, which most of the time has to be processed from voltage and current signals)
- Organized as figure-specific data (e.g., "Fig1", "Figure_3e", "FigS4")
- Small-to-moderate file sizes appropriate for figure data
- Theoretical calculation or simulation data
- Optical microscopy data (Specifically, white light imaging for sample geometry. File type is usually jpg or png)
- Can be directly loaded and plotted with minimal processing
- "Source Data" deposits organized by figure = Type 1 (source data ≠ raw data)

Type 2 (Raw/unprocessed):
- Instrument output: binary/proprietary formats, microscopy images, HDF5, etc.
- Files named after scans, sample names, experiments, experimental conditions, or instrument runs
- Files in which all variables/units are directly measured from instruments (for example, voltage, current, Gauss/kilogauss)
- Files requiring processing scripts to generate figures
- Files explicitly described as raw in the paper or description in the online data repository link
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
6. If the paper explicitly states data is figure → prioritize that (Type 1)
7. For AFM and other microscopy data that is not white light imaging (normal microscope pictures) that is not stated raw/processed clearly in any descriptions: Consider as type 1, if there is a good amount of type 1 (>=2 files or 30%) data in this dataset. Consider them as type 2, if otherwise.

=== REASONING PROCEDURE ===

For each file, follow this step-by-step reasoning:

Step A. Paper Evidence
- Identify any statements about whether the dataset is raw, processed, or figure data

Step B. File Evidence
- Inspect filename, extension, size, structure, headers, sheet names, variable names and units

Step C. Functional Role
- Determine if the file is:
  - figure-ready data
  - raw measurement data
  - script
  - documentation
  - other

Step D. Replot Test
- Can this file be directly plotted with common variables as the axes with minimal processing?
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
  "type1_files": ["..."],
  "type2_files": ["..."],
  "data_organization": "e.g. figure-based folders / raw folders / mixed / not specified",
  "replot_ready_data_present": true/false,
  "replot_reason": "why the data is or is not directly usable for replotting",
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

    selected_reports = _select_reports_for_prompt(file_reports)

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
    dataset_char = analysis.get("dataset_characterization", {}) or {}
    if dataset_char.get("data_availability_statement"):
        lines.append(f"Data availability: {dataset_char.get('data_availability_statement', '')}")
    provided_types = dataset_char.get("data_provided_types", [])
    if provided_types:
        lines.append(f"Data provided types: {', '.join(provided_types)}")
    prior = analysis.get("classification_prior", {}) or {}
    if prior:
        lines.append("Classification prior:")
        lines.append(f"  raw_data_expected: {prior.get('raw_data_expected', False)}")
        lines.append(f"  source_data_expected: {prior.get('source_data_expected', False)}")
        if prior.get("raw_data_evidence"):
            lines.append(f"  raw_data_evidence: {prior.get('raw_data_evidence', '')}")
        if prior.get("source_data_evidence"):
            lines.append(f"  source_data_evidence: {prior.get('source_data_evidence', '')}")
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


def _select_reports_for_prompt(file_reports: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Keep prompt inputs manageable without adding classification logic.

    This function preserves the original file order and only trims overly large
    file sets so the prompt fits within model limits.
    """
    return file_reports


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
        "type1_files": [],
        "type2_files": [],
        "data_organization": "",
        "replot_ready_data_present": False,
        "replot_reason": "",
        "confidence": "low",
        "notes": reason,
    }
