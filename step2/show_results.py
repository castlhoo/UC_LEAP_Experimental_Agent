"""Quick script to display Step 2 data-presence results for manual verification."""
import collections
import json
import sys


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    data = json.load(open("step2/output/step2_inventory_latest.json", "r", encoding="utf-8"))
    papers = data["papers"]

    status_counts = collections.Counter(p["dataset_status"] for p in papers)

    print("=" * 80)
    print("STEP 2 DATA PRESENCE SUMMARY")
    print("=" * 80)
    for status, count in status_counts.most_common():
        print(f"{status:>17}: {count}")

    with_data = [
        p for p in papers
        if p["dataset_status"] in ("verified", "source_data_found", "link_found")
    ]
    upon_request = [p for p in papers if p["dataset_status"] == "upon_request"]

    print("=" * 80)
    print("PAPERS WITH DATA LINKS / FILES")
    print("=" * 80)
    for i, p in enumerate(with_data[:50], 1):
        title = p["title"][:70]
        journal = p["journal"]
        doi = p["doi"]
        score = p["priority_score"]
        status = p["dataset_status"]
        n_data = len(p.get("data_url_candidates", p.get("source_data_files", [])))
        n_ambiguous = len(p.get("ambiguous_url_candidates", []))
        pdf_status = p.get("pdf_resolution_status", "not_found")
        pdf_source = p.get("paper_pdf_source", "")
        n_ignored = len(p.get("ignored_urls", []))
        repos = p.get("repositories", [])
        repo_summary = ", ".join(
            f"{r.get('repo_type', '?')}({r.get('inventory', {}).get('file_count', 0)} files)"
            for r in repos
            if r.get("inventory", {}).get("success")
        )

        print(f"{i:2d}. [{score:5.1f}] [{status}] {title}")
        print(f"    Journal: {journal}")
        print(f"    DOI: {doi}")
        print(
            f"    Repos: {repo_summary or 'none'} | Data URLs: {n_data} | "
            f"PDF: {pdf_status}{('/' + pdf_source) if pdf_source else ''} | "
            f"Ambiguous: {n_ambiguous} | Ignored: {n_ignored}"
        )
        print()

    print("=" * 80)
    print("UPON REQUEST")
    print("=" * 80)
    for i, p in enumerate(upon_request[:30], 1):
        print(f"{i:2d}. {p['title'][:70]}")

    print("=" * 80)
    print(
        f"Summary: {len(with_data)} with data/link, {len(upon_request)} upon-request, "
        f"{status_counts.get('no_dataset_found', 0)} no-data"
    )


if __name__ == "__main__":
    main()
