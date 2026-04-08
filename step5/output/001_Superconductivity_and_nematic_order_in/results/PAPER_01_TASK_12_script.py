import os
import re
import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Optional dependency handling
try:
    import openpyxl  # noqa: F401
except Exception:
    pass

dataset_path = Path(r"C:/UCLEAP/UC_LEAP/step4/organized/001_Superconductivity_and_nematic_order_in/type1_data/Fig3h.xlsx")
figure_path = Path(r"C:/UCLEAP/UC_LEAP/step5/output/001_Superconductivity_and_nematic_order_in/results/PAPER_01_TASK_12_figure.png")
analysis_path = Path(r"C:/UCLEAP/UC_LEAP/step5/output/001_Superconductivity_and_nematic_order_in/results/PAPER_01_TASK_12_Analysis.txt")

figure_path.parent.mkdir(parents=True, exist_ok=True)
analysis_path.parent.mkdir(parents=True, exist_ok=True)

analysis_lines = []

def log(msg):
    analysis_lines.append(msg)

log("Task PAPER_01_TASK_12 Analysis")
log("Objective: Reconstruct the 2D numeric map from the spreadsheet and render it as a heatmap/image-style plot.")
log(f"Dataset file: {dataset_path}")

if not dataset_path.exists():
    log("Status: Dataset file not found. Task cannot be completed.")
    analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")
    raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

# Step 0: Inspect workbook and locate numeric grid region and index information.
log("Step 0: Inspect workbook structure and identify grid layout.")
try:
    xls = pd.ExcelFile(dataset_path)
    log(f"Workbook sheets: {xls.sheet_names}")
    df_raw = pd.read_excel(dataset_path, sheet_name=xls.sheet_names[0], header=None)
    log(f"Loaded sheet '{xls.sheet_names[0]}' with shape {df_raw.shape[0]} rows x {df_raw.shape[1]} cols.")
except Exception as e:
    log(f"Failed to load workbook: {e}")
    analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")
    raise

# Inspect top-left region
preview_rows = min(8, df_raw.shape[0])
preview_cols = min(20, df_raw.shape[1])
log("Preview of top-left region indicates:")
for r in range(preview_rows):
    vals = [str(df_raw.iat[r, c]) for c in range(preview_cols)]
    log(f"  Row {r}: {vals}")

# Determine likely structure:
# Row 0: blank corner + x-axis labels
# Odd rows: y-axis label in first column + data row
# Even rows after row 0: repeated x-axis label rows or separators
# We will parse rows where first column is numeric row index and remaining cells are numeric data.
def is_number(x):
    try:
        if pd.isna(x):
            return False
        float(str(x))
        return True
    except Exception:
        return False

# Identify candidate data rows: first column numeric and at least some numeric values in remaining columns
candidate_rows = []
for i in range(df_raw.shape[0]):
    first = df_raw.iat[i, 0]
    if is_number(first):
        numeric_count = sum(is_number(df_raw.iat[i, j]) for j in range(1, df_raw.shape[1]))
        if numeric_count > 0:
            candidate_rows.append(i)

log(f"Candidate rows with numeric first-column indices and numeric data: {candidate_rows}")

# Extract x-axis labels from first row if present
x_labels = []
if df_raw.shape[0] > 1:
    for j in range(1, df_raw.shape[1]):
        if is_number(df_raw.iat[1, j]):
            x_labels.append(float(df_raw.iat[1, j]))
        else:
            break
log(f"Detected {len(x_labels)} x-axis labels from row 1.")

# Parse matrix from odd-numbered rows with data
row_indices = []
matrix_rows = []
for i in candidate_rows:
    row_id = float(df_raw.iat[i, 0])
    # Use rows where the row contains a sequence of numeric values after the first column
    values = []
    for j in range(1, df_raw.shape[1]):
        v = df_raw.iat[i, j]
        if is_number(v):
            values.append(float(v))
        else:
            break
    if len(values) >= 2:
        row_indices.append(row_id)
        matrix_rows.append(values)

if not matrix_rows:
    log("No valid numeric grid rows could be parsed. Task cannot proceed.")
    analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")
    raise ValueError("No valid numeric grid rows found.")

# Ensure consistent row lengths by truncating to minimum common length
min_len = min(len(r) for r in matrix_rows)
if len(set(len(r) for r in matrix_rows)) != 1:
    log(f"Row lengths vary; truncating all rows to common length {min_len} to form a rectangular matrix.")
matrix = np.array([r[:min_len] for r in matrix_rows], dtype=float)
row_indices = np.array(row_indices, dtype=float)

# If x labels exist and match matrix width, use them; otherwise infer from row 1
if len(x_labels) >= min_len:
    x_labels = np.array(x_labels[:min_len], dtype=float)
else:
    x_labels = np.arange(min_len, dtype=float)
    log("Insufficient x-axis labels detected; using column indices as fallback labels.")

log(f"Parsed matrix shape: {matrix.shape[0]} rows x {matrix.shape[1]} cols.")
log(f"Row index range: {row_indices.min()} to {row_indices.max()}")
log(f"Column label range: {x_labels.min()} to {x_labels.max()}")

# Determine orientation:
# Since row indices increase downward in the file, we preserve the parsed order unless
# the data appear to be reversed by label convention. We inspect whether row indices are ascending.
ascending_rows = np.all(np.diff(row_indices) > 0)
if ascending_rows:
    log("Row indices are ascending in the file; preserving row order for plotting.")
else:
    log("Row indices are not strictly ascending; preserving file order to avoid unsupported reorientation.")

# Step 1: Convert values into 2D matrix with correct row/column ordering.
log("Step 1: Matrix conversion completed using rows with numeric first-column indices and contiguous numeric data.")
log("Validation: matrix contains only finite numeric values after parsing." if np.all(np.isfinite(matrix)) else "Validation warning: matrix contains non-finite values.")

# Step 2: Plot the matrix as a heatmap or image with a colorbar.
log("Step 2: Rendering heatmap/image-style plot with colorbar.")
fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

# Use extent to preserve labels if available
extent = [x_labels[0], x_labels[-1], row_indices[-1], row_indices[0]] if len(x_labels) > 1 else None

im = ax.imshow(
    matrix,
    aspect="auto",
    origin="upper",
    cmap="viridis",
    interpolation="nearest",
    extent=extent
)

cbar = fig.colorbar(im, ax=ax)
cbar.set_label("Intensity / value", rotation=90)

# Step 3: Preserve any directly available labels or annotations from the file.
log("Step 3: Preserving directly available labels from the spreadsheet where possible.")
if len(x_labels) > 1:
    # Reduce tick density for readability
    n_xticks = min(10, len(x_labels))
    xtick_idx = np.linspace(0, len(x_labels) - 1, n_xticks).astype(int)
    ax.set_xticks(x_labels[xtick_idx])
    ax.set_xticklabels([f"{x_labels[i]:g}" for i in xtick_idx], rotation=45, ha="right")
    ax.set_xlabel("Column index / x-axis label")
else:
    ax.set_xlabel("Column index")

n_yticks = min(10, len(row_indices))
ytick_idx = np.linspace(0, len(row_indices) - 1, n_yticks).astype(int)
if extent is None:
    ax.set_yticks(ytick_idx)
    ax.set_yticklabels([f"{row_indices[i]:g}" for i in ytick_idx])
else:
    ax.set_yticks(row_indices[ytick_idx])
    ax.set_yticklabels([f"{row_indices[i]:g}" for i in ytick_idx])
ax.set_ylabel("Row index / y-axis label")

ax.set_title("Reconstructed 2D map from Fig3h.xlsx")
ax.set_xlim(0, matrix.shape[1] - 1 if extent is None else x_labels[-1])
ax.set_ylim(matrix.shape[0] - 1 if extent is None else row_indices[-1], 0 if extent is None else row_indices[0])

# Add a subtle grid for readability
ax.grid(False)

plt.tight_layout()

# Step 4: Save the final visualization.
log("Step 4: Saving final visualization.")
fig.savefig(figure_path, bbox_inches="tight")
plt.close(fig)
log(f"Figure saved to: {figure_path}")

# Write analysis file
analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")