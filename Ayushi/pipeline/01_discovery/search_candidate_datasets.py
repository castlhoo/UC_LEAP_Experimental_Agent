"""
Phase 1 — Discovery.

Search Zenodo (and optionally figshare) for candidate condensed-matter
datasets matching a set of subfield queries, verify each record is live,
collect basic shape metadata, and write a deduplicated candidates.json.

The original orchestrator spec calls Claude sub-agents to do web search.
This script is a Python-only stand-in: it queries the Zenodo REST search
API directly with topical keyword strings — no LLM, no shell sub-agents.

Usage:
    python search_candidate_datasets.py \
        --out candidates.json --per-query 8 --target 20

The script is read-only against the network and writes only the output JSON.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import urllib.parse
import urllib.request

# Subfield queries (mirrors the 5 discovery agents in the orchestrator spec).
SUBFIELD_QUERIES = {
    "superconductors": (
        "experimental superconductor CSV figure data 2023 2024"
    ),
    "topological_insulators": (
        "topological insulator transport experimental dataset figure"
    ),
    "2d_materials_moire": (
        "twisted bilayer graphene moire experimental dataset"
    ),
    "kagome_cdw": (
        "kagome metal charge density wave experimental dataset"
    ),
    "altermagnets_arpes": (
        "altermagnet ARPES experimental dataset"
    ),
}

ZENODO_SEARCH = "https://zenodo.org/api/records"
ZENODO_FILES = "https://zenodo.org/api/records/{rid}/files"


def http_get_json(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "cm-discover/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def zenodo_search(query: str, size: int) -> list[dict]:
    """Run a Zenodo search restricted to datasets, sorted by relevance."""
    params = urllib.parse.urlencode({
        "q": query,
        "size": size,
        "type": "dataset",
        "sort": "bestmatch",
    })
    url = f"{ZENODO_SEARCH}?{params}"
    try:
        body = http_get_json(url)
    except Exception as exc:  # noqa: BLE001 -- network errors get logged, not raised
        print(f"zenodo search failed for {query!r}: {exc}", file=sys.stderr)
        return []
    return body.get("hits", {}).get("hits", [])


def shape_record(hit: dict) -> dict | None:
    """Extract the bits we need from a Zenodo hit."""
    rid = str(hit.get("id") or "")
    if not rid:
        return None
    metadata = hit.get("metadata", {}) or {}
    doi = metadata.get("doi") or hit.get("doi") or ""
    title = metadata.get("title") or ""
    creators = metadata.get("creators") or []
    authors = ", ".join(c.get("name", "") for c in creators[:5])
    pub_date = metadata.get("publication_date", "")
    year = int(pub_date[:4]) if pub_date[:4].isdigit() else None
    journal = (metadata.get("journal") or {}).get("title", "")

    files = hit.get("files") or []
    file_count = len(files)
    total_bytes = sum(int(f.get("size", 0)) for f in files)

    return {
        "title": title,
        "authors": authors,
        "year": year,
        "journal": journal,
        "doi": doi,
        "dataset_url": f"https://zenodo.org/records/{rid}",
        "dataset_record_id": rid,
        "dataset_repository": "zenodo",
        "file_count": file_count,
        "total_size_mb": round(total_bytes / 1024 / 1024, 2),
    }


def verify_files_endpoint(record_id: str) -> bool:
    """Confirm the record's files endpoint actually returns content."""
    try:
        body = http_get_json(ZENODO_FILES.format(rid=record_id))
    except Exception:
        return False
    entries = body.get("entries") or body.get("hits", {}).get("hits") or []
    return len(entries) > 0


def discover(per_query: int, target: int, sleep: float) -> list[dict]:
    seen: dict[str, dict] = {}
    for tag, query in SUBFIELD_QUERIES.items():
        print(f"[{tag}] searching: {query!r}", file=sys.stderr)
        for hit in zenodo_search(query, size=per_query):
            shaped = shape_record(hit)
            if shaped is None:
                continue
            key = shaped["doi"] or shaped["dataset_record_id"]
            if key in seen:
                continue
            if shaped["file_count"] == 0:
                continue
            shaped["subfield_query"] = tag
            seen[key] = shaped
            time.sleep(sleep)
        if len(seen) >= target * 2:
            break

    candidates = sorted(
        seen.values(),
        key=lambda c: (-(c["file_count"] or 0), -(c["total_size_mb"] or 0)),
    )

    verified: list[dict] = []
    for cand in candidates:
        if len(verified) >= target:
            break
        rid = cand["dataset_record_id"]
        if not verify_files_endpoint(rid):
            print(f"  drop {rid}: files endpoint empty", file=sys.stderr)
            continue
        verified.append(cand)
        time.sleep(sleep)
    return verified


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path,
                   default=Path(__file__).with_name("candidates.json"))
    p.add_argument("--per-query", type=int, default=8,
                   help="Zenodo hits per subfield query")
    p.add_argument("--target", type=int, default=20,
                   help="number of verified candidates to keep")
    p.add_argument("--sleep", type=float, default=0.5,
                   help="seconds to sleep between API calls (be polite)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    candidates = discover(
        per_query=args.per_query, target=args.target, sleep=args.sleep,
    )
    args.out.write_text(json.dumps({"candidates": candidates}, indent=2))
    print(f"wrote {len(candidates)} candidates to {args.out}")


if __name__ == "__main__":
    main()
