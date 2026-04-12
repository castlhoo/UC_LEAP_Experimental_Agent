"""
Phase 4 — Scan paper PDFs for data-availability statements (Issue 2).

For every preprint.pdf under cm_papers/, run pdftotext (with -layout) and
search the resulting text for sentences mentioning Zenodo, figshare,
'data availability', 'raw data', 'source data', 'deposited', etc.

This addresses the user feedback that some papers have no formal Data
Availability section but still cite the dataset as a numbered reference in
the body of the paper or in the reference list. Without scanning the full
text we miss those.

Output: a JSON dict {paper_id: [statement, ...]} that can be merged into
collection_summary.json under each paper's `paper_data_statements` field.

Usage:
    python scan_pdfs_for_data_statements.py --src /path/to/cm_papers
    python scan_pdfs_for_data_statements.py --src ... --out statements.json
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

KEYWORD_PATTERNS = [
    re.compile(r"\bzenodo\b", re.I),
    re.compile(r"\bfigshare\b", re.I),
    re.compile(r"data availability", re.I),
    re.compile(r"raw data", re.I),
    re.compile(r"source data", re.I),
    re.compile(r"deposit(ed|ory)", re.I),
    re.compile(r"data for figure", re.I),
    re.compile(r"available (?:at|on)\s+(?:zenodo|figshare|https?://)", re.I),
    re.compile(r"10\.5281/zenodo\.\d+", re.I),
]


def have_pdftotext() -> bool:
    return shutil.which("pdftotext") is not None


def pdf_to_text(pdf: Path) -> str:
    proc = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(f"pdftotext failed for {pdf}: {proc.stderr.strip()}",
              file=sys.stderr)
        return ""
    return proc.stdout


def extract_statements(text: str) -> list[str]:
    """Return up to ~10 short snippets matching the data-statement patterns."""
    out: list[str] = []
    seen: set[str] = set()
    # Split into sentences crudely on punctuation+whitespace.
    sentences = re.split(r"(?<=[\.!?])\s+", text)
    for sent in sentences:
        clean = " ".join(sent.split())
        if not clean or len(clean) > 350:
            continue
        for pat in KEYWORD_PATTERNS:
            if pat.search(clean):
                key = clean[:120].lower()
                if key in seen:
                    break
                seen.add(key)
                out.append(clean)
                break
        if len(out) >= 12:
            break
    return out


def scan(src: Path) -> dict[str, list[str]]:
    if not have_pdftotext():
        raise SystemExit("pdftotext not found on PATH (install poppler-utils)")
    results: dict[str, list[str]] = {}
    for pdf in sorted(src.glob("P*/paper/*.pdf")):
        paper_id = pdf.parent.parent.name.split("_", 1)[0]
        text = pdf_to_text(pdf)
        results[paper_id] = extract_statements(text)
        print(f"{paper_id}: {len(results[paper_id])} statements")
    return results


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--src", type=Path, required=True,
                   help="cm_papers root containing P##_<slug>/paper/preprint.pdf")
    p.add_argument("--out", type=Path, default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    results = scan(args.src.resolve())
    text = json.dumps(results, indent=2)
    if args.out:
        args.out.write_text(text)
        print(f"wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
