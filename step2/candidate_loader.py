"""
Step 2 - Candidate Loader
===========================
Load Step 1 candidates and filter by decision (keep/maybe).
"""

import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def load_candidates(
    input_path: str,
    include_decisions: List[str] = None,
) -> List[Dict[str, Any]]:
    """
    Load candidates from Step 1 output JSON.

    Args:
        input_path: Path to step1_candidates_latest.json
        include_decisions: List of decisions to include (e.g., ["keep", "maybe"])

    Returns:
        List of candidate paper dicts
    """
    if include_decisions is None:
        include_decisions = ["keep", "maybe"]

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_candidates = data.get("candidates", [])
    logger.info(f"Loaded {len(all_candidates)} total candidates from Step 1")

    filtered = [
        c for c in all_candidates
        if c.get("screening_decision") in include_decisions
    ]
    logger.info(
        f"Filtered to {len(filtered)} candidates "
        f"(decisions: {include_decisions})"
    )

    # Sort by priority score descending
    filtered.sort(key=lambda x: x.get("priority_score", 0), reverse=True)

    return filtered
