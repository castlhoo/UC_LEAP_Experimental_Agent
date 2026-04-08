"""
Step 5 - Task Generator
=========================
Generate research tasks from paper + dataset summary via GPT.
This is the 2nd GPT call in Step 5.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

from step5.gpt_client import call_gpt_json

logger = logging.getLogger(__name__)


# ===================================================================
# Task Generation Prompt (2nd GPT call)
# ===================================================================

TASK_GEN_SYSTEM = """You are an expert research assistant specializing in materials science and the creation of benchmarks for AI research agents. Your task is to act as a principal investigator who is breaking down a complex research paper into smaller, well-defined tasks for your team of junior scientists (or AI agents) to execute. Return structured JSON."""

TASK_GEN_PROMPT = """Here is a material science paper; the following is the dataset description from it:

{dataset_summary}

-----

Your Mission: You are given a material science paper and its associated datasets. The datasets have been classified into:
- **Type 1**: Cleaned, replot-ready datasets with annotated variable names — each file corresponds to a specific figure in the paper and can be used for 1-step figure replotting.
- **Type 2**: Un-processed raw measurement data that requires additional processing before visualization.

Your goal is to generate **one task per Type 1 data file**. Each task must reproduce (replot) the corresponding figure from the paper using that file. If a Type 1 file's figure reference is unclear from the filename, infer it from the dataset summary and paper analysis.

IMPORTANT: Generate a task for EVERY Type 1 file listed below. Do not skip any. The number of tasks must equal the number of Type 1 files.

Core Principles for Task Generation

1. Self-Contained & Unambiguous: Each task must provide all the necessary information and research context for an agent to begin work immediately. The objective should be crystal clear, leaving no room for ambiguity. The agent should be able to solve the task using only the provided dataset and general scientific knowledge, without needing to read the source paper. Do not provide any derived information from the discussions or conclusions of the paper.

2. Trigger Analysis, Not Factual Recall: The tasks must demand action. They should require the agent to perform calculations, write code, process data, plot figures, or conduct a targeted literature search for a method.
 - DO ask the agent to calculate, plot, derive, identify, process, or compare.
 - AVOID simple extractive questions like, "What material was studied?" or "What were the main conclusions of the paper?"

3. Atomic & Focused: Each task should focus on a single figure replot. One Type 1 file = one task. If a file contains data for multiple panels (e.g., Fig2a has multiple traces), that is still one task.

=== PAPER CONTEXT ===
Title: {title}
Journal: {journal}
DOI: {doi}

=== PAPER ANALYSIS (from reading the full publication) ===
{paper_analysis}

=== AVAILABLE DATASET FILES ===
Type 1 (replot-ready): {type1_files}
Type 2 (raw data): {type2_files}
Scripts: {script_files}

Output Format Specification

You must provide the output as a single JSON object containing a list named research_tasks. Each object in the list represents one task and must adhere to the following schema:
{{
  "research_tasks": [
    {{
      "task_id": "{paper_id}_TASK_01",
      "task_title": "A concise, descriptive title for the task.",
      "task_description": "A detailed, step-by-step description of the task. This is the prompt that will be given to the research agent. It should be written clearly and assume the agent has not read the source paper.",
      "task_type": "One of: ['Data Processing & Visualization', 'Quantitative Analysis', 'Literature-Informed Method Application', 'Result Interpretation & Comparison']",

      "execution_steps": ["Step_0: ...", "Step_1: ...", "Step_2: ..."],

      "required_inputs": {{
        "dataset_file": "The exact filename from the provided dataset.",
        "relevant_variables": ["A list of key variables/columns from the dataset needed for this task."]
      }},
      "ground_truth_outcome": {{
        "description": "The expected result description.",
        "expected_figure": "The corresponding figure reference from the paper (e.g. Fig2a)"
      }}
    }}
  ]
}}

Now, generate exactly ONE task per Type 1 data file listed above. Each task should replot the corresponding figure from the paper.
Total number of tasks expected: {num_type1_files} (one per Type 1 file).
Do NOT skip any Type 1 file. If a file cannot be mapped to a figure, still create a task to inspect and visualize its contents.
"""


def generate_research_tasks(
    paper: Dict[str, Any],
    dataset_summary: str,
    paper_analysis: Optional[Dict[str, Any]],
    config: Dict[str, Any],
    model: str = "gpt-5.4-mini",
) -> Dict[str, Any]:
    """
    Generate research tasks for a paper using GPT.

    Args:
        paper: Paper entry from Step 4 manifest
        dataset_summary: Generated dataset summary text
        paper_analysis: Paper analysis from Step 3
        config: Step 5 config dict
        model: GPT model to use

    Returns:
        Dict with research_tasks list
    """
    # Format paper analysis
    analysis_str = _format_paper_analysis(paper_analysis)

    # Format file lists
    files = paper.get("files", {})
    type1_files = files.get("type1_data", [])
    type2_files = files.get("type2_data", [])
    script_files = files.get("scripts", [])

    # Paper ID from index
    paper_id = f"PAPER_{paper.get('paper_index', 1):02d}"

    # Extract just filenames if list contains dicts
    type1_names = []
    for f in type1_files:
        if isinstance(f, dict):
            type1_names.append(f.get("renamed", f.get("original", "")))
        else:
            type1_names.append(str(f))

    prompt = TASK_GEN_PROMPT.format(
        dataset_summary=dataset_summary,
        title=paper.get("title", ""),
        journal=paper.get("journal", ""),
        doi=paper.get("doi", ""),
        paper_analysis=analysis_str,
        type1_files=json.dumps(type1_names),
        type2_files=json.dumps(type2_files),
        script_files=json.dumps(script_files),
        paper_id=paper_id,
        num_type1_files=len(type1_names),
    )

    max_tokens = config.get("gpt", {}).get("task_gen_max_tokens", 8000)

    try:
        result = call_gpt_json(
            prompt=prompt,
            system_prompt=TASK_GEN_SYSTEM,
            model=model,
            temperature=0.3,
            max_tokens=max_tokens,
        )

        tasks = result.get("research_tasks", [])
        logger.info(f"  Generated {len(tasks)} research tasks")
        return result

    except Exception as e:
        logger.warning(f"  Task generation GPT failed: {e}")
        return {"research_tasks": [], "error": str(e)}


# ===================================================================
# Agent Execution Prompt (3rd prompt — saved as text for agent use)
# ===================================================================

AGENT_PROMPT = """You are a materials science expert agent responsible for performing data analysis on research tasks listed in tasks.json.

Use the dataset_file specified for each task as the primary dataset. Before analysis, briefly inspect the dataset to understand the file structure, filename conventions, and dataset organization.
Use the variables implied by the task description and execution steps in tasks.json. The listed variable names may represent conceptual variables rather than exact field names. Infer spectral features, peak locations, and measurement structure only from tasks.json and the dataset itself.

Do not infer, fabricate, or substitute missing data. If information required for peak identification or interpretation is unavailable, state this clearly and explain the limitation.

Before performing peak-related calculations, identify peaks only when they are supported by clear local maxima in the spectrum. Do not treat noise as peaks. If defensible peaks cannot be identified, report the limitation.

Follow each task step by step. Document the main analysis steps in Task_<task_number>_Analysis.txt, including file loading, data interpretation, feature identification, validation of features, quantitative analysis, and any exclusions. For each step, you must provide explicit reasoning. Describe what you observe from the data, how you interpret it, and why your decision is valid.

Before drawing quantitative conclusions, confirm that the necessary conditions are present in the data. For example, verify that the spectrum is valid, peaks are clearly defined, and calculations are supported by the signal. If these conditions are not met, do not proceed to unsupported downstream interpretation.

Ensure that all extracted quantities are supported directly by the data. If absolute physical interpretation is unclear, do not invent calibrated observables. In that case, report only justified quantities such as peak positions, relative intensities, and intensity ratios.

For each task, generate outputs as specified in tasks.json. Ensure that all outputs are clearly saved under the designated output folder with consistent and descriptive filenames.

If a task cannot be completed because of missing files, corrupted data, insufficient signal quality, lack of identifiable peaks, or ambiguity in interpretation, explain why and do not resolve the issue by making assumptions."""


def _format_paper_analysis(analysis: Optional[Dict[str, Any]]) -> str:
    """Format paper analysis dict into readable text."""
    if not analysis or not analysis.get("summary"):
        return "(Paper analysis not available)"

    lines = []
    lines.append(f"Summary: {analysis.get('summary', '')}")

    mtypes = analysis.get("measurement_types", [])
    if mtypes:
        lines.append(f"Measurement types: {', '.join(mtypes)}")

    if analysis.get("has_raw_measurements"):
        lines.append(f"Raw measurements: {analysis.get('raw_measurement_details', '')}")
    if analysis.get("has_processed_plots"):
        lines.append(f"Processed plots: {analysis.get('processed_plot_details', '')}")

    figures = analysis.get("figures", [])
    if figures:
        lines.append(f"\nFigures ({len(figures)}):")
        for fig in figures[:20]:
            fid = fig.get("figure_id", "?")
            desc = fig.get("description", "?")
            dtype = fig.get("data_type", "?")
            lines.append(f"  {fid}: {desc} [{dtype}]")

    return "\n".join(lines)
