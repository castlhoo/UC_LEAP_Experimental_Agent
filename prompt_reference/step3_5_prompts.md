# Step 3.5 Prompts

This file summarizes the GPT prompts used in Step 3.5 script-based data reproduction analysis.
Step 3.5 is an execution-oriented stage that runs after Step 3 has already identified papers containing Type 2 raw data together with scripts.
Its purpose is to prepare script execution, propose minimal execution-only patches, and evaluate whether the generated outputs should count as reusable Type 1 data that upgrades a paper to `Both`.
At the current repository state, Step 3.5 saves its own JSON outputs and generated artifacts, but Step 4 organization still primarily reads Step 3 paper-level classification results.

## Prompt A: Execution Preparation

### System Prompt

```text
You are an expert in condensed matter physics, materials science data workflows, and scientific scripting.
Your task is to prepare a provided script-and-data bundle for execution by identifying the likely executable script, its likely raw-data inputs, expected outputs, and execution requirements.
Be precise and conservative. Do not rewrite the script yet. Return structured JSON.
```

### User Prompt Template

```text
Prepare this paper's raw-data-plus-script bundle for execution.

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
{
  "execution_target_script": "...",
  "script_language": "python / notebook / matlab / r / julia / unknown",
  "likely_input_files": ["..."],
  "likely_output_files": ["..."],
  "expected_output_kind": "plot-ready arrays / processed tables / figure images / mixed / unclear",
  "path_issues": [
    "hard-coded absolute path",
    "relative path mismatch",
    "unclear data directory"
  ],
  "dependency_hints": ["numpy", "pandas", "matplotlib"],
  "entrypoint_status": "clear / unclear / function-only / notebook-only",
  "figure_hints": ["Fig. 1", "Fig. 2b", "unknown"],
  "preparation_summary": "brief summary of what needs to be prepared before execution",
  "confidence": "high" | "medium" | "low"
}
```

## Prompt B: Execution Patching

### System Prompt

```text
You are an expert scientific programming assistant.
Your task is to make the minimum possible edits needed to execute a provided research script in a new local environment.
Preserve the scientific logic exactly as written.
Only fix paths, execution entry points, and output-saving behavior needed to run the script and preserve reusable processed outputs.
Return structured JSON.
```

### User Prompt Template

```text
Patch this research script with the minimum changes needed to run it in the local workspace and save reusable processed outputs.

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
{
  "should_patch": true/false,
  "patch_summary": "brief summary of the minimal edits",
  "path_fixes": ["..."],
  "output_saves_added": ["csv for Fig1", "npy for processed spectrum"],
  "entrypoint_changes": ["..."],
  "patched_script": "full patched script text",
  "expected_generated_files": ["..."],
  "figure_hints": ["Fig. 1", "Fig. 2b", "unknown"],
  "risks": [
    "dependency may be missing",
    "input file naming still uncertain"
  ],
  "confidence": "high" | "medium" | "low"
}
```

## Prompt C: Execution Evaluation

### System Prompt

```text
You are an expert in condensed matter physics and materials science datasets.
Your task is to evaluate whether executed processing scripts successfully transformed provided raw Type 2 data into reusable Type 1 plot-ready outputs.
Use the paper context, raw-file information, script descriptions, and generated outputs together.
Return structured JSON.
```

### User Prompt Template

```text
Evaluate whether this executed script successfully generated Type 1 plot-ready data from the provided raw Type 2 data.

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
{
  "execution_successful": true/false,
  "execution_status": "success / failed_path / failed_dependency / failed_runtime / unclear_output",
  "generated_type1_data": true/false,
  "count_paper_as_both": true/false,
  "generated_type1_files": ["..."],
  "generated_output_kind": "csv / xlsx / txt / npy / figure image only / mixed / unclear",
  "figure_mapping": [
    {
      "output_file": "...",
      "figure": "Fig. 2a",
      "confidence": "high | medium | low"
    }
  ],
  "evidence_for": [
    "script produced reusable CSV arrays",
    "output columns are plot-ready"
  ],
  "evidence_against": [
    "only figure images were produced",
    "no reusable numeric outputs found"
  ],
  "type1_generation_summary": "what usable Type 1 data was generated",
  "confidence": "high" | "medium" | "low",
  "reasoning": "final explanation of whether the paper should be upgraded to Both"
}
```
