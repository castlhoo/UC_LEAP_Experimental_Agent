# Step 2 Prompts

This file summarizes the GPT prompt used in Step 2 repository and inventory assessment.
The prompt is applied after Step 2 has already discovered candidate repository links or publisher-hosted source-data files for a paper.
Its role is to inspect the visible inventory, infer what kinds of data are present, and estimate how relevant that repository is to the paper.
The structured output is then used to help assign `dataset_status`, estimate `type1 / type2 / both / unknown`, and decide whether the paper should move forward to Step 3.

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
  - "type1": Clean, figure-replot-ready dataset. Tabular data (.csv, .xlsx, .txt) with clear
    column headers, or organized figure source data. Can be directly loaded and plotted.
    Examples: FigureData/ folders, Source_Data.xlsx, plot_data.csv
  - "type2": Raw measurement dataset. Original instrument output files that need processing
    before plotting. Examples: .h5, .nxs, .dat, .spe, raw images, binary formats
  - "both": Contains both type1 and type2 data (e.g., raw/ + processed/ directories)
  - "unknown": Cannot determine from file listing alone
- replot_feasibility: How easy to re-create figures from this data
  - "high": tabular data with clear columns, can directly plot
  - "medium": data present but needs some processing
  - "low": raw instrument data, complex formats
  - "unknown": can't determine from file listing alone
```
