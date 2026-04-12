# Step 4 Prompts

This file summarizes what Step 4 uses instead of a direct GPT prompt.
Step 4 is a rule-based organization stage that consumes the reasoning already produced in Step 3 and turns it into a local paper corpus.
Its role is not to make a new model judgment, but to preserve the earlier Type 1 / Type 2 reasoning in a human-readable and file-system-friendly format.
That is why Step 4 writes organized folders, `manifest_latest.json`, and per-paper `reasoning.txt` files rather than sending a new prompt to GPT.

Instead, Step 4 is a rule-based organization stage that:

- reads Step 3 classification output
- selects papers to organize
- downloads PDFs if available
- copies files into `type1_data`, `type2_data`, `annotations`, and `scripts`
- writes `manifest_latest.json`
- writes `reasoning.txt` into each paper folder

## What Step 4 uses instead of a prompt

Step 4 depends on these upstream reasoning fields:

- paper-level reasoning from Step 3:
  - `type1_summary`
  - `type2_summary`
  - `classification_confidence`
- file-level reasoning from Step 3:
  - `type`
  - `reasoning`
  - `paper_evidence`
  - `file_evidence`
  - `ambiguity`
  - `key_columns_or_structure`

## Step 4 human-readable output

Each organized paper folder now gets a `reasoning.txt` file containing:

- title / DOI / journal / year
- final label (`Both`, `Type1 only`, `Type2 only`, or `Neither`)
- paper-level Type 1 and Type 2 summaries
- file-level classification reasoning for copied files

So Step 4 has no direct model prompt, but it preserves and exports the reasoning generated in Step 3.
