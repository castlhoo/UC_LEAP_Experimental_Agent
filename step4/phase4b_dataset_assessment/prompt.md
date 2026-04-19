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
  twisted bilayers, moiré systems
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
