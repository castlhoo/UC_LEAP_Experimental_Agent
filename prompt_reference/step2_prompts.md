# Step 2 Prompt Reference

Step 2 verifies whether Step 1 candidates have actual dataset evidence.
It resolves links, classifies repository URLs, collects repository inventories, and optionally asks GPT to assess the visible inventory.

## Active Role

Step 2 does **not** download every data file for inspection. It works at the link and repository-inventory level.

## Inputs

- `step1/output/step1_candidates_latest.json`
- Paper DOI / landing page / metadata links
- Data availability links and repository URLs
- Repository inventory APIs where available

## Outputs

- `step2/output/step2_inventory_<timestamp>.json`
- `step2/output/step2_inventory_latest.json`

## Dataset Status Values

Step 2 records a paper-level dataset status such as:

- `verified`
- `source_data_found`
- `unclassified_link`
- `upon_request`
- `no_dataset_found`

It also records repository URLs, data URL candidates, ambiguous URLs, ignored URLs, paper PDF URLs, inventory counts, and verification notes.

## GPT Use

Step 2 uses the inventory assessment prompt in `step2/gpt_client.py` when GPT inventory assessment is enabled.
The prompt sees repository metadata and up to the first 50 visible files from an inventory.

## Prompt A: Inventory Assessment

### System Prompt

```text
You are an expert in condensed matter physics and materials science data.
Your task is to analyze a dataset repository's file inventory, assess its contents,
and classify the dataset type. Return structured JSON. Be concise and accurate.
```

### User Prompt Template

```text
Analyze this dataset inventory for a condensed matter / materials science paper.

Paper title: {paper_title}
Paper abstract summary: {abstract_summary}
Repository type: {repo_type}
Repository title: {repo_title}
Repository description: {repo_description}

Files in the repository:
{file_list}

Return JSON:
{
  "summary": "1-2 sentence description of what data is in this repository",
  "data_types": ["list of data types found, e.g. 'transport measurements', 'XRD spectra', 'STM images'"],
  "file_formats": ["list of unique file formats/extensions found"],
  "has_raw_data": {
    "flag": true/false,
    "detail": "brief explanation"
  },
  "has_processed_data": {
    "flag": true/false,
    "detail": "brief explanation"
  },
  "has_code": {
    "flag": true/false,
    "detail": "brief explanation"
  },
  "dataset_type": "type1" | "type2" | "both" | "unknown",
  "type1_evidence": "evidence for clean/replot-ready data, or 'none'",
  "type2_evidence": "evidence for raw measurement data, or 'none'",
  "confidence": "high" | "medium" | "low",
  "evidence_for": ["short supporting evidence"],
  "evidence_against": ["short contradictory or missing evidence"],
  "recommended_status": "verified" | "source_data_found" | "link_found" | "unclassified_link" | "no_dataset_found",
  "needs_human_review": true | false,
  "replot_feasibility": "high" | "medium" | "low" | "unknown",
  "replot_reason": "brief reason for feasibility assessment",
  "relevance_to_paper": "high" | "medium" | "low"
}

Definitions:
- has_raw_data: Original measurement files (e.g., .dat, .nxs, .h5, raw images, instrument output)
- has_processed_data: Cleaned/analyzed data (e.g., .csv, .xlsx, .txt with columns, figure source data)
- has_code: Analysis scripts (e.g., .py, .m, .ipynb, .R)
- dataset_type:
  - "type1": Clean, figure-replot-ready dataset. Tabular data (.csv, .xlsx, .txt) with clear column headers, or organized figure source data. Can be directly loaded and plotted.
  - "type2": Raw measurement dataset. Original instrument output files that need processing before plotting. Examples: .h5, .nxs, .dat, .spe, raw images, binary formats.
  - "both": Contains both type1 and type2 data.
  - "unknown": Cannot determine from file listing alone.
- replot_feasibility:
  - "high": tabular data with clear columns, can directly plot
  - "medium": data present but needs some processing
  - "low": raw instrument data, complex formats
  - "unknown": cannot determine from file listing alone
```

## Decision Logic

Step 2 remains inventory-first. It should not make the final Type 1 / Type 2 decision.
Its purpose is to decide whether there is enough dataset evidence to send the paper to Step 3 and Step 4.
