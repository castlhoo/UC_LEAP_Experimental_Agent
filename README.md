# UC LEAP — Framework Documentation

A reproducible multi-stage pipeline for discovering, verifying, downloading, classifying, and organizing materials-science papers with usable datasets.

---

## Table of contents

1. [What this is and why it exists](#1-what-this-is-and-why-it-exists)
2. [What we start with](#2-what-we-start-with)
3. [The pipeline](#3-the-pipeline)
   - [Step 1 - Candidate Paper Search](#step-1---candidate-paper-search)
   - [Step 2 - Dataset Presence and Inventory Check](#step-2---dataset-presence-and-inventory-check)
   - [Step 3 - Dataset Download, Inspection, and Type Classification](#step-3---dataset-download-inspection-and-type-classification)
   - [Step 3.5 - Script-Based Type 1 Reproduction Check](#step-35---script-based-type-1-reproduction-check)
   - [Step 4 - Local Storage and Organization](#step-4---local-storage-and-organization)
4. [File and folder conventions](#4-file-and-folder-conventions)
5. [Running the pipeline end-to-end](#5-running-the-pipeline-end-to-end)
6. [Key design decisions and rationale](#6-key-design-decisions-and-rationale)
7. [Current repository status](#7-current-repository-status)
8. [Open questions and future work](#8-open-questions-and-future-work)
9. [Glossary](#9-glossary)

---

## 1. What this is and why it exists

UC LEAP is a data curation pipeline for building a high-quality corpus of materials-science papers that are suitable for downstream AI-agent benchmarking and experimental data analysis.

The immediate goal is not yet to evaluate agents directly. The goal of this repository is to solve the prerequisite problem first:

- find candidate papers in the right scientific domain,
- verify whether those papers actually expose usable datasets,
- inspect whether the released files contain **Type 1** and/or **Type 2** data,
- optionally check whether raw data plus provided scripts can reproduce Type 1 outputs,
- and organize the selected papers into a consistent local structure for later benchmarking work.

This matters because dataset availability in materials science is noisy and inconsistent. Papers may mention data in publisher supplements, repository deposits, source-data spreadsheets, code archives, or raw instrument outputs. A benchmark cannot be built reliably unless these sources are located, inspected, and normalized first.

What makes this pipeline useful:

- It separates broad paper discovery from stricter dataset verification.
- It distinguishes processed figure-ready data from raw instrument outputs.
- It produces auditable JSON artifacts at every stage.
- It leaves a clear local folder structure that downstream task-generation and evaluation workflows can build on.

---

## 2. What we start with

The repository begins with broad scientific search, not with a pre-curated paper list.

The practical inputs are:

| Input | Description | Where it enters |
|---|---|---|
| Search keywords and query templates | Materials-science topics, experiment terms, and dataset-related keywords | `step1/query_generator.py` |
| Academic metadata APIs | Semantic Scholar, OpenAlex, CrossRef, and arXiv | `step1/paper_searcher.py` |
| Dataset links discovered from papers | Repository URLs, DOI links, source-data references, generic downloadable links, and data availability statements | `step2/dataset_link_resolver.py` |
| Repository inventories and downloadable files | Zenodo/Figshare/GitHub/Dryad plus Materials Cloud, OSF, Dataverse, and Mendeley Data inventories; publisher source data; PDFs; archives; spreadsheets; raw measurement files | `step2`-`step4` |
| OpenAI model calls | Used for paper screening, inventory assessment, paper understanding, Type 1/Type 2 classification, and script-reproduction analysis | `step1/gpt_client.py`, `step2/gpt_client.py`, `step3/gpt_client.py`, `step3_5/prompt_client.py` |

### The fundamental distinction between Type 1 and Type 2 data

This distinction drives the later organization logic.

- **Type 1 data** is cleaned, figure-ready, or source-data style material. It is typically tabular and suitable for re-plotting or direct inspection.
- **Type 2 data** is raw or minimally processed experimental output. It often comes from instruments or archives and is closer to the original measurement stream.

In practice, the repository treats this distinction as a classification problem informed by:

- file extensions and structure,
- file contents,
- repository context,
- and paper/PDF context.

---

## 3. The pipeline

The pipeline transforms broad literature search results into a locally organized benchmark-ready paper set.

```text
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Step 1    │ -> │   Step 2    │ -> │   Step 3    │ -> │  Step 3.5   │ -> │   Step 4    │
│ Candidate   │    │ Dataset     │    │ Download +  │    │ Script      │    │ Local       │
│ Search      │    │ Verification│    │ Classification│   │ Reproduction│    │ Organization│
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  │                  │                  │
       ▼                  ▼                  ▼                  ▼                  ▼
 step1/output/      step2/output/      step3/output/      step3_5/output/   step4/organized/
 candidates         inventory          classification     script checks      manifest + folders
```

### Step 1 - Candidate Paper Search

**Purpose:** Build a high-recall list of candidate papers in condensed matter and materials science that are likely to contain relevant experimental datasets.

**Input:**

- Topic, experiment, and data-related keywords
- Hand-crafted search templates
- Metadata APIs:
  - Semantic Scholar
  - OpenAlex
  - CrossRef
  - arXiv

**Process:**

Step 1 builds broad search queries, searches multiple metadata APIs, deduplicates results, scores papers by priority, and assigns a screening decision such as `keep`, `maybe`, or `drop`.

The active GPT use in Step 1 is the paper-screening prompt, which evaluates field match, experimental relevance, soft-material mismatch, review status, and whether data availability is mentioned.

Key components:

- `step1/pipeline.py`
- `step1/query_generator.py`
- `step1/paper_searcher.py`
- `step1/deduplicator.py`
- `step1/dataset_signal_scanner.py`
- `step1/scorer.py`
- `step1/gpt_client.py`

**Output:**

- `step1/output/step1_candidates_<timestamp>.json`
- `step1/output/step1_candidates_latest.json`
- `step1/output/step1_keep_maybe_<timestamp>.json`
- `step1/output/step1_run.log`

**Rationale:** Step 1 optimizes for recall, not precision. It is acceptable to retain uncertain papers as `maybe` if they might become useful after deeper dataset inspection.

**Current note:** Step 1 is recall-oriented and may include noisy candidates. Semantic Scholar is treated as a best-effort source and can be rate-limited independently of the other APIs.

---

### Step 2 - Dataset Presence and Inventory Check

**Purpose:** Determine whether Step 1 candidates actually expose datasets and, if so, what repositories or source-data files are available.

**Input:**

- `step1/output/step1_candidates_latest.json`
- DOI landing pages and data availability statements
- Repository APIs and publisher-hosted source-data links

**Process:**

Step 2 orchestrates six phases:

1. load Step 1 candidates,
2. resolve dataset links from DOI landing pages and related metadata,
3. classify repositories,
4. collect file inventories,
5. use GPT to assess inventory quality and likely dataset type,
6. save normalized results.

The default repositories supported in config are:

- Zenodo
- Figshare
- GitHub
- Dryad
- Materials Cloud
- OSF
- Dataverse
- Mendeley Data

Key components:

- `step2/pipeline.py`
- `step2/dataset_link_resolver.py`
- `step2/repository_classifier.py`
- `step2/inventory_collector.py`
- `step2/candidate_loader.py`
- `step2/gpt_client.py`
- `step2/config/step2_config.yaml`

**Output:**

- `step2/output/step2_inventory_<timestamp>.json`
- `step2/output/step2_inventory_latest.json`

Each paper is assigned a `dataset_status`, such as:

- `verified`
- `link_found`
- `source_data_found`
- `upon_request`
- `unclassified_link`
- `no_dataset_found`

Step 2 also records verification metadata such as:

- `verification_score`
- `verification_reasons`
- `needs_human_review`

**Rationale:** This stage narrows the broad Step 1 pool into papers with actual evidence of data availability, which is a stronger requirement than promising metadata alone.

**Current note:** Step 2 is still inventory-first. It does not yet decide final paper inclusion by itself; instead, it prepares normalized repository and file evidence for Step 3.

---

### Step 3 - Dataset Download, Inspection, and Type Classification

**Purpose:** Download candidate datasets, inspect their contents, and classify each paper as containing Type 1, Type 2, both, or neither.

**Input:**

- `step2/output/step2_inventory_latest.json`
- Downloadable dataset files and paper PDFs

**Process:**

Step 3 runs six phases:

1. load Step 2 results,
2. download paper PDFs and analyze paper text when available,
3. download dataset files,
4. inspect file contents,
5. classify files into Type 1 / Type 2 with GPT and paper context,
6. save per-paper and combined classification outputs.

The downloader and inspector handle a wide range of file types, including:

- tabular files such as `.csv`, `.xlsx`, `.xls`, `.tsv`,
- numerical arrays such as `.npy`, `.npz`, `.mat`,
- instrument and archive formats such as `.h5`, `.hdf5`, `.nxs`, `.sxm`, `.ibw`, `.zip`,
- and PDFs/scripts when useful for contextual understanding.

Key components:

- `step3/pipeline.py`
- `step3/downloader.py`
- `step3/file_inspector.py`
- `step3/pdf_reader.py`
- `step3/gpt_client.py`
- `step3/config/step3_config.yaml`

**Output:**

- `step3/output/step3_classification_latest.json`
- `step3/output/papers/*.json`
- downloaded files under `step3/downloads/`
- logs in `step3/output/step3.log`

Step 3 now uses two main kinds of evidence during Type 1 / Type 2 classification:

1. paper/PDF analysis,
2. file inspection reports.

The current design is prompt-led: paper context and file evidence are passed to GPT, while code-side inspection is used to summarize files rather than to override the final classification judgment.

**Rationale:** This is the first stage where the repository reasons about the actual file contents rather than just repository metadata.

**Important implementation note:** Step 3 and Step 4 now share the same PDF download strategy through `pdf_utils.py`, with the Step 3 downloader logic treated as the source of truth.

---

### Step 3.5 - Script-Based Type 1 Reproduction Check

**Purpose:** Examine papers that contain Type 2 raw data plus scripts, and determine whether those scripts can reproduce reusable Type 1 outputs from the provided raw data.

**Input:**

- `step3/output/step3_classification_latest.json`
- raw Type 2 files under `step3/downloads/`
- script files identified in Step 3

**Process:**

Step 3.5 is split into three prompt-guided substeps:

1. **Execution preparation**: identify the likely execution target, input files, expected outputs, and execution issues,
2. **Execution patching**: make minimal path/entry-point/output-saving edits without changing the scientific logic,
3. **Execution evaluation**: assess whether execution produced reusable Type 1 outputs and whether the paper should be upgraded to `Both`.

This stage is implemented as an execution-oriented extension rather than a replacement for Step 3.

Key components:

- `step3_5/pipeline.py`
- `step3_5/preparation.py`
- `step3_5/patcher.py`
- `step3_5/runner.py`
- `step3_5/evaluator.py`
- `step3_5/prompt_client.py`
- `step3_5/config/step3_5_config.yaml`

**Output:**

- `step3_5/output/step3_5_results_latest.json`
- per-paper results under `step3_5/output/papers/`
- temporary execution bundles under `step3_5/work/`

**Current note:** Step 3.5 is implemented, but it should still be considered an experimental extension. The current release can analyze and execute candidate script bundles, but Step 4 still primarily consumes Step 3 classification output rather than fully merging Step 3.5-generated Type 1 artifacts.

---

### Step 4 - Local Storage and Organization

**Purpose:** Convert the Step 3 classification output into a clean local corpus organized by paper and dataset type.

**Input:**

- `step3/output/step3_classification_latest.json`
- downloaded files from `step3/downloads/`
- optional PDF downloads

**Process:**

Step 4 performs five phases:

1. load Step 3 classification results,
2. select papers to organize,
3. reuse Step 3 paper PDFs when possible and otherwise retry the shared downloader,
4. copy and rename files into a stable local structure using `relative_path`-aware file matching,
5. generate a manifest for human and programmatic use.

The default output grouping is:

- `Both/`
- `Type1/`
- `Type2/`
- `Neither/` when `all`-style organization is requested

Within each paper folder, the organizer separates:

- `type1_data`
- `type2_data`
- annotation or documentation files
- scripts or notebooks
- `pdf/` when available

Step 4 also now treats supplementary information and peer-review attachments as documentation artifacts rather than dataset files when they appear as PDF/Word documents. Those files are organized under annotations rather than `type1_data` or `type2_data`.

Key components:

- `step4/pipeline.py`
- `step4/file_organizer.py`
- `step4/pdf_downloader.py`
- `step4/config/step4_config.yaml`

**Output:**

- `step4/organized/manifest_<timestamp>.json`
- `step4/organized/manifest_latest.json`
- organized paper folders under `step4/organized/Both`, `step4/organized/Type1`, and `step4/organized/Type2`

**Rationale:** Downstream benchmarking work becomes much easier once each paper has a predictable folder layout and a manifest that records what was preserved and why.

**Current note:** Step 4 writes `reasoning.txt` into each organized paper folder so that paper-level and file-level classification reasoning can be reviewed without opening JSON files directly.

---

## 4. File and folder conventions

At the repository root:

```text
UC_LEAP/
├── step1/
├── step2/
├── step3/
├── step3_5/
├── step4/
├── prompt_reference/
├── requirements.txt
├── run_pipeline.py
├── pdf_utils.py
├── utils.py
├── .env
└── .env.example
```

Pipeline artifact conventions:

- Step 1 writes candidate lists under `step1/output/`
- Step 2 writes dataset verification inventories under `step2/output/`
- Step 3 writes classification summaries under `step3/output/` and raw downloads under `step3/downloads/`
- Step 3.5 writes script-reproduction summaries under `step3_5/output/` and temporary execution bundles under `step3_5/work/`
- Step 4 writes the curated local corpus under `step4/organized/`

The Step 4 organized structure looks like:

```text
step4/organized/
├── Both/
│   └── <paper_index>_<short_title>/
├── Type1/
│   └── <paper_index>_<short_title>/
├── Type2/
│   └── <paper_index>_<short_title>/
└── manifest_latest.json
```

Each paper directory may contain:

- `pdf/`
- renamed Type 1 data files
- renamed Type 2 data files
- annotations such as `README`, metadata, or descriptions
- scripts such as `.py`, `.m`, `.R`, `.jl`, `.ipynb`, or `.sh`

---

## 5. Running the pipeline end-to-end

### Environment setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set `OPENAI_API_KEY` in `.env`.
   A safe starting point is to copy `.env.example` and fill in the real key locally.

3. Run the full pipeline from the repository root:

```bash
python run_pipeline.py
```

This unified entry point runs:

- Step 1
- Step 2
- Step 3
- Step 3.5
- Step 4

If you prefer, you can still run each step manually:

```bash
python -m step1.run_step1
python -m step2.run_step2
python -m step3.run_step3
python -m step3_5.run_step3_5
python -m step4.run_step4
```

To compare Step 1 query strategies, you can point Step 1 at different config files:

```bash
$env:STEP1_CONFIG_FILE="step1_config.yaml"; python -m step1.run_step1
$env:STEP1_CONFIG_FILE="step1_config_gpt_queries.yaml"; python -m step1.run_step1
```

### Step-by-step recipe

#### Step 1

1. Generate broad, recall-oriented paper candidates.
2. Review `step1/output/step1_candidates_latest.json`.
3. Focus on `keep` and `maybe` decisions for the next stage.

#### Step 2

1. Resolve dataset links and inventory available repositories.
2. Review `step2/output/step2_inventory_latest.json`.
3. Confirm whether promising papers have `verified` or `source_data_found` status.

#### Step 3

1. Download candidate datasets and paper PDFs.
2. Inspect file structures and classify files into Type 1 / Type 2.
3. Review `step3/output/step3_classification_latest.json` and per-paper JSON files under `step3/output/papers/`.

#### Step 4

1. Organize selected papers into the local corpus.
2. Review `step4/organized/manifest_latest.json`.
3. Use the organized folders as the curated starting point for downstream benchmark construction.

#### Step 3.5

1. Identify papers with raw Type 2 data plus scripts.
2. Prepare and minimally patch executable bundles when possible.
3. Evaluate whether script execution can generate reusable Type 1 outputs from the provided raw data.
4. Review `step3_5/output/step3_5_results_latest.json` and per-paper JSON files under `step3_5/output/papers/`.

## 6. Key design decisions and rationale

### D1. Multi-API search for recall

**Decision:** Search across multiple academic metadata APIs rather than relying on a single provider.

**Rationale:** No single API has complete coverage for this domain. Combining multiple sources increases recall and makes candidate discovery more robust.

### D2. Separate candidate discovery from dataset verification

**Decision:** Use Step 1 for broad discovery and Step 2 for evidence-based dataset verification.

**Rationale:** A paper can look promising scientifically but still fail the benchmark-building requirement if the data is unavailable or inaccessible.

### D3. Distinguish Type 1 from Type 2 explicitly

**Decision:** Preserve the distinction between processed/source data and raw experimental data.

**Rationale:** This distinction is central for later benchmark design. Type 1 and Type 2 support different evaluation and task-generation goals.

### D4. Use GPT only after collecting concrete evidence

**Decision:** GPT calls are used to interpret inventories, paper text, and file contents, but only after the repository has gathered structured evidence from APIs and downloaded files.

**Rationale:** This keeps the pipeline grounded and auditable. GPT is used as a classifier/interpreter, not as the primary source of facts.

### D5. Save JSON artifacts at every step

**Decision:** Every stage emits explicit JSON outputs rather than keeping results transient.

**Rationale:** This makes the pipeline resumable, inspectable, and easier to debug.

### D6. Organize final outputs by dataset availability

**Decision:** Step 4 groups papers under `Both`, `Type1`, `Type2`, and explicitly handles `Neither` when needed.

**Rationale:** Downstream consumers often need to prioritize papers with both processed and raw data, but it is still useful to retain one-sided cases for future work.

### D7. Prefer path-aware file matching over filename-only matching

**Decision:** Step 4 matches files primarily by relative path rather than filename alone.

**Rationale:** Repository and supplementary archives often contain repeated filenames such as `README.md` or `data.csv`. Relative-path matching reduces classification collisions and preserves Step 3 intent more faithfully.

### D8. Preserve outputs safely before cleaning older artifacts

**Decision:** New pipeline artifacts are written before older timestamped outputs are cleaned up.

**Rationale:** Long-running download and classification stages should not lose the last good snapshot if a run fails midway.

### D9. Keep script-based reproduction separate from file classification

**Decision:** Use Step 3 for direct file classification and Step 3.5 for script-based reproduction analysis.

**Rationale:** Raw-plus-script bundles are important, but mixing execution logic directly into Step 3 would make the core Type 1 / Type 2 classifier much harder to interpret and maintain.

### D10. Use shared PDF download logic across Step 3 and Step 4

**Decision:** Treat the Step 3 PDF downloader as the source of truth and reuse the same download strategy in Step 4 through a shared utility module.

**Rationale:** The paper PDF retrieval problem should not diverge between classification and organization stages. A shared implementation reduces patch drift and debugging confusion.

---

## 7. Current repository status

As of the current code state in this repository:

- Step 1 is runnable through `run_pipeline.py` and its standalone module entry point.
- Step 2 includes broader repository coverage and richer verification metadata.
- Step 3 uses prompt-led paper/file classification and shared PDF download logic.
- Step 3.5 is implemented as a script-reproduction extension with preparation, patching, and execution-evaluation stages.
- Step 4 organizes selected papers, preserves reasoning text files, and routes supplementary/peer-review documents into annotations.

The codebase has also been updated so that:

- the full pipeline can be launched through `python run_pipeline.py`,
- prompt reference documents under `prompt_reference/` reflect the current prompts,
- Step 3 and Step 4 now share the same PDF retrieval strategy,
- Step 4 writes per-paper `reasoning.txt` summaries for easier human review.

---

## 8. Open questions and future work

1. Improve Step 1 handling of heavily rate-limited metadata APIs without slowing the full pipeline excessively.
2. Continue expanding repository support and publisher-source parsing for less common hosting patterns.
3. Tighten Step 3.5 integration so generated Type 1 artifacts can be merged more directly into Step 4.
4. Add stronger corpus-side review reports and manifests for ambiguous or human-review-needed files.
5. Add aggregation scripts and quality-control reports across the full corpus.

---

## 9. Glossary

| Term | Definition |
|---|---|
| **Candidate paper** | A paper surfaced in Step 1 before dataset availability is verified. |
| **Dataset status** | Step 2 label describing whether usable data links were found. |
| **Type 1 data** | Cleaned, processed, source-data-style files suitable for direct inspection or re-plotting. |
| **Type 2 data** | Raw or minimally processed measurement files closer to instrument output. |
| **Inventory** | The file listing collected from a repository or source-data location in Step 2. |
| **Inspection** | File-level structural or content analysis performed in Step 3. |
| **Manifest** | The Step 4 JSON summary describing the organized local paper corpus. |

---

*Document version: 1.2 - UC LEAP pipeline documentation (step1-step4 plus step3.5)*
