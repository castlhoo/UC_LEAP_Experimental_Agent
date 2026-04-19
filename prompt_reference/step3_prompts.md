# Step 3 Prompt Reference

Step 3 reads paper PDFs and produces paper-level scientific and dataset-semantics analysis.
It is no longer the stage that performs final file-level Type 1 / Type 2 classification.

## Active Role

Step 3 connects the paper text to the expected dataset meaning:

- scientific summary,
- measurement modalities,
- expected raw file extensions / instrument outputs,
- figure-level descriptions,
- data availability and source-data statements,
- paper-level prior for later file classification.

## Inputs

- `step2/output/step2_inventory_latest.json`
- Paper PDF URLs discovered by Step 2
- Downloaded paper PDFs in `step3/papers/`

## Outputs

- `step3/output/step3_paper_analysis_latest.json`
- `step3/output/step3.log`
- downloaded/analyzed paper files under `step3/papers/`

## GPT Use

Step 3 uses one GPT prompt in `step3/gpt_client.py`: Paper Analysis.
The result is passed to Step 4 as `paper_analysis`.

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
(3) Types of experiments done and the expected raw data file extensions

Paper title: {title}
Paper journal: {journal}

=== PAPER TEXT ===
{paper_text}

=== TASK ===

Provide:

1. Scientific summary
2. Measurement types and expected raw data file extensions
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
  }
}

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

## Downstream Use

Step 4 uses this `paper_analysis` together with Step 1/2 discovery evidence and Step 4 file inspection reports.
Off-topic filtering and final Type 1 / Type 2 classification happen only after Step 4 has inspected actual dataset files.
