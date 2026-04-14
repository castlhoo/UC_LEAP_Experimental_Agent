"""Orchestrate Step 3.5 script-assisted Type1 reproduction."""

import json
import logging
import os
import shutil
from typing import Any, Dict, List

import yaml

from step3_5.evaluator import evaluate_execution
from step3_5.patcher import patch_execution_target
from step3_5.preparation import heuristic_preparation, preparation_payload, select_candidates
from step3_5.prompt_client import prompt_enabled, run_preparation_prompt
from step3_5.runner import execute_target_script
from utils import save_with_latest

logger = logging.getLogger(__name__)


def _load_config() -> Dict[str, Any]:
    config_path = os.path.join(os.path.dirname(__file__), "config", "step3_5_config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _copy_bundle(download_dir: str, bundle_dir: str) -> None:
    if os.path.exists(bundle_dir):
        shutil.rmtree(bundle_dir)
    shutil.copytree(download_dir, bundle_dir)


def _paper_slug(paper: Dict[str, Any]) -> str:
    slug = paper.get("paper_id") or paper.get("doi") or paper.get("title", "paper")
    return str(slug).replace('/', '_').replace(':', '_')


def run_step3_5() -> Dict[str, Any]:
    config = _load_config()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_path = os.path.join(project_root, config.get("input_file", ""))
    output_dir = os.path.join(project_root, config.get("output_dir", "step3_5/output"))
    papers_dir = os.path.join(output_dir, "papers")
    work_root = os.path.join(project_root, config.get("work_dir", "step3_5/work"))
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(papers_dir, exist_ok=True)
    os.makedirs(work_root, exist_ok=True)

    with open(input_path, "r", encoding="utf-8") as f:
        step3_data = json.load(f)

    max_papers = config.get("selection", {}).get("max_papers")
    candidates = select_candidates(step3_data, max_papers=max_papers)
    logger.info(f"Selected {len(candidates)} Step 3.5 candidates with type2 data and scripts")

    results: List[Dict[str, Any]] = []
    both_count = 0

    for idx, paper in enumerate(candidates, start=1):
        slug = _paper_slug(paper)
        logger.info(f"[{idx}/{len(candidates)}] Step 3.5 processing: {paper.get('title', '')[:70]}")
        download_dir = paper.get("download_dir", "")
        if not download_dir or not os.path.isdir(download_dir):
            logger.warning("  Missing download_dir; skipping")
            continue

        paper_workdir = os.path.join(work_root, slug)
        bundle_dir = os.path.join(paper_workdir, "bundle")
        generated_dir = os.path.join(paper_workdir, "generated_type1")
        os.makedirs(generated_dir, exist_ok=True)
        _copy_bundle(download_dir, bundle_dir)

        preparation = None
        if prompt_enabled(config):
            try:
                preparation = run_preparation_prompt(preparation_payload(paper), config)
            except Exception as exc:
                logger.warning(f"  Preparation prompt failed; using heuristic: {exc}")
        if not preparation:
            preparation = heuristic_preparation(paper)

        patch_result = patch_execution_target(paper, preparation, bundle_dir, generated_dir, config)
        execution_result = execute_target_script(patch_result.get("patched_script_path", ""), bundle_dir, config)
        evaluation = evaluate_execution(paper, preparation, patch_result, execution_result, bundle_dir, config)

        result = {
            "paper_id": paper.get("paper_id", ""),
            "title": paper.get("title", ""),
            "doi": paper.get("doi", ""),
            "journal": paper.get("journal", ""),
            "download_dir": download_dir,
            "workdir": paper_workdir,
            "execution_target_script": preparation.get("execution_target_script", ""),
            "script_language": preparation.get("script_language", "unknown"),
            "preparation": preparation,
            "patch_result": patch_result,
            "execution_result": execution_result,
            "evaluation": evaluation,
            "both_via_script": bool(evaluation.get("count_paper_as_both", False)),
            "generated_type1_files": evaluation.get("generated_type1_files", []),
            "source_raw_files": preparation.get("likely_input_files", []),
            "figure_mapping": evaluation.get("figure_mapping", []),
        }
        if result["both_via_script"]:
            both_count += 1

        result_path = os.path.join(papers_dir, f"{idx:03d}_{slug}.json")
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        results.append(result)

    summary = {
        "metadata": {
            "step": "step3_5",
            "input_file": config.get("input_file", ""),
            "total_candidates": len(candidates),
        },
        "summary": {
            "total_candidates": len(candidates),
            "both_via_script_count": both_count,
            "execution_success_count": sum(1 for r in results if r.get("evaluation", {}).get("execution_successful")),
            "generated_type1_count": sum(1 for r in results if r.get("evaluation", {}).get("generated_type1_data")),
        },
        "papers": results,
    }
    save_with_latest(summary, output_dir, "step3_5_results")
    return {
        "total_candidates": len(candidates),
        "both_via_script_count": both_count,
        "execution_success_count": summary["summary"]["execution_success_count"],
    }
