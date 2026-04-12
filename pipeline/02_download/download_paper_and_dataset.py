"""
Phase 2 — Download.

Given a paper ID + arXiv ID + Zenodo (or figshare) record ID, download:
  paper/preprint.pdf       <- arXiv PDF
  dataset/<original files> <- every file in the deposit
  scripts/<script files>   <- moved out of dataset/ if any code files exist

Idempotent: if a file is already on disk with a non-zero size and matches
the remote size, it is skipped.

Usage:
    python download_paper_and_dataset.py \
        --paper-id P21 \
        --short-title bismuthene_dft \
        --arxiv-id 2403.06046 \
        --zenodo-id 25737993 \
        --out-root /path/to/cm_papers
"""

import argparse
import json
import shutil
import sys
import urllib.request
from pathlib import Path

CODE_EXTS = {".py", ".ipynb", ".m", ".r", ".jl", ".sh"}

ZENODO_FILES = "https://zenodo.org/api/records/{rid}/files"
FIGSHARE_FILES = "https://api.figshare.com/v2/articles/{rid}/files"
ARXIV_PDF = "https://arxiv.org/pdf/{aid}"


def http_get_json(url: str, timeout: int = 60) -> dict:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "cm-download/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def download_stream(url: str, dest: Path, expected_size: int | None) -> bool:
    """Stream a URL to dest. Skip if already correct size. Return True on success."""
    if dest.exists() and expected_size and dest.stat().st_size == expected_size:
        print(f"  skip (already complete): {dest.name}")
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  GET  {url} -> {dest}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "cm-download/1.0"})
        with urllib.request.urlopen(req, timeout=300) as resp, dest.open("wb") as out:
            shutil.copyfileobj(resp, out)
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL {url}: {exc}", file=sys.stderr)
        return False
    return True


def list_zenodo_files(record_id: str) -> list[dict]:
    body = http_get_json(ZENODO_FILES.format(rid=record_id))
    raw = body.get("entries") or body.get("hits", {}).get("hits") or []
    out: list[dict] = []
    for f in raw:
        # Newer "entries" shape vs older "hits" shape — normalize.
        name = f.get("key") or f.get("filename") or ""
        size = int(f.get("size") or f.get("filesize") or 0)
        url = (
            (f.get("links") or {}).get("self")
            or (f.get("links") or {}).get("content")
            or (f.get("links") or {}).get("download")
            or ""
        )
        if name and url:
            out.append({"name": name, "size": size, "url": url})
    return out


def list_figshare_files(record_id: str) -> list[dict]:
    body = http_get_json(FIGSHARE_FILES.format(rid=record_id))
    out = []
    for f in body if isinstance(body, list) else []:
        out.append({
            "name": f.get("name", ""),
            "size": int(f.get("size", 0)),
            "url": f.get("download_url", ""),
        })
    return out


def move_scripts(dataset_dir: Path, scripts_dir: Path) -> int:
    """Move any code files found inside dataset/ over to scripts/."""
    moved = 0
    for path in dataset_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in CODE_EXTS:
            scripts_dir.mkdir(parents=True, exist_ok=True)
            target = scripts_dir / path.name
            if target.exists():
                target = scripts_dir / f"{path.stem}_{path.parent.name}{path.suffix}"
            shutil.move(str(path), target)
            moved += 1
    return moved


def download_paper(args: argparse.Namespace) -> dict:
    paper_dir = args.out_root / f"{args.paper_id}_{args.short_title}"
    paper_pdf_dir = paper_dir / "paper"
    dataset_dir = paper_dir / "dataset"
    scripts_dir = paper_dir / "scripts"
    for d in (paper_pdf_dir, dataset_dir, scripts_dir):
        d.mkdir(parents=True, exist_ok=True)

    pdf_ok = download_stream(
        ARXIV_PDF.format(aid=args.arxiv_id),
        paper_pdf_dir / "preprint.pdf",
        expected_size=None,
    )

    if args.repository == "zenodo":
        files = list_zenodo_files(args.record_id)
    elif args.repository == "figshare":
        files = list_figshare_files(args.record_id)
    else:
        raise SystemExit(f"unknown repository {args.repository!r}")

    downloaded: list[str] = []
    for f in files:
        ok = download_stream(f["url"], dataset_dir / f["name"], f["size"])
        if ok:
            downloaded.append(f["name"])

    moved = move_scripts(dataset_dir, scripts_dir)

    result = {
        "paper_id": args.paper_id,
        "paper_dir": str(paper_dir),
        "paper_pdf_downloaded": pdf_ok,
        "dataset_repository": args.repository,
        "dataset_record_id": args.record_id,
        "files_listed": len(files),
        "files_downloaded": len(downloaded),
        "scripts_moved": moved,
    }
    print(json.dumps(result, indent=2))
    return result


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--paper-id", required=True)
    p.add_argument("--short-title", required=True,
                   help="snake_case slug used in the folder name")
    p.add_argument("--arxiv-id", required=True)
    p.add_argument("--record-id", required=True,
                   help="Zenodo or figshare record ID (digits only)")
    p.add_argument("--repository", choices=["zenodo", "figshare"],
                   default="zenodo")
    p.add_argument("--out-root", type=Path,
                   default=Path("/Users/ayushimishra/dataset_collection/cm_papers"))
    return p.parse_args()


if __name__ == "__main__":
    download_paper(parse_args())
