# Step 3 Prompts

This file summarizes the GPT prompts used in Step 3 dataset understanding and file classification.
Step 3 is the first stage that works with actual downloaded files rather than only metadata or repository inventories.
The first prompt reads the paper itself to understand the scientific context and how the authors describe their data, while the second prompt uses that context together with file inspection reports to classify files into Type 1, Type 2, scripts, or documentation.
These outputs drive the paper-level `has_type1 / has_type2 / has_both_types` decision that later feeds Step 4 organization.

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
      "likely_source": "raw measurement / processed data / derived"
    }
  ],

  "has_raw_measurements": true/false,
  "raw_measurement_details": "what raw data was collected (e.g. STM scans, neutron spectra)",

  "has_processed_plots": true/false,
  "processed_plot_details": "what processed data is plotted",

  "dataset_characterization": {
    "data_availability_statement": "summarize any statement about data availability in the paper",

    "data_provided_types": [
      "raw",
      "processed",
      "source_data",
      "scripts",
      "unknown"
    ],

    "raw_data_description": "how raw data is described in the paper (files, instruments, formats)",

    "processed_data_description": "how processed data is described (tables, extracted values, etc.)",

    "figure_data_description": "whether figure-specific data is provided (e.g. source data per figure)",

    "scripts_description": "whether analysis scripts or notebooks are mentioned",

    "data_organization": "e.g. figure-based folders / raw folders / mixed / not specified",

    "replot_ready_data_present": true/false,

    "replot_reason": "why the data is or is not directly usable for replotting",

    "notes": "any important observations about how data is structured or described"
  },

  "classification_prior": {
    "raw_data_expected": true/false,
    "source_data_expected": true/false,
    "both_expected": true/false,
    "raw_data_evidence": "brief evidence from the paper",
    "source_data_evidence": "brief evidence from the paper",
    "both_evidence": "brief evidence if both are implied, else 'none'",
    "data_availability_section_relevant": "important phrases from data availability / methods / figure captions",
    "priority_modalities": ["measurement or file modalities likely to appear in dataset"],
    "review_notes": "anything the classifier should be careful about"
  }}

=== IMPORTANT RULES ===

1. Do NOT assume based only on general knowledge.
2. Use only evidence from the paper text.
3. Distinguish clearly between:
   - raw measurement data
   - processed/cleaned data
   - figure/source data
   - scripts
4. "Source data" usually means processed figure data, NOT raw data.
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

=== RULE-BASED PRIOR ===
{rule_prior}

=== FILE INSPECTION REPORTS ===
{file_reports}

=== CLASSIFICATION DEFINITIONS ===

Type 1 (Cleaned, replot-ready):
- Tabular data (CSV, XLSX, TXT) with column headers naming physical variables
- Organized as figure-specific data (e.g., "Fig1", "Figure_3e", "FigS4")
- Small-to-moderate file sizes appropriate for figure data
- Can be directly loaded and plotted with minimal processing
- "Source Data" deposits organized by figure = Type 1 (source data ≠ raw data)

Type 2 (Raw/unprocessed):
- Instrument output: binary/proprietary formats, microscopy images, HDF5, etc.
- Files named after scans, experiments, or instrument runs
- Files requiring processing scripts to generate figures
- Files explicitly described as raw in the paper
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
6. If the paper explicitly states data is figure/source data → prioritize that (Type 1)

=== REASONING PROCEDURE ===

For each file, follow this step-by-step reasoning:

Step A. Paper Evidence
- Identify any statements about whether the dataset is raw, processed, or figure data

Step B. File Evidence
- Inspect filename, extension, size, structure, headers, sheet names

Step C. Functional Role
- Determine if the file is:
  - figure-ready data
  - raw measurement data
  - script
  - documentation
  - other

Step D. Replot Test
- Can this file be directly plotted with minimal processing?
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
  "rule_based_alignment": "whether the final decision agrees with the rule-based prior, and why",
  "type1_files": ["..."],
  "type2_files": ["..."],
  "confidence": "high" | "medium" | "low",
  "notes": "important observations"
}
```
