"""
Build the type1 / type2 / both directory layout for the cm_papers collection.

Reads collection_summary.json, then for each paper creates a symlink under
  <out_dir>/type1/<paper_dir>           if classification == "Type1"
  <out_dir>/type2/<paper_dir>           if classification == "Type2"
  <out_dir>/both/<paper_dir>            if classification == "Type1+Type2"

Each symlink targets the original paper folder under <src_dir>. Symlinks are
used (not copies) so the source-of-truth files in cm_papers/ are not
duplicated.

Usage:
    python organize_by_classification.py \
        --src  /path/to/cm_papers \
        --out  /path/to/cm_papers_organized_v2 \
        --json /path/to/cm_papers_organized_v2/collection_summary.json
"""

import argparse
import json
import os
import sys
from pathlib import Path

CLASSIFICATION_TO_BUCKET = {
    "Type1": "type1",
    "Type2": "type2",
    "Type1+Type2": "both",
}


def find_paper_dir(src_dir: Path, paper_id: str) -> Path | None:
    """Locate the source folder for a paper by its P## prefix."""
    matches = sorted(src_dir.glob(f"{paper_id}_*"))
    if not matches:
        return None
    if len(matches) > 1:
        print(
            f"warning: multiple source folders match {paper_id}: {matches}; "
            f"using first",
            file=sys.stderr,
        )
    return matches[0]


def organize(src_dir: Path, out_dir: Path, summary_path: Path) -> None:
    summary = json.loads(summary_path.read_text())
    papers = summary["papers"]

    for bucket in CLASSIFICATION_TO_BUCKET.values():
        (out_dir / bucket).mkdir(parents=True, exist_ok=True)

    created, skipped, missing = 0, 0, 0
    for paper in papers:
        paper_id = paper["paper_id"]
        cls = paper["classification"]

        bucket = CLASSIFICATION_TO_BUCKET.get(cls)
        if bucket is None:
            print(f"skip {paper_id}: unrecognized classification {cls!r}")
            skipped += 1
            continue

        src = find_paper_dir(src_dir, paper_id)
        if src is None:
            print(f"missing source folder for {paper_id} under {src_dir}")
            missing += 1
            continue

        link = out_dir / bucket / src.name
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(src.resolve())
        print(f"linked {bucket}/{src.name} -> {src}")
        created += 1

    print(
        f"\ndone: {created} linked, {skipped} skipped, {missing} missing source"
    )


def parse_args() -> argparse.Namespace:
    # This file lives in:
    #   dataset_collection/UC_LEAP_Experimental_Agent/pipeline/05_organize/
    # cm_papers (source of truth) sits at dataset_collection/cm_papers/,
    # collected_papers (categorised view) sits at
    #   dataset_collection/UC_LEAP_Experimental_Agent/collected_papers/.
    here = Path(__file__).resolve().parent
    uc_leap_root = here.parent.parent          # .../UC_LEAP_Experimental_Agent
    dataset_root = uc_leap_root.parent         # .../dataset_collection
    default_src = dataset_root / "cm_papers"
    default_out = uc_leap_root / "collected_papers"
    default_json = default_out / "collection_summary.json"

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--src", type=Path, default=default_src,
                   help=f"source cm_papers/ dir (default: {default_src})")
    p.add_argument("--out", type=Path, default=default_out,
                   help=f"output organized dir (default: {default_out})")
    p.add_argument("--json", type=Path, default=default_json,
                   help=f"collection_summary.json (default: {default_json})")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    organize(args.src.resolve(), args.out.resolve(), args.json.resolve())
