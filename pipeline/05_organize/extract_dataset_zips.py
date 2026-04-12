"""
Extract any data.zip files found under cm_papers/<paper>/dataset/ in place.

Some Zenodo deposits ship a single zip rather than loose files. This script
walks the source tree, locates each zip, and extracts it to a sibling
'extracted/' folder so the contents are browsable without altering the
original zip.

Idempotent: if 'extracted/' already exists for a given zip and contains files,
the zip is skipped (use --force to re-extract).

Usage:
    python extract_dataset_zips.py --src /path/to/cm_papers
    python extract_dataset_zips.py --src /path/to/cm_papers --force
"""

import argparse
import sys
import zipfile
from pathlib import Path


def find_dataset_zips(src_dir: Path) -> list[Path]:
    """Find every *.zip beneath any */dataset/ subtree."""
    return sorted(src_dir.glob("*/dataset/**/*.zip"))


def extract_zip(zip_path: Path, force: bool) -> None:
    target = zip_path.parent / "extracted"
    if target.exists() and any(target.iterdir()) and not force:
        print(f"skip {zip_path.name}: {target} already populated")
        return

    target.mkdir(exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        bad = zf.testzip()
        if bad is not None:
            print(f"corrupt entry in {zip_path}: {bad}", file=sys.stderr)
            return
        zf.extractall(target)
    print(f"extracted {zip_path} -> {target} ({len(list(target.rglob('*')))} entries)")


def parse_args() -> argparse.Namespace:
    # pipeline/05_organize/ -> ../../../cm_papers
    # (.../UC_LEAP_Experimental_Agent/pipeline/05_organize/ -> dataset_collection/cm_papers)
    here = Path(__file__).resolve().parent
    default_src = here.parent.parent.parent / "cm_papers"

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--src", type=Path, default=default_src,
                   help=f"source cm_papers/ dir (default: {default_src})")
    p.add_argument("--force", action="store_true",
                   help="re-extract even if target already populated")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    zips = find_dataset_zips(args.src.resolve())
    if not zips:
        print(f"no dataset zips found under {args.src}")
        sys.exit(0)

    print(f"found {len(zips)} dataset zip(s)")
    for z in zips:
        extract_zip(z, force=args.force)
