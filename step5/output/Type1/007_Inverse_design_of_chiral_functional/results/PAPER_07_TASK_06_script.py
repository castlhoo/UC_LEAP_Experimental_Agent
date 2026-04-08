import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

dataset_path = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/007_Inverse_design_of_chiral_functional/type1_data/cgan_test_result_ABS_467_1.72.csv"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/007_Inverse_design_of_chiral_functional/results/PAPER_07_TASK_06_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/007_Inverse_design_of_chiral_functional/results/PAPER_07_TASK_06_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)
os.makedirs(os.path.dirname(analysis_path), exist_ok=True)

analysis_lines = []

def log(line=""):
    analysis_lines.append(line)

log("Task PAPER_07_TASK_06 Analysis")
log("Objective: Replot the absorption-target inverse-design results at 467 nm for the first candidate set.")
log("")
log("Step_0: Load the CSV and inspect the schema, focusing on the 467 nm absorption-target entries.")
try:
    df = pd.read_csv(dataset_path)
    log(f"Loaded dataset successfully from: {dataset_path}")
    log(f"Dataset shape: {df.shape[0]} rows x {df.shape[1]} columns")
    log(f"Columns detected: {list(df.columns)}")
except Exception as e:
    log(f"Failed to load dataset: {e}")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise

log("")
log("Step_1: Identify the columns corresponding to generated output, predicted output, and error or deviation.")
required_cols = ["G_GAN", "G_Predict", "dG"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    log(f"Missing required columns: {missing}")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise ValueError(f"Required columns missing: {missing}")
else:
    log("Identified columns:")
    log("  G_GAN: generated output from cGAN")
    log("  G_Predict: predicted output")
    log("  dG: deviation/error term")
    target_info = []
    for c in df.columns:
        if "467" in c or "ABS" in c.upper():
            target_info.append(c)
    if target_info:
        log(f"Target-related columns/identifiers found in file context: {target_info}")
    else:
        log("No explicit wavelength column found in the table; target wavelength is inferred from the filename and task description (467 nm).")

log("")
log("Step_2: Clean the data and standardize numeric values and labels.")
work = df.copy()
for col in work.columns:
    work[col] = pd.to_numeric(work[col], errors="ignore")

for col in required_cols:
    work[col] = pd.to_numeric(work[col], errors="coerce")

before_drop = len(work)
work = work.dropna(subset=required_cols).reset_index(drop=True)
after_drop = len(work)
log(f"Converted required columns to numeric and dropped rows with missing required values.")
log(f"Rows before cleaning: {before_drop}, after cleaning: {after_drop}, removed: {before_drop - after_drop}")

if after_drop == 0:
    log("No valid rows remain after cleaning; cannot proceed with plotting.")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise ValueError("No valid data after cleaning.")

log("")
log("Step_3: Create a comparison plot that makes the agreement between generated and predicted absorption-related values visually obvious.")
gan = work["G_GAN"].to_numpy()
pred = work["G_Predict"].to_numpy()
dg = work["dG"].to_numpy()
idx = np.arange(1, len(work) + 1)

diff = gan - pred
mae = float(np.mean(np.abs(diff)))
rmse = float(np.sqrt(np.mean(diff ** 2)))
mean_abs_dg = float(np.mean(np.abs(dg)))
max_abs_dg = float(np.max(np.abs(dg)))

log(f"Computed comparison metrics from the cleaned data:")
log(f"  Mean absolute difference |G_GAN - G_Predict| = {mae:.6f}")
log(f"  RMSE(G_GAN, G_Predict) = {rmse:.6f}")
log(f"  Mean absolute dG = {mean_abs_dg:.6f}")
log(f"  Max absolute dG = {max_abs_dg:.6f}")

log("")
log("Step_4: Annotate the figure with the 467 nm target and any relevant performance metric.")
log("The figure will include:")
log("  - Scatter/line comparison of G_GAN and G_Predict across candidate designs")
log("  - A 1:1 reference line in a parity inset to show agreement")
log("  - Annotation of the 467 nm target and summary error metrics")
log("  - A secondary panel for dG to show deviation magnitude")

log("")
log("Step_5: Export the plot in a style consistent with the paper’s inverse-design result panels.")
plt.style.use("default")
fig = plt.figure(figsize=(10.5, 7.5), dpi=300)
gs = fig.add_gridspec(2, 1, height_ratios=[2.2, 1.0], hspace=0.25)

ax1 = fig.add_subplot(gs[0, 0])
ax1.plot(idx, gan, marker="o", markersize=4.5, linewidth=1.4, color="#1f77b4", label="G_GAN (generated)")
ax1.plot(idx, pred, marker="s", markersize=4.0, linewidth=1.4, color="#d62728", label="G_Predict (predicted)")
ax1.set_xlabel("Candidate design index")
ax1.set_ylabel("Absorption-related value")
ax1.set_title("Inverse-design evaluation at 467 nm (ABS target, first candidate set)")
ax1.grid(True, alpha=0.25)
ax1.legend(frameon=False, loc="best")

text = (
    f"Target: 467 nm\n"
    f"Mean |Δ| = {mae:.4f}\n"
    f"RMSE = {rmse:.4f}\n"
    f"Mean |dG| = {mean_abs_dg:.4f}"
)
ax1.text(
    0.02, 0.98, text,
    transform=ax1.transAxes,
    va="top", ha="left",
    fontsize=9,
    bbox=dict(boxstyle="round,pad=0.35", facecolor="white", edgecolor="0.7", alpha=0.9)
)

ax2 = fig.add_subplot(gs[1, 0], sharex=ax1)
ax2.bar(idx, dg, color="#2ca02c", width=0.8, alpha=0.85)
ax2.axhline(0, color="black", linewidth=0.8)
ax2.set_xlabel("Candidate design index")
ax2.set_ylabel("dG")
ax2.grid(True, axis="y", alpha=0.25)

# Add a small parity inset to emphasize agreement
inset = ax1.inset_axes([0.68, 0.12, 0.28, 0.34])
inset.scatter(gan, pred, s=14, color="#444444", alpha=0.75)
minv = float(min(np.min(gan), np.min(pred)))
maxv = float(max(np.max(gan), np.max(pred)))
pad = 0.02 * (maxv - minv if maxv > minv else 1.0)
inset.plot([minv - pad, maxv + pad], [minv - pad, maxv + pad], "--", color="gray", linewidth=1.0)
inset.set_xlim(minv - pad, maxv + pad)
inset.set_ylim(minv - pad, maxv + pad)
inset.set_xlabel("G_GAN", fontsize=8)
inset.set_ylabel("G_Predict", fontsize=8)
inset.tick_params(labelsize=8)
inset.grid(True, alpha=0.2)
inset.set_title("Parity", fontsize=9)

fig.suptitle("PAPER_07_TASK_06: 467 nm ABS inverse-design result", y=0.98, fontsize=13)
fig.tight_layout(rect=[0, 0, 1, 0.965])

try:
    fig.savefig(figure_path, bbox_inches="tight")
    log(f"Figure saved successfully to: {figure_path}")
except Exception as e:
    log(f"Failed to save figure: {e}")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise

log("")
log("Validation and exclusions:")
log("  - The dataset contains the required generated, predicted, and deviation columns.")
log("  - No explicit wavelength column was present in the previewed schema; the 467 nm target is therefore taken from the filename and task context.")
log("  - The plot uses all valid rows after numeric cleaning; no rows were excluded beyond missing/invalid required values.")
log("  - No peak identification or spectral interpretation was needed because this task concerns inverse-design tabular results, not a spectrum.")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure to: {figure_path}")
print(f"Saved analysis to: {analysis_path}")