"""
Step 1 - Scorer
================
Computes priority score for each paper candidate and makes keep/maybe/drop decisions.
Scoring weights and thresholds are loaded from config for easy tuning.
"""

import logging
from typing import Dict, Any, Tuple, List

logger = logging.getLogger(__name__)


# Default scoring weights (overridden by config)
DEFAULT_WEIGHTS = {
    "field_match_strong": 3,
    "field_match_general": 2,
    "field_match_weak": 1,
    "experimental_clear": 3,
    "experimental_mixed": 1,
    "experimental_theory_only": 0,
    "dataset_signal_high": 3,
    "dataset_signal_medium": 1,
    "dataset_signal_low": 0,
    "soft_material_penalty": -4,
    "review_penalty": -4,
    "theory_only_penalty": -3,
}

DEFAULT_THRESHOLDS = {
    "keep_min": 7,
    "maybe_min": 4,
}


def _normalize_journal(journal: str) -> str:
    """Normalize journal name for matching."""
    if not journal:
        return ""
    import re
    j = journal.lower().strip()
    # Remove extra whitespace
    j = re.sub(r"\s+", " ", j)
    return j


def _journal_matches(journal_norm: str, target_norm: str) -> bool:
    """
    Check if a paper's journal matches a target journal name.
    Strict: target must appear at the START of the journal name,
    or be an exact match. This prevents 'science advances' from
    matching 'analytical science advances'.
    """
    if not journal_norm or not target_norm:
        return False
    # Exact match
    if journal_norm == target_norm:
        return True
    # Target must be at the beginning of journal name
    # e.g., "nature" matches "nature physics", "nature communications"
    # but "science advances" does NOT match "analytical science advances"
    if journal_norm.startswith(target_norm):
        # Make sure it's a word boundary (not partial word)
        rest = journal_norm[len(target_norm):]
        if not rest or rest[0] in (" ", ",", ":", ";", "-"):
            return True
    return False


def compute_score(
    screening: Dict[str, Any],
    dataset_signal: Dict[str, Any],
    paper: Dict[str, Any],
    high_priority_journals: List[str],
    mid_priority_journals: List[str],
    weights: Dict[str, Any] = None,
) -> Tuple[float, List[str]]:
    """
    Compute priority score for a paper.

    Returns: (score, score_breakdown)
    """
    w = weights or DEFAULT_WEIGHTS
    score = 0.0
    breakdown = []

    # 1. Field match score
    field_level = screening.get("field_match_level", "none")
    if field_level == "strong":
        pts = w.get("field_match_strong", 3)
        score += pts
        breakdown.append(f"Field strong: +{pts}")
    elif field_level == "general":
        pts = w.get("field_match_general", 2)
        score += pts
        breakdown.append(f"Field general: +{pts}")
    elif field_level == "weak":
        pts = w.get("field_match_weak", 1)
        score += pts
        breakdown.append(f"Field weak: +{pts}")
    else:
        breakdown.append("Field none: +0")

    # 2. Experimental match score
    exp_level = screening.get("experimental_level", "uncertain")
    if exp_level in ("clear", "likely"):
        pts = w.get("experimental_clear", 3)
        score += pts
        breakdown.append(f"Experimental clear: +{pts}")
    elif exp_level == "mixed":
        pts = w.get("experimental_mixed", 1)
        score += pts
        breakdown.append(f"Experimental mixed: +{pts}")
    elif exp_level == "theory_only":
        pts = w.get("theory_only_penalty", -3)
        score += pts
        breakdown.append(f"Theory only: {pts}")
    else:
        breakdown.append("Experimental uncertain: +0")

    # 3. Dataset signal score
    ds_level = dataset_signal.get("level", "low")
    if ds_level == "high":
        pts = w.get("dataset_signal_high", 3)
        score += pts
        breakdown.append(f"Dataset signal high: +{pts}")
    elif ds_level == "medium":
        pts = w.get("dataset_signal_medium", 1)
        score += pts
        breakdown.append(f"Dataset signal medium: +{pts}")
    else:
        breakdown.append("Dataset signal low: +0")

    # 4. Penalties
    if screening.get("soft_material_flag"):
        conf = screening.get("soft_material_confidence", "medium")
        pts = w.get("soft_material_penalty", -4)
        if conf == "high":
            score += pts
            breakdown.append(f"Soft material (high conf): {pts}")
        elif conf == "medium":
            half_pts = pts / 2
            score += half_pts
            breakdown.append(f"Soft material (medium conf): {half_pts}")

    if screening.get("is_review"):
        pts = w.get("review_penalty", -4)
        score += pts
        breakdown.append(f"Review article: {pts}")

    # 5. Multi-API bonus (found by multiple sources = more reliable)
    source_apis = paper.get("source_apis") or [paper.get("source_api", "")]
    if len(source_apis) > 1:
        bonus = 0.5
        score += bonus
        breakdown.append(f"Multi-API bonus ({len(source_apis)} sources): +{bonus}")

    return round(score, 1), breakdown


def decide(
    score: float,
    screening: Dict[str, Any],
    thresholds: Dict[str, Any] = None,
) -> str:
    """
    Make keep/maybe/drop decision based on score and screening.

    Key principle: when in doubt, keep as 'maybe' (recall > precision in Step 1).
    """
    t = thresholds or DEFAULT_THRESHOLDS
    keep_min = t.get("keep_min", 7)
    maybe_min = t.get("maybe_min", 4)

    # Hard drops: theory-only + no dataset signal + no field match
    if (
        screening.get("experimental_level") == "theory_only"
        and not screening.get("field_match")
    ):
        return "drop"

    # Hard drops: strong soft material + no dataset signal
    if (
        screening.get("soft_material_flag")
        and screening.get("soft_material_confidence") == "high"
    ):
        return "drop"

    # Hard drops: review articles
    if screening.get("is_review"):
        return "drop"

    # Score-based decision
    if score >= keep_min:
        return "keep"
    elif score >= maybe_min:
        return "maybe"
    else:
        return "drop"
