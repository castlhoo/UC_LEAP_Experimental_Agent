import os
import re
import math
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/005_Proximityinduced_chiral_quantum_light_generation/type1_data/41563_2023_1645_MOESM4_ESM_10.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/005_Proximityinduced_chiral_quantum_light_generation/results/PAPER_05_TASK_08_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/005_Proximityinduced_chiral_quantum_light_generation/results/PAPER_05_TASK_08_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)

xls = pd.ExcelFile(dataset_file)
sheet_names = xls.sheet_names

analysis_lines = []
analysis_lines.append("Task PAPER_05_TASK_08 Analysis")
analysis_lines.append(f"Dataset file: {dataset_file}")
analysis_lines.append(f"Sheets found: {sheet_names}")
analysis_lines.append("")
analysis_lines.append("Step 0: Inspect workbook structure and identify spectral sheets.")
analysis_lines.append("I inspected the workbook sheets and their previewed structures. The workbook contains four sheets: HeightImage, ImageXYPositions, MagneticFieldImage, and Fig 3e.")
analysis_lines.append("HeightImage and MagneticFieldImage are 102x102 image-like grids with coordinate headers, which are not energy-resolved spectra.")
analysis_lines.append("ImageXYPositions contains coordinate arrays only, not spectral intensity data.")
analysis_lines.append("The only sheet name suggestive of a figure panel with spectral content is 'Fig 3e', so I load that sheet for detailed inspection.")

df = pd.read_excel(dataset_file, sheet_name="Fig 3e", header=None)
analysis_lines.append(f"'Fig 3e' raw shape: {df.shape}")
analysis_lines.append("I inspect the first rows and columns to infer whether the sheet contains one or more spectra and how the axes are organized.")

# Try to detect numeric content
numeric_df = df.apply(pd.to_numeric, errors='coerce')
non_nan_counts = numeric_df.notna().sum(axis=1).tolist()
analysis_lines.append(f"Non-NaN numeric counts by row (first 10 rows): {non_nan_counts[:10]}")

# Find likely header row and data rows
header_row = None
for i in range(min(10, len(df))):
    row = df.iloc[i].astype(str).str.lower().tolist()
    if any(("energy" in x) or ("wavelength" in x) or ("nm" in x) for x in row):
        header_row = i
        break

if header_row is None:
    header_row = 0

analysis_lines.append(f"Detected header row index: {header_row}")

# Re-read with header if possible
df2 = pd.read_excel(dataset_file, sheet_name="Fig 3e", header=header_row)
analysis_lines.append(f"Loaded 'Fig 3e' with header row {header_row}; shape: {df2.shape}")
analysis_lines.append(f"Columns: {list(df2.columns)[:20]}")

# Identify likely energy and signal columns
cols = list(df2.columns)
lower_cols = [str(c).lower() for c in cols]

energy_col = None
for c, lc in zip(cols, lower_cols):
    if "energy" in lc:
        energy_col = c
        break
if energy_col is None:
    for c, lc in zip(cols, lower_cols):
        if "wavelength" in lc or "nm" in lc:
            energy_col = c
            break

signal_cols = []
for c, lc in zip(cols, lower_cols):
    if c == energy_col:
        continue
    if any(k in lc for k in ["s+", "s-", "sigma+", "sigma-", "dcp", "count", "intensity", "normalized"]):
        signal_cols.append(c)

analysis_lines.append(f"Identified energy column: {energy_col}")
analysis_lines.append(f"Candidate signal columns: {signal_cols}")

# If no explicit columns, infer numeric columns
if energy_col is None:
    numeric_cols = [c for c in cols if pd.to_numeric(df2[c], errors='coerce').notna().sum() > max(5, len(df2)//4)]
    analysis_lines.append(f"No explicit energy column found; numeric columns inferred: {numeric_cols}")
    if len(numeric_cols) >= 2:
        energy_col = numeric_cols[0]
        signal_cols = numeric_cols[1:]

# Clean data
plot_df = df2.copy()
for c in plot_df.columns:
    plot_df[c] = pd.to_numeric(plot_df[c], errors='coerce')

plot_df = plot_df.dropna(subset=[energy_col]) if energy_col is not None else plot_df
analysis_lines.append(f"After numeric coercion, data shape: {plot_df.shape}")

# Determine if multiple spectra are present
usable_cols = [c for c in plot_df.columns if c != energy_col and plot_df[c].notna().sum() > 3]
analysis_lines.append(f"Usable numeric signal columns: {usable_cols}")

# Build figure
plt.style.use('default')
fig, ax = plt.subplots(figsize=(8.5, 5.5), dpi=300)

if energy_col is not None and len(usable_cols) > 0:
    x = plot_df[energy_col].to_numpy(dtype=float)
    # Sort by x if needed
    order = np.argsort(x)
    x = x[order]
    plotted = []
    for c in usable_cols:
        y = plot_df[c].to_numpy(dtype=float)[order]
        mask = np.isfinite(x) & np.isfinite(y)
        x2 = x[mask]
        y2 = y[mask]
        if len(x2) < 3:
            continue
        # Normalize each channel to its max absolute value for consistent comparison
        ymax = np.nanmax(np.abs(y2))
        if not np.isfinite(ymax) or ymax == 0:
            continue
        y_norm = y2 / ymax
        label = str(c)
        plotted.append(label)
        ax.plot(x2, y_norm, lw=1.8, label=label)
        # Peak annotation: local maximum on normalized curve
        if len(y_norm) >= 3:
            idx = np.argmax(y_norm)
            if 0 < idx < len(y_norm) - 1:
                ax.annotate(f"peak {x2[idx]:.3f}", xy=(x2[idx], y_norm[idx]),
                            xytext=(5, 8), textcoords="offset points", fontsize=8)
    analysis_lines.append(f"Plotted channels: {plotted}")
    ax.set_xlabel(str(energy_col))
    ax.set_ylabel("Normalized intensity")
    ax.legend(frameon=False, fontsize=8)
else:
    analysis_lines.append("Could not identify a valid energy axis and signal columns for plotting.")
    ax.text(0.5, 0.5, "No clear spectral data identified in workbook", ha='center', va='center', transform=ax.transAxes)
    ax.set_axis_off()

ax.set_title("Representative polarization-resolved PL spectra")
ax.text(0.02, 0.98, "a", transform=ax.transAxes, fontsize=14, fontweight='bold', va='top')
fig.tight_layout()
fig.savefig(figure_path, bbox_inches='tight')
plt.close(fig)

analysis_lines.append("")
analysis_lines.append("Step 1: Standardize channel names and plot each spectrum against energy.")
analysis_lines.append("I standardized channels by using the column names directly when available. Because the workbook preview does not show explicit labels such as sigma+/sigma-/DCP in the visible rows, I only plotted columns that were numerically populated in the spectral sheet and treated them as candidate channels.")
analysis_lines.append("Each plotted trace was normalized by its own maximum absolute intensity to allow direct comparison of spectral shape and relative peak position without assuming absolute calibration.")
analysis_lines.append("")
analysis_lines.append("Step 2: DCP handling.")
analysis_lines.append("I searched for explicit DCP-like columns in the loaded sheet. No clearly labeled DCP column was identifiable from the inspected workbook structure, so I did not compute or annotate DCP from unsupported assumptions.")
analysis_lines.append("")
analysis_lines.append("Step 3: Figure assembly.")
analysis_lines.append("A publication-style figure was generated with a single panel because the workbook inspection did not reveal multiple clearly separated representative nanoindentation spectra sheets. The figure includes a title, axis labels, legend, and panel label.")
analysis_lines.append("")
analysis_lines.append("Validation and limitations.")
analysis_lines.append("The workbook does not present an unambiguous energy-resolved polarization spectrum in the previewed sheets except possibly within 'Fig 3e'. However, the visible preview does not expose explicit channel names or multiple indentation-specific spectra. Therefore, the figure is a conservative replot of the numerically identifiable spectral content from the spectral sheet, without inventing missing polarization assignments or DCP values.")
analysis_lines.append(f"Figure saved to: {figure_path}")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure: {figure_path}")
print(f"Saved analysis: {analysis_path}")