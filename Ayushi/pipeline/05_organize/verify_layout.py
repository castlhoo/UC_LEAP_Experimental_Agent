"""
Verify that the on-disk type1/type2/both layout matches collection_summary.json.

Reports:
  - papers in JSON but missing from disk
  - directories on disk that are not in JSON
  - papers whose on-disk bucket disagrees with the JSON classification
  - dangling symlinks

Usage:
    python verify_layout.py
    python verify_layout.py --out /path/to/cm_papers_organized_v2
"""

import argparse
import json
import sys
from pathlib import Path

CLASSIFICATION_TO_BUCKET = {
    "Type1": "type1",
    "Type2": "type2",
    "Type1+Type2": "both",
}
BUCKETS = list(CLASSIFICATION_TO_BUCKET.values())


def scan_disk(out_dir: Path) -> dict[str, str]:
    """Return {paper_id: bucket} for whatever is currently on disk."""
    on_disk: dict[str, str] = {}
    for bucket in BUCKETS:
        bdir = out_dir / bucket
        if not bdir.is_dir():
            continue
        for entry in bdir.iterdir():
            if not entry.name.startswith("P"):
                continue
            paper_id = entry.name.split("_", 1)[0]
            if paper_id in on_disk:
                print(
                    f"warning: {paper_id} appears in both "
                    f"{on_disk[paper_id]} and {bucket}",
                    file=sys.stderr,
                )
            on_disk[paper_id] = bucket
            if entry.is_symlink() and not entry.exists():
                print(f"dangling symlink: {entry} -> {entry.resolve()}",
                      file=sys.stderr)
    return on_disk


def verify(out_dir: Path, summary_path: Path) -> int:
    summary = json.loads(summary_path.read_text())
    expected = {
        p["paper_id"]: CLASSIFICATION_TO_BUCKET.get(p["classification"])
        for p in summary["papers"]
    }
    on_disk = scan_disk(out_dir)

    errors = 0
    for paper_id, bucket in sorted(expected.items()):
        if bucket is None:
            print(f"unknown classification for {paper_id} in JSON")
            errors += 1
            continue
        actual = on_disk.get(paper_id)
        if actual is None:
            print(f"missing on disk: {paper_id} (expected {bucket})")
            errors += 1
        elif actual != bucket:
            print(f"bucket mismatch: {paper_id} on disk in {actual}, "
                  f"JSON says {bucket}")
            errors += 1

    extra = sorted(set(on_disk) - set(expected))
    for paper_id in extra:
        print(f"on disk but not in JSON: {paper_id} (in {on_disk[paper_id]})")
        errors += 1

    if errors == 0:
        print(f"OK: {len(expected)} papers, layout matches JSON")
    else:
        print(f"FAIL: {errors} discrepancy/discrepancies")
    return errors


def parse_args() -> argparse.Namespace:
    # pipeline/05_organize/ -> ../../collected_papers
    # (.../UC_LEAP_Experimental_Agent/pipeline/05_organize/ ->
    #   .../UC_LEAP_Experimental_Agent/collected_papers/)
    here = Path(__file__).resolve().parent
    default_out = here.parent.parent / "collected_papers"
    default_json = default_out / "collection_summary.json"

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=default_out,
                   help=f"organized output dir (default: {default_out})")
    p.add_argument("--json", type=Path, default=default_json,
                   help=f"collection_summary.json (default: {default_json})")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    sys.exit(verify(args.out.resolve(), args.json.resolve()))
