import os
import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/005_Proximityinduced_chiral_quantum_light_generation/type1_data/41563_2023_1645_MOESM8_ESM_10.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/005_Proximityinduced_chiral_quantum_light_generation/results/PAPER_05_TASK_12_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/005_Proximityinduced_chiral_quantum_light_generation/results/PAPER_05_TASK_12_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)
os.makedirs(os.path.dirname(analysis_path), exist_ok=True)

analysis_lines = []
analysis_lines.append("Task PAPER_05_TASK_12 Analysis")
analysis_lines.append("Objective: Replot the second-order photon correlation g(2)(τ) trace from the workbook.")
analysis_lines.append("")

# Step 0: inspect workbook structure
analysis_lines.append("Step 0: Inspect workbook structure and identify the correlation sheet.")
analysis_lines.append(f"Loaded dataset file: {dataset_file}")

xls = pd.ExcelFile(dataset_file)
sheet_names = xls.sheet_names
analysis_lines.append(f"Workbook sheets found: {sheet_names}")

# Read sheets for inspection
sheet_data = {}
for sh in sheet_names:
    df = pd.read_excel(dataset_file, sheet_name=sh, header=None)
    sheet_data[sh] = df
    analysis_lines.append(f"Sheet '{sh}' shape: {df.shape[0]} rows x {df.shape[1]} cols")
    preview_rows = min(5, len(df))
    for i in range(preview_rows):
        row = df.iloc[i].tolist()
        analysis_lines.append(f"  Row {i}: {row}")

analysis_lines.append("")
analysis_lines.append("Interpretation:")
analysis_lines.append("The sheet 'ED Fig 4c' contains columns labeled 'Pix', 'Pak1', 'P2', 'P3', 'P4', 'P5', 'FitPix', and fitted peak columns.")
analysis_lines.append("This structure is consistent with a multi-peak spectral calibration table, not a time-delay correlation trace.")
analysis_lines.append("The sheet 'ED Fig 4a' contains only two columns: 'Energy' and 'DCP', which is a polarization-related dataset, not a g(2)(τ) correlation trace.")
analysis_lines.append("No sheet in the workbook previewed here contains explicit time-delay, coincidence, normalized counts, or g(2)(τ) labels.")
analysis_lines.append("")

# Attempt to identify a correlation-like sheet by column names
correlation_sheet = None
for sh, df in sheet_data.items():
    header = [str(x).strip().lower() for x in df.iloc[0].tolist()]
    joined = " | ".join(header)
    if any(k in joined for k in ["delay", "tau", "g(2)", "g2", "coincidence", "count", "normalized"]):
        correlation_sheet = sh
        break

if correlation_sheet is None:
    analysis_lines.append("Step 0 conclusion:")
    analysis_lines.append("No correlation sheet with time-delay or coincidence data could be identified from the workbook structure.")
    analysis_lines.append("Because the required g(2)(τ) variables are absent, a defensible replot of the second-order correlation trace cannot be produced from this file.")
    analysis_lines.append("")

    # Create a clear placeholder figure explaining limitation
    fig, ax = plt.subplots(figsize=(8.5, 5.5), dpi=200)
    ax.axis("off")
    msg = (
        "No g(2)(τ) correlation data found in workbook.\n\n"
        "Sheets inspected:\n"
        f"{', '.join(sheet_names)}\n\n"
        "Available sheets appear to contain:\n"
        "- ED Fig 4a: Energy vs DCP\n"
        "- ED Fig 4c: Peak-position / fit table\n\n"
        "Without time-delay and coincidence/count data,\n"
        "a publication-quality g(2)(τ) replot cannot be generated."
    )
    ax.text(0.5, 0.5, msg, ha="center", va="center", fontsize=12, wrap=True)
    plt.tight_layout()
    plt.savefig(figure_path, bbox_inches="tight")
    plt.close(fig)

    analysis_lines.append("Step 1: Plotting was not performed because no valid delay/count dataset was available.")
    analysis_lines.append("Step 2: No normalization or background correction could be applied because no correlation trace exists in the workbook.")
    analysis_lines.append("Step 3: No antibunching dip or fit annotation could be added because the required data are missing.")
    analysis_lines.append("")
    analysis_lines.append("Final conclusion:")
    analysis_lines.append("The workbook does not contain the data needed to reconstruct the second-order photon correlation g(2)(τ) trace.")
else:
    # If a correlation sheet is found, parse it robustly
    df = sheet_data[correlation_sheet].copy()
    header = df.iloc[0].tolist()
    df = df.iloc[1:].reset_index(drop=True)
    df.columns = header

    analysis_lines.append(f"Correlation sheet identified: {correlation_sheet}")
    analysis_lines.append(f"Columns: {list(df.columns)}")

    # Try to infer delay and count columns
    cols_lower = {str(c).strip().lower(): c for c in df.columns}
    delay_col = None
    count_col = None
    norm_col = None
    fit_col = None

    for key in cols_lower:
        if delay_col is None and any(k in key for k in ["delay", "tau", "time"]):
            delay_col = cols_lower[key]
        if count_col is None and any(k in key for k in ["count", "coincidence", "cts", "intensity"]):
            count_col = cols_lower[key]
        if norm_col is None and any(k in key for k in ["g(2)", "g2", "normalized", "norm"]):
            norm_col = cols_lower[key]
        if fit_col is None and "fit" in key:
            fit_col = cols_lower[key]

    # Fallback: use first two numeric columns
    numeric_cols = []
    for c in df.columns:
        s = pd.to_numeric(df[c], errors="coerce")
        if s.notna().sum() > 0:
            numeric_cols.append(c)

    if delay_col is None and len(numeric_cols) >= 1:
        delay_col = numeric_cols[0]
    if count_col is None and len(numeric_cols) >= 2:
        count_col = numeric_cols[1]
    if norm_col is None and len(numeric_cols) >= 3:
        norm_col = numeric_cols[2]

    analysis_lines.append(f"Inferred delay column: {delay_col}")
    analysis_lines.append(f"Inferred count column: {count_col}")
    analysis_lines.append(f"Inferred normalized/fit column: {norm_col if norm_col is not None else 'None'}")

    delay = pd.to_numeric(df[delay_col], errors="coerce").to_numpy()
    counts = pd.to_numeric(df[count_col], errors="coerce").to_numpy()

    valid = np.isfinite(delay) & np.isfinite(counts)
    delay = delay[valid]
    counts = counts[valid]

    analysis_lines.append(f"Valid numeric points retained: {len(delay)}")

    # Sort by delay
    order = np.argsort(delay)
    delay = delay[order]
    counts = counts[order]

    # Center around zero if applicable by using symmetric delay axis if data appear offset
    # If a fit/normalized column exists, use it as the plotted trace when appropriate.
    y = counts.copy()
    y_label = "Counts"
    if norm_col is not None:
        norm_vals = pd.to_numeric(df[norm_col], errors="coerce").to_numpy()[valid][order]
        if np.isfinite(norm_vals).sum() > 0:
            y = norm_vals
            y_label = str(norm_col)

    # Basic normalization if values are clearly count-like and not already normalized
    if y_label == "Counts":
        if np.nanmax(y) > 0:
            y = y / np.nanmax(y)
            y_label = "Normalized counts (scaled to max = 1)"

    # Determine if zero delay is present or if axis should be centered
    zero_present = np.any(np.isclose(delay, 0, atol=max(1e-12, 1e-6 * np.nanmax(np.abs(delay)))))
    analysis_lines.append(f"Zero delay present in data: {zero_present}")

    # Identify central antibunching dip only if supported by local minimum near zero
    dip_idx = None
    if len(delay) >= 3:
        near_zero = np.argsort(np.abs(delay))[:max(3, min(11, len(delay)))]
        local_min_idx = near_zero[np.argmin(y[near_zero])]
        dip_idx = int(local_min_idx)
        analysis_lines.append(f"Candidate central dip at delay = {delay[dip_idx]:.6g}, value = {y[dip_idx]:.6g}")
    else:
        analysis_lines.append("Insufficient points to identify a central dip reliably.")

    # Plot
    fig, ax = plt.subplots(figsize=(7.2, 5.0), dpi=300)
    ax.plot(delay, y, color="#1f77b4", lw=1.8, label="g(2)(τ) trace")

    if dip_idx is not None:
        ax.scatter([delay[dip_idx]], [y[dip_idx]], color="crimson", s=35, zorder=5, label="Central dip")
        ax.annotate(
            f"dip: {y[dip_idx]:.3f} at τ={delay[dip_idx]:.3g}",
            xy=(delay[dip_idx], y[dip_idx]),
            xytext=(10, 12),
            textcoords="offset points",
            fontsize=9,
            color="crimson",
            arrowprops=dict(arrowstyle="->", color="crimson", lw=1),
        )

    ax.axvline(0, color="black", lw=1.0, ls="--", alpha=0.7)
    ax.axhline(1.0 if np.nanmax(y) <= 2.5 else np.nanmean(y), color="gray", lw=0.8, ls=":", alpha=0.7)

    ax.set_xlabel("Delay τ")
    ax.set_ylabel(y_label)
    ax.set_title("Second-order photon correlation g(2)(τ)")
    ax.legend(frameon=False, loc="best")
    ax.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(figure_path, bbox_inches="tight")
    plt.close(fig)

    analysis_lines.append("Step 1: Correlation trace plotted versus delay.")
    analysis_lines.append("Step 2: If a normalized column was available, it was used directly; otherwise counts were scaled to the maximum for a relative trace.")
    analysis_lines.append("Step 3: The central dip was annotated only as a candidate local minimum near zero delay, without fitting unsupported parameters.")
    analysis_lines.append("Final conclusion: A g(2)(τ) plot was generated from the identified correlation-like sheet.")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure to: {figure_path}")
print(f"Saved analysis to: {analysis_path}")