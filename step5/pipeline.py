"""
Step 5 - Pipeline
===================
Orchestrates Dataset Summary, Task Generation & Reproducibility:
  Phase 1: Load Step 4 manifest + Step 3 paper analyses
  Phase 2: Generate dataset summaries (1st GPT call per paper)
  Phase 3: Generate research tasks (2nd GPT call per paper)
  Phase 4: Save outputs (summaries, tasks.json, agent prompt)
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import yaml

from step5.dataset_summarizer import generate_dataset_summary
from step5.task_generator import generate_research_tasks, AGENT_PROMPT
from step5.task_executor import execute_task
from utils import save_with_latest

logger = logging.getLogger(__name__)


def _load_config() -> Dict[str, Any]:
    """Load Step 5 configuration."""
    config_path = os.path.join(
        os.path.dirname(__file__), "config", "step5_config.yaml"
    )
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_step5() -> Dict[str, Any]:
    """Execute the full Step 5 pipeline."""
    config = _load_config()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    gpt_config = config.get("gpt", {})
    use_gpt = gpt_config.get("enabled", True)
    gpt_model = gpt_config.get("model", "gpt-5.4-mini")

    # ---- Phase 1: Load Step 4 manifest + Step 3 analyses ----
    logger.info("=" * 60)
    logger.info("Phase 1: Loading Step 4 manifest & Step 3 paper analyses...")

    manifest_path = os.path.join(project_root, config.get("step4_manifest", ""))
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    papers = manifest.get("papers", [])
    logger.info(f"  Loaded {len(papers)} organized papers from Step 4")

    # Load Step 3 results for paper analyses
    step3_path = os.path.join(project_root, config.get("step3_results", ""))
    paper_analyses = {}
    if os.path.exists(step3_path):
        with open(step3_path, "r", encoding="utf-8") as f:
            step3_data = json.load(f)
        # Build DOI → paper_analysis mapping
        for p in step3_data.get("all_papers", []):
            doi = p.get("doi", "")
            if doi and p.get("paper_analysis"):
                paper_analyses[doi] = p["paper_analysis"]
        logger.info(f"  Loaded {len(paper_analyses)} paper analyses from Step 3")
    else:
        logger.warning(f"  Step 3 results not found at {step3_path}")

    if not papers:
        logger.warning("No papers to process!")
        return {"status": "empty", "papers_processed": 0}

    # ---- Phase 2: Generate dataset summaries ----
    logger.info("=" * 60)
    logger.info("Phase 2: Generating dataset summaries...")

    organized_base = os.path.join(
        project_root, manifest.get("metadata", {}).get("output_dir", "step4/organized")
    )
    # Fallback: infer from manifest path
    if not os.path.isdir(organized_base):
        organized_base = os.path.dirname(manifest_path)

    results = []
    for i, paper in enumerate(papers):
        title = paper.get("title", "")[:50]
        doi = paper.get("doi", "")
        logger.info(f"  [{i+1}/{len(papers)}] {title}...")

        paper_dir = os.path.join(organized_base, paper["directory"])
        analysis = paper_analyses.get(doi)

        if use_gpt:
            summary = generate_dataset_summary(
                paper, paper_dir, analysis, config, model=gpt_model
            )
            logger.info(f"    Summary: {len(summary)} chars")
        else:
            summary = "(GPT disabled)"

        results.append({
            "paper": paper,
            "paper_dir": paper_dir,
            "paper_analysis": analysis,
            "dataset_summary": summary,
            "tasks": None,
        })

    # ---- Phase 3: Generate research tasks ----
    logger.info("=" * 60)
    logger.info("Phase 3: Generating research tasks...")

    total_tasks = 0
    for i, entry in enumerate(results):
        paper = entry["paper"]
        title = paper.get("title", "")[:50]
        logger.info(f"  [{i+1}/{len(results)}] {title}...")

        if use_gpt:
            tasks_result = generate_research_tasks(
                paper,
                entry["dataset_summary"],
                entry["paper_analysis"],
                config,
                model=gpt_model,
            )
            entry["tasks"] = tasks_result
            n_tasks = len(tasks_result.get("research_tasks", []))
            total_tasks += n_tasks
            logger.info(f"    Generated {n_tasks} tasks")
        else:
            entry["tasks"] = {"research_tasks": []}
            logger.info("    Skipped (GPT disabled)")

    logger.info(f"  Total tasks generated: {total_tasks}")

    # ---- Phase 4: Save outputs ----
    logger.info("=" * 60)
    logger.info("Phase 4: Saving outputs...")

    output_dir = os.path.join(project_root, config.get("output_dir", "step5/output"))
    os.makedirs(output_dir, exist_ok=True)

    for i, entry in enumerate(results):
        paper = entry["paper"]
        paper_idx = paper.get("paper_index", i + 1)
        paper_slug = paper["directory"]

        # Create per-paper output directory
        paper_out_dir = os.path.join(output_dir, paper_slug)
        os.makedirs(paper_out_dir, exist_ok=True)

        # Save dataset summary
        summary_path = os.path.join(paper_out_dir, "dataset_summary.txt")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(entry["dataset_summary"])

        # Save tasks.json
        tasks_path = os.path.join(paper_out_dir, "tasks.json")
        with open(tasks_path, "w", encoding="utf-8") as f:
            json.dump(entry["tasks"], f, indent=2, ensure_ascii=False)

        # Save agent prompt
        agent_path = os.path.join(paper_out_dir, "agent_prompt.txt")
        with open(agent_path, "w", encoding="utf-8") as f:
            f.write(AGENT_PROMPT)

        # Save paper context
        context_path = os.path.join(paper_out_dir, "paper_context.json")
        context = {
            "title": paper.get("title", ""),
            "doi": paper.get("doi", ""),
            "journal": paper.get("journal", ""),
            "year": paper.get("year", ""),
            "type1_summary": paper.get("type1_summary", ""),
            "type2_summary": paper.get("type2_summary", ""),
            "files": paper.get("files", {}),
            "paper_analysis": entry.get("paper_analysis"),
        }
        with open(context_path, "w", encoding="utf-8") as f:
            json.dump(context, f, indent=2, ensure_ascii=False)

        logger.info(f"  Saved outputs for: {paper_slug}")
        entry["paper_out_dir"] = paper_out_dir

    # ---- Phase 5: Execute tasks ----
    logger.info("=" * 60)
    logger.info("Phase 5: Executing research tasks...")

    total_executed = 0
    total_success = 0
    for i, entry in enumerate(results):
        paper = entry["paper"]
        title = paper.get("title", "")[:50]
        paper_out_dir = entry.get("paper_out_dir", "")
        paper_dir = entry.get("paper_dir", "")
        tasks_data = entry.get("tasks") or {}
        task_list = tasks_data.get("research_tasks", [])

        if not task_list:
            continue

        logger.info(f"  [{i+1}/{len(results)}] {title} ({len(task_list)} tasks)")

        # Read agent prompt from the saved file
        agent_path = os.path.join(paper_out_dir, "agent_prompt.txt")
        agent_text = ""
        if os.path.exists(agent_path):
            with open(agent_path, "r", encoding="utf-8") as f:
                agent_text = f.read()

        execution_results = []
        for j, task in enumerate(task_list):
            task_id = task.get("task_id", f"TASK_{j+1}")
            logger.info(f"    [{j+1}/{len(task_list)}] {task_id}: {task.get('task_title', '')[:50]}")

            task_output_dir = os.path.join(paper_out_dir, "results")

            if use_gpt:
                exec_result = execute_task(
                    task=task,
                    paper_dir=paper_dir,
                    output_dir=task_output_dir,
                    agent_prompt=agent_text,
                    config=config,
                    model=gpt_model,
                )
            else:
                exec_result = {"status": "skipped", "output_files": []}

            execution_results.append(exec_result)
            total_executed += 1
            if exec_result.get("status") == "success":
                total_success += 1

        entry["execution_results"] = execution_results

    logger.info(f"  Executed: {total_executed}, Success: {total_success}")

    # Save overall manifest
    overall = {
        "metadata": {
            "step": 5,
            "description": "Dataset Summary, Task Generation & Reproducibility",
            "generated_at": datetime.now().isoformat(),
            "total_papers": len(results),
            "total_tasks": total_tasks,
        },
        "papers": [],
    }

    for entry in results:
        paper = entry["paper"]
        tasks = entry["tasks"] or {}
        task_list = tasks.get("research_tasks", [])
        exec_results = entry.get("execution_results", [])
        overall["papers"].append({
            "paper_index": paper.get("paper_index", 0),
            "title": paper.get("title", ""),
            "doi": paper.get("doi", ""),
            "directory": paper.get("directory", ""),
            "num_tasks": len(task_list),
            "task_titles": [t.get("task_title", "") for t in task_list],
            "output_dir": os.path.join(output_dir, paper["directory"]),
            "execution": [
                {
                    "task_id": task_list[k].get("task_id", "") if k < len(task_list) else "",
                    "status": r.get("status", "unknown"),
                    "has_figure": r.get("has_figure", False),
                    "has_analysis": r.get("has_analysis", False),
                }
                for k, r in enumerate(exec_results)
            ],
        })

    latest_path = save_with_latest(overall, output_dir, "step5_manifest")

    # Print summary
    _print_summary(overall)

    logger.info(f"Manifest saved to {latest_path}")

    return {
        "status": "complete",
        "output_path": latest_path,
        "papers_processed": len(results),
        "total_tasks": total_tasks,
        "total_executed": total_executed,
        "total_success": total_success,
    }


def _print_summary(output: Dict[str, Any]):
    """Print formatted summary."""
    meta = output["metadata"]
    logger.info("=" * 60)
    logger.info("STEP 5 RESULTS SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Papers processed:     {meta['total_papers']}")
    logger.info(f"Total tasks generated: {meta['total_tasks']}")
    logger.info("-" * 60)

    for p in output["papers"]:
        logger.info(f"  Paper {p['paper_index']}: {p['title'][:50]}")
        logger.info(f"    Tasks: {p['num_tasks']}")
        for t in p["task_titles"]:
            logger.info(f"      - {t}")
