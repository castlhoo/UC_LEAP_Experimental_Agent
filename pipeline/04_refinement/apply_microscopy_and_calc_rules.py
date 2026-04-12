"""
Phase 4 — Apply user-feedback overrides to existing classifications.

The user has provided several overrides that supersede the default rules:

  * AFM .tiff files, MFM .gwy files, and SEM/TEM .tif microscopy images
    are assumed to be processed (Type 1) unless the data README, the
    Zenodo description, or the paper main text explicitly says they are
    raw/unprocessed.
  * DFT calculation outputs and Monte Carlo simulation results deposited
    for figure reproduction are treated as Type 1 (calculation results
    for figures, not raw instrument data).
  * Type 2 datasets can still have annotated headers; the deciding factor
    is whether the data is cleaned-for-replotting vs. underlying
    measurement data.

This script walks an existing collection_summary.json, looks at each
paper's recorded classification + classification_reason, and:

  - Demotes Type 2 classifications that were driven *only* by microscopy
    images (.tif/.tiff/.gwy) or *only* by DFT/Monte Carlo computational
    outputs to Type 1.
  - Demotes Type1+Type2 classifications to Type 1 if the only Type 2
    evidence is microscopy / DFT / Monte Carlo.

It only acts when there is no overriding text evidence (i.e. the
classification_reason does not contain phrases like 'raw data',
'instrument', or 'unprocessed').

By default the script runs in --dry-run mode and just reports proposed
changes; pass --apply to write the updates back into the JSON.

Usage:
    python apply_microscopy_and_calc_rules.py \
        --collection /path/to/collection_summary.json
    python apply_microscopy_and_calc_rules.py --collection ... --apply
"""

import argparse
import json
import re
from pathlib import Path

MICROSCOPY_TOKENS = (
    "tiff", "tif", "gwy", "afm", "mfm", "sem", "tem", "microscop",
)
COMPUTATION_TOKENS = (
    "dft", "monte carlo", "monte-carlo", "simulation results",
    "calculation outputs", "calculation results",
)
RAW_OVERRIDE_TOKENS = (
    "raw data", "raw measurement", "unprocessed", "instrument",
    "binary instrument", ".3ds", ".sxm", ".pkl", ".npy", ".h5", ".hdf5",
    ".mat", ".spe", ".ibw",
)


def reason_lower(paper: dict) -> str:
    return (paper.get("classification_reason") or "").lower()


def has_token(text: str, tokens) -> bool:
    return any(tok in text for tok in tokens)


def should_demote(paper: dict) -> tuple[bool, str]:
    """Return (demote, why) for a single paper entry."""
    cls = paper.get("classification", "")
    if cls not in {"Type2", "Type1+Type2"}:
        return False, ""
    text = reason_lower(paper)
    if has_token(text, RAW_OVERRIDE_TOKENS):
        return False, "explicit raw/instrument evidence present"
    micro = has_token(text, MICROSCOPY_TOKENS)
    comp = has_token(text, COMPUTATION_TOKENS)
    if not (micro or comp):
        return False, "no microscopy/computation tokens"
    drivers = []
    if micro:
        drivers.append("microscopy")
    if comp:
        drivers.append("DFT/Monte Carlo")
    return True, "Type 2 evidence is only " + " + ".join(drivers)


def apply_rules(collection_path: Path, apply: bool) -> list[dict]:
    summary = json.loads(collection_path.read_text())
    changes: list[dict] = []
    for paper in summary["papers"]:
        demote, why = should_demote(paper)
        if not demote:
            continue
        old = paper["classification"]
        new = "Type1"
        changes.append({
            "paper_id": paper["paper_id"],
            "from": old,
            "to": new,
            "why": why,
        })
        if apply:
            paper["classification"] = new
            note = (
                f" [v2 override: demoted from {old} to Type 1 — "
                f"{why} per user feedback rules]"
            )
            paper["classification_reason"] = (
                paper.get("classification_reason", "") + note
            )
    if apply:
        collection_path.write_text(json.dumps(summary, indent=2))
    return changes


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--collection", type=Path, required=True)
    p.add_argument("--apply", action="store_true",
                   help="write changes back; otherwise dry-run")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    changes = apply_rules(args.collection.resolve(), apply=args.apply)
    if not changes:
        print("no changes proposed")
        return
    mode = "applied" if args.apply else "DRY RUN — would apply"
    print(f"{mode} {len(changes)} demotion(s):")
    for c in changes:
        print(f"  {c['paper_id']}: {c['from']} -> {c['to']}  ({c['why']})")


if __name__ == "__main__":
    main()
