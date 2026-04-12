"""
Phase 3 step B — Classify a paper from its inspection.json.

Applies the rule order from the refinement spec, and the user-feedback
overrides recorded in memory:

  1. Folder names: 'raw data' folder => raw evidence;
                   'data in plots'/'figure data'/'processed' => processed.
  2. File formats:
       - text data with labeled headers      => Type 1
       - spreadsheets (.xlsx etc.)            => Type 1
       - binary instrument files (.h5/.3ds/.pkl/.sxm/.spe/...) => Type 2
  3. Microscopy images (.tif/.tiff/.gwy)     => Type 1 (assumed processed,
                                                 user feedback override)
  4. Calculation outputs (DFT/Monte Carlo)   => Type 1 (user feedback)
  5. If both processed AND raw evidence are present  => Type1+Type2.
  6. Otherwise pick whichever side has any evidence;
     default to Type 1 if only labeled text data exists.

Output: classification + reason string, suitable for splicing into
collection_summary.json.

Usage:
    python classify_from_inspection.py --inspection /path/to/inspection.json
"""

import argparse
import json
from pathlib import Path


def classify(inspection: dict) -> dict:
    files = inspection.get("files", [])

    type1_signals: list[str] = []
    type2_signals: list[str] = []

    by_kind = inspection.get("totals", {}).get("by_kind", {})
    by_folder = inspection.get("totals", {}).get("by_folder_class", {})

    # --- Folder-name signals (highest priority structural hint) ---
    if by_folder.get("raw", 0) > 0:
        type2_signals.append(
            f"{by_folder['raw']} files under 'raw data' folder(s)"
        )
    if by_folder.get("processed", 0) > 0:
        type1_signals.append(
            f"{by_folder['processed']} files under 'data in plots' / 'processed' folder(s)"
        )
    if by_folder.get("calculation", 0) > 0:
        type1_signals.append(
            f"{by_folder['calculation']} files under 'calculations'/'simulations' folder(s)"
        )

    # --- Per-file signals ---
    labeled_text = sum(
        1 for f in files
        if f["kind"] == "text_data" and f.get("has_headers")
    )
    unlabeled_text = sum(
        1 for f in files
        if f["kind"] == "text_data" and not f.get("has_headers")
    )
    spreadsheets = by_kind.get("spreadsheet", 0)
    binary_raw = by_kind.get("binary_raw", 0)
    microscopy = by_kind.get("microscopy_image", 0)

    if labeled_text:
        type1_signals.append(f"{labeled_text} text/CSV files with labeled headers")
    if spreadsheets:
        type1_signals.append(f"{spreadsheets} spreadsheet (xlsx/opju) files")
    if binary_raw:
        type2_signals.append(
            f"{binary_raw} binary instrument files "
            "(.h5/.npy/.mat/.pkl/.3ds/.sxm/...)"
        )
    if unlabeled_text and binary_raw == 0 and labeled_text == 0:
        type2_signals.append(
            f"{unlabeled_text} text files without labeled headers"
        )

    # --- User-feedback overrides ---
    if microscopy:
        type1_signals.append(
            f"{microscopy} microscopy image(s) (.tif/.tiff/.gwy) — "
            "assumed processed unless paper/README says otherwise"
        )

    # --- Decide ---
    has_t1 = bool(type1_signals)
    has_t2 = bool(type2_signals)
    if has_t1 and has_t2:
        cls = "Type1+Type2"
    elif has_t2 and not has_t1:
        cls = "Type2"
    elif has_t1 and not has_t2:
        cls = "Type1"
    else:
        # No clear signals — default to Type 1 with a low-confidence note.
        cls = "Type1"
        type1_signals.append("no strong signals found; defaulted to Type 1")

    reason_parts = []
    if type1_signals:
        reason_parts.append("Type 1 evidence: " + "; ".join(type1_signals) + ".")
    if type2_signals:
        reason_parts.append("Type 2 evidence: " + "; ".join(type2_signals) + ".")

    return {
        "classification": cls,
        "classification_reason": " ".join(reason_parts),
        "type1_signals": type1_signals,
        "type2_signals": type2_signals,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inspection", type=Path, required=True)
    p.add_argument("--out", type=Path, default=None,
                   help="defaults to stdout")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    inspection = json.loads(args.inspection.read_text())
    result = classify(inspection)
    text = json.dumps(result, indent=2)
    if args.out:
        args.out.write_text(text)
        print(f"wrote {args.out}")
    else:
        print(text)
