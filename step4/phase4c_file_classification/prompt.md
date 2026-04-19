Analyze these dataset files from a condensed matter / materials science paper and classify each file.

Paper title: $title
Paper journal: $journal
Paper abstract: $abstract

=== STEP 1/2 DISCOVERY AND LINK EVIDENCE ===
$discovery_evidence

=== PAPER ANALYSIS (from reading the full publication) ===
$paper_analysis

=== DATASET-LEVEL ASSESSMENT (from Step 4B) ===
$dataset_assessment

=== FILE INSPECTION REPORTS ===
$file_reports

=== CLASSIFICATION DEFINITIONS ===

Type 1 (Cleaned, replot-ready):
- Tabular data (CSV, XLSX, TXT) with column headers naming variables, especially processed variables (e.g. “R”/”resistance”, which most of the time has to be processed from voltage and current signals; “fitting”, which indicates that data has been fitted)
- Organized as figure-specific data (e.g., "Fig1", "Figure_3e", "FigS4")
- Small-to-moderate file sizes appropriate for figure data
- Theoretical calculation or simulation data
- Optical microscopy data (Specifically, white light imaging for sample geometry. File type is usually jpg or png)
- Can be directly loaded and plotted with minimal processing
- "Source Data" deposits organized by figure = Type 1 (source data ≠ raw data)

Type 2 (Raw/unprocessed):
- Instrument output: binary/proprietary formats, microscopy images, HDF5, etc. File with extensions that are expected to be the direct raw file output.
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
8. If the DATASET-LEVEL ASSESSMENT says field_match=none or out_of_scope=true, classify data files as "other", set has_type1=false, has_type2=false, has_both=false, and explain the out-of-scope reason.
9. If field_match=weak, be conservative. Use Type 1/Type 2 only when both paper evidence and file evidence clearly show materials/condensed-matter relevance. Otherwise use "other".

=== REASONING PROCEDURE ===

For each file, follow this step-by-step reasoning:
Before performing file-level reasoning, first conduct an overall dataset-level assessment using the paper_analysis from Prompt A, especially the data availability statement, raw_data_expected, source_data_expected, and dataset_characterization, to determine whether the dataset is mostly Type 1, mostly Type 2, or mixed. Refine this using overall file structure, filename patterns, and column/variable naming. Then organize files by moving PDFs (main, supplementary, peer review) to the pdf folder, script files (.py, .m, .ipynb, .R) to the scripts folder and excluding them from classification, and README or description files to the annotation folder, and decompress all files while preserving structure. After that, evaluate each file in the context of the overall judgement rather than independently, and for unclear files, hold them and decide at the end based on the majority type.

Step A. File Evidence
- Refer to FILE INSPECTION REPORTS from Step 4A.
- Inspect filename, extension, size, structure, headers, sheet names, variable names and units
If the file is main text pdf/supplementary pdf/peer review pdf, move to pdf folder. If the file is any kind of script, move to script folder. If the file is data annotation like README files, move to annotation folder.

Step B. Paper Evidence
- Refer to PAPER ANALYSIS from Step 3 / Prompt A.
- Identify any statements in main text or supplementary about whether the dataset is raw, processed, or figure data
If there is a clear statement about the datasets being “raw”, or “processed”, skip the other reasoning procedure and mark the datasets as the corresponding type.

Step C. Field Relevance After File Inspection
- Refer to STEP 1/2 DISCOVERY AND LINK EVIDENCE, DATASET-LEVEL ASSESSMENT, and this batch's FILE INSPECTION REPORTS.
- If clearly out-of-scope, classify data files as "other", set has_type1=false, has_type2=false, has_both=false, and explain why in notes and file reasoning.

Step D. Functional Role
- Determine if the file is:
  - figure-ready data
  - raw measurement data
  - script
  - documentation
  - other

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
