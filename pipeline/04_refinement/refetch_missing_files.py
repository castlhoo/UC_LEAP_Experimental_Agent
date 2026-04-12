"""
Phase 4 — Refetch missing files (Issue 1 in the refinement spec).

For each paper folder that has a Zenodo or figshare deposit, fetch the
authoritative file list from the API and compare it against what's actually
on disk under dataset/. Anything missing or size-mismatched gets downloaded.

This is the script you run when 'some files were silently skipped on the
first pass' — typical for tiff/png and other large binary files.

Usage:
    python refetch_missing_files.py \
        --collection /path/to/cm_papers_organized_v2/collection_summary.json \
        --src /path/to/cm_papers
    python refetch_missing_files.py ... --dry-run
"""

import argparse
import json
import shutil
import sys
import urllib.request
from pathlib import Path

ZENODO_FILES = "https://zenodo.org/api/records/{rid}/files"
FIGSHARE_FILES = "https://api.figshare.com/v2/articles/{rid}/files"


def http_get_json(url: str, timeout: int = 60) -> dict:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "cm-refetch/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def list_remote_files(repo: str, record_id: str) -> list[dict]:
    if repo == "zenodo":
        body = http_get_json(ZENODO_FILES.format(rid=record_id))
        raw = body.get("entries") or body.get("hits", {}).get("hits") or []
        out = []
        for f in raw:
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
    if repo == "figshare":
        body = http_get_json(FIGSHARE_FILES.format(rid=record_id))
        return [
            {
                "name": f.get("name", ""),
                "size": int(f.get("size", 0)),
                "url": f.get("download_url", ""),
            }
            for f in body if isinstance(f, dict)
        ]
    return []


def find_local_file(dataset_dir: Path, name: str) -> Path | None:
    """Locate a file by name anywhere under dataset_dir (it may be in a subfolder)."""
    for path in dataset_dir.rglob(name):
        if path.is_file():
            return path
    return None


def download(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  GET {url} -> {dest}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "cm-refetch/1.0"})
        with urllib.request.urlopen(req, timeout=600) as resp, dest.open("wb") as out:
            shutil.copyfileobj(resp, out)
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL: {exc}", file=sys.stderr)
        return False
    return True


def refetch_for_paper(paper_dir: Path, repo: str, record_id: str,
                      dry_run: bool) -> dict:
    dataset_dir = paper_dir / "dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)

    try:
        remote = list_remote_files(repo, record_id)
    except Exception as exc:  # noqa: BLE001
        print(f"  failed to list {repo}/{record_id}: {exc}", file=sys.stderr)
        return {"paper_dir": str(paper_dir), "error": str(exc)}

    missing: list[dict] = []
    for f in remote:
        local = find_local_file(dataset_dir, f["name"])
        if local is None:
            missing.append({**f, "reason": "not present"})
            continue
        if f["size"] and local.stat().st_size != f["size"]:
            missing.append({**f, "reason": f"size mismatch: local={local.stat().st_size} remote={f['size']}"})

    print(f"{paper_dir.name}: {len(remote)} remote / {len(missing)} missing")
    fetched: list[str] = []
    if not dry_run:
        for f in missing:
            dest = dataset_dir / f["name"]
            if download(f["url"], dest):
                fetched.append(f["name"])

    return {
        "paper_dir": str(paper_dir),
        "remote_count": len(remote),
        "missing_count": len(missing),
        "fetched_count": len(fetched),
        "missing": [m["name"] for m in missing],
        "fetched": fetched,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--collection", type=Path, required=True,
                   help="collection_summary.json")
    p.add_argument("--src", type=Path, required=True,
                   help="cm_papers/ root containing the per-paper folders")
    p.add_argument("--paper-id", default=None,
                   help="if set, only refetch this paper")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    summary = json.loads(args.collection.read_text())
    report = []
    for paper in summary["papers"]:
        if args.paper_id and paper["paper_id"] != args.paper_id:
            continue
        repo = paper.get("dataset_repository")
        rid = paper.get("dataset_record_id")
        if not repo or not rid:
            continue
        # Find the on-disk paper folder by P## prefix.
        matches = sorted(args.src.glob(f"{paper['paper_id']}_*"))
        if not matches:
            print(f"no folder for {paper['paper_id']}", file=sys.stderr)
            continue
        report.append(refetch_for_paper(matches[0], repo, str(rid), args.dry_run))

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
