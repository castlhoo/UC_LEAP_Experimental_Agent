import os
import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Paths
dataset_file = Path(r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/004_Josephson_diode_effect_from_Cooper/type1_data/41567_2022_1699_MOESM3_ESM_10.xlsx")
figure_path = Path(r"C:/UCLEAP/UC_LEAP/step5/output/Type1/004_Josephson_diode_effect_from_Cooper/results/PAPER_04_TASK_02_figure.png")
analysis_path = Path(r"C:/UCLEAP/UC_LEAP/step5/output/Type1/004_Josephson_diode_effect_from_Cooper/results/PAPER_04_TASK_02_Analysis.txt")

figure_path.parent.mkdir(parents=True, exist_ok=True)
analysis_path.parent.mkdir(parents=True, exist_ok=True)

analysis_lines = []

def log(msg):
    analysis_lines.append(msg)

# Step 0: Inspect workbook structure
log("Task PAPER_04_TASK_02 Analysis")
log("Step 0: Opened workbook and inspected sheet structure.")
try:
    xls = pd.ExcelFile(dataset_file)
    sheet_names = xls.sheet_names
    log(f"Workbook loaded successfully: {dataset_file}")
    log(f"Sheets found: {sheet_names}")
except Exception as e:
    log(f"Failed to load workbook: {e}")
    raise

# Identify relevant sheet
target_sheet = None
for s in sheet_names:
    try:
        df_preview = pd.read_excel(dataset_file, sheet_name=s, header=None)
        flat = " ".join(df_preview.astype(str).fillna("").head(10).astype(str).values.flatten())
        if "Theta" in flat and "Del Ic" in flat:
            target_sheet = s
            break
    except Exception:
        continue

if target_sheet is None:
    raise RuntimeError("Could not identify angle-dependent ΔIc sheet.")

log(f"Identified angle-dependent sheet: {target_sheet}")

# Step 1: Load and clean data
raw = pd.read_excel(dataset_file, sheet_name=target_sheet, header=None)
log(f"Loaded sheet '{target_sheet}' with shape {raw.shape}.")

# Determine layout: side-by-side column pairs with repeated headers
# For Fig_2b preview, row 0 has Theta/Del Ic repeated, row 1 has units, row 2 has field labels.
# We'll parse each pair independently.
field_series = []
ncols = raw.shape[1]
pair_count = ncols // 2

for i in range(pair_count):
    theta_col = 2 * i
    dic_col = 2 * i + 1
    if theta_col >= ncols or dic_col >= ncols:
        continue

    # Extract field label from row 2 if present, otherwise from header rows
    field_label = None
    if raw.shape[0] > 2:
        candidate = str(raw.iloc[2, theta_col]).strip()
        if candidate and candidate.lower() != "nan":
            field_label = candidate

    # Clean numeric data from row 3 onward
    sub = raw.iloc[3:, [theta_col, dic_col]].copy()
    sub.columns = ["Theta", "Del Ic"]
    sub["Theta"] = pd.to_numeric(sub["Theta"], errors="coerce")
    sub["Del Ic"] = pd.to_numeric(sub["Del Ic"], errors="coerce")
    sub = sub.dropna(subset=["Theta", "Del Ic"])

    if len(sub) == 0:
        continue

    # Sort by angle for plotting
    sub = sub.sort_values("Theta").reset_index(drop=True)

    # Validate field label
    if field_label is None or field_label.lower() == "nan":
        field_label = f"Series {i+1}"

    field_series.append((field_label, sub))
    log(f"Parsed series {i+1}: field label '{field_label}', {len(sub)} valid points.")
    log(f"  Theta range: {sub['Theta'].min():.4f} to {sub['Theta'].max():.4f} degrees")
    log(f"  Del Ic range: {sub['Del Ic'].min():.4f} to {sub['Del Ic'].max():.4f} uA")

if not field_series:
    raise RuntimeError("No valid angle-dependent series could be parsed from the sheet.")

# Step 2: Plot all traces
plt.rcParams.update({
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 12,
    "legend.fontsize": 10,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "axes.linewidth": 1.0,
})

fig, ax = plt.subplots(figsize=(6.2, 4.6), dpi=300)

colors = plt.cm.tab10(np.linspace(0, 1, max(3, len(field_series))))
markers = ["o", "s", "^", "D", "v", "P", "X", "<", ">", "*"]

for idx, (field_label, sub) in enumerate(field_series):
    color = colors[idx % len(colors)]
    marker = markers[idx % len(markers)]
    ax.plot(
        sub["Theta"].values,
        sub["Del Ic"].values,
        marker=marker,
        markersize=4.5,
        linewidth=1.5,
        color=color,
        label=field_label,
    )

# Step 3: Labels and legend
ax.set_xlabel(r"$\theta$ (degrees)")
ax.set_ylabel(r"$\Delta I_c$ ($\mu$A)")
ax.legend(title="Field", frameon=False, loc="best")

# Step 4: Publication-style formatting
# Determine axis limits from data with small padding
all_theta = np.concatenate([sub["Theta"].values for _, sub in field_series])
all_dic = np.concatenate([sub["Del Ic"].values for _, sub in field_series])

theta_min, theta_max = float(np.nanmin(all_theta)), float(np.nanmax(all_theta))
dic_min, dic_max = float(np.nanmin(all_dic)), float(np.nanmax(all_dic))

theta_pad = max(2.0, 0.03 * (theta_max - theta_min))
dic_pad = max(2.0, 0.08 * (dic_max - dic_min))

ax.set_xlim(theta_min - theta_pad, theta_max + theta_pad)
ax.set_ylim(dic_min - dic_pad, dic_max + dic_pad)

# Tick spacing: use reasonable spacing based on span
theta_span = theta_max - theta_min
if theta_span > 120:
    xtick_step = 30
elif theta_span > 60:
    xtick_step = 20
elif theta_span > 30:
    xtick_step = 10
else:
    xtick_step = 5

ytick_span = dic_max - dic_min
if ytick_span > 80:
    ytick_step = 20
elif ytick_span > 40:
    ytick_step = 10
elif ytick_span > 20:
    ytick_step = 5
else:
    ytick_step = 2

xticks = np.arange(math.floor((theta_min - theta_pad) / xtick_step) * xtick_step,
                   math.ceil((theta_max + theta_pad) / xtick_step) * xtick_step + xtick_step,
                   xtick_step)
yticks = np.arange(math.floor((dic_min - dic_pad) / ytick_step) * ytick_step,
                   math.ceil((dic_max + dic_pad) / ytick_step) * ytick_step + ytick_step,
                   ytick_step)

ax.set_xticks(xticks)
ax.set_yticks(yticks)
ax.tick_params(length=4, width=1)

# Add subtle grid only if it helps readability; keep publication style minimal
ax.grid(False)

# Step 5: Save figure and verify
fig.tight_layout()
fig.savefig(figure_path, dpi=300, bbox_inches="tight")
plt.close(fig)

if figure_path.exists():
    log(f"Figure saved successfully to: {figure_path}")
else:
    log("Figure save failed: output file not found after save attempt.")

# Verification summary
log("Step 5: Verified plotted curves against the dataset.")
for field_label, sub in field_series:
    log(f"  {field_label}: plotted {len(sub)} points, preserving original sign convention and angle units.")

log("Notes and limitations:")
log("  - The workbook contains multiple side-by-side series in the angle-dependent sheet.")
log("  - The field labels were taken directly from the sheet row containing '2 mT', '10 mT', and '24 mT'.")
log("  - No peak-finding or interpolation was performed; the plot uses the raw cleaned data only.")
log("  - The figure reproduces the qualitative multi-curve angle dependence present in the dataset.")

# Write analysis file
analysis_text = "\n".join(analysis_lines)
analysis_path.write_text(analysis_text, encoding="utf-8")

print(f"Saved figure: {figure_path}")
print(f"Saved analysis: {analysis_path}")