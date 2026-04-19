"""
Phase 3 step A — Inspect a paper folder.

Walks one paper folder and produces a JSON record describing every file:
  - format
  - size
  - whether it has a labeled header (for text formats)
  - sample header tokens
  - which subfolder of dataset/ it lives in (raw_data / data_in_plots / etc.)

Output is a per-paper inspection.json that classify_from_inspection.py
consumes in step B.

Usage:
    python inspect_paper_folder.py --paper-dir /path/to/cm_papers/P01_xxx
    python inspect_paper_folder.py --paper-dir ... --out inspection.json
"""

import argparse
import json
from pathlib import Path

CODE_EXTS = {".py", ".ipynb", ".m", ".r", ".jl", ".sh"}
TEXT_EXTS = {".csv", ".tsv", ".txt", ".dat", ".xy", ".asc"}
BINARY_RAW_EXTS = {
    ".h5", ".hdf5", ".npy", ".npz", ".mat", ".spe", ".ibw", ".sxm",
    ".3ds", ".tof", ".pkl", ".tdms", ".nxs",
}
MICROSCOPY_IMG_EXTS = {".tif", ".tiff", ".gwy"}
PLOT_IMG_EXTS = {".png", ".svg", ".eps", ".pdf", ".jpg", ".jpeg"}
SHEET_EXTS = {".xlsx", ".xls", ".ods", ".opju", ".oggu"}

# Folder-name signals from the refinement spec.
RAW_FOLDER_TOKENS = {"raw data", "raw_data", "rawdata"}
PROCESSED_FOLDER_TOKENS = {
    "data in plots", "data_for_figures", "figure_data", "processed",
    "data_in_plots",
}
CALC_FOLDER_TOKENS = {"calculation results", "calculations", "simulations"}
SCRIPT_FOLDER_TOKENS = {"scripts", "code", "analysis"}
FIGURE_FOLDER_TOKENS = {"figures", "plots", "pics"}


def classify_folder(folder_name: str) -> str:
    name = folder_name.lower()
    if any(tok in name for tok in RAW_FOLDER_TOKENS):
        return "raw"
    if any(tok in name for tok in PROCESSED_FOLDER_TOKENS):
        return "processed"
    if any(tok in name for tok in CALC_FOLDER_TOKENS):
        return "calculation"
    if any(tok in name for tok in SCRIPT_FOLDER_TOKENS):
        return "scripts"
    if any(tok in name for tok in FIGURE_FOLDER_TOKENS):
        return "figures"
    return "unknown"


def sample_text_headers(path: Path, max_bytes: int = 4096) -> list[str]:
    """Read the first chunk of a text file and try to extract column headers."""
    try:
        with path.open("rb") as f:
            chunk = f.read(max_bytes)
    except OSError:
        return []
    try:
        text = chunk.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    first = lines[0].lstrip("#% ").strip()
    for sep in ("\t", ",", ";", "  ", " "):
        if sep in first:
            tokens = [t.strip() for t in first.split(sep) if t.strip()]
            if 1 < len(tokens) <= 12:
                return tokens
    return [first] if 1 <= len(first) <= 80 else []


def header_looks_labeled(headers: list[str]) -> bool:
    if not headers:
        return False
    has_letter = any(any(c.isalpha() for c in h) for h in headers)
    has_unit = any(("(" in h and ")" in h) or any(u in h.lower()
                   for u in ["temperature", "field", "voltage", "current",
                             "energy", "freq", "intensity", "resistance"])
                   for h in headers)
    return has_letter and (has_unit or len(headers) >= 2 and has_letter)


def file_kind(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in CODE_EXTS:
        return "script"
    if ext in TEXT_EXTS:
        return "text_data"
    if ext in SHEET_EXTS:
        return "spreadsheet"
    if ext in BINARY_RAW_EXTS:
        return "binary_raw"
    if ext in MICROSCOPY_IMG_EXTS:
        return "microscopy_image"
    if ext in PLOT_IMG_EXTS:
        return "plot_image"
    if ext == ".zip":
        return "archive"
    return "other"


def inspect(paper_dir: Path) -> dict:
    dataset_dir = paper_dir / "dataset"
    files_info: list[dict] = []

    if dataset_dir.is_dir():
        for path in dataset_dir.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(dataset_dir)
            parent_class = "root"
            for parent in rel.parents:
                if parent == Path("."):
                    continue
                cls = classify_folder(parent.name)
                if cls != "unknown":
                    parent_class = cls
                    break
            kind = file_kind(path)
            entry = {
                "name": str(rel),
                "size_bytes": path.stat().st_size,
                "kind": kind,
                "folder_class": parent_class,
            }
            if kind == "text_data":
                headers = sample_text_headers(path)
                entry["sample_headers"] = headers
                entry["has_headers"] = header_looks_labeled(headers)
            files_info.append(entry)

    scripts_dir = paper_dir / "scripts"
    scripts: list[str] = []
    if scripts_dir.is_dir():
        scripts = sorted(p.name for p in scripts_dir.iterdir()
                         if p.is_file() and p.suffix.lower() in CODE_EXTS)

    readme_present = any(
        (paper_dir / "dataset").rglob(pat)
        for pat in ("README*", "readme*", "Readme*")
    ) if dataset_dir.is_dir() else False

    return {
        "paper_dir": str(paper_dir),
        "files": files_info,
        "scripts": scripts,
        "readme_present": readme_present,
        "totals": {
            "files": len(files_info),
            "size_mb": round(
                sum(f["size_bytes"] for f in files_info) / 1024 / 1024, 3
            ),
            "by_kind": _count_by(files_info, "kind"),
            "by_folder_class": _count_by(files_info, "folder_class"),
        },
    }


def _count_by(items: list[dict], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in items:
        out[item[key]] = out.get(item[key], 0) + 1
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--paper-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, default=None,
                   help="defaults to <paper-dir>/inspection.json")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    data = inspect(args.paper_dir.resolve())
    out = args.out or (args.paper_dir / "inspection.json")
    out.write_text(json.dumps(data, indent=2))
    print(f"wrote {out} ({data['totals']['files']} files, "
          f"{data['totals']['size_mb']} MB)")
