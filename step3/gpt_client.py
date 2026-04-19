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
    finish_reason = getattr(resp.choices[0], "finish_reason", "")
    if finish_reason == "length":
        raise ValueError("GPT response truncated before valid JSON was complete")
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
(3) Types of experiments done and the expected raw data file extensions

Paper title: {title}
Paper journal: {journal}

=== PAPER TEXT ===
{paper_text}

=== TASK ===

Provide:

1. Scientific summary
2. Measurement types and expected raw data file extensions
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
