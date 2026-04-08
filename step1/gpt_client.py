"""
Step 1 - GPT Client
=====================
Wrapper around OpenAI API for Step 1 tasks:
  - Query generation (Phase 1)
  - Paper screening (Phase 5)

Uses structured JSON responses for reliable parsing.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

from openai import OpenAI
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env from project root
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


def call_gpt(
    prompt: str,
    system_prompt: str = "",
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: int = 2000,
    response_format: Optional[Dict] = None,
) -> str:
    """
    Call GPT API and return the response text.

    Args:
        prompt: User message
        system_prompt: System message
        model: Model name
        temperature: Sampling temperature
        max_tokens: Max response tokens
        response_format: If set to {"type": "json_object"}, forces JSON output

    Returns:
        Response text string
    """
    client = _get_client()
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_completion_tokens": max_tokens,
    }
    if response_format:
        kwargs["response_format"] = response_format

    try:
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"GPT API error: {e}")
        raise


def call_gpt_json(
    prompt: str,
    system_prompt: str = "",
    model: str = "gpt-4o-mini",
    temperature: float = 0.3,
    max_tokens: int = 2000,
) -> Dict[str, Any]:
    """
    Call GPT API and parse response as JSON.

    Returns:
        Parsed JSON dict
    """
    raw = call_gpt(
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"GPT returned invalid JSON: {raw[:200]}")
        raise ValueError(f"GPT JSON parse error: {e}")


# ===================================================================
# Phase 1: Query Generation
# ===================================================================

QUERY_GEN_SYSTEM = """You are an expert in condensed matter physics and materials science research.
Your task is to generate effective search queries for academic paper APIs.
You understand what makes a good search query for finding experimental papers with open datasets."""

QUERY_GEN_PROMPT = """Generate search queries to find condensed matter / materials science EXPERIMENTAL papers 
that provide open-access datasets (e.g., on Zenodo, Figshare, or as supplementary data).

Requirements:
- Papers should be from the last 5 years (2021-2026)
- Focus on hard condensed matter (NOT soft matter like polymers, gels, biomaterials)
- Papers should describe original experimental measurements (not purely computational/theoretical)
- Prioritize papers that explicitly mention datasets, source data, or data repositories

Generate queries for these APIs:
1. OpenAlex: general academic search, supports free text queries (3-8 words each)
2. CrossRef: DOI-centric search, works best with short queries (3-6 words each)
3. arXiv: preprint server, will be filtered to cond-mat category, so focus on specific topics + experimental keywords (2-4 words each)

Topics to cover (but not limited to):
- Moiré / twisted bilayer systems
- Topological materials (insulators, semimetals, Weyl)
- 2D materials and van der Waals heterostructures
- Superconductivity
- Magnetic ordering, multiferroics, ferroelectrics
- Charge density waves, kagome metals
- Quantum oscillations, transport measurements
- Spectroscopy (ARPES, Raman, STM, neutron scattering)
- Thin films, epitaxial growth

Return JSON:
{
  "openalex": ["query1", "query2", ...],  // 20-25 queries
  "crossref": ["query1", "query2", ...],  // 12-15 queries
  "arxiv": ["query1", "query2", ...]      // 15-20 queries
}"""


def gpt_generate_queries(model: str = "gpt-4o-mini") -> Dict[str, List[str]]:
    """Use GPT to generate search queries for each API."""
    logger.info("Generating search queries with GPT...")
    result = call_gpt_json(
        prompt=QUERY_GEN_PROMPT,
        system_prompt=QUERY_GEN_SYSTEM,
        model=model,
        temperature=0.8,
        max_tokens=3000,
    )
    for api in ["openalex", "crossref", "arxiv"]:
        queries = result.get(api, [])
        logger.info(f"  GPT generated {len(queries)} queries for {api}")
    return result


# ===================================================================
# Phase 5: Paper Screening
# ===================================================================

SCREEN_SYSTEM = """You are an expert in condensed matter physics and materials science.
Your task is to screen research papers for relevance.
You must return structured JSON judgments. Be accurate and concise."""

SCREEN_PROMPT_TEMPLATE = """Analyze this paper and answer each question.

Title: {title}
Journal: {journal}
Year: {year}
Abstract: {abstract}

Return JSON with these fields:
{{
  "summary": "1-sentence summary of the research",
  "field_match": {{
    "level": "strong" | "general" | "weak" | "none",
    "reason": "brief reason"
  }},
  "experimental": {{
    "level": "clear" | "likely" | "mixed" | "theory_only" | "uncertain",
    "reason": "brief reason"
  }},
  "soft_material": {{
    "flag": true | false,
    "reason": "brief reason"
  }},
  "is_review": {{
    "flag": true | false,
    "reason": "brief reason"
  }},
  "dataset_mentioned": {{
    "flag": true | false,
    "detail": "what dataset/data availability was mentioned, or 'none'"
  }}
}}

Definitions:
- field_match "strong": clearly condensed matter / materials science (topological, moire, superconductor, 2D materials, etc.)
- field_match "general": materials science related but not core condensed matter
- field_match "weak": tangentially related
- field_match "none": unrelated field
- experimental "clear": describes original experimental measurements
- experimental "likely": mentions experiments but not the main focus
- experimental "mixed": both experimental and computational
- experimental "theory_only": purely theoretical/computational
- soft_material: polymers, gels, biomaterials, colloids, liquid crystals, etc.
- is_review: review articles, perspectives, roadmaps"""


def gpt_screen_paper(
    paper: Dict[str, Any],
    model: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    """
    Use GPT to screen a single paper.

    Returns screening result dict compatible with scorer.py.
    """
    title = paper.get("title", "")
    abstract = paper.get("abstract", "")
    journal = paper.get("journal", "")
    year = paper.get("year", "")

    if not abstract and not title:
        return _empty_screening()

    prompt = SCREEN_PROMPT_TEMPLATE.format(
        title=title,
        journal=journal,
        year=year,
        abstract=abstract[:1500],  # Limit abstract length
    )

    try:
        result = call_gpt_json(
            prompt=prompt,
            system_prompt=SCREEN_SYSTEM,
            model=model,
            temperature=0.2,
            max_tokens=500,
        )
        return _parse_gpt_screening(result)
    except Exception as e:
        logger.warning(f"GPT screening failed for '{title[:50]}': {e}")
        return _empty_screening()


def _parse_gpt_screening(gpt_result: Dict[str, Any]) -> Dict[str, Any]:
    """Convert GPT screening JSON to the format expected by scorer.py."""
    field = gpt_result.get("field_match", {})
    exp = gpt_result.get("experimental", {})
    soft = gpt_result.get("soft_material", {})
    review = gpt_result.get("is_review", {})
    dataset = gpt_result.get("dataset_mentioned", {})

    field_level = field.get("level", "none")
    exp_level = exp.get("level", "uncertain")
    is_soft = soft.get("flag", False)
    is_review_flag = review.get("flag", False)

    field_match = field_level in ("strong", "general")
    experimental_match = exp_level in ("clear", "likely", "mixed")

    reasons = []
    if field_match:
        reasons.append(f"Field match ({field_level})")
    else:
        reasons.append(f"Field match weak/none ({field_level})")
    if experimental_match:
        reasons.append(f"Experimental ({exp_level})")
    else:
        reasons.append(f"Not clearly experimental ({exp_level})")
    if is_soft:
        reasons.append(f"Soft material")
    if is_review_flag:
        reasons.append("Review article")

    return {
        "field_match": field_match,
        "field_match_level": field_level,
        "field_evidence": [field.get("reason", "")],
        "experimental_match": experimental_match,
        "experimental_level": exp_level,
        "experimental_evidence": [exp.get("reason", "")],
        "soft_material_flag": is_soft,
        "soft_material_confidence": "high" if is_soft else "none",
        "soft_material_evidence": [soft.get("reason", "")],
        "is_review": is_review_flag,
        "review_evidence": [review.get("reason", "")] if is_review_flag else [],
        "reasons": reasons,
        "gpt_summary": gpt_result.get("summary", ""),
        "gpt_dataset_mentioned": dataset.get("flag", False),
        "gpt_dataset_detail": dataset.get("detail", ""),
    }


def _empty_screening() -> Dict[str, Any]:
    """Return empty screening result when GPT fails."""
    return {
        "field_match": False,
        "field_match_level": "none",
        "field_evidence": ["GPT screening failed"],
        "experimental_match": False,
        "experimental_level": "uncertain",
        "experimental_evidence": ["GPT screening failed"],
        "soft_material_flag": False,
        "soft_material_confidence": "none",
        "soft_material_evidence": [],
        "is_review": False,
        "review_evidence": [],
        "reasons": ["GPT screening failed"],
        "gpt_summary": "",
        "gpt_dataset_mentioned": False,
        "gpt_dataset_detail": "",
    }
