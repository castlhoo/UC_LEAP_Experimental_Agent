# UC LEAP — Framework Documentation

A reproducible four-stage pipeline for discovering, verifying, downloading, and organizing materials-science papers with usable datasets.

---

## Table of contents

1. [What this is and why it exists](#1-what-this-is-and-why-it-exists)
2. [What we start with](#2-what-we-start-with)
3. [The four-stage pipeline](#3-the-four-stage-pipeline)
   - [Step 1 - Candidate Paper Search](#step-1---candidate-paper-search)
   - [Step 2 - Dataset Presence and Inventory Check](#step-2---dataset-presence-and-inventory-check)
   - [Step 3 - Dataset Download, Inspection, and Type Classification](#step-3---dataset-download-inspection-and-type-classification)
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
| Dataset links discovered from papers | Repository URLs, DOI links, source-data references, and data availability statements | `step2/dataset_link_resolver.py` |
| Repository inventories and downloadable files | Zenodo/Figshare/GitHub/Dryad inventories, publisher source data, PDFs, archives, spreadsheets, raw measurement files | `step2`-`step4` |
| OpenAI model calls | Used for query generation, inventory assessment, paper understanding, and Type 1/Type 2 classification | `step1/gpt_client.py`, `step2/gpt_client.py`, `step3/gpt_client.py` |

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

## 3. The four-stage pipeline

The pipeline transforms broad literature search results into a locally organized benchmark-ready paper set.

```text
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Step 1    │ -> │   Step 2    │ -> │   Step 3    │ -> │   Step 4    │
│ Candidate   │    │ Dataset     │    │ Download +  │    │ Local       │
│ Search      │    │ Verification│    │ Classification│   │ Organization│
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  │                  │
       ▼                  ▼                  ▼                  ▼
 step1/output/      step2/output/      step3/output/      step4/organized/
 candidates         inventory          classification     manifest + folders
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

Step 1 combines two kinds of search generation:

1. manual high-value queries,
2. automatically combined keyword queries.

It then searches multiple metadata APIs, deduplicates results, scores papers by priority, and assigns a screening decision such as `keep`, `maybe`, or `drop`.

Key components:

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

**Current snapshot result:** The latest saved Step 1 output contains **82 candidates**: **21 keep**, **23 maybe**, **38 drop**.

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

Key components:

- `step2/pipeline.py`
- `step2/dataset_link_resolver.py`
- `step2/repository_classifier.py`
- `step2/candidate_loader.py`
- `step2/gpt_client.py`
- `step2/config/step2_config.yaml`

**Output:**

- `step2/output/step2_inventory_<timestamp>.json`
- `step2/output/step2_inventory_latest.json`

Each paper is assigned a `dataset_status`, such as:

- `verified`
- `source_data_found`
- `upon_request`
- `unclassified_link`
- `no_dataset_found`

**Rationale:** This stage narrows the broad Step 1 pool into papers with actual evidence of data availability, which is a stronger requirement than promising metadata alone.

**Current snapshot result:** The latest saved Step 2 output processed **44 papers**, found **13 papers with data**, and recorded a status distribution of **3 verified**, **10 source_data_found**, **17 upon_request**, and **14 no_dataset_found**.

---

### Step 3 - Dataset Download, Inspection, and Type Classification

**Purpose:** Download candidate datasets, inspect their contents, and classify each paper as containing Type 1, Type 2, both, or neither.

**Input:**

- `step2/output/step2_inventory_latest.json`
- Downloadable dataset files and paper PDFs

**Process:**

Step 3 runs six phases:

1. load Step 2 results,
2. download paper PDFs and analyze paper text,
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

**Rationale:** This is the first stage where the repository reasons about the actual file contents rather than just repository metadata.

**Current snapshot result:** The latest saved Step 3 output processed **13 papers**, with **1 paper containing both Type 1 and Type 2**, **8 Type 1 only**, **1 Type 2 only**, and **3 neither**. Across those papers, **39 files were downloaded** and **204 files were inspected**.

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
3. download PDFs when possible,
4. copy and rename files into a stable local structure,
5. generate a manifest for human and programmatic use.

The default output grouping is:

- `Both/`
- `Type1/`
- `Type2/`

Within each paper folder, the organizer separates:

- `type1_data`
- `type2_data`
- annotation or documentation files
- scripts or notebooks
- `pdf/` when available

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

**Current snapshot result:** The latest Step 4 manifest records **10 organized papers**, including **1 Both**, **8 Type1-only**, and **1 Type2-only**. It also records **7 PDFs**, **41 Type 1 files**, **36 Type 2 files**, **5 annotation files**, and **17 script files**.

---

## 4. File and folder conventions

At the repository root:

```text
UC_LEAP/
├── step1/
├── step2/
├── step3/
├── step4/
├── requirements.txt
├── utils.py
└── .env
```

Pipeline artifact conventions:

- Step 1 writes candidate lists under `step1/output/`
- Step 2 writes dataset verification inventories under `step2/output/`
- Step 3 writes classification summaries under `step3/output/` and raw downloads under `step3/downloads/`
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

3. Run each step from the repository root:

```bash
python -m step1.run_step1
python -m step2.run_step2
python -m step3.run_step3
python -m step4.run_step4
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

### Important note about the current snapshot

`step1/run_step1.py` imports `step1.pipeline`, but that module is not present in the current repository snapshot. The saved Step 1 outputs are present, so the project state is still well documented, but Step 1 may need restoration or refactoring before a fresh rerun succeeds.

---

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

**Decision:** Step 4 groups papers under `Both`, `Type1`, and `Type2`.

**Rationale:** Downstream consumers often need to prioritize papers with both processed and raw data, but it is still useful to retain one-sided cases for future work.

---

## 7. Current repository status

As of the current saved outputs in this repository:

- Step 1 has produced and saved candidate screening artifacts.
- Step 2 has verified or partially verified dataset availability for a subset of papers.
- Step 3 has completed download and classification outputs for 13 papers.
- Step 4 has organized 10 papers into the local corpus.

This means the repository already contains a meaningful curated dataset snapshot, even if some earlier steps may still need code cleanup for perfectly reproducible reruns.

---

## 8. Open questions and future work

1. Restore or reimplement the missing Step 1 pipeline module so the full pipeline can be rerun cleanly from scratch.
2. Expand repository support beyond the currently configured sources when papers host data in less common locations.
3. Improve the Type 1 / Type 2 classifier with more transparent rule-based checks in addition to GPT judgments.
4. Add a downstream stage that converts the organized corpus into benchmark-ready paper packages.
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

*Document version: 1.0 - UC LEAP step1-step4 repository documentation*
