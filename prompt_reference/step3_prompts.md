# Step 3 Prompts

This file summarizes the GPT prompts used in Step 3 paper understanding and file classification.
Step 3 is the first stage that works with actual downloaded files rather than only metadata or repository inventories.
The first prompt reads the paper itself to extract scientific context and dataset semantics, while the second prompt uses that paper context together with file inspection reports to classify files into Type 1, Type 2, scripts, or documentation.
In the current codebase, Step 3 classification is prompt-led: paper analysis and file evidence are passed directly to GPT, while older rule-based prior and reconciliation logic are no longer part of the active classification prompt flow.

## Prompt A: Paper Analysis

### System Prompt

```text
You are an expert in condensed matter physics and materials science.
You carefully read scientific papers and extract BOTH scientific understanding and dataset semantics.
You must distinguish between raw data, processed data, figure data, and scripts based on the paper.
Return structured JSON.
```

### User Prompt Template

```text
Read this condensed matter / materials science paper and extract BOTH:

(1) Scientific understanding of the paper
(2) Dataset semantics (how data is generated, processed, and provided)

Paper title: {title}
Paper journal: {journal}

=== PAPER TEXT ===
{paper_text}

=== TASK ===

Provide:

1. Scientific summary
2. Measurement types
3. Figure-level descriptions
4. Dataset semantics (VERY IMPORTANT)

=== OUTPUT FORMAT ===

Return JSON:

{
  "summary": "2-3 sentence summary: material, technique, key findings",

  "measurement_types": [
    "e.g. STM topography",
    "transport",
    "ARPES",
    "XRD"
  ],

  "figures": [
    {
      "figure_id": "Fig1a",
      "description": "what this figure shows",
      "data_type": "image / spectrum / transport curve / diffraction pattern",
      "likely_source": "theoretical calculations or simulations / experimental data"
    }
  ],

  "has_raw_measurements": true/false,
  "raw_measurement_details": "what raw data was collected (e.g. STM scans, neutron spectra)",

  "dataset_characterization": {
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
  },

  "classification_prior": {
    "raw_data_expected": true/false,
    "source_data_expected": true/false,
    "raw_data_evidence": "brief evidence from the paper",
    "source_data_evidence": "brief evidence from the paper",
    "data_availability_section_relevant": "important phrases from data availability / methods / figure captions",
    "priority_modalities": ["measurement or file modalities likely to appear in dataset"]
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
```

## Prompt B: Dataset Type Classification

### System Prompt

```text
You are an expert in condensed matter physics and materials science datasets.
Your task is to classify dataset files into Type 1 and Type 2 based on BOTH paper evidence and file evidence.
You must follow a structured reasoning process and be precise, conservative, and evidence-based. Return structured JSON.
```

### User Prompt Template

```text
Analyze these dataset files from a condensed matter / materials science paper and classify each file.

Paper title: {title}
Paper journal: {journal}
Paper abstract: {abstract}

=== PAPER ANALYSIS (from reading the full publication) ===
{paper_analysis}

=== FILE INSPECTION REPORTS ===
{file_reports}

=== CLASSIFICATION DEFINITIONS ===

Type 1 (Cleaned, replot-ready):
- Tabular data (CSV, XLSX, TXT) with column headers naming variables, especially processed variables (e.g. R/resistance, which most of the time has to be processed from voltage and current signals)
- Organized as figure-specific data (e.g., "Fig1", "Figure_3e", "FigS4")
- Small-to-moderate file sizes appropriate for figure data
- Theoretical calculation or simulation data
- Optical microscopy data (Specifically, white light imaging for sample geometry. File type is usually jpg or png)
- Can be directly loaded and plotted with minimal processing
- "Source Data" deposits organized by figure = Type 1 (source data ≠ raw data)

Type 2 (Raw/unprocessed):
- Instrument output: binary/proprietary formats, microscopy images, HDF5, etc.
- Files named after scans, sample names, experiments, experimental conditions, or instrument runs
- Files in which all variables/units are directly measured from instruments (for example, voltage, current, Gauss/kilogauss)
- Files requiring processing scripts to generate figures
- Files explicitly described as raw in the paper or description in the online data repository link
- Large files significantly bigger than typical figure datasets
- Data requiring significant preprocessing before plotting

=== IMPORTANT REASONING RULES ===

1. Do NOT classify based on file extension alone.
2. Do NOT classify based on filename alone.
3. Use BOTH:
   - Paper evidence (statements from the publication)
   - File evidence (structure, format, content)
4. If paper evidence and file evidence conflict:
   - Explicitly describe the conflict
   - Resolve conservatively
5. If the paper explicitly states data is raw → prioritize that (Type 2)
6. If the paper explicitly states data is figure → prioritize that (Type 1)
7. For AFM and other microscopy data that is not white light imaging (normal microscope pictures) that is not stated raw/processed clearly in any descriptions: Consider as type 1, if there is a good amount of type 1 (>=2 files or 30%) data in this dataset. Consider them as type 2, if otherwise.

=== REASONING PROCEDURE ===

For each file, follow this step-by-step reasoning:

Step A. Paper Evidence
- Identify any statements about whether the dataset is raw, processed, or figure data

Step B. File Evidence
- Inspect filename, extension, size, structure, headers, sheet names, variable names and units

Step C. Functional Role
- Determine if the file is:
  - figure-ready data
  - raw measurement data
  - script
  - documentation
  - other

Step D. Replot Test
- Can this file be directly plotted with common variables as the axes with minimal processing?
  → Yes → supports Type 1
  → No → supports Type 2

Step E. Conflict Handling
- If ambiguous, explain why
- Do NOT silently guess

Step F. Final Decision
- Assign type only after completing reasoning

=== OUTPUT FORMAT ===

Return JSON:
{
  "file_classifications": [
    {
      "relative_path": "...",
      "filename": "...",
      "type": "type1" | "type2" | "script" | "documentation" | "other",
      "paper_evidence": "brief paper-based evidence",
      "file_evidence": "brief file-based evidence",
      "reasoning": "how the final decision was made",
      "ambiguity": "none or explanation if uncertain",
      "key_columns_or_structure": "e.g., Temperature(K), Magnetization(emu/g)"
    }
  ],
  "has_type1": true/false,
  "has_type2": true/false,
  "has_both": true/false,
  "type1_summary": "...",
  "type2_summary": "...",
  "type1_files": ["..."],
  "type2_files": ["..."],
  "data_organization": "e.g. figure-based folders / raw folders / mixed / not specified",
  "replot_ready_data_present": true/false,
  "replot_reason": "why the data is or is not directly usable for replotting",
  "confidence": "high" | "medium" | "low",
  "notes": "important observations"
}
```
