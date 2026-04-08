import os
import re
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/005_Proximityinduced_chiral_quantum_light_generation/type1_data/41563_2023_1645_MOESM11_ESM_10.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/005_Proximityinduced_chiral_quantum_light_generation/results/PAPER_05_TASK_02_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/005_Proximityinduced_chiral_quantum_light_generation/results/PAPER_05_TASK_02_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)
os.makedirs(os.path.dirname(analysis_path), exist_ok=True)

analysis_lines = []

def log(msg):
    analysis_lines.append(msg)

log("Task PAPER_05_TASK_02 Analysis")
log("Objective: Replot control PL spectra and polarization analysis for unstrained and unindented samples.")
log(f"Dataset file: {dataset_file}")
log("Step 0: Inspect workbook structure and identify sheets relevant to control spectra and polarization analysis.")

# Load workbook sheets
xls = pd.ExcelFile(dataset_file)
sheet_names = xls.sheet_names
log(f"Workbook sheets found: {sheet_names}")

# Read sheets as raw tables
sheets = {}
for sh in sheet_names:
    df = pd.read_excel(dataset_file, sheet_name=sh, header=None)
    sheets[sh] = df
    log(f"Loaded sheet '{sh}' with shape {df.shape}.")

# Inspect structure
for sh, df in sheets.items():
    preview = df.iloc[:5, :5].astype(str).values.tolist()
    log(f"Sheet '{sh}' preview (top-left 5x5): {preview}")

# Identify likely data types
# RTXYPositions: coordinate table
# RTHeightImage and RTMagneticFieldImage: 2D image-like arrays
height_df = sheets.get("RTHeightImage")
mag_df = sheets.get("RTMagneticFieldImage")
xy_df = sheets.get("RTXYPositions")

log("Interpretation of sheet organization:")
log(" - RTHeightImage and RTMagneticFieldImage are 2D matrices with one header row and one header column, consistent with image/intensity maps.")
log(" - RTXYPositions contains coordinate values for the image grid.")
log(" - No sheet names or visible headers indicate explicit PL spectra, sigma+/sigma-, DCP, DLP, or angle-resolved polarization tables.")
log("Therefore, the workbook appears to contain spatial image data rather than the requested control PL spectra/polarization spectra.")

# Parse coordinate axes from RTXYPositions
x_vals = None
y_vals = None
if xy_df is not None and xy_df.shape[1] >= 3:
    try:
        x_vals = pd.to_numeric(xy_df.iloc[1:, 1], errors="coerce").dropna().to_numpy()
        y_vals = pd.to_numeric(xy_df.iloc[1:, 2], errors="coerce").dropna().to_numpy()
        log(f"Parsed RTXYPositions: {len(x_vals)} x-values and {len(y_vals)} y-values.")
        if len(x_vals) > 1:
            log(f"X range: {np.min(x_vals):.3e} to {np.max(x_vals):.3e}")
        if len(y_vals) > 1:
            log(f"Y range: {np.min(y_vals):.3e} to {np.max(y_vals):.3e}")
    except Exception as e:
        log(f"Could not parse RTXYPositions numerically: {e}")

def parse_image(df, name):
    if df is None or df.shape[0] < 2 or df.shape[1] < 2:
        return None
    # first row contains column labels, first column contains row labels/blank
    data = df.iloc[1:, 1:].copy()
    data = data.apply(pd.to_numeric, errors="coerce")
    return data

height_img = parse_image(height_df, "RTHeightImage")
mag_img = parse_image(mag_df, "RTMagneticFieldImage")

log("Step 1: Standardize axis labels and channel names, then plot the available data.")
log("Because the workbook does not contain explicit PL spectra, the figure will present the available control-related image channels with clear labels and note the limitation.")

# Determine axes
if x_vals is None or len(x_vals) != height_img.shape[1]:
    x_vals = np.arange(height_img.shape[1])
    log("Using pixel index for x-axis because coordinate vector length did not match image width.")
if y_vals is None or len(y_vals) != height_img.shape[0]:
    y_vals = np.arange(height_img.shape[0])
    log("Using pixel index for y-axis because coordinate vector length did not match image height.")

# Prepare figure
fig = plt.figure(figsize=(12, 10), constrained_layout=True)
gs = fig.add_gridspec(2, 2)

ax1 = fig.add_subplot(gs[0, 0])
ax2 = fig.add_subplot(gs[0, 1])
ax3 = fig.add_subplot(gs[1, :])

# Panel A: height image
im1 = ax1.imshow(
    height_img.to_numpy(),
    origin="lower",
    aspect="auto",
    cmap="viridis",
)
ax1.set_title("RTHeightImage")
ax1.set_xlabel("X position (a.u.)")
ax1.set_ylabel("Y position (a.u.)")
cbar1 = fig.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04)
cbar1.set_label("Intensity (a.u.)")

# Panel B: magnetic field image
im2 = ax2.imshow(
    mag_img.to_numpy(),
    origin="lower",
    aspect="auto",
    cmap="coolwarm",
)
ax2.set_title("RTMagneticFieldImage")
ax2.set_xlabel("X position (a.u.)")
ax2.set_ylabel("Y position (a.u.)")
cbar2 = fig.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04)
cbar2.set_label("Intensity (a.u.)")

# Panel C: line profiles through center for both images
center_row = height_img.shape[0] // 2
center_col = height_img.shape[1] // 2
height_row = height_img.iloc[center_row, :].to_numpy(dtype=float)
height_col = height_img.iloc[:, center_col].to_numpy(dtype=float)
mag_row = mag_img.iloc[center_row, :].to_numpy(dtype=float)
mag_col = mag_img.iloc[:, center_col].to_numpy(dtype=float)

ax3.plot(np.arange(len(height_row)), height_row, label="Height image: center row", color="tab:blue", lw=1.8)
ax3.plot(np.arange(len(height_col)), height_col, label="Height image: center column", color="tab:cyan", lw=1.8, ls="--")
ax3.plot(np.arange(len(mag_row)), mag_row, label="Magnetic field image: center row", color="tab:red", lw=1.8)
ax3.plot(np.arange(len(mag_col)), mag_col, label="Magnetic field image: center column", color="tab:orange", lw=1.8, ls="--")
ax3.set_title("Central line profiles from available control-related image channels")
ax3.set_xlabel("Pixel index")
ax3.set_ylabel("Signal (a.u.)")
ax3.legend(ncol=2, fontsize=9, frameon=False)
ax3.grid(True, alpha=0.25)

fig.suptitle(
    "Control comparison figure reconstruction attempt\n"
    "Note: workbook contains image channels, not explicit PL spectra/polarization tables",
    fontsize=13
)

# Quantitative summary of available data
log("Step 2: Check for linear polarization data or derived polarization metrics.")
candidate_keywords = ["sigma", "dcp", "dlp", "angle", "polar", "count", "normalized"]
found_candidates = []
for sh in sheet_names:
    df = sheets[sh].astype(str)
    text = " ".join(df.head(20).astype(str).fillna("").values.flatten().tolist()).lower()
    if any(k in text for k in candidate_keywords):
        found_candidates.append(sh)

if found_candidates:
    log(f"Potential polarization-related content detected in sheets: {found_candidates}")
else:
    log("No explicit polarization-resolved spectra or derived metrics were detected in sheet names or visible headers.")
    log("Therefore, no defensible DCP/DLP or angle-dependent anisotropy calculation can be performed from this workbook.")

# Save figure
fig.savefig(figure_path, dpi=300, bbox_inches="tight")
plt.close(fig)

log("Step 3: Assemble publication-style figure.")
log(f"Figure saved to: {figure_path}")
log("Because the required PL spectra and polarization tables are absent, the figure is a best-effort visualization of the available workbook content rather than the target Extended Data Fig. 2 reproduction.")
log("Exclusions:")
log(" - No spectral peak identification was attempted because no wavelength/energy axis or PL intensity spectra were present.")
log(" - No polarization anisotropy metrics were computed because no sigma+/sigma-, DCP, DLP, or angle-resolved data were present.")
log(" - No assumptions were made about missing control spectra.")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure to: {figure_path}")
print(f"Saved analysis to: {analysis_path}")