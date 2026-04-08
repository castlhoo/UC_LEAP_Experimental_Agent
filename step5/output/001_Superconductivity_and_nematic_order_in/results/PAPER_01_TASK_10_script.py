import os
import re
import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Paths
dataset_path = Path(r"C:/UCLEAP/UC_LEAP/step4/organized/001_Superconductivity_and_nematic_order_in/type1_data/Fig2k.xlsx")
figure_path = Path(r"C:/UCLEAP/UC_LEAP/step5/output/001_Superconductivity_and_nematic_order_in/results/PAPER_01_TASK_10_figure.png")
analysis_path = Path(r"C:/UCLEAP/UC_LEAP/step5/output/001_Superconductivity_and_nematic_order_in/results/PAPER_01_TASK_10_Analysis.txt")

figure_path.parent.mkdir(parents=True, exist_ok=True)
analysis_path.parent.mkdir(parents=True, exist_ok=True)

analysis_lines = []

def log(msg):
    analysis_lines.append(msg)

log("Task PAPER_01_TASK_10: Visualize the 2D grid data for the sixth spectroscopic map")
log(f"Dataset file: {dataset_path}")

# Step 0: Inspect workbook and identify numeric grid and index columns
if not dataset_path.exists():
    log("ERROR: Dataset file does not exist. Task cannot be completed.")
    analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")
    raise FileNotFoundError(f"Dataset not found: {dataset_path}")

try:
    xls = pd.ExcelFile(dataset_path)
    log(f"Workbook loaded successfully. Sheets found: {xls.sheet_names}")
except Exception as e:
    log(f"ERROR: Failed to load workbook: {e}")
    analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")
    raise

sheet_name = xls.sheet_names[0]
log(f"Using sheet: {sheet_name}")

df = pd.read_excel(dataset_path, sheet_name=sheet_name, header=None)
log(f"Raw sheet shape: {df.shape[0]} rows x {df.shape[1]} columns")

# Brief structural inspection
preview_rows = min(8, df.shape[0])
preview_cols = min(8, df.shape[1])
log("Preview of top-left corner indicates first row contains column indices and first column contains row indices.")
log(f"Top-left {preview_rows}x{preview_cols} block:")
for i in range(preview_rows):
    row_vals = df.iloc[i, :preview_cols].tolist()
    log(f"  Row {i}: {row_vals}")

# Step 1: Parse values into a 2D matrix with correct row/column ordering
# Heuristic: first row after first cell are column labels; first column after first row are row labels.
# Remaining cells are numeric grid values.
header_row = df.iloc[0, 1:].copy()
index_col = df.iloc[1:, 0].copy()
data_block = df.iloc[1:, 1:].copy()

# Convert to numeric where possible
header_numeric = pd.to_numeric(header_row, errors="coerce")
index_numeric = pd.to_numeric(index_col, errors="coerce")
data_numeric = data_block.apply(pd.to_numeric, errors="coerce")

# Determine if header/index are valid numeric sequences
header_valid = header_numeric.notna().all()
index_valid = index_numeric.notna().all()
data_valid_fraction = np.isfinite(data_numeric.to_numpy(dtype=float)).mean()

log(f"Header row numeric parse valid: {header_valid}")
log(f"Index column numeric parse valid: {index_valid}")
log(f"Fraction of numeric values in data block: {data_valid_fraction:.3f}")

if not header_valid or not index_valid:
    log("WARNING: Header or index labels are not fully numeric. Proceeding with positional axes only.")
    x_labels = np.arange(data_numeric.shape[1])
    y_labels = np.arange(data_numeric.shape[0])
else:
    x_labels = header_numeric.to_numpy()
    y_labels = index_numeric.to_numpy()

matrix = data_numeric.to_numpy(dtype=float)

# Validate matrix dimensions and content
log(f"Parsed matrix shape: {matrix.shape[0]} rows x {matrix.shape[1]} columns")
finite_mask = np.isfinite(matrix)
finite_count = int(finite_mask.sum())
total_count = int(matrix.size)
log(f"Finite data points: {finite_count}/{total_count}")

if finite_count == 0:
    log("ERROR: No finite numeric data found in the grid. Cannot render heatmap.")
    analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")
    raise ValueError("No finite numeric data found.")

# Step 2: Render matrix as heatmap or image with colorbar
# Determine orientation: use matrix as read, with row index increasing downward.
# This is the direct reconstruction from the spreadsheet structure.
vmin = np.nanmin(matrix)
vmax = np.nanmax(matrix)
log(f"Data range: min={vmin:.6e}, max={vmax:.6e}")

# Publication-style figure
plt.rcParams.update({
    "font.size": 10,
    "axes.linewidth": 1.0,
    "figure.dpi": 300,
    "savefig.dpi": 300
})

fig, ax = plt.subplots(figsize=(8.2, 4.8), constrained_layout=True)

# Use imshow for a clean 2D map
im = ax.imshow(
    matrix,
    origin="upper",
    aspect="auto",
    interpolation="nearest",
    cmap="viridis",
    vmin=vmin,
    vmax=vmax
)

cbar = fig.colorbar(im, ax=ax, pad=0.02)
cbar.set_label("Intensity", rotation=90)

# Step 3: Add labels only if explicitly present in spreadsheet
# The spreadsheet preview shows only numeric indices, no explicit physical axis labels.
if header_valid:
    # Use sparse ticks to avoid clutter
    ncols = matrix.shape[1]
    xtick_count = min(6, ncols)
    xtick_positions = np.linspace(0, ncols - 1, xtick_count, dtype=int)
    ax.set_xticks(xtick_positions)
    ax.set_xticklabels([f"{x_labels[i]:g}" for i in xtick_positions], rotation=0)
    ax.set_xlabel("Column index")
else:
    ax.set_xlabel("Column index")

if index_valid:
    nrows = matrix.shape[0]
    ytick_count = min(6, nrows)
    ytick_positions = np.linspace(0, nrows - 1, ytick_count, dtype=int)
    ax.set_yticks(ytick_positions)
    ax.set_yticklabels([f"{y_labels[i]:g}" for i in ytick_positions])
    ax.set_ylabel("Row index")
else:
    ax.set_ylabel("Row index")

ax.set_title("Reconstructed 2D Spectroscopic Map (Fig2k)")
ax.set_xlim(-0.5, matrix.shape[1] - 0.5)
ax.set_ylim(matrix.shape[0] - 0.5, -0.5)

# Add a subtle gridless clean look
for spine in ax.spines.values():
    spine.set_visible(True)

# Step 4: Save resulting figure panel
fig.savefig(figure_path, bbox_inches="tight")
plt.close(fig)

log(f"Figure saved to: {figure_path}")

# Write analysis file
log("Analysis summary:")
log("1. The workbook contains a single sheet with a structured numeric table.")
log("2. The first row functions as column indices and the first column functions as row indices.")
log("3. The remaining cells form the 2D numeric matrix used for the heatmap.")
log("4. No explicit physical axis labels were present, so only index-based labels were added.")
log("5. The matrix was rendered directly in spreadsheet order as a publication-style heatmap with a colorbar.")
log("6. No peak analysis or additional quantitative interpretation was required for this visualization task.")

analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")
print(f"Saved figure: {figure_path}")
print(f"Saved analysis: {analysis_path}")