"""
Step 1 - Pipeline
=================
Orchestrates candidate paper discovery:
  Phase 1: Build search queries
  Phase 2: Search academic APIs
  Phase 3: Deduplicate raw results
  Phase 4: Scan dataset signals
  Phase 5: Screen and score papers
  Phase 6: Save outputs
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List

import yaml

from step1.dataset_signal_scanner import scan_dataset_signal
from step1.deduplicator import deduplicate
from step1.gpt_client import gpt_generate_queries, gpt_screen_paper
from step1.paper_searcher import search_all_apis
from step1.query_generator import generate_api_specific_queries
from step1.scorer import compute_score, decide

logger = logging.getLogger(__name__)


def _load_config(config_dir: str, config_name: str = "step1_config.yaml") -> Dict[str, Any]:
    config_path = os.path.join(config_dir, config_name)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_step1(
    config_dir: str,
    output_dir: str,
    config_name: str = "step1_config.yaml",
) -> List[Dict[str, Any]]:
    """
    Execute the full Step 1 pipeline and return candidate records.
    """
    config = _load_config(config_dir, config_name=config_name)
    os.makedirs(output_dir, exist_ok=True)

    start_time = time.time()

    # ---- Phase 1: Query generation ----
    logger.info("=" * 60)
    logger.info("Phase 1: Building search queries...")

    query_config = config.get("queries", {})
    use_gpt_queries = query_config.get("use_gpt", False)
    gpt_model = config.get("gpt", {}).get("model", "gpt-5.4-mini")

    queries_by_api = generate_api_specific_queries(query_config)
    if use_gpt_queries:
        try:
            gpt_queries = gpt_generate_queries(model=gpt_model)
            for api_name, queries in gpt_queries.items():
                merged = queries_by_api.setdefault(api_name, [])
                merged.extend(q for q in queries if q)
                # Preserve order while deduplicating
                queries_by_api[api_name] = list(dict.fromkeys(merged))
        except Exception as exc:
            logger.warning(f"GPT query generation failed, using static queries only: {exc}")

    for api_name, queries in queries_by_api.items():
        logger.info(f"  {api_name}: {len(queries)} queries")

    # ---- Phase 2: Search APIs ----
    logger.info("=" * 60)
    logger.info("Phase 2: Searching academic APIs...")
    raw_papers = search_all_apis(queries_by_api, config.get("search", {}))

    # ---- Phase 3: Deduplicate ----
    logger.info("=" * 60)
    logger.info("Phase 3: Deduplicating results...")
    unique_papers = deduplicate(raw_papers)

    # ---- Phase 4/5: Dataset signal + screening ----
    logger.info("=" * 60)
    logger.info("Phase 4-5: Scanning dataset signals and scoring candidates...")

    high_priority_journals = config.get("journals", {}).get("high_priority", [])
    mid_priority_journals = config.get("journals", {}).get("mid_priority", [])
    weights = config.get("scoring", {}).get("weights", {})
    thresholds = config.get("scoring", {}).get("thresholds", {})
    use_gpt_screening = config.get("gpt", {}).get("enabled", True)

    candidates = []
    for idx, paper in enumerate(unique_papers, start=1):
        if idx == 1 or idx % 10 == 0 or idx == len(unique_papers):
            logger.info(f"  Processing paper {idx}/{len(unique_papers)}...")

        dataset_signal = scan_dataset_signal(paper)

        if use_gpt_screening:
            screening = gpt_screen_paper(paper, model=gpt_model)
        else:
            screening = {
                "field_match": False,
                "field_match_level": "none",
                "field_evidence": ["GPT screening disabled"],
                "experimental_match": False,
                "experimental_level": "uncertain",
                "experimental_evidence": ["GPT screening disabled"],
                "soft_material_flag": False,
                "soft_material_confidence": "none",
                "soft_material_evidence": [],
                "is_review": False,
                "review_evidence": [],
                "reasons": ["GPT screening disabled"],
                "gpt_summary": "",
                "gpt_dataset_mentioned": False,
                "gpt_dataset_detail": "",
            }

        score, breakdown = compute_score(
            screening=screening,
            dataset_signal=dataset_signal,
            paper=paper,
            high_priority_journals=high_priority_journals,
            mid_priority_journals=mid_priority_journals,
            weights=weights,
        )
        decision = decide(score=score, screening=screening, thresholds=thresholds)

        candidates.append({
            "paper_id": f"step1_{idx:04d}",
            "title": paper.get("title", ""),
            "paper_url": paper.get("paper_url", ""),
            "journal": paper.get("journal", ""),
            "year": paper.get("year"),
            "doi": paper.get("doi", ""),
            "authors": paper.get("authors", [])[:10],
            "abstract_summary": screening.get("gpt_summary", "") or (paper.get("abstract", "")[:500]),
            "field_match": screening.get("field_match", False),
            "field_match_level": screening.get("field_match_level", "none"),
            "experimental_match": screening.get("experimental_match", False),
            "experimental_level": screening.get("experimental_level", "uncertain"),
            "soft_material_excluded": not screening.get("soft_material_flag", False),
            "priority_score": score,
            "score_breakdown": breakdown,
            "dataset_signal": dataset_signal.get("level", "low"),
            "dataset_signal_evidence": dataset_signal.get("evidence", []),
            "dataset_url_candidates": dataset_signal.get("url_candidates", []),
            "screening_reason": screening.get("reasons", []),
            "screening_decision": decision,
            "source_apis": paper.get("source_apis", [paper.get("source_api", "")]),
            "citation_count": paper.get("citation_count"),
            "open_access_url": paper.get("open_access_url", ""),
            "raw_metadata": paper.get("raw_metadata", {}),
        })

    candidates.sort(
        key=lambda item: (
            {"keep": 0, "maybe": 1, "drop": 2}.get(item["screening_decision"], 3),
            -item["priority_score"],
            item["title"].lower(),
        )
    )

    # ---- Phase 6: Save outputs ----
    logger.info("=" * 60)
    logger.info("Phase 6: Saving outputs...")

    keep = sum(1 for c in candidates if c["screening_decision"] == "keep")
    maybe = sum(1 for c in candidates if c["screening_decision"] == "maybe")
    drop = sum(1 for c in candidates if c["screening_decision"] == "drop")
    elapsed = round(time.time() - start_time, 1)

    metadata = {
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "total_raw_results": len(raw_papers),
        "total_unique": len(unique_papers),
        "total_keep": keep,
        "total_maybe": maybe,
        "total_drop": drop,
        "search_time_seconds": elapsed,
        "year_range": config.get("search", {}).get("year_range", {"start": 2021, "end": 2026}),
    }

    full_output = {"metadata": metadata, "candidates": candidates}
    keep_maybe_output = {
        "metadata": metadata,
        "candidates": [c for c in candidates if c["screening_decision"] in ("keep", "maybe")],
    }

    timestamp = metadata["timestamp"]
    paths = {
        "all_ts": os.path.join(output_dir, f"step1_candidates_{timestamp}.json"),
        "all_latest": os.path.join(output_dir, "step1_candidates_latest.json"),
        "keep_maybe_ts": os.path.join(output_dir, f"step1_keep_maybe_{timestamp}.json"),
    }

    for path, payload in (
        (paths["all_ts"], full_output),
        (paths["all_latest"], full_output),
        (paths["keep_maybe_ts"], keep_maybe_output),
    ):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    logger.info(f"  Saved: {paths['all_ts']}")
    logger.info(f"  Saved: {paths['all_latest']}")
    logger.info(f"  Saved: {paths['keep_maybe_ts']}")

    logger.info("=" * 60)
    logger.info("STEP 1 RESULTS SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Raw API results:         {len(raw_papers)}")
    logger.info(f"Unique papers:           {len(unique_papers)}")
    logger.info(f"Keep:                    {keep}")
    logger.info(f"Maybe:                   {maybe}")
    logger.info(f"Drop:                    {drop}")

    return candidates
