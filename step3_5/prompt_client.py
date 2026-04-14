"""Helpers for Step 3.5 prompt calls."""

import json
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not found in .env")
        _client = OpenAI(api_key=api_key)
    return _client


def call_gpt_json(prompt: str, system_prompt: str, model: str, temperature: float, max_tokens: int) -> Dict[str, Any]:
    client = _get_client()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_completion_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    text = (resp.choices[0].message.content or "").strip()
    if not text:
        raise ValueError("GPT returned empty response")
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return json.loads(text)


PREP_SYSTEM = """You are an expert in condensed matter physics, materials science data workflows, and scientific scripting.
Your task is to prepare a provided script-and-data bundle for execution by identifying the likely executable script, its likely raw-data inputs, expected outputs, and execution requirements.
Be precise and conservative. Do not rewrite the script yet. Return structured JSON."""

PREP_PROMPT = """Prepare this paper's raw-data-plus-script bundle for execution.

Paper title: {title}
Paper journal: {journal}
Paper abstract: {abstract}

=== PAPER ANALYSIS ===
{paper_analysis}

=== TYPE 2 RAW FILES ===
{type2_files}

=== SCRIPT FILES ===
{script_files}

=== SCRIPT CONTENT / SUMMARIES ===
{script_summaries}

=== TASK ===

Identify:
1. which script is the most likely execution target,
2. which raw files it likely depends on,
3. what outputs it likely tries to generate,
4. what path, dependency, or entry-point issues must be fixed before execution.

This step is only for execution preparation.
Do not rewrite the script yet.

=== OUTPUT FORMAT ===

Return JSON:
{{
  "execution_target_script": "...",
  "script_language": "python / notebook / matlab / r / julia / unknown",
  "likely_input_files": ["..."],
  "likely_output_files": ["..."],
  "expected_output_kind": "plot-ready arrays / processed tables / figure images / mixed / unclear",
  "path_issues": ["..."],
  "dependency_hints": ["numpy", "pandas", "matplotlib"],
  "entrypoint_status": "clear / unclear / function-only / notebook-only",
  "figure_hints": ["Fig. 1", "Fig. 2b", "unknown"],
  "preparation_summary": "brief summary of what needs to be prepared before execution",
  "confidence": "high" | "medium" | "low"
}}"""

PATCH_SYSTEM = """You are an expert scientific programming assistant.
Your task is to make the minimum possible edits needed to execute a provided research script in a new local environment.
Preserve the scientific logic exactly as written.
Only fix paths, execution entry points, and output-saving behavior needed to run the script and preserve reusable processed outputs.
Return structured JSON."""

PATCH_PROMPT = """Patch this research script with the minimum changes needed to run it in the local workspace and save reusable processed outputs.

Paper title: {title}

=== EXECUTION PREPARATION ===
{execution_preparation}

=== ORIGINAL SCRIPT PATH ===
{script_path}

=== ORIGINAL SCRIPT CONTENT ===
{script_content}

=== AVAILABLE RAW FILES ===
{type2_files}

=== WORKING DIRECTORY ===
{workdir}

=== OUTPUT DIRECTORY ===
{output_dir}

=== TASK ===

Make only the minimum changes needed to:
1. fix input/output paths,
2. make the script executable in this workspace,
3. save processed, plot-ready numeric outputs if possible,
4. preserve the original scientific logic.

=== STRICT LIMITS ===

- Do NOT change the scientific processing logic.
- Do NOT add new filtering, smoothing, fitting, interpolation, normalization, or data transformation steps unless they are already explicitly present in the original script.
- Do NOT redesign the analysis.
- Do NOT invent new scientific processing steps.
- Only fix paths, entry points, and output-saving behavior.

Prefer saving reusable numeric arrays/tables over only saving figure images.

=== OUTPUT FORMAT ===

Return JSON:
{{
  "should_patch": true/false,
  "patch_summary": "brief summary of the minimal edits",
  "path_fixes": ["..."],
  "output_saves_added": ["..."],
  "entrypoint_changes": ["..."],
  "patched_script": "full patched script text",
  "expected_generated_files": ["..."],
  "figure_hints": ["Fig. 1", "Fig. 2b", "unknown"],
  "risks": ["..."],
  "confidence": "high" | "medium" | "low"
}}"""

EVAL_SYSTEM = """You are an expert in condensed matter physics and materials science datasets.
Your task is to evaluate whether executed processing scripts successfully transformed provided raw Type 2 data into reusable Type 1 plot-ready outputs.
Use the paper context, raw-file information, script descriptions, and generated outputs together.
Return structured JSON."""

EVAL_PROMPT = """Evaluate whether this executed script successfully generated Type 1 plot-ready data from the provided raw Type 2 data.

Paper title: {title}
Paper journal: {journal}

=== PAPER ANALYSIS ===
{paper_analysis}

=== TYPE 2 RAW FILES ===
{type2_files}

=== SCRIPT FILES ===
{script_files}

=== EXECUTION PREPARATION ===
{execution_preparation}

=== PATCH SUMMARY ===
{patch_summary}

=== EXECUTION LOG ===
{execution_log}

=== GENERATED OUTPUT FILES ===
{generated_outputs}

=== TASK ===

Decide:
1. whether execution succeeded meaningfully,
2. whether reusable Type 1 data was generated,
3. whether this paper should now be counted as Both Type 1 and Type 2,
4. which generated outputs correspond to which figures, if that can be inferred.

=== IMPORTANT RULES ===

1. Reusable numeric outputs (CSV, TXT, XLSX, NPY, arrays, tables) are the strongest evidence for Type 1. If these exist, count_paper_as_both = true.
2. If only figure images (.png, .pdf, .svg) were generated, count_paper_as_both = true ONLY IF there is clear evidence the script actually reads and processes Type 2 raw data files (e.g. the script loads a .dat/.csv/.h5 file listed in the Type 2 files, or the execution log shows it reading input data). If the figure was generated without using Type 2 data, count_paper_as_both = false.
3. Use output filenames, save commands, script comments, variable names, and references in the paper text or figure captions when inferring figure mappings.
4. If there is no clear figure evidence, return "unknown".
5. If outputs remain ambiguous, lower confidence and explain why.
6. Only set count_paper_as_both to false if: the script failed, produced no outputs, OR produced only figures without evidence of reading Type 2 data.

=== OUTPUT FORMAT ===

Return JSON:
{{
  "execution_successful": true/false,
  "execution_status": "success / failed_path / failed_dependency / failed_runtime / unclear_output",
  "generated_type1_data": true/false,
  "count_paper_as_both": true/false,
  "generated_type1_files": ["..."],
  "generated_output_kind": "csv / xlsx / txt / npy / figure image only / mixed / unclear",
  "figure_mapping": [
    {{
      "output_file": "...",
      "figure": "Fig. 2a",
      "confidence": "high | medium | low"
    }}
  ],
  "evidence_for": ["..."],
  "evidence_against": ["..."],
  "type1_generation_summary": "what usable Type 1 data was generated",
  "confidence": "high" | "medium" | "low",
  "reasoning": "final explanation of whether the paper should be upgraded to Both"
}}"""


def prompt_enabled(config: Dict[str, Any]) -> bool:
    return bool(config.get("prompt", {}).get("enabled", True)) and bool(os.getenv("OPENAI_API_KEY"))


def _run(prompt: str, system: str, config: Dict[str, Any], max_tokens: int) -> Dict[str, Any]:
    p = config.get("prompt", {})
    return call_gpt_json(prompt, system, p.get("model", "gpt-5.4-mini"), p.get("temperature", 0.1), max_tokens)


def run_preparation_prompt(payload: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    return _run(PREP_PROMPT.format(**payload), PREP_SYSTEM, config, 2200)


def run_patch_prompt(payload: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    return _run(PATCH_PROMPT.format(**payload), PATCH_SYSTEM, config, 4000)


def run_evaluation_prompt(payload: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    return _run(EVAL_PROMPT.format(**payload), EVAL_SYSTEM, config, 2600)
