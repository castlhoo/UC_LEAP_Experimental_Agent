# Workflow and Prompt Overview

This directory documents the active Step 1-5 UC LEAP workflow and the GPT prompts used by each stage.

## Current Prompt Reference Files

| File | Stage | GPT use |
|---|---|---|
| `step1_prompts.md` | Step 1 candidate discovery and screening | Optional paper screening; query generation template exists but active query flow is static/config-driven |
| `step2_prompts.md` | Step 2 link and repository inventory verification | Optional repository inventory assessment |
| `step3_prompts.md` | Step 3 paper reading | Paper-level scientific and dataset-semantics extraction |
| `step4_prompts.md` | Step 4 dataset assessment and file classification | Dataset-level assessment plus batched file classification |
| `step5_prompts.md` | Step 5 final storage | No GPT; rule-based organization and sidecar generation |

The old Step 3.5 script-reproduction prompt reference has been removed from the active prompt set because the current workflow is Step 1 -> Step 2 -> Step 3 -> Step 4 -> Step 5.

## End-to-End Flow

```text
Step 1
Candidate paper search and metadata screening
  input: query config + metadata APIs
  output: step1/output/step1_candidates_latest.json

Step 2
Dataset-link discovery, repository classification, and inventory check
  input: Step 1 candidates
  output: step2/output/step2_inventory_latest.json

Step 3
Paper PDF reading and paper-level dataset semantics
  input: Step 2 dataset evidence + paper PDFs
  output: step3/output/step3_paper_analysis_latest.json

Step 4
Dataset download, file inspection, dataset-level assessment, file classification
  input: Step 2 evidence + Step 3 paper analysis
  output: step4/output/step4_classification_latest.json

Step 5
Final local organization and sidecar generation
  input: Step 4 classification output
  output: step5/organized/
```

## Prompt Dependency Chain

```text
Step 1 screening
  -> field/experiment/data-mention hints

Step 2 inventory assessment
  -> repository and visible-file evidence

Step 3 paper analysis
  -> scientific context, measurement types, data availability statements,
     raw/source-data expectations

Step 4B dataset-level assessment
  -> dataset meaning, field relevance, out-of-scope handling,
     classification plan

Step 4C file-level classification
  -> type1/type2/script/documentation/other file decisions

Step 5 rule-based organization
  -> final folders, manifest, reasoning sidecars
```

## Type Definitions

### Type 1

Cleaned, processed, source-data, figure-ready, or directly replot-ready data.
Typical signals:

- figure-specific source-data folders/files,
- CSV/XLSX/TXT with named columns,
- processed variables such as resistance or fitting outputs,
- theoretical/simulation data prepared for figures,
- optical sample-geometry images.

### Type 2

Raw or minimally processed experimental/instrument output.
Typical signals:

- binary/proprietary formats,
- HDF5 or instrument-run outputs,
- scan/sample/condition folders,
- direct measurement variables such as voltage/current/field,
- files requiring scripts or preprocessing before plotting,
- files explicitly described as raw.

### Other

Used by Step 4 when a data file is out of project scope after both paper and file evidence are inspected.
Out-of-scope data must not be counted as Type 1 or Type 2.

## Field-Relevance Policy

Out-of-scope filtering belongs in Step 4, after actual dataset files have been inspected.
The field guide used in Step 4 is:

- `strong`: condensed matter / quantum materials / solid-state physics.
- `general`: broader materials science, devices, synthesis, characterization, or materials-relevant computation.
- `weak`: tangential relevance; only count Type 1/Type 2 when both paper and file evidence clearly support materials/condensed-matter relevance.
- `none`: unrelated fields such as biomedical, virology, ecology, astronomy, high-energy particle physics, pure CV/ML benchmarks, facial recognition, social science, or economics.

## Final Output Contract

Step 5 final paper folders use this layout:

```text
<paper_folder>/
  paper_dataset_summary.json
  reasoning.json
  reasoning.txt
  pdf/
  type1/
  type2/
  scripts/
  annotations/
```

Generated sidecars are stored at the paper-folder root.
Original README/metadata/description files stay in `annotations/`.
