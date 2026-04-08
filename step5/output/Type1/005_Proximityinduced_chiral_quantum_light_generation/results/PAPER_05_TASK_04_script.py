import os
import re
import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

warnings.filterwarnings("ignore")

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/005_Proximityinduced_chiral_quantum_light_generation/type1_data/41563_2023_1645_MOESM13_ESM_10.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/005_Proximityinduced_chiral_quantum_light_generation/results/PAPER_05_TASK_04_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/005_Proximityinduced_chiral_quantum_light_generation/results/PAPER_05_TASK_04_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)
os.makedirs(os.path.dirname(analysis_path), exist_ok=True)

analysis_lines = []
analysis_lines.append("Task PAPER_05_TASK_04 Analysis")
analysis_lines.append("=" * 40)
analysis_lines.append(f"Dataset file: {dataset_file}")
analysis_lines.append("")

# Step 0: inspect workbook structure
analysis_lines.append("Step 0: Identify spectral image matrix and accompanying coordinate or fit-summary sheets")
analysis_lines.append("I loaded the workbook and inspected sheet names and table shapes to determine which sheets contain spectral-image data and which may contain supporting summaries.")
try:
    xls = pd.ExcelFile(dataset_file)
    sheet_names = xls.sheet_names
    analysis_lines.append(f"Workbook sheets: {sheet_names}")
except Exception as e:
    analysis_lines.append(f"Failed to open workbook: {e}")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise

dfs = {}
for sh in sheet_names:
    try:
        df = pd.read_excel(dataset_file, sheet_name=sh)
        dfs[sh] = df
        analysis_lines.append(f"Sheet '{sh}': shape={df.shape}, columns={list(df.columns)}")
    except Exception as e:
        analysis_lines.append(f"Sheet '{sh}' could not be read: {e}")

analysis_lines.append("")
analysis_lines.append("Interpretation of workbook structure:")
analysis_lines.append("The workbook contains sheets ED 9a through ED 9f. Based on the preview and column names, ED 9b is the only sheet that clearly contains a multi-condition spectral matrix with energy and multiple signal channels across magnetic-field conditions.")
analysis_lines.append("ED 9a and ED 9c contain only 0T sig- and 0T sig+ columns, so they appear to be single-condition spectra rather than a 2D spectral image matrix.")
analysis_lines.append("No sheet names or columns explicitly indicate spatial coordinates such as FitPix, Pix, 2DX, or LX. Therefore, the workbook does not expose a direct spatial-coordinate table in the provided sheets.")
analysis_lines.append("")

# Helper to clean numeric columns
def to_numeric_df(df):
    out = df.copy()
    for c in out.columns:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return out

# Identify candidate spectral image matrix
candidate_sheet = None
for sh, df in dfs.items():
    cols = [str(c).strip() for c in df.columns]
    if any("energy" == c.lower() for c in cols) and len(cols) > 3:
        candidate_sheet = sh
        break
if candidate_sheet is None:
    candidate_sheet = "ED 9b" if "ED 9b" in dfs else sheet_names[0]

analysis_lines.append(f"Selected candidate spectral matrix sheet: {candidate_sheet}")
analysis_lines.append("Reasoning: it contains an energy axis and multiple intensity columns corresponding to different field/polarization conditions, which is the closest available structure to a spectral-image matrix in this workbook.")
analysis_lines.append("")

# Step 1: reconstruct 2D spectral map
analysis_lines.append("Step 1: Reconstruct the 2D spectral map using the correct axes and intensity values")
df = to_numeric_df(dfs[candidate_sheet])
cols = list(dfs[candidate_sheet].columns)
energy_col = cols[0]
energy = pd.to_numeric(dfs[candidate_sheet].iloc[:, 0], errors="coerce").to_numpy()

signal_cols = cols[1:]
signal_data = {}
for c in signal_cols:
    signal_data[c] = pd.to_numeric(dfs[candidate_sheet][c], errors="coerce").to_numpy()

valid_energy = np.isfinite(energy)
energy = energy[valid_energy]
for c in signal_cols:
    signal_data[c] = signal_data[c][valid_energy]

# Sort energy ascending for plotting
sort_idx = np.argsort(energy)
energy = energy[sort_idx]
for c in signal_cols:
    signal_data[c] = signal_data[c][sort_idx]

# Build matrix
matrix = np.column_stack([signal_data[c] for c in signal_cols])

analysis_lines.append(f"Energy axis extracted from column '{energy_col}'.")
analysis_lines.append(f"Energy range: {np.nanmin(energy):.5f} to {np.nanmax(energy):.5f} eV")
analysis_lines.append(f"Number of energy points: {len(energy)}")
analysis_lines.append(f"Number of signal channels: {len(signal_cols)}")
analysis_lines.append("Signal channels: " + ", ".join(signal_cols))
analysis_lines.append("The matrix is reconstructed as intensity vs energy (vertical axis) and channel index / field condition (horizontal axis).")
analysis_lines.append("Because no explicit spatial coordinate sheet is present, the horizontal axis is interpreted as the available measurement-condition axis rather than a true pixel coordinate axis.")
analysis_lines.append("")

# Step 2: extract peak metrics if possible
analysis_lines.append("Step 2: Extract peak-fit parameters or spatially resolved peak metrics")
analysis_lines.append("I searched the workbook for columns or sheet names suggesting fitted peak positions, amplitudes, linewidths, or spatial coordinates.")
keywords = ["fitpix", "pix", "p1", "p2", "p3", "p4", "p5", "2dx", "lx", "linewidth", "peak position", "amplitude"]
found_related = []
for sh, df0 in dfs.items():
    for c in df0.columns:
        cl = str(c).strip().lower()
        if any(k in cl for k in keywords):
            found_related.append((sh, c))
if found_related:
    analysis_lines.append("Potentially relevant columns found:")
    for sh, c in found_related:
        analysis_lines.append(f"  - Sheet '{sh}': column '{c}'")
else:
    analysis_lines.append("No explicit fit-summary or spatial-coordinate columns matching the requested variables were found in the provided sheets.")
analysis_lines.append("Therefore, no defensible peak-position or amplitude summary can be reconstructed from dedicated fit tables.")
analysis_lines.append("")

# Peak identification on representative channels
analysis_lines.append("Peak validation on representative spectra")
analysis_lines.append("I checked whether the spectra contain clear local maxima suitable for peak identification. The provided preview shows nearly flat intensities with small fluctuations, so I only report peaks if they are supported by clear local maxima above neighboring points.")
def find_local_maxima(y, min_prominence=0.0):
    y = np.asarray(y, dtype=float)
    peaks = []
    for i in range(1, len(y)-1):
        if np.isfinite(y[i-1]) and np.isfinite(y[i]) and np.isfinite(y[i+1]):
            if y[i] > y[i-1] and y[i] >= y[i+1]:
                left = y[i] - y[i-1]
                right = y[i] - y[i+1]
                prom = min(left, right)
                if prom >= min_prominence:
                    peaks.append(i)
    return peaks

peak_summary = {}
for c in signal_cols:
    y = signal_data[c]
    # Use a modest prominence threshold relative to local variation
    std = np.nanstd(y)
    thr = max(1.0, 0.5 * std)
    peaks = find_local_maxima(y, min_prominence=thr)
    peak_summary[c] = peaks

for c, peaks in peak_summary.items():
    if len(peaks) == 0:
        analysis_lines.append(f"  - {c}: no clear peaks identified with a conservative prominence threshold.")
    else:
        top = peaks[:5]
        analysis_lines.append(f"  - {c}: {len(peaks)} candidate peak(s) at energies {[round(float(energy[i]), 5) for i in top]}")
analysis_lines.append("Given the weak contrast and absence of dedicated fit tables, I do not infer additional peak positions or amplitudes beyond what is directly supported by the data.")
analysis_lines.append("")

# Step 3: create publication-style figure
analysis_lines.append("Step 3: Format the result as a publication-style multi-panel figure with clear axis labels and peak annotations")
analysis_lines.append("I constructed a multi-panel figure with: (i) a spectral image of intensity versus energy and measurement condition, (ii) line cuts for representative channels, and (iii) a compact summary of mean intensity across channels.")
analysis_lines.append("Because no explicit spatial map or fit-summary sheet is available, the figure is a faithful reconstruction of the available spectral matrix rather than a true spatial coordinate map.")
analysis_lines.append("")

# Choose representative channels for line cuts
rep_cols = signal_cols[:min(6, len(signal_cols))]
mean_intensity = np.nanmean(matrix, axis=1)
std_intensity = np.nanstd(matrix, axis=1)

# Plot
plt.rcParams.update({
    "font.size": 9,
    "axes.linewidth": 1.0,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "figure.dpi": 200
})

fig = plt.figure(figsize=(11, 8.5))
gs = GridSpec(2, 2, figure=fig, width_ratios=[1.25, 1.0], height_ratios=[1.0, 0.9], wspace=0.28, hspace=0.28)

ax0 = fig.add_subplot(gs[:, 0])
im = ax0.imshow(
    matrix,
    aspect="auto",
    origin="lower",
    extent=[0, len(signal_cols)-1, energy.min(), energy.max()],
    cmap="magma"
)
ax0.set_xlabel("Measurement condition / channel index")
ax0.set_ylabel("Energy (eV)")
ax0.set_title("Reconstructed spectral image")
cbar = fig.colorbar(im, ax=ax0, pad=0.02)
cbar.set_label("Intensity (a.u.)")

# annotate channel labels sparsely
xticks = np.arange(len(signal_cols))
ax0.set_xticks(xticks)
ax0.set_xticklabels([str(i+1) for i in xticks], rotation=0)

ax1 = fig.add_subplot(gs[0, 1])
for c in rep_cols:
    ax1.plot(energy, signal_data[c], lw=1.2, label=c)
ax1.set_xlabel("Energy (eV)")
ax1.set_ylabel("Intensity (a.u.)")
ax1.set_title("Representative line cuts")
ax1.legend(frameon=False, fontsize=7, ncol=1)

ax2 = fig.add_subplot(gs[1, 1])
ax2.plot(energy, mean_intensity, color="black", lw=1.5, label="Mean")
ax2.fill_between(energy, mean_intensity - std_intensity, mean_intensity + std_intensity, color="gray", alpha=0.25, label="±1 SD")
ax2.set_xlabel("Energy (eV)")
ax2.set_ylabel("Intensity (a.u.)")
ax2.set_title("Across-channel summary")
ax2.legend(frameon=False, fontsize=7)

fig.suptitle("PAPER_05_TASK_04: Spectral image and localized-peak analysis", y=0.98, fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.97])

fig.savefig(figure_path, dpi=300, bbox_inches="tight")
plt.close(fig)

analysis_lines.append(f"Figure saved to: {figure_path}")
analysis_lines.append("")

analysis_lines.append("Limitations and exclusions")
analysis_lines.append("1. No explicit spatial coordinate sheet (e.g., FitPix, Pix, 2DX, LX) was found in the workbook.")
analysis_lines.append("2. No dedicated peak-fit summary table with peak positions, amplitudes, or linewidths was found.")
analysis_lines.append("3. The available data support a spectral matrix across measurement conditions, but not a true spatial emission map with calibrated coordinates.")
analysis_lines.append("4. Peak identification was intentionally conservative; only clear local maxima would be reported, and the spectra here do not show strong, defensible isolated peaks in the previewed data.")
analysis_lines.append("")

analysis_lines.append("Conclusion")
analysis_lines.append("The workbook supports reconstruction of a spectral-image-style matrix from ED 9b and associated line cuts, but it does not provide enough explicit spatial or fit-summary information to reproduce a full nanoindentation spatial map with multiple localized emitter peak parameters. The generated figure therefore presents the available spectral matrix and summary traces without inventing unsupported spatial coordinates or peak fits.")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure to: {figure_path}")
print(f"Saved analysis to: {analysis_path}")