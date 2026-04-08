"""Quick script to display Step 2 results for manual verification."""
import json

data = json.load(open("step2/output/step2_inventory_latest.json", "r", encoding="utf-8"))

print("=" * 80)
print("TYPE 1 (Clean / Replot-ready) Papers")
print("=" * 80)

t1 = [p for p in data["papers"] if p.get("dataset_type") == "type1"]
for i, p in enumerate(t1, 1):
    title = p["title"][:70]
    journal = p["journal"]
    doi = p["doi"]
    score = p["priority_score"]
    ev = p.get("type1_evidence", "none")[:150]
    url = p["paper_url"]
    n_files = len(p.get("source_data_files", []))
    print(f"{i:2d}. [{score:5.1f}] {title}")
    print(f"    Journal: {journal}")
    print(f"    DOI: {doi}")
    print(f"    URL: {url}")
    print(f"    Source files: {n_files}")
    print(f"    Type1 evidence: {ev}")
    print()

print("=" * 80)
print("UNKNOWN TYPE (but data found) Papers")
print("=" * 80)

unk = [p for p in data["papers"]
       if p.get("dataset_type") == "unknown"
       and p["dataset_status"] not in ("no_dataset_found",)]
for i, p in enumerate(unk, 1):
    title = p["title"][:70]
    status = p["dataset_status"]
    journal = p["journal"]
    url = p["paper_url"]
    print(f"{i:2d}. [{status}] {title}")
    print(f"    Journal: {journal} | URL: {url}")
    print()

print("=" * 80)
print(f"Summary: {len(t1)} type1, {len(unk)} unknown-with-data, "
      f"{sum(1 for p in data['papers'] if p['dataset_status']=='no_dataset_found')} no-data")
