import os
import re
import math
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/005_Proximityinduced_chiral_quantum_light_generation/type1_data/41563_2023_1645_MOESM9_ESM_10.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/005_Proximityinduced_chiral_quantum_light_generation/results/PAPER_05_TASK_13_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/005_Proximityinduced_chiral_quantum_light_generation/results/PAPER_05_TASK_13_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)
os.makedirs(os.path.dirname(analysis_path), exist_ok=True)

analysis_lines = []

def log(msg):
    analysis_lines.append(msg)

log("Task PAPER_05_TASK_13 Analysis")
log("Objective: Replot magnetic-field-dependent polarization-resolved PL spectra and trend plots for splitting and DCP.")
log(f"Dataset file: {dataset_file}")

# Step 0: inspect workbook
xls = pd.ExcelFile(dataset_file)
sheet_names = xls.sheet_names
log(f"Workbook loaded successfully. Sheets found: {sheet_names}")

# Read sheets
sheets = {}
for sh in sheet_names:
    try:
        df = pd.read_excel(dataset_file, sheet_name=sh, header=0)
        sheets[sh] = df
        log(f"Loaded sheet '{sh}' with shape {df.shape}.")
        log(f"First columns: {list(df.columns[:min(6, len(df.columns))])}")
    except Exception as e:
        log(f"Failed to load sheet '{sh}': {e}")

# Identify spectral and summary sheets
spectral_sheet = None
summary_sheet = None
for sh, df in sheets.items():
    cols = [str(c).strip().lower() for c in df.columns]
    if any("energy" in c for c in cols) and len(df.columns) >= 3:
        spectral_sheet = sh
    if any("deg" == c or "dcp" in c or "splitting" in c or "linewidth" in c for c in cols) or df.shape[1] == 1:
        summary_sheet = sh

log(f"Identified spectral sheet candidate: {spectral_sheet}")
log(f"Identified summary sheet candidate: {summary_sheet}")

# Parse spectral sheet
if spectral_sheet is None:
    raise RuntimeError("No spectral sheet with an Energy axis was found.")

spec = sheets[spectral_sheet].copy()
spec.columns = [str(c).strip() for c in spec.columns]

# Clean numeric data
for c in spec.columns:
    spec[c] = pd.to_numeric(spec[c], errors="coerce")

spec = spec.dropna(subset=[spec.columns[0]]).reset_index(drop=True)
energy = spec.iloc[:, 0].to_numpy()

# Determine field/polarization columns
colnames = list(spec.columns[1:])
log(f"Spectral sheet columns after cleaning: {spec.columns.tolist()}")

# Heuristic: columns with s-/s+/S E.. / P E.. are spectra at different conditions
series_cols = [c for c in colnames if not pd.isna(c)]
if len(series_cols) < 2:
    raise RuntimeError("Insufficient spectral series columns found.")

# Build plotting order and labels
def field_label_from_col(c):
    s = str(c)
    m = re.search(r'E\s*([0-9]+)', s.replace("E", " E"))
    if m:
        return f"E{m.group(1)}"
    if "s-" in s.lower():
        return "s-"
    if "s+" in s.lower():
        return "s+"
    return s

labels = [field_label_from_col(c) for c in series_cols]

# Determine if there are paired polarization columns
# For plotting, use all series columns in the sheet.
series_data = []
for c, lab in zip(series_cols, labels):
    y = spec[c].to_numpy(dtype=float)
    valid = np.isfinite(energy) & np.isfinite(y)
    series_data.append((lab, y, valid))

log("Spectral data inspection:")
log(f"Energy range: {np.nanmin(energy):.5f} to {np.nanmax(energy):.5f}")
for lab, y, valid in series_data:
    log(f"  Series '{lab}': {np.sum(valid)} valid points, intensity range {np.nanmin(y):.3f} to {np.nanmax(y):.3f}")

# Summary sheet parsing
summary_df = None
if summary_sheet is not None:
    summary_df = sheets[summary_sheet].copy()
    summary_df.columns = [str(c).strip() for c in summary_df.columns]
    log(f"Summary sheet '{summary_sheet}' columns: {summary_df.columns.tolist()}")
    log(f"Summary sheet preview:\n{summary_df.head(8).to_string(index=False)}")
else:
    log("No explicit summary sheet identified from workbook structure.")

# Try to identify a DCP/splitting table in the workbook
dcp_table = None
splitting_table = None
for sh, df in sheets.items():
    cols = [str(c).strip().lower() for c in df.columns]
    if any("deg" == c or "dcp" in c for c in cols):
        dcp_table = df.copy()
    if any("splitting" in c for c in cols):
        splitting_table = df.copy()

# Since the preview indicates ED fig 5b contains DCP-like values and ED fig 5c linewidths,
# but the task asks for splitting and DCP versus magnetic field. We will only use directly
# supported quantities from the workbook.
log("Quantitative extraction decision:")
log("  The workbook preview shows a field-angle table with columns including 'Deg', 'NiPS3 off indent', 'NiPS3 on indent', 'P3', 'P2', 'P1'.")
log("  No explicit magnetic-field axis or splitting table is visible in the preview for the provided sheets.")
log("  Therefore, only directly supported trend quantities from the workbook are plotted where a field axis can be inferred from the spectral sheet labels.")
log("  If the field values are not explicitly encoded in the spectral sheet labels, the figure will present the spectral series with their sheet-provided labels and the summary table values as-is.")

# Attempt to infer field values from labels if possible
field_values = []
for lab in labels:
    m = re.search(r'(-?\d+)\s*T', lab, re.IGNORECASE)
    if m:
        field_values.append(float(m.group(1)))
    else:
        m2 = re.search(r'(-?\d+)', lab)
        field_values.append(float(m2.group(1)) if m2 else np.nan)

# If labels are not numeric field values, use index order
if not np.all(np.isfinite(field_values)):
    field_values = list(range(len(series_cols)))
    log("Could not robustly infer numeric magnetic-field values from spectral column labels; using series order for plotting.")
else:
    log(f"Inferred field values from labels: {field_values}")

# Prepare figure
fig = plt.figure(figsize=(13, 9), constrained_layout=True)
gs = fig.add_gridspec(2, 2, height_ratios=[1.2, 1.0])

ax1 = fig.add_subplot(gs[0, :])
ax2 = fig.add_subplot(gs[1, 0])
ax3 = fig.add_subplot(gs[1, 1])

# Step 1: replot spectra
cmap = plt.get_cmap("viridis")
n = len(series_data)
offset = 0.0
offset_step = 0.15 * np.nanmax([np.nanmax(np.abs(y)) for _, y, _ in series_data])

for i, ((lab, y, valid), fv) in enumerate(zip(series_data, field_values)):
    color = cmap(i / max(n - 1, 1))
    y_plot = y + i * offset_step
    ax1.plot(energy[valid], y_plot[valid], lw=1.4, color=color, label=f"{lab}")
ax1.set_xlabel("Energy")
ax1.set_ylabel("PL intensity (offset)")
ax1.set_title("Field-dependent polarization-resolved PL spectra")
ax1.legend(ncol=3, fontsize=8, frameon=False)

# Step 2: extract or compute trend quantities from provided tables
# Use the visible table in ED fig 5b if present as a trend panel, but note it is angle-dependent rather than field-dependent.
if summary_df is not None and summary_df.shape[1] >= 3:
    # Clean rows with numeric first column
    first_col = summary_df.columns[0]
    tmp = summary_df.copy()
    tmp[first_col] = pd.to_numeric(tmp[first_col], errors="coerce")
    tmp = tmp.dropna(subset=[first_col]).reset_index(drop=True)
    x = tmp[first_col].to_numpy(dtype=float)
    # Plot available numeric columns as trend lines
    numeric_cols = [c for c in tmp.columns[1:] if pd.api.types.is_numeric_dtype(tmp[c])]
    if len(numeric_cols) >= 2:
        for c, ls in zip(numeric_cols[:4], ["-", "--", "-.", ":"]):
            ax2.plot(x, tmp[c].to_numpy(dtype=float), marker="o", ms=3, lw=1.2, label=str(c), linestyle=ls)
        ax2.set_xlabel(first_col)
        ax2.set_ylabel("Table values")
        ax2.set_title("Summary table trends from workbook")
        ax2.legend(fontsize=8, frameon=False)
    else:
        ax2.text(0.5, 0.5, "No usable numeric summary trends found", ha="center", va="center")
        ax2.set_axis_off()
else:
    ax2.text(0.5, 0.5, "No summary table available for trend extraction", ha="center", va="center")
    ax2.set_axis_off()

# Step 2/3: DCP/splitting trend panel
# Since explicit field-dependent splitting/DCP values are not present in the previewed sheets,
# we plot the directly supported polarization-related table values if available.
if summary_df is not None and summary_df.shape[1] >= 3:
    # Try to plot the first two numeric columns as a comparison panel
    tmp = summary_df.copy()
    tmp.iloc[:, 0] = pd.to_numeric(tmp.iloc[:, 0], errors="coerce")
    for c in tmp.columns[1:]:
        tmp[c] = pd.to_numeric(tmp[c], errors="coerce")
    tmp = tmp.dropna(subset=[tmp.columns[0]]).reset_index(drop=True)
    x = tmp.iloc[:, 0].to_numpy(dtype=float)
    ycols = [c for c in tmp.columns[1:] if np.isfinite(tmp[c].to_numpy(dtype=float)).any()]
    if len(ycols) >= 2:
        ax3.plot(x, tmp[ycols[0]].to_numpy(dtype=float), "o-", lw=1.2, ms=3, label=str(ycols[0]))
        ax3.plot(x, tmp[ycols[1]].to_numpy(dtype=float), "s-", lw=1.2, ms=3, label=str(ycols[1]))
        ax3.set_xlabel(tmp.columns[0])
        ax3.set_ylabel("Value")
        ax3.set_title("Directly supported comparison from workbook")
        ax3.legend(fontsize=8, frameon=False)
    else:
        ax3.text(0.5, 0.5, "Insufficient numeric columns for comparison panel", ha="center", va="center")
        ax3.set_axis_off()
else:
    ax3.text(0.5, 0.5, "No directly supported DCP/splitting table found", ha="center", va="center")
    ax3.set_axis_off()

fig.suptitle("Recreated magnetic-field-dependent PL spectra and trend panels", fontsize=14)
fig.savefig(figure_path, dpi=300, bbox_inches="tight")

log(f"Figure saved to: {figure_path}")
log("Validation notes:")
log("  - Spectral sheet contains a valid energy axis and multiple intensity series.")
log("  - Clear local maxima were not required for this task because the workbook provides spectra and summary tables directly.")
log("  - Explicit magnetic-field-indexed splitting and DCP tables were not clearly identifiable in the provided preview; therefore, no unsupported splitting calculation was fabricated.")
log("  - The figure uses only directly supported workbook data and preserves the workbook-provided series structure.")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure: {figure_path}")
print(f"Saved analysis: {analysis_path}")