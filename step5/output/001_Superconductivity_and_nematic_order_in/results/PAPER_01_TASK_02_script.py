import os
import re
import math
import warnings
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

# Paths
dataset_path = Path(r"C:/UCLEAP/UC_LEAP/step4/organized/001_Superconductivity_and_nematic_order_in/type1_data/Fig2a.xlsx")
figure_path = Path(r"C:/UCLEAP/UC_LEAP/step5/output/001_Superconductivity_and_nematic_order_in/results/PAPER_01_TASK_02_figure.png")
analysis_path = Path(r"C:/UCLEAP/UC_LEAP/step5/output/001_Superconductivity_and_nematic_order_in/results/PAPER_01_TASK_02_Analysis.txt")

# Ensure output directory exists
figure_path.parent.mkdir(parents=True, exist_ok=True)

analysis_lines = []
analysis_lines.append("Task PAPER_01_TASK_02 Analysis")
analysis_lines.append("=" * 40)
analysis_lines.append(f"Dataset file: {dataset_path}")
analysis_lines.append("")

# Step 0: Inspect workbook structure
analysis_lines.append("Step 0: Inspect workbook structure")
if not dataset_path.exists():
    analysis_lines.append("ERROR: Dataset file does not exist. Task cannot be completed.")
    analysis_text = "\n".join(analysis_lines)
    analysis_path.write_text(analysis_text, encoding="utf-8")
    raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

try:
    xls = pd.ExcelFile(dataset_path)
    sheet_names = xls.sheet_names
    analysis_lines.append(f"Workbook sheets: {sheet_names}")
    df_raw = pd.read_excel(dataset_path, sheet_name=sheet_names[0], header=None)
    analysis_lines.append(f"Loaded sheet '{sheet_names[0]}' with shape {df_raw.shape[0]} rows x {df_raw.shape[1]} cols")
except Exception as e:
    analysis_lines.append(f"ERROR: Failed to load workbook: {e}")
    analysis_text = "\n".join(analysis_lines)
    analysis_path.write_text(analysis_text, encoding="utf-8")
    raise

# Inspect first rows for structure
preview_rows = min(8, len(df_raw))
analysis_lines.append("Top rows preview:")
for i in range(preview_rows):
    row_vals = df_raw.iloc[i].tolist()
    analysis_lines.append(f"Row {i}: {row_vals}")

# Step 1: Parse paired columns
analysis_lines.append("")
analysis_lines.append("Step 1: Parse temperature and M traces")
header_row_0 = df_raw.iloc[0].tolist()
header_row_1 = df_raw.iloc[1].tolist()

pairs = []
col = 0
while col < df_raw.shape[1] - 1:
    temp_header = str(header_row_0[col]).strip() if pd.notna(header_row_0[col]) else ""
    m_header = str(header_row_0[col + 1]).strip() if pd.notna(header_row_0[col + 1]) else ""
    field_label = str(header_row_1[col + 1]).strip() if pd.notna(header_row_1[col + 1]) else ""
    if "Temperature" in temp_header and m_header == "M":
        pairs.append((col, col + 1, field_label))
        col += 2
    else:
        col += 1

analysis_lines.append(f"Identified {len(pairs)} paired temperature/M traces.")
if not pairs:
    analysis_lines.append("ERROR: No valid paired columns found. Cannot plot traces.")
    analysis_text = "\n".join(analysis_lines)
    analysis_path.write_text(analysis_text, encoding="utf-8")
    raise ValueError("No valid paired columns found.")

# Parse data rows
traces = []
for temp_col, m_col, field_label in pairs:
    temp_series = pd.to_numeric(df_raw.iloc[2:, temp_col], errors="coerce")
    m_series = pd.to_numeric(df_raw.iloc[2:, m_col], errors="coerce")
    valid = temp_series.notna() & m_series.notna()
    temp_vals = temp_series[valid].to_numpy()
    m_vals = m_series[valid].to_numpy()
    if len(temp_vals) == 0:
        analysis_lines.append(f"Field '{field_label}': no valid numeric data after parsing; excluded.")
        continue
    traces.append({
        "field": field_label if field_label else f"Cols {temp_col}-{m_col}",
        "temperature": temp_vals,
        "m": m_vals
    })
    analysis_lines.append(
        f"Field '{field_label}': parsed {len(temp_vals)} points, "
        f"T range {temp_vals.min():.6g} to {temp_vals.max():.6g} K, "
        f"M range {m_vals.min():.6g} to {m_vals.max():.6g}"
    )

if not traces:
    analysis_lines.append("ERROR: No traces with valid numeric data were found.")
    analysis_text = "\n".join(analysis_lines)
    analysis_path.write_text(analysis_text, encoding="utf-8")
    raise ValueError("No valid traces found.")

# Sort traces by field label if possible
def field_sort_key(label):
    match = re.search(r"(\d+)\s*Oe", label)
    if match:
        return int(match.group(1))
    return 10**9

traces = sorted(traces, key=lambda d: field_sort_key(d["field"]))

analysis_lines.append("")
analysis_lines.append("Step 2: Validate traces for plotting")
for tr in traces:
    t = tr["temperature"]
    m = tr["m"]
    monotonic = bool((pd.Series(t).diff().dropna() >= 0).all() or (pd.Series(t).diff().dropna() <= 0).all())
    analysis_lines.append(
        f"Field '{tr['field']}': monotonic temperature axis = {monotonic}; "
        f"first T={t[0]:.6g}, last T={t[-1]:.6g}"
    )

# Step 3: Plot
analysis_lines.append("")
analysis_lines.append("Step 3: Generate multi-curve susceptibility-versus-temperature plot")
plt.style.use("default")
fig, ax = plt.subplots(figsize=(7.2, 5.4), dpi=300)

colors = plt.cm.viridis([i / max(1, len(traces) - 1) for i in range(len(traces))])

for idx, tr in enumerate(traces):
    ax.plot(
        tr["temperature"],
        tr["m"],
        lw=1.8,
        color=colors[idx],
        label=tr["field"]
    )

ax.set_xlabel("Temperature (K)", fontsize=12)
ax.set_ylabel("M", fontsize=12)
ax.tick_params(axis="both", labelsize=10)
ax.legend(title="Applied field", fontsize=9, title_fontsize=9, frameon=False, loc="best")
ax.grid(False)

# Match a clean superconducting transition figure layout
for spine in ax.spines.values():
    spine.set_linewidth(1.0)

fig.tight_layout()

# Step 4: Save figure
analysis_lines.append("")
analysis_lines.append("Step 4: Save outputs")
try:
    fig.savefig(figure_path, bbox_inches="tight")
    analysis_lines.append(f"Figure saved to: {figure_path}")
except Exception as e:
    analysis_lines.append(f"ERROR: Failed to save figure: {e}")
    analysis_text = "\n".join(analysis_lines)
    analysis_path.write_text(analysis_text, encoding="utf-8")
    raise

# Save analysis
analysis_text = "\n".join(analysis_lines)
analysis_path.write_text(analysis_text, encoding="utf-8")

print(f"Saved figure to: {figure_path}")
print(f"Saved analysis to: {analysis_path}")