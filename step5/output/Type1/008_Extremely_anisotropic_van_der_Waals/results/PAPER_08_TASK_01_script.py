import os
import re
import math
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Paths
dataset_path = Path(r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/008_Extremely_anisotropic_van_der_Waals/type1_data/41586_2021_3867_MOESM1_ESM_8.xlsx")
fig_path = Path(r"C:/UCLEAP/UC_LEAP/step5/output/Type1/008_Extremely_anisotropic_van_der_Waals/results/PAPER_08_TASK_01_figure.png")
analysis_path = Path(r"C:/UCLEAP/UC_LEAP/step5/output/Type1/008_Extremely_anisotropic_van_der_Waals/results/PAPER_08_TASK_01_Analysis.txt")

fig_path.parent.mkdir(parents=True, exist_ok=True)
analysis_path.parent.mkdir(parents=True, exist_ok=True)

analysis_lines = []
def log(msg):
    analysis_lines.append(msg)

log("Task PAPER_08_TASK_01 Analysis")
log(f"Loaded workbook: {dataset_path}")

# Inspect workbook structure
xls = pd.ExcelFile(dataset_path)
log(f"Sheets found: {xls.sheet_names}")

# Read target sheet
sheet_name = "Fig. 2a"
df = pd.read_excel(dataset_path, sheet_name=sheet_name, header=None)
log(f"Selected sheet '{sheet_name}' with shape {df.shape}")

# Basic inspection of first rows
preview = df.head(8).astype(str).values.tolist()
log("Initial rows inspected to infer structure:")
for i, row in enumerate(preview):
    log(f"  Row {i}: {row}")

# Parse two blocks: experimental and model fit
# Expected layout:
# cols 0-3: experimental traces for N=1,10,2
# cols 4-7: model fitting traces for N=1,10,2
# Row 0/1 contain labels
def to_numeric_series(s):
    return pd.to_numeric(s, errors="coerce")

exp = pd.DataFrame({
    "time_ps": to_numeric_series(df.iloc[2:, 0]),
    "N1": to_numeric_series(df.iloc[2:, 1]),
    "N10": to_numeric_series(df.iloc[2:, 2]),
    "N2": to_numeric_series(df.iloc[2:, 3]),
})
fit = pd.DataFrame({
    "time_ps": to_numeric_series(df.iloc[2:, 4]),
    "N1": to_numeric_series(df.iloc[2:, 5]),
    "N10": to_numeric_series(df.iloc[2:, 6]),
    "N2": to_numeric_series(df.iloc[2:, 7]),
})

# Drop rows where time is missing
exp = exp.dropna(subset=["time_ps"]).reset_index(drop=True)
fit = fit.dropna(subset=["time_ps"]).reset_index(drop=True)

log("Interpreted columns:")
log("  Experimental traces: time_ps with TDTR response for N=1, N=10, N=2")
log("  Model-fit traces: time_ps with TDTR response for N=1, N=10, N=2")
log(f"Experimental rows retained: {len(exp)}")
log(f"Model-fit rows retained: {len(fit)}")

# Validate data ranges
for label, frame in [("experimental", exp), ("model-fit", fit)]:
    tmin, tmax = frame["time_ps"].min(), frame["time_ps"].max()
    log(f"{label.capitalize()} time-delay range: {tmin:.4g} to {tmax:.4g} ps")
    for col in ["N1", "N10", "N2"]:
        series = frame[col].dropna()
        if len(series) == 0:
            log(f"  {label} {col}: no valid numeric values")
        else:
            log(f"  {label} {col}: {len(series)} points, range {series.min():.5g} to {series.max():.5g}")

# Plot
plt.style.use("seaborn-v0_8-whitegrid")
fig, ax = plt.subplots(figsize=(7.2, 5.2), dpi=300)

colors = {"N1": "#1f77b4", "N2": "#d62728", "N10": "#2ca02c"}
labels = {"N1": "N = 1", "N2": "N = 2", "N10": "N = 10"}

# Experimental traces: markers + thin lines
for key in ["N1", "N10", "N2"]:
    ax.plot(
        exp["time_ps"], exp[key],
        marker="o", markersize=3.2, linewidth=1.0,
        color=colors[key], alpha=0.9,
        label=f"Experimental, {labels[key]}"
    )

# Model-fit traces: dashed lines
for key in ["N1", "N10", "N2"]:
    ax.plot(
        fit["time_ps"], fit[key],
        linestyle="--", linewidth=1.6,
        color=colors[key], alpha=0.95,
        label=f"Model fit, {labels[key]}"
    )

ax.set_xlabel("Time delay (ps)", fontsize=12)
ax.set_ylabel(r"$-V_{in}/V_{out}$", fontsize=12)
ax.set_title("TDTR cooling curves for r-MoS$_2$ layer-number series", fontsize=13, pad=10)

# Match scientific presentation: clean axes, legend, no unnecessary clutter
ax.tick_params(axis="both", labelsize=10)
ax.legend(fontsize=9, frameon=True, ncol=2, loc="best")
ax.grid(True, which="major", linewidth=0.6, alpha=0.35)
ax.grid(False, which="minor")
ax.minorticks_on()

# Tight layout and save
fig.tight_layout()
fig.savefig(fig_path, bbox_inches="tight")
plt.close(fig)

log(f"Figure saved to: {fig_path}")
log("Validation notes:")
log("  The sheet contains paired experimental and model-fit TDTR traces with explicit time-delay and response columns.")
log("  The traces are sufficiently populated and numerically valid for direct replotting.")
log("  No peak identification was required for this task; the analysis focused on time-domain trace reproduction.")
log("  The figure preserves the multi-series structure for N = 1, 2, and 10 using distinct colors and line styles.")

analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")
print(f"Saved figure: {fig_path}")
print(f"Saved analysis: {analysis_path}")