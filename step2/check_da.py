"""Check DA text and GPT analysis for type1 papers."""
import json

data = json.load(open("step2/output/step2_inventory_latest.json", "r", encoding="utf-8"))

print("=" * 80)
print("TYPE1 PAPERS - DA TEXT & GPT ANALYSIS CHECK")
print("=" * 80)

for i, p in enumerate(data["papers"]):
    if p["dataset_type"] != "type1":
        continue
    da = p.get("data_availability_text", "")
    gpt = p.get("gpt_data_analysis", {})
    gpt_loc = gpt.get("dataset_location", "?")
    n_src = len(p.get("source_data_files", []))

    # Flag if DA text contains "upon request" / "reasonable request"
    da_lower = da.lower()
    flag = ""
    if "upon request" in da_lower or "reasonable request" in da_lower:
        flag = " *** UPON REQUEST ***"
    elif not da:
        flag = " (no DA text)"

    print(f"{i+1:2d}. {p['title'][:65]}")
    print(f"    GPT loc: {gpt_loc} | src files: {n_src}{flag}")
    if da:
        print(f"    DA: {da[:150]}")
    print()

print("=" * 80)
print("NON-NATURE PAPERS STATUS")
print("=" * 80)
for p in data["papers"]:
    j = p["journal"]
    if "nature" not in j.lower() and "pubmed" not in j.lower():
        print(f"  [{p['dataset_status']:>17}] [{p['dataset_type']:>7}] {j}: {p['title'][:55]}")
