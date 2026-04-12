# pipeline — Condensed Matter Dataset Collection

Python re-implementation of the orchestrator workflow that built
`../collected_papers/` from a directory of source paper folders.
Each numbered subfolder is one phase; run them in order, or invoke any
script standalone.

The original task was driven by Claude sub-agents calling shell tools.
The scripts here do the same work in plain Python so the pipeline is
reproducible without an LLM in the loop. The user-feedback overrides
(microscopy = processed, DFT/MC = Type 1, full-text PDF scanning) are
baked into phases 03 and 04.

## Where things live

```
UC_LEAP_Experimental_Agent/
├── pipeline/                  ← you are here
│   ├── 01_discovery/
│   ├── 02_download/
│   ├── 03_inspect_classify/
│   ├── 04_refinement/
│   └── 05_organize/
└── collected_papers/          categorised view of the source folders
    ├── type1/                 (symlinks pointing into the source dir)
    ├── type2/
    ├── both/
    └── collection_summary.json
```

The pipeline reads source paper folders (one folder per paper, each
containing `paper/preprint.pdf`, `dataset/<files>`, `scripts/<files>`)
from a configurable location passed via `--src` / `--out-root`. The
default in the organize scripts assumes the source dir lives one level
above the `UC_LEAP_Experimental_Agent/` folder; override it with the
flag if your layout differs.

The 5 phases at a glance:

| phase | scripts | purpose |
|-------|---------|---------|
| 01 discovery | `search_candidate_datasets.py` | query Zenodo for candidate datasets |
| 02 download  | `download_paper_and_dataset.py` | fetch arXiv PDF + every Zenodo file |
| 03 inspect / classify | `inspect_paper_folder.py`, `classify_from_inspection.py` | walk a paper folder, decide Type 1 / Type 2 / Both |
| 04 refinement | `refetch_missing_files.py`, `scan_pdfs_for_data_statements.py`, `apply_microscopy_and_calc_rules.py` | re-fetch missing files, scan PDFs end-to-end, apply user-feedback overrides |
| 05 organize | `organize_by_classification.py`, `extract_dataset_zips.py`, `verify_layout.py` | (re)build collected_papers/ symlinks, extract bundled zips, verify layout |

In the command examples below, replace `<paper-source>` with the
absolute path to your source paper directory.

## Phase 01 — Discovery

[`01_discovery/search_candidate_datasets.py`](01_discovery/search_candidate_datasets.py)

Queries the Zenodo REST search API for five condensed-matter subfields
(superconductors, topological insulators, 2D / moiré, kagome / CDW,
altermagnets / ARPES), deduplicates by DOI, verifies each record's
`/files` endpoint is non-empty, and writes `candidates.json`.

```bash
python 01_discovery/search_candidate_datasets.py \
    --out 01_discovery/candidates.json \
    --per-query 8 --target 20
```

## Phase 02 — Download

[`02_download/download_paper_and_dataset.py`](02_download/download_paper_and_dataset.py)

Materialises one paper folder under the source paper directory:

```
<paper-source>/P##_<short_title>/
├── paper/preprint.pdf       <- arXiv PDF
├── dataset/<remote files>   <- every file from the deposit
└── scripts/<code files>     <- moved out of dataset/ if any code is found
```

Idempotent (skips files already on disk that match the remote size).
Supports both Zenodo and figshare.

```bash
python 02_download/download_paper_and_dataset.py \
    --paper-id P21 \
    --short-title bismuthene_dft \
    --arxiv-id 2403.06046 \
    --record-id 25737993 \
    --repository zenodo \
    --out-root <paper-source>
```

In a real run, loop this over `candidates.json` from phase 01.

## Phase 03 — Inspect + classify

[`03_inspect_classify/inspect_paper_folder.py`](03_inspect_classify/inspect_paper_folder.py)
[`03_inspect_classify/classify_from_inspection.py`](03_inspect_classify/classify_from_inspection.py)

`inspect_paper_folder.py` walks one paper folder and writes an
`inspection.json` describing every dataset file: format, size, sample
header tokens, whether the headers look labelled, and which folder-name
class the file lives under (`raw` / `processed` / `calculation` /
`scripts` / `figures` / `unknown`).

`classify_from_inspection.py` consumes that JSON and applies the
classification rules in order:

| signal                                              | type            |
|-----------------------------------------------------|-----------------|
| labelled CSV/TSV/TXT headers                        | Type 1          |
| spreadsheets (xlsx / opju / oggu)                   | Type 1          |
| files under `raw data/` folder                      | Type 2          |
| binary instrument files (.h5 .npy .pkl .3ds .sxm .mat .spe .ibw …) | Type 2 |
| microscopy images (.tif .tiff .gwy)                 | Type 1 *(override)* |
| DFT / Monte Carlo outputs                           | Type 1 *(override)* |
| both Type 1 *and* Type 2 evidence present           | Type1+Type2     |

```bash
python 03_inspect_classify/inspect_paper_folder.py \
    --paper-dir <paper-source>/P12_magnon_dynamics_Mn2Au

python 03_inspect_classify/classify_from_inspection.py \
    --inspection <paper-source>/P12_magnon_dynamics_Mn2Au/inspection.json
```

## Phase 04 — Refinement

Three scripts addressing the issues found after the first collection
pass.

[`04_refinement/refetch_missing_files.py`](04_refinement/refetch_missing_files.py)
walks each paper in `collection_summary.json`, fetches the live file
listing from Zenodo / figshare, and downloads any file that is missing
or has the wrong size. Defaults to `--dry-run`.

```bash
python 04_refinement/refetch_missing_files.py \
    --collection ../collected_papers/collection_summary.json \
    --src        <paper-source> \
    --dry-run
```

[`04_refinement/scan_pdfs_for_data_statements.py`](04_refinement/scan_pdfs_for_data_statements.py)
runs `pdftotext -layout` over every preprint PDF, sentence-splits the
result, and extracts up to ~12 sentences matching data-availability
keywords (`zenodo`, `figshare`, `data availability`, `raw data`,
`source data`, `deposit*`, `10.5281/zenodo.<id>`, …). This catches
papers with no Data Availability section but with the dataset cited as
a numbered reference in the body or reference list (e.g. P08, P19).

```bash
python 04_refinement/scan_pdfs_for_data_statements.py \
    --src <paper-source> \
    --out 04_refinement/statements.json
```

Requires `pdftotext` from poppler-utils on PATH.

[`04_refinement/apply_microscopy_and_calc_rules.py`](04_refinement/apply_microscopy_and_calc_rules.py)
applies the user-feedback overrides to an existing
`collection_summary.json`. Any paper currently classified `Type2` or
`Type1+Type2` whose Type 2 evidence comes *only* from microscopy images
or DFT/Monte Carlo outputs (with no overriding "raw" / "instrument"
language) is demoted to `Type1`.

```bash
# dry run — show proposed demotions
python 04_refinement/apply_microscopy_and_calc_rules.py \
    --collection ../collected_papers/collection_summary.json

# write changes back
python 04_refinement/apply_microscopy_and_calc_rules.py \
    --collection ../collected_papers/collection_summary.json \
    --apply
```

## Phase 05 — Organise

Three scripts that materialise the final
`../collected_papers/{type1,type2,both}/` layout. They default to the
correct paths when run from `pipeline/05_organize/`.

[`05_organize/organize_by_classification.py`](05_organize/organize_by_classification.py)
reads `collection_summary.json` and (re)creates symlinks under
`collected_papers/{type1,type2,both}/` that point at the per-paper
folders inside the source paper directory.

[`05_organize/extract_dataset_zips.py`](05_organize/extract_dataset_zips.py)
walks `<paper-source>/*/dataset/**/*.zip` and extracts each archive to
a sibling `extracted/` folder, so the contents of bundled deposits
become browsable.

[`05_organize/verify_layout.py`](05_organize/verify_layout.py)
sanity-checks that every paper in the JSON is present on disk in the
right bucket and reports any drift.

```bash
python 05_organize/organize_by_classification.py
python 05_organize/extract_dataset_zips.py
python 05_organize/verify_layout.py
```

## Reproducing the whole pipeline

```bash
cd UC_LEAP_Experimental_Agent/pipeline

# 1. Find candidates (network)
python 01_discovery/search_candidate_datasets.py \
    --out 01_discovery/candidates.json

# 2. Download each one (network) — loop over candidates.json
python 02_download/download_paper_and_dataset.py \
    --paper-id P21 --short-title <slug> \
    --arxiv-id <id> --record-id <id> --repository zenodo \
    --out-root <paper-source>

# 3. Inspect and classify each paper folder
for d in <paper-source>/P*/; do
    python 03_inspect_classify/inspect_paper_folder.py --paper-dir "$d"
    python 03_inspect_classify/classify_from_inspection.py \
        --inspection "$d/inspection.json"
done

# 4. Refinement: refetch missing files, scan PDFs, apply overrides
python 04_refinement/refetch_missing_files.py \
    --collection ../collected_papers/collection_summary.json \
    --src        <paper-source>
python 04_refinement/scan_pdfs_for_data_statements.py \
    --src <paper-source> \
    --out 04_refinement/statements.json
python 04_refinement/apply_microscopy_and_calc_rules.py \
    --collection ../collected_papers/collection_summary.json --apply

# 5. Materialise the layout and verify
python 05_organize/organize_by_classification.py
python 05_organize/extract_dataset_zips.py
python 05_organize/verify_layout.py
```

## Dependencies

Standard library only, plus `pdftotext` from poppler-utils for the PDF
scanner in phase 04. No `requests`, no `pandas`.

```bash
brew install poppler             # macOS
apt-get install poppler-utils    # debian / ubuntu
```

## Note on the source paper directory and pushing to GitHub

The pipeline writes per-paper folders into the source paper directory,
which lives **outside** `UC_LEAP_Experimental_Agent/` and therefore
will not be included in a `git add .` from this repo. The symlinks in
`../collected_papers/{type1,type2,both}/` use absolute paths, so they
will only resolve on machines where the source dir lives at the same
absolute path. If you intend to share the actual datasets with
collaborators, either also move the source dir under this repo and
re-run `organize_by_classification.py`, or distribute the source data
separately.

## What is and isn't reproducible

The pipeline is fully reproducible from phase 02 onwards: given the
same Zenodo record IDs, the same files download and the
inspect/classify/organize steps are deterministic.

Phase 01 is order-dependent. Zenodo's `bestmatch` ranking changes as
new records are added, so re-running discovery may yield a different
candidate set. The original collection used Claude sub-agents to do
free-form web search; this Python version uses a fixed set of keyword
queries against the Zenodo REST API instead. Treat its output as a
starting point that needs human review, not as authoritative.
