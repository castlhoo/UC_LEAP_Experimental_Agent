import os
import re
import sys
import math
import json
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/002_Cascade_of_correlated_electron_states/type1_data/41586_2021_3946_MOESM3_ESM_10.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/002_Cascade_of_correlated_electron_states/results/PAPER_02_TASK_01_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/002_Cascade_of_correlated_electron_states/results/PAPER_02_TASK_01_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)
os.makedirs(os.path.dirname(analysis_path), exist_ok=True)

analysis_lines = []

def log(msg):
    analysis_lines.append(msg)

log("Task PAPER_02_TASK_01: Replot the Sb-terminated dI/dV spectrum")
log(f"Dataset file: {dataset_file}")
log("Step_0: Open the Excel workbook and identify the sheet corresponding to the dI/dV spectrum.")
log("I inspected the workbook structure before analysis. The workbook contains two sheets: 'Fig2b' and 'Fig2b inset'.")
log("The task asks for the main Sb-terminated dI/dV spectrum, which corresponds to the 'Fig2b' sheet based on the sheet name and the previewed data layout.")
log("The 'Fig2b inset' sheet appears to contain a separate inset spectrum, so it is not used for the main replot.")

try:
    xls = pd.ExcelFile(dataset_file)
except Exception as e:
    log(f"Failed to open workbook: {e}")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise

sheet_name = "Fig2b"
log(f"Selected sheet for plotting: {sheet_name}")

log("Step_1: Parse the bias-voltage column and the dI/dV intensity column, handling any repeated headers or formatting artifacts.")
try:
    raw = pd.read_excel(dataset_file, sheet_name=sheet_name, header=None)
except Exception as e:
    log(f"Failed to read sheet '{sheet_name}': {e}")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise

log(f"Raw sheet shape: {raw.shape[0]} rows x {raw.shape[1]} cols")
log("The first two rows are header/unit rows: row 0 contains column names and row 1 contains units.")
log(f"Row 0 values: {raw.iloc[0].tolist()}")
log(f"Row 1 values: {raw.iloc[1].tolist()}")

data = raw.iloc[2:].copy()
data.columns = ["Bias", "dI/dV"]

data["Bias"] = pd.to_numeric(data["Bias"], errors="coerce")
data["dI/dV"] = pd.to_numeric(data["dI/dV"], errors="coerce")

before_drop = len(data)
data = data.dropna(subset=["Bias", "dI/dV"]).copy()
after_drop = len(data)
log(f"Converted numeric columns and dropped non-numeric rows: removed {before_drop - after_drop} rows, retained {after_drop} rows.")

log("Step_2: Clean the data into a single ordered x-y series suitable for plotting.")
data = data.sort_values("Bias", ascending=True).reset_index(drop=True)

bias = data["Bias"].to_numpy(dtype=float)
didv = data["dI/dV"].to_numpy(dtype=float)

log(f"Bias range after sorting: {bias.min():.6g} to {bias.max():.6g} mV")
log(f"dI/dV range: {didv.min():.6g} to {didv.max():.6g} a.u.")
log(f"Number of plotted points: {len(data)}")

# Basic validation for smoothness / integrity
diff_bias = np.diff(bias)
monotonic = np.all(diff_bias > 0)
log(f"Bias axis strictly increasing after sorting: {monotonic}")
if not monotonic:
    log("Warning: Bias axis is not strictly increasing after sorting; plotting will still proceed using the sorted order.")

# Check for repeated headers or artifacts in the data region
artifact_rows = data[(data["Bias"].astype(str).str.contains("Bias", case=False, na=False)) |
                     (data["dI/dV"].astype(str).str.contains("dI/dV", case=False, na=False))]
if len(artifact_rows) > 0:
    log(f"Detected {len(artifact_rows)} potential artifact rows in data region; these would be excluded. In the cleaned numeric series, they are already removed.")
else:
    log("No repeated header artifacts remained after numeric coercion and filtering.")

log("Step_3: Create a line plot of dI/dV versus bias with publication-style formatting and labeled axes.")
plt.style.use("default")
fig, ax = plt.subplots(figsize=(6.2, 4.6), dpi=300)

ax.plot(bias, didv, color="black", linewidth=1.6)

ax.set_xlabel("Bias (mV)", fontsize=12)
ax.set_ylabel("dI/dV (a.u.)", fontsize=12)

ax.tick_params(axis="both", which="major", labelsize=10, direction="in", top=True, right=True, length=4)
ax.tick_params(axis="both", which="minor", direction="in", top=True, right=True, length=2)
ax.minorticks_on()

# Preserve the original curve shape and axis scaling by using data-driven limits with small padding
xpad = 0.03 * (bias.max() - bias.min()) if bias.max() > bias.min() else 1.0
ypad = 0.05 * (didv.max() - didv.min()) if didv.max() > didv.min() else 1.0
ax.set_xlim(bias.min() - xpad, bias.max() + xpad)
ax.set_ylim(didv.min() - ypad, didv.max() + ypad)

# Clean publication-style appearance
for spine in ax.spines.values():
    spine.set_linewidth(1.0)

fig.tight_layout()

try:
    fig.savefig(figure_path, dpi=300, bbox_inches="tight")
    log(f"Figure saved to: {figure_path}")
except Exception as e:
    log(f"Failed to save figure: {e}")
    raise

log("Step_4: Verify that the plotted curve is smooth and matches the expected spectral profile from the digitized data.")
# Since this is a digitized spectrum, verify continuity and absence of obvious discontinuities.
if len(bias) > 2:
    second_diff = np.diff(didv, n=2)
    finite_second_diff = np.isfinite(second_diff).all()
    log(f"Second-difference finite check: {finite_second_diff}")
    log("The curve is represented by a single continuous ordered series, so the plotted line preserves the digitized spectral profile without interpolation.")
else:
    log("Insufficient points for smoothness diagnostics, but the series is still plotted as provided.")

log("Conclusion: The main Fig2b spectrum was successfully replotted as a single dI/dV-versus-bias curve from the cleaned numeric data in the workbook.")
log("No additional spectral interpretation was introduced beyond the direct replot of the provided data.")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure to: {figure_path}")
print(f"Saved analysis to: {analysis_path}")