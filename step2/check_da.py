"""Check Step 2 data-availability text and discovered data locations."""
import json
import sys


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    data = json.load(open("step2/output/step2_inventory_latest.json", "r", encoding="utf-8"))

    print("=" * 80)
    print("PAPERS WITH DATA AVAILABILITY TEXT OR DATA LINKS")
    print("=" * 80)

    for i, p in enumerate(data["papers"], 1):
        da = p.get("data_availability_text", "")
        n_data = len(p.get("data_url_candidates", p.get("source_data_files", [])))
        n_ambiguous = len(p.get("ambiguous_url_candidates", []))
        pdf_status = p.get("pdf_resolution_status", "not_found")
        n_ignored = len(p.get("ignored_urls", []))
        n_urls = len(p.get("discovered_urls", []))
        repos = p.get("repositories", [])
        repo_summary = ", ".join(
            f"{r.get('repo_type', '?')}:{r.get('inventory', {}).get('file_count', 0)} files"
            for r in repos
            if r.get("inventory", {}).get("success")
        )

        if not (da or n_data or n_ambiguous or n_urls or repo_summary or pdf_status == "found"):
            continue

        da_lower = da.lower()
        flag = ""
        if "upon request" in da_lower or "reasonable request" in da_lower:
            flag = " *** UPON REQUEST ***"
        elif not da:
            flag = " (no DA text)"

        print(f"{i:3d}. [{p['dataset_status']:>17}] {p['title'][:65]}")
        print(
            f"     repos: {repo_summary or 'none'} | data urls: {n_data} | "
            f"pdf: {pdf_status} | urls: {n_urls} | ambiguous: {n_ambiguous} | ignored: {n_ignored}{flag}"
        )
        if da:
            print(f"     DA: {da[:180]}")
        print()

    print("=" * 80)
    print("NON-NATURE PAPERS WITH DATA")
    print("=" * 80)
    for p in data["papers"]:
        j = p["journal"]
        if (
            p["dataset_status"] in ("verified", "source_data_found", "link_found")
            and "nature" not in j.lower()
            and "pubmed" not in j.lower()
        ):
            print(f"  [{p['dataset_status']:>17}] {j}: {p['title'][:65]}")


if __name__ == "__main__":
    main()
