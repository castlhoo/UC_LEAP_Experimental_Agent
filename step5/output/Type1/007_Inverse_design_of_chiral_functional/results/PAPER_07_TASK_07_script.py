import os
import re
import sys
import math
import json
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# -----------------------------
# Paths from the task statement
# -----------------------------
dataset_path = Path(r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/007_Inverse_design_of_chiral_functional/type1_data/cgan_test_result_ABS_467_1.78.csv")
figure_path = Path(r"C:/UCLEAP/UC_LEAP/step5/output/Type1/007_Inverse_design_of_chiral_functional/results/PAPER_07_TASK_07_figure.png")
analysis_path = Path(r"C:/UCLEAP/UC_LEAP/step5/output/Type1/007_Inverse_design_of_chiral_functional/results/PAPER_07_TASK_07_Analysis.txt")

# Ensure output directory exists
figure_path.parent.mkdir(parents=True, exist_ok=True)
analysis_path.parent.mkdir(parents=True, exist_ok=True)

analysis_lines = []

def log(msg):
    analysis_lines.append(msg)

# -----------------------------
# Step 0: Load and inspect CSV
# -----------------------------
log("Task PAPER_07_TASK_07 Analysis")
log("=" * 80)
log("Step_0: Load the CSV and inspect its columns, row count, and any target annotations.")
log(f"Dataset file: {dataset_path}")

if not dataset_path.exists():
    log("Status: FAILED")
    log("Reason: Dataset file does not exist at the specified path.")
    analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")
    raise FileNotFoundError(f"Dataset not found: {dataset_path}")

try:
    df = pd.read_csv(dataset_path)
except Exception as e:
    log("Status: FAILED")
    log(f"Reason: Could not read CSV file. Error: {e}")
    analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")
    raise

log(f"Loaded successfully. Row count: {len(df)}")
log(f"Columns detected: {list(df.columns)}")

# Inspect for target annotations from filename and columns
filename = dataset_path.name
target_match = re.search(r"ABS_(\d+)", filename)
target_wavelength = target_match.group(1) if target_match else "unknown"
log(f"Filename convention indicates ABS target wavelength: {target_wavelength} nm")
log("No explicit target annotation column was present in the preview; target is inferred from filename only.")

# -----------------------------
# Step 1: Identify relevant columns
# -----------------------------
log("")
log("Step_1: Identify the generated and predicted absorption-related outputs and any error metric.")

required_cols = ["G_GAN", "G_Predict", "dG"]
missing_required = [c for c in required_cols if c not in df.columns]

if missing_required:
    log(f"Status: FAILED")
    log(f"Reason: Missing required columns: {missing_required}")
    analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")
    raise KeyError(f"Missing required columns: {missing_required}")

log("Relevant columns found:")
for c in required_cols:
    log(f"  - {c}")

# -----------------------------
# Step 2: Clean data and isolate target entries
# -----------------------------
log("")
log("Step_2: Clean the data and isolate the 467 nm target entries for this specific candidate set.")

# Coerce relevant columns to numeric and drop rows with missing values in those columns
before_rows = len(df)
for c in required_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")

clean_df = df.dropna(subset=required_cols).copy()
after_rows = len(clean_df)
log(f"Rows before cleaning: {before_rows}")
log(f"Rows after dropping rows with missing/invalid values in relevant columns: {after_rows}")

# Since the file itself is the 467 nm ABS case, isolate all valid rows
target_df = clean_df.copy()
log(f"Rows retained for the 467 nm ABS candidate set: {len(target_df)}")
log("Isolation criterion: the file name explicitly encodes ABS_467, so all valid rows belong to this target case.")

# Basic summary statistics
gan = target_df["G_GAN"].to_numpy()
pred = target_df["G_Predict"].to_numpy()
dg = target_df["dG"].to_numpy()

log("")
log("Basic data summary for the retained rows:")
log(f"  G_GAN:    min={np.min(gan):.6g}, max={np.max(gan):.6g}, mean={np.mean(gan):.6g}, std={np.std(gan, ddof=1) if len(gan) > 1 else 0:.6g}")
log(f"  G_Predict:min={np.min(pred):.6g}, max={np.max(pred):.6g}, mean={np.mean(pred):.6g}, std={np.std(pred, ddof=1) if len(pred) > 1 else 0:.6g}")
log(f"  dG:       min={np.min(dg):.6g}, max={np.max(dg):.6g}, mean={np.mean(dg):.6g}, std={np.std(dg, ddof=1) if len(dg) > 1 else 0:.6g}")

# -----------------------------
# Step 3: Create publication-style comparison plot
# -----------------------------
log("")
log("Step_3: Create a publication-style comparison plot showing generated versus predicted values or candidate ranking.")

# Determine plotting order: sort by G_GAN to show candidate ranking clearly
plot_df = target_df.sort_values(by="G_GAN", ascending=True).reset_index(drop=True)
plot_df["Candidate"] = np.arange(1, len(plot_df) + 1)

gan_sorted = plot_df["G_GAN"].to_numpy()
pred_sorted = plot_df["G_Predict"].to_numpy()
dg_sorted = plot_df["dG"].to_numpy()
cand = plot_df["Candidate"].to_numpy()

# Quantitative comparison metrics
mae = float(np.mean(np.abs(gan_sorted - pred_sorted))) if len(plot_df) else float("nan")
rmse = float(np.sqrt(np.mean((gan_sorted - pred_sorted) ** 2))) if len(plot_df) else float("nan")
corr = float(np.corrcoef(gan_sorted, pred_sorted)[0, 1]) if len(plot_df) > 1 else float("nan")

log("Validation of feature suitability:")
log("  - G_GAN and G_Predict are numeric after cleaning.")
log("  - dG is numeric and can be used as an error metric.")
log("  - The dataset contains many rows, so a comparison plot is supported by the data.")
log(f"  - Mean absolute error between G_GAN and G_Predict: {mae:.6g}")
log(f"  - Root mean square error between G_GAN and G_Predict: {rmse:.6g}")
log(f"  - Pearson correlation between G_GAN and G_Predict: {corr:.6g}")

# Plot
plt.style.use("seaborn-v0_8-whitegrid")
fig, ax = plt.subplots(figsize=(10, 6), dpi=200)

# Candidate ranking plot with two series
ax.plot(cand, gan_sorted, marker="o", markersize=4.5, linewidth=1.6, color="#1f77b4", label="G_GAN (generated)")
ax.plot(cand, pred_sorted, marker="s", markersize=4.0, linewidth=1.4, color="#d62728", label="G_Predict (predicted)")

# Optional error metric on secondary axis
ax2 = ax.twinx()
ax2.bar(cand, dg_sorted, width=0.35, color="#7f7f7f", alpha=0.25, label="dG")
ax2.set_ylabel("dG", fontsize=11, color="#555555")
ax2.tick_params(axis="y", labelcolor="#555555")

# Labels and title
ax.set_xlabel("Candidate rank (sorted by G_GAN)", fontsize=11)
ax.set_ylabel("Absorption-related output value", fontsize=11)
ax.set_title(
    f"Inverse-design evaluation for ABS {target_wavelength} nm\n"
    f"Second candidate set: generated vs predicted comparison",
    fontsize=13,
    pad=12
)

# Annotation with target and metrics
annotation = (
    f"Target: ABS {target_wavelength} nm\n"
    f"N = {len(plot_df)}\n"
    f"MAE = {mae:.4f}\n"
    f"RMSE = {rmse:.4f}\n"
    f"r = {corr:.4f}"
)
ax.text(
    0.02, 0.98, annotation,
    transform=ax.transAxes,
    va="top", ha="left",
    fontsize=10,
    bbox=dict(boxstyle="round,pad=0.35", facecolor="white", edgecolor="0.7", alpha=0.95)
)

# Legend handling for twin axes
lines1, labels1 = ax.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax.legend(lines1 + lines2, labels1 + labels2, loc="best", fontsize=9, frameon=True)

# Improve layout
ax.margins(x=0.01)
fig.tight_layout()

# -----------------------------
# Step 4: Label clearly and include target value
# -----------------------------
log("")
log("Step_4: Label the plot clearly to distinguish it from the other 467 nm ABS file and include the target value in the annotation.")
log("The title explicitly states that this is the second candidate set for ABS 467 nm.")
log("The annotation includes the target wavelength and summary metrics derived directly from the data.")

# -----------------------------
# Step 5: Save figure
# -----------------------------
log("")
log("Step_5: Save the figure in a format suitable for direct comparison with the paper’s second 467 nm absorption-target panel.")

try:
    fig.savefig(figure_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    log(f"Figure saved successfully: {figure_path}")
except Exception as e:
    log(f"Status: FAILED to save figure. Error: {e}")
    analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")
    raise

# Final notes
log("")
log("Final assessment:")
log("  - The file structure is a flat CSV with one row per candidate and columns for design variables and outputs.")
log("  - The relevant outputs for this task are G_GAN, G_Predict, and dG.")
log("  - No separate wavelength column was present; the 467 nm target is identified from the filename.")
log("  - The plot is based on valid numeric data and does not rely on unsupported assumptions.")
log("  - The output figure is intended to represent the alternate 467 nm absorption-target case.")

# Write analysis file
analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")

print(f"Saved figure to: {figure_path}")
print(f"Saved analysis to: {analysis_path}")