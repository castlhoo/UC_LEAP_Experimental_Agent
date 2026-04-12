# UC LEAP Workflow and Prompt Overview

This document is a concise shareable overview of the current UC LEAP workflow and the prompts used to generate the present results.
It is intended for collaborators who want to review the pipeline, understand how papers/files are being classified, and suggest targeted improvements.
The pipeline currently runs from Step 1 through Step 4, with GPT used mainly in Step 1 screening, Step 2 inventory interpretation, and Step 3 paper/file classification.
Step 4 does not use a new GPT prompt; instead, it organizes files and preserves the reasoning generated upstream.

## High-level workflow

### Step 1. Candidate paper screening

Step 1 starts from academic API search results and screens papers using metadata and abstracts.
The goal is to decide whether each paper belongs to the target domain, whether it is experimental, and whether it shows any sign of dataset availability.
The output is a `keep / maybe / drop` decision with a score, and the `keep + maybe` set is passed to Step 2.
In the current active setup, GPT is used only for screening, not for query generation.

Main files:
- [step1/gpt_client.py](C:\UCLEAP\UC_LEAP\step1\gpt_client.py)
- [step1/query_generator.py](C:\UCLEAP\UC_LEAP\step1\query_generator.py)
- [step1/pipeline.py](C:\UCLEAP\UC_LEAP\step1\pipeline.py)
- [step1_prompts.md](C:\UCLEAP\UC_LEAP\prompt_reference\step1_prompts.md)

### Step 2. Dataset presence and inventory assessment

Step 2 takes the Step 1 candidate set and tries to find actual repository links, source-data files, or downloadable assets associated with each paper.
It then inspects repository inventories and uses GPT to estimate whether the repository contains raw data, processed/source data, both, or something unclear.
The result is a paper-level `dataset_status` such as `verified`, `source_data_found`, or `no_dataset_found`, plus supporting metadata like verification score and human-review flags.
This step is designed to filter the broad candidate set into papers that are worth downloading and inspecting more deeply.

Main files:
- [step2/gpt_client.py](C:\UCLEAP\UC_LEAP\step2\gpt_client.py)
- [step2/dataset_link_resolver.py](C:\UCLEAP\UC_LEAP\step2\dataset_link_resolver.py)
- [step2/repository_classifier.py](C:\UCLEAP\UC_LEAP\step2\repository_classifier.py)
- [step2/pipeline.py](C:\UCLEAP\UC_LEAP\step2\pipeline.py)
- [step2_prompts.md](C:\UCLEAP\UC_LEAP\prompt_reference\step2_prompts.md)

### Step 3. Paper understanding and file-level classification

Step 3 is the most detailed stage.
It downloads the actual dataset files and, when possible, the paper PDF; GPT first reads the paper to extract scientific context and dataset semantics, and then classifies the downloaded files using both paper evidence and file inspection results.
The main goal is to determine whether a paper has Type 1 data, Type 2 data, both, or neither.
This step produces both paper-level summaries and file-level reasoning, which are later reused in Step 4.

Main files:
- [step3/gpt_client.py](C:\UCLEAP\UC_LEAP\step3\gpt_client.py)
- [step3/file_inspector.py](C:\UCLEAP\UC_LEAP\step3\file_inspector.py)
- [step3/pdf_reader.py](C:\UCLEAP\UC_LEAP\step3\pdf_reader.py)
- [step3/pipeline.py](C:\UCLEAP\UC_LEAP\step3\pipeline.py)
- [step3_prompts.md](C:\UCLEAP\UC_LEAP\prompt_reference\step3_prompts.md)

### Step 4. Local organization and human-readable reasoning export

Step 4 takes the Step 3 classification results and organizes selected papers into a local folder structure.
It copies Type 1 files, Type 2 files, scripts, annotations, and PDFs into paper folders grouped by `Both`, `Type1`, `Type2`, or `Neither`.
It also writes a `reasoning.txt` file into each paper folder so a human reviewer can quickly see why the paper and its files were classified that way without opening the JSON outputs.
This step is rule-based and does not call GPT directly.

Main files:
- [step4/pipeline.py](C:\UCLEAP\UC_LEAP\step4\pipeline.py)
- [step4/file_organizer.py](C:\UCLEAP\UC_LEAP\step4\file_organizer.py)
- [step4_prompts.md](C:\UCLEAP\UC_LEAP\prompt_reference\step4_prompts.md)

## Type definitions used in classification

### Type 1

Type 1 means cleaned, organized, figure-replot-ready data.
Typical examples include `.csv`, `.xlsx`, or structured text files with clear columns, figure source data, and small or medium tabular datasets that can be plotted directly with little preprocessing.

### Type 2

Type 2 means raw or minimally processed measurement data.
Typical examples include instrument outputs, microscopy data, archives of original runs, HDF5/Nexus-style files, or large opaque bundles that likely need substantial processing before they can be replotted.

## Prompt files

For convenience, the current prompt references are split into separate files:

- [step1_prompts.md](C:\UCLEAP\UC_LEAP\prompt_reference\step1_prompts.md)
- [step2_prompts.md](C:\UCLEAP\UC_LEAP\prompt_reference\step2_prompts.md)
- [step3_prompts.md](C:\UCLEAP\UC_LEAP\prompt_reference\step3_prompts.md)
- [step4_prompts.md](C:\UCLEAP\UC_LEAP\prompt_reference\step4_prompts.md)

## Notes for reviewers

The most useful places to comment are usually:
- Step 1 screening criteria that may be too broad or too narrow
- Step 2 repository relevance checks that may over-trust unrelated links
- Step 3 Type 1 / Type 2 reasoning, especially when a paper looks misclassified
- Step 4 `reasoning.txt` output format if it can be made easier for human review

If you are reviewing classification quality, the most actionable artifacts are:
- Step 2 inventory JSON for paper-level repository evidence
- Step 3 per-paper JSON for detailed classification reasoning
- Step 4 `reasoning.txt` files for quick human review
