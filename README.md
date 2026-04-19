# UC LEAP

UC LEAP is a reproducible pipeline for finding materials-science papers with usable datasets, verifying the dataset evidence, reading the paper context, classifying released files as Type 1 / Type 2, and organizing the final corpus into a stable local folder structure.

The current active workflow is:

```text
Step 1 -> Step 2 -> Step 3 -> Step 4 -> Step 5
```

There is no active Step 3.5 stage in the current prompt/workflow documentation.

## Target Scope

The target domain is condensed matter physics, quantum materials, solid-state physics, and closely related materials science datasets.

Strong in-scope signals include:

- graphene, TMDs, cuprates, nickelates, iron-based superconductors,
- topological insulators, Weyl/Dirac semimetals, Mott insulators,
- van der Waals heterostructures, twisted bilayers, moire systems,
- superconductivity, magnetism, charge density waves, Kondo physics,
- spin-orbit coupling, skyrmions, phase transitions, quantum oscillations,
- STM/STS, ARPES, XRD, TEM, AFM, EELS, Raman, neutron scattering,
- transport, Hall effect, magnetoresistance, tunneling, Fermi surface, band structure.

Broader materials science can still be in scope when the paper and dataset are genuinely about synthesis, characterization, properties, devices, simulations, or materials-relevant computation.

Off-topic handling happens in Step 4 after file inspection. A paper should not be rejected as off-topic from title/abstract alone.

## Type Definitions

### Type 1

Type 1 data are cleaned, processed, figure-ready, source-data, or directly replot-ready files.

Common examples:

- figure-specific source data,
- CSV/XLSX/TXT files with useful column headers,
- processed variables such as resistance, fitted quantities, normalized spectra,
- simulation/theory output prepared for figures,
- optical sample-geometry images.

### Type 2

Type 2 data are raw or minimally processed measurement/instrument files.

Common examples:

- proprietary or binary instrument output,
- HDF5 or other structured raw measurement containers,
- scan/sample/condition folders,
- direct measurement variables such as voltage, current, field, counts,
- files requiring scripts or preprocessing before plotting,
- files explicitly described as raw.

### Other

`other` is used in Step 4 when inspected files are out of project scope or cannot validly be counted as Type 1 / Type 2 for this project.

## Repository Layout

```text
step1/                  Candidate paper search and screening
step2/                  Dataset-link and repository-inventory verification
step3/                  Paper PDF download/reading and paper-level dataset semantics
step4/                  Dataset download, file inspection, GPT assessment/classification
step5/                  Final local organization
prompt_reference/       Current prompt and workflow documentation
```

Important current outputs:

```text
step1/output/step1_candidates_latest.json
step2/output/step2_inventory_latest.json
step3/output/step3_paper_analysis_latest.json
step4/output/step4_classification_latest.json
step5/organized/manifest_latest.json
step5/organized/
```

Large intermediate folders such as `step4/downloads/` are cache/output folders and can be deleted after Step 5 has produced the final organized corpus.

## Step 1: Candidate Paper Search

Purpose: build a broad candidate set of papers that may have useful datasets.

Main work:

- generate API-specific search queries from config keywords,
- search academic metadata APIs,
- deduplicate papers,
- scan metadata for dataset signals,
- optionally use GPT to screen field relevance and experimental fit,
- score papers and assign `keep`, `maybe`, or `drop`.

Key files:

```text
step1/pipeline.py
step1/query_generator.py
step1/paper_searcher.py
step1/dataset_signal_scanner.py
step1/scorer.py
step1/gpt_client.py
```

Run:

```powershell
python -m step1.run_step1
```

Output:

```text
step1/output/step1_candidates_latest.json
```

Prompt reference:

```text
prompt_reference/step1_prompts.md
```

## Step 2: Dataset Presence and Inventory Check

Purpose: verify whether Step 1 candidates expose real dataset links or repository inventories.

Main work:

- resolve links from DOI pages, paper metadata, and data availability hints,
- classify repository/source-data URLs,
- collect visible inventories from repositories,
- optionally ask GPT to assess repository contents,
- assign dataset status such as `verified`, `source_data_found`, `unclassified_link`, `upon_request`, or `no_dataset_found`.

Key files:

```text
step2/pipeline.py
step2/dataset_link_resolver.py
step2/repository_classifier.py
step2/inventory_collector.py
step2/gpt_client.py
```

Run:

```powershell
python -m step2.run_step2
```

Output:

```text
step2/output/step2_inventory_latest.json
```

Prompt reference:

```text
prompt_reference/step2_prompts.md
```

## Step 3: Paper Analysis

Purpose: read paper PDFs and extract paper-level scientific context and dataset semantics.

Main work:

- download/read paper PDFs,
- extract paper text,
- ask GPT for scientific summary, measurement types, figure descriptions, data availability statements, and raw/source-data expectations,
- save `paper_analysis` for Step 4.

Key files:

```text
step3/pipeline.py
step3/downloader.py
step3/pdf_reader.py
step3/gpt_client.py
```

Run:

```powershell
python -m step3.run_step3
```

Output:

```text
step3/output/step3_paper_analysis_latest.json
step3/papers/
```

Prompt reference:

```text
prompt_reference/step3_prompts.md
```

## Step 4: Dataset Assessment and File Classification

Purpose: inspect actual dataset files and decide Type 1 / Type 2 / script / documentation / other.

Main work:

- load Step 2 dataset evidence and Step 3 paper analyses,
- download dataset files,
- decompress archives with limits,
- inspect filenames, extensions, sizes, tabular headers, sheet names, HDF5 groups, JSON keys, and related metadata,
- run Step 4B dataset-level assessment,
- run Step 4C batched file-level classification,
- merge classifications and recalculate paper-level flags,
- write `step4_classification_latest.json`.

Key files:

```text
step4/pipeline.py
step4/phase4a_inventory/
step4/phase4b_dataset_assessment/
step4/phase4c_file_classification/
step4/phase4d_merge_summary/
step4/shared/
```

Run:

```powershell
python -m step4.run_step4
```

Output:

```text
step4/output/step4_classification_latest.json
```

Prompt reference:

```text
prompt_reference/step4_prompts.md
```

## Step 5: Final Local Organization

Purpose: create the final local paper corpus.

Main work:

- load Step 4 classification output,
- select papers according to config,
- copy final PDFs/data/scripts/annotations into a stable folder layout,
- place generated summaries and reasoning sidecars at the paper-folder root,
- write `manifest_latest.json`.

Key files:

```text
step5/pipeline.py
step5/file_organizer.py
step5/config/step5_config.yaml
```

Run:

```powershell
python -m step5.run_step5
```

Output:

```text
step5/organized/
step5/organized/manifest_latest.json
```

Prompt reference:

```text
prompt_reference/step5_prompts.md
```

## Final Step 5 Folder Contract

Each organized paper folder follows this layout:

```text
<paper_folder>/
  paper_dataset_summary.json
  reasoning.json
  reasoning.txt
  pdf/
    paper_main.pdf
    paper_supplementary.pdf
    paper_peer_review.pdf
  type1/
  type2/
  scripts/
  annotations/
```

Generated sidecars:

- `paper_dataset_summary.json`
- `reasoning.json`
- `reasoning.txt`

These live at the paper-folder root.

Original README, metadata, manifest, and dataset-description files live in `annotations/`.

## Prompt Documentation

All active prompt documentation is under:

```text
prompt_reference/
```

Current files:

```text
prompt_reference/step1_prompts.md
prompt_reference/step2_prompts.md
prompt_reference/step3_prompts.md
prompt_reference/step4_prompts.md
prompt_reference/step5_prompts.md
prompt_reference/workflow_and_prompts_overview.md
```

## Current Cleanup Policy

Keep:

- code and config,
- `*_latest.json` outputs,
- Step 3 paper analyses/PDFs if manual recheck is needed,
- final `step5/organized/`.

Safe to remove after Step 5 is complete:

- `__pycache__/`,
- Step 4 download caches,
- old Step 4 organized folders,
- older timestamped Step 5 manifests when `manifest_latest.json` is current.

## Typical Full Run

```powershell
python -m step1.run_step1
python -m step2.run_step2
python -m step3.run_step3
python -m step4.run_step4
python -m step5.run_step5
```

Run each step only after confirming that the previous step's `*_latest.json` output is present and reasonable.
