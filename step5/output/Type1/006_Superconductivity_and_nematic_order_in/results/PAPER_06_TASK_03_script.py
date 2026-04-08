import os
import re
import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Paths
dataset_file = Path(r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/006_Superconductivity_and_nematic_order_in/type1_data/Fig2b.xlsx")
figure_path = Path(r"C:/UCLEAP/UC_LEAP/step5/output/Type1/006_Superconductivity_and_nematic_order_in/results/PAPER_06_TASK_03_figure.png")
analysis_path = Path(r"C:/UCLEAP/UC_LEAP/step5/output/Type1/006_Superconductivity_and_nematic_order_in/results/PAPER_06_TASK_03_Analysis.txt")

figure_path.parent.mkdir(parents=True, exist_ok=True)
analysis_path.parent.mkdir(parents=True, exist_ok=True)

analysis_lines = []

def log(msg):
    analysis_lines.append(msg)

log("Task PAPER_06_TASK_03: Replot ultra-low-field magnetization versus temperature")
log(f"Dataset file: {dataset_file}")

# Step 0: Inspect workbook structure
if not dataset_file.exists():
    raise FileNotFoundError(f"Dataset file not found: {dataset_file}")

xls = pd.ExcelFile(dataset_file)
log(f"Workbook sheets: {xls.sheet_names}")

# Load sheet
df_raw = pd.read_excel(dataset_file, sheet_name=xls.sheet_names[0], header=None)
log(f"Loaded sheet '{xls.sheet_names[0]}' with shape {df_raw.shape}")

# Brief structural inspection
preview_rows = min(8, len(df_raw))
for i in range(preview_rows):
    row_vals = df_raw.iloc[i].tolist()
    log(f"Row {i} preview: {row_vals[:min(12, len(row_vals))]}{' ...' if len(row_vals) > 12 else ''}")

# Step 1: Identify repeated data blocks and field labels
# The sheet appears to have paired columns: T (K), M repeated across the row.
# Row 0 contains repeated headers; row 1 contains field labels in the M columns.
header_row = df_raw.iloc[0].tolist()
label_row = df_raw.iloc[1].tolist()

pairs = []
for c in range(0, df_raw.shape[1], 2):
    t_header = str(header_row[c]).strip() if c < len(header_row) else ""
    m_header = str(header_row[c+1]).strip() if c+1 < len(header_row) else ""
    field_label = str(label_row[c+1]).strip() if c+1 < len(label_row) else ""
    pairs.append((c, c+1, t_header, m_header, field_label))

log("Detected column pairs and labels:")
for idx, (tc, mc, th, mh, fl) in enumerate(pairs):
    log(f"  Pair {idx+1}: cols ({tc},{mc}) headers=({th},{mh}), field label='{fl}'")

# Step 2: Extract numeric data, remove non-numeric rows / artifacts
def to_numeric_series(s):
    return pd.to_numeric(s, errors='coerce')

traces = []
for idx, (tc, mc, th, mh, fl) in enumerate(pairs):
    if tc >= df_raw.shape[1] or mc >= df_raw.shape[1]:
        continue
    t = to_numeric_series(df_raw.iloc[2:, tc])
    m = to_numeric_series(df_raw.iloc[2:, mc])
    valid = t.notna() & m.notna()
    t = t[valid].astype(float).to_numpy()
    m = m[valid].astype(float).to_numpy()
    if len(t) == 0:
        log(f"  Skipping pair {idx+1} ('{fl}') because no numeric data were found.")
        continue
    # Preserve ordering as in file
    traces.append({
        "field_label": fl,
        "t": t,
        "m": m,
        "pair_index": idx + 1
    })
    log(f"  Extracted pair {idx+1}: field='{fl}', points={len(t)}, T range=({np.min(t):.6g}, {np.max(t):.6g}), M range=({np.min(m):.6g}, {np.max(m):.6g})")

if not traces:
    raise ValueError("No valid traces could be extracted from the workbook.")

# Sort by field magnitude while preserving original order if parsing fails
def parse_field_value(label):
    if label is None:
        return np.nan
    s = str(label).strip()
    m = re.search(r'([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*Oe', s)
    if m:
        return float(m.group(1))
    m = re.search(r'([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)', s)
    return float(m.group(1)) if m else np.nan

for tr in traces:
    tr["field_value"] = parse_field_value(tr["field_label"])

# Preserve field ordering from the sheet; if numeric values are available, use them only for annotation
ordered_traces = traces

log("Field ordering preserved as in the source sheet:")
for tr in ordered_traces:
    log(f"  Pair {tr['pair_index']}: label='{tr['field_label']}', parsed_field={tr['field_value']}")

# Step 3: Plot all magnetization curves versus temperature
plt.figure(figsize=(8.2, 6.2), dpi=200)
ax = plt.gca()

# Use a color map across traces
cmap = plt.get_cmap("viridis")
n = len(ordered_traces)

for i, tr in enumerate(ordered_traces):
    color = cmap(i / max(n - 1, 1))
    label = tr["field_label"] if tr["field_label"] else f"Trace {i+1}"
    ax.plot(tr["t"], tr["m"], lw=1.6, color=color, label=label)

# Step 4: Annotate and format
ax.set_xlabel("Temperature (K)", fontsize=12)
ax.set_ylabel("Magnetization M", fontsize=12)
ax.set_title("Ultra-low-field magnetization vs temperature", fontsize=13)

ax.tick_params(direction="in", top=True, right=True)
ax.minorticks_on()
ax.grid(False)

# Improve legend readability
leg = ax.legend(
    title="Applied field",
    fontsize=8,
    title_fontsize=9,
    loc="best",
    frameon=True,
    framealpha=0.9,
    ncol=1
)

# Tight layout and save
plt.tight_layout()
plt.savefig(figure_path, bbox_inches="tight")
plt.close()

log(f"Figure saved to: {figure_path}")

# Write analysis file
analysis_text = "\n".join(analysis_lines)
analysis_path.write_text(analysis_text, encoding="utf-8")

print(f"Saved figure: {figure_path}")
print(f"Saved analysis: {analysis_path}")