# Step 4 Prompt Reference

Step 4 is the main dataset classification stage.
It downloads dataset files, inspects file contents, performs a dataset-level assessment, classifies files in batches, merges the results, and writes per-paper dataset summaries.

## Active Role

Step 4 decides whether inspected dataset files should count as:

- `type1`: cleaned, processed, figure-ready, source-data, or replot-ready data,
- `type2`: raw/unprocessed instrument or measurement data,
- `script`,
- `documentation`,
- `other`.

It also handles off-topic / out-of-scope papers **after file inspection**, not before.

## Inputs

- `step2/output/step2_inventory_latest.json`
- `step3/output/step3_paper_analysis_latest.json`
- Step 3 paper PDFs under `step3/papers/`
- Repository/source-data links from Step 2

## Outputs

- `step4/output/step4_classification_latest.json`
- `step4/output/step4.log`
- per-paper intermediate summaries while running:
  - `step4/downloads/<paper>/summary/paper_dataset_summary.json`

`step4/downloads/` is a cache/intermediate folder and can be deleted after Step 5 has copied the final selected data.

## Phase Structure

1. Load Step 2 evidence and Step 3 paper analyses.
2. Download dataset files.
3. Inspect file contents.
4. Run Step 4B dataset-level assessment.
5. Run Step 4C file-level classification in batches.
6. Merge batch results and write Step 4 output.

## Prompt B: Dataset-Level Assessment

Source file: `step4/phase4b_dataset_assessment/prompt.md`

### Purpose

This prompt is derived from the previous file-classification prompt, but it does not classify every file.
It first asks GPT to understand the dataset as a whole, connect it to the paper, and determine whether the paper/data are within project scope after reviewing file evidence.

### User Prompt Template

```text
Analyze this condensed matter / materials science paper and dataset evidence at the DATASET LEVEL.

This prompt is derived from Prompt B, but do NOT classify every file here. First understand what the dataset contains,
how it connects to the paper, and whether the paper/data are within the project scope after reviewing file evidence.

Paper title: $title
Paper journal: $journal
Paper abstract: $abstract

=== STEP 1/2 DISCOVERY AND LINK EVIDENCE ===
$discovery_evidence

=== PAPER ANALYSIS (from reading the full publication) ===
$paper_analysis

=== FILE INVENTORY / INSPECTION OVERVIEW ===
$file_overview

=== PROJECT TARGET SCOPE / FIELD RELEVANCE GUIDE ===

Before deciding whether a dataset is in or out of scope, inspect the dataset file reports above.
Do NOT decide out-of-scope from title, abstract, journal, or paper topic alone.
Use BOTH:
- Paper evidence from PAPER ANALYSIS
- File evidence from FILE INVENTORY / INSPECTION OVERVIEW

The target project scope is condensed matter physics, quantum materials, solid-state physics,
and closely related materials science datasets.

Use this field relevance guide:

strong:
Clearly condensed matter / quantum materials / solid-state physics.
Indicators include:
- Systems: graphene, TMDs, cuprates, nickelates, iron-based superconductors,
  topological insulators, Weyl/Dirac semimetals, Mott insulators, heavy fermions,
  spin liquids, frustrated magnets, van der Waals materials, heterostructures,
  twisted bilayers, moire systems
- Phenomena: superconductivity, magnetism, charge density waves, Kondo effect,
  spin-orbit coupling, Majorana modes, skyrmions, phase transitions, quantum oscillations
- Measurements: electronic transport, thermal transport, Hall effect, magnetoresistance,
  specific heat, tunneling spectroscopy, Fermi surface, band structure
- Experimental techniques: STM/STS, ARPES, SET, XRD, TEM, AFM, EELS, Raman,
  neutron scattering
- Growth/fabrication: MBE, PLD, CVD, sputtering, exfoliation, flux growth, Bridgman

general:
Broader materials science, such as functional materials, materials devices, synthesis,
nanomaterials, thin films, semiconductors, photodetectors, catalysts, piezoelectrics,
ferroelectrics, microscopy/materials characterization, or materials-relevant computation.
These can be in scope if the paper/data are genuinely about materials synthesis,
characterization, properties, devices, or simulations.

weak:
Tangential relevance. The paper may mention a material, device, imaging, nanostructure,
or physical measurement, but the main scientific objective may belong to another field.
Classify as Type 1/Type 2 only if the dataset files are clearly materials /
condensed-matter experimental or computational data.

none:
Unrelated field. Examples include biomedical/clinical/virology/genomics,
ecology/microbiome, astronomy/cosmology/astrophysics, high-energy particle physics,
pure computer vision/ML benchmark datasets, facial recognition, social science,
economics, or other datasets not tied to condensed matter/materials science.

Scope handling rule:
- First inspect the files and understand what the dataset contains.
- Then use the guide above to decide whether the paper AND dataset are within scope.
- If, after reviewing both paper evidence and file evidence, the paper/data are clearly
  field_match=none, do NOT classify data files as Type 1 or Type 2 for this project.
  Use "other" for data files unless they are scripts or documentation.
  Set has_type1=false, has_type2=false, has_both=false.
  Explain the out-of-scope reason in file reasoning and notes.
- If field_match=weak, be conservative. Use Type 1/Type 2 only when both paper evidence
  and file evidence clearly show materials/condensed-matter relevance. Otherwise use "other".
- If field_match=strong or field_match=general, proceed with Type 1 / Type 2 classification
  using the definitions below.

=== DATASET-LEVEL TASK ===

Using the same evidence standards as Prompt B, provide:
1. What this dataset contains
2. How the dataset connects to the paper
3. The scientific/data modalities represented
4. Whether the paper/data are in project scope after reviewing file evidence
5. A conservative plan for the later file-level Type 1 / Type 2 classification

=== OUTPUT FORMAT ===

Return JSON:
{
  "dataset_overview": "what the dataset contains overall",
  "paper_dataset_link": "how the dataset connects to the paper/results/figures/methods",
  "scientific_context": "scientific meaning of the dataset",
  "data_contents_summary": "summary based on folders, filenames, file types, columns, sheets, groups, README/metadata clues",
  "data_modalities": ["e.g. transport curves", "ARPES spectra", "DFT calculations"],
  "data_generation_or_processing": "how data appear to be generated, processed, or provided",
  "field_match": "strong" | "general" | "weak" | "none",
  "field_match_reasoning": "scope reasoning using BOTH paper evidence and file evidence",
  "likely_dataset_structure": "figure-based source data / raw instrument data / mixed / scripts-only / documentation-only / unclear / out-of-scope",
  "type_classification_plan": {
    "likely_type1_evidence": "dataset-level evidence likely pointing to Type 1",
    "likely_type2_evidence": "dataset-level evidence likely pointing to Type 2",
    "files_or_groups_to_prioritize": ["relative folders/files/groups to prioritize during file classification"]
  },
  "out_of_scope": true/false,
  "out_of_scope_reason": "if out_of_scope=true, explain based on paper and file evidence; otherwise empty",
  "notes": "important observations"
}
```

## Prompt C: File-Level Classification

Source file: `step4/phase4c_file_classification/prompt.md`

### Purpose

This prompt classifies inspected files after Step 4B has already formed a dataset-level assessment.
It receives Step 1/2 discovery evidence, Step 3 paper analysis, Step 4B dataset assessment, and the current batch of file inspection reports.

### Required Classification Definitions

```text
Type 1 (Cleaned, replot-ready):
- Tabular data (CSV, XLSX, TXT) with column headers naming variables, especially processed variables
- Organized as figure-specific data
- Small-to-moderate file sizes appropriate for figure data
- Theoretical calculation or simulation data
- Optical microscopy data for sample geometry
- Can be directly loaded and plotted with minimal processing
- "Source Data" deposits organized by figure = Type 1

Type 2 (Raw/unprocessed):
- Instrument output: binary/proprietary formats, microscopy images, HDF5, etc.
- Files named after scans, sample names, experiments, experimental conditions, or instrument runs
- Files in which variables/units are directly measured from instruments
- Files requiring processing scripts to generate figures
- Files explicitly described as raw in the paper or repository description
- Large files significantly bigger than typical figure datasets
- Data requiring significant preprocessing before plotting
```

### Critical Rules

```text
1. Do NOT classify based on file extension alone.
2. Do NOT classify based on filename alone.
3. Use BOTH paper evidence and file evidence.
4. If paper evidence and file evidence conflict, describe the conflict and resolve conservatively.
5. If the paper explicitly states data is raw, prioritize Type 2.
6. If the paper explicitly states data is figure/source/processed, prioritize Type 1.
7. Apply the AFM / non-white-light microscopy rule from the prompt.
8. If DATASET-LEVEL ASSESSMENT says field_match=none or out_of_scope=true, classify data files as "other".
9. If field_match=weak, use Type 1/Type 2 only when paper and file evidence clearly support materials/condensed-matter relevance.
```

### Output Shape

```json
{
  "file_classifications": [
    {
      "relative_path": "...",
      "filename": "...",
      "type": "type1 | type2 | script | documentation | other",
      "paper_evidence": "...",
      "file_evidence": "...",
      "reasoning": "...",
      "ambiguity": "none or explanation",
      "key_columns_or_structure": "..."
    }
  ],
  "has_type1": true,
  "has_type2": false,
  "has_both": false,
  "type1_summary": "...",
  "type2_summary": "...",
  "type1_files": ["..."],
  "type2_files": ["..."],
  "data_organization": "...",
  "replot_ready_data_present": true,
  "replot_reason": "...",
  "confidence": "high | medium | low",
  "notes": "..."
}
```

## Merge and Summary Behavior

Step 4 merges batch classifications, normalizes malformed GPT fields, recalculates `has_type1`, `has_type2`, and `has_both`, and writes a per-paper `paper_dataset_summary.json`.
Out-of-scope papers should end as neither Type 1 nor Type 2.
