import os
import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Paths
dataset_path = Path(r"C:/UCLEAP/UC_LEAP/step4/organized/001_Superconductivity_and_nematic_order_in/type1_data/Fig2i.xlsx")
figure_path = Path(r"C:/UCLEAP/UC_LEAP/step5/output/001_Superconductivity_and_nematic_order_in/results/PAPER_01_TASK_09_figure.png")
analysis_path = Path(r"C:/UCLEAP/UC_LEAP/step5/output/001_Superconductivity_and_nematic_order_in/results/PAPER_01_TASK_09_Analysis.txt")

figure_path.parent.mkdir(parents=True, exist_ok=True)
analysis_path.parent.mkdir(parents=True, exist_ok=True)

analysis_lines = []

def log(msg):
    analysis_lines.append(msg)

log("Task PAPER_01_TASK_09 Analysis")
log("Objective: Reconstruct the 2D spectroscopic map from the spreadsheet and render it as an image-style heatmap.")
log(f"Dataset file: {dataset_path}")

# Step 0: Inspect sheet structure
if not dataset_path.exists():
    log("ERROR: Dataset file does not exist. Task cannot be completed.")
    analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")
    raise FileNotFoundError(f"Missing dataset file: {dataset_path}")

log("Step_0: Inspecting workbook structure.")
try:
    xls = pd.ExcelFile(dataset_path)
    log(f"Workbook sheets: {xls.sheet_names}")
    df_raw = pd.read_excel(dataset_path, sheet_name=xls.sheet_names[0], header=None)
    log(f"Loaded sheet '{xls.sheet_names[0]}' with shape {df_raw.shape[0]} rows x {df_raw.shape[1]} cols.")
except Exception as e:
    log(f"ERROR: Failed to load workbook or sheet: {e}")
    analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")
    raise

# Inspect preview-like structure
log("Observed structure from raw sheet:")
for i in range(min(7, df_raw.shape[0])):
    row_preview = df_raw.iloc[i, :min(20, df_raw.shape[1])].tolist()
    log(f"  Row {i}: {row_preview}")

# Step 1: Convert numeric table into 2D array with correct orientation
log("Step_1: Parsing numeric grid and identifying boundaries.")
# The preview indicates:
# Row 0: column indices
# Column 0: row indices
# Data grid starts at row 1, col 1
try:
    col_labels = pd.to_numeric(df_raw.iloc[0, 1:], errors="coerce")
    row_labels = pd.to_numeric(df_raw.iloc[1:, 0], errors="coerce")
    data = df_raw.iloc[1:, 1:].apply(pd.to_numeric, errors="coerce").to_numpy()
except Exception as e:
    log(f"ERROR: Failed during numeric parsing: {e}")
    analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")
    raise

valid_col_labels = np.isfinite(col_labels.to_numpy())
valid_row_labels = np.isfinite(row_labels.to_numpy())
valid_data = np.isfinite(data)

log(f"Parsed column labels: {len(col_labels)} entries, finite count = {valid_col_labels.sum()}")
log(f"Parsed row labels: {len(row_labels)} entries, finite count = {valid_row_labels.sum()}")
log(f"Parsed data matrix shape: {data.shape}, finite fraction = {valid_data.mean():.4f}")

# Determine if there is any need to transpose:
# Since row labels are in first column and column labels in first row, the data matrix is already oriented as rows x cols.
# We validate by checking dimensions against labels.
if data.shape != (len(row_labels), len(col_labels)):
    log("WARNING: Data shape does not match label dimensions exactly; attempting to reconcile orientation.")
    if data.T.shape == (len(row_labels), len(col_labels)):
        data = data.T
        log("Transposed data matrix to match row/column labels.")
    else:
        log("ERROR: Could not reconcile data orientation with labels. Task cannot proceed reliably.")
        analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")
        raise ValueError("Unable to determine correct orientation.")

# Use only finite labels and data if needed
if not valid_row_labels.all() or not valid_col_labels.all():
    log("WARNING: Some axis labels are non-numeric or missing; using available numeric labels only.")
if not valid_data.all():
    log("WARNING: Some grid values are non-numeric or missing; these will be rendered as masked values.")

# Step 2: Plot as heatmap/image with colorbar
log("Step_2: Rendering heatmap with color scale.")
# Preserve directly available axis labels/annotations from the sheet
x = col_labels.to_numpy(dtype=float)
y = row_labels.to_numpy(dtype=float)

# Determine extent for imshow
if len(x) > 1:
    dx = np.nanmedian(np.diff(x))
else:
    dx = 1.0
if len(y) > 1:
    dy = np.nanmedian(np.diff(y))
else:
    dy = 1.0

extent = [x[0] - dx / 2, x[-1] + dx / 2, y[-1] + dy / 2, y[0] - dy / 2]

masked_data = np.ma.masked_invalid(data)

fig, ax = plt.subplots(figsize=(8, 5.5), dpi=200)
cmap = plt.get_cmap("viridis").copy()
cmap.set_bad(color="lightgray")

im = ax.imshow(
    masked_data,
    aspect="auto",
    origin="upper",
    interpolation="nearest",
    cmap=cmap,
    extent=extent
)

cbar = fig.colorbar(im, ax=ax, pad=0.02)
cbar.set_label("Grid value", rotation=90)

# Step 3: Preserve axis labels/annotations
log("Step_3: Preserving available axis labels from spreadsheet indices.")
ax.set_xlabel("Column index")
ax.set_ylabel("Row index")
ax.set_title("Reconstructed 2D spectroscopic map (Fig2i)")

# Use a manageable number of ticks based on available labels
def choose_ticks(vals, max_ticks=8):
    vals = np.asarray(vals, dtype=float)
    vals = vals[np.isfinite(vals)]
    if len(vals) == 0:
        return []
    if len(vals) <= max_ticks:
        return vals
    idx = np.linspace(0, len(vals) - 1, max_ticks).round().astype(int)
    return vals[idx]

xticks = choose_ticks(x, max_ticks=10)
yticks = choose_ticks(y, max_ticks=8)
ax.set_xticks(xticks)
ax.set_yticks(yticks)

# Improve readability
ax.tick_params(axis='x', rotation=45)
ax.grid(False)

# Step 4: Export reconstructed panel
log("Step_4: Exporting figure.")
try:
    fig.tight_layout()
    fig.savefig(figure_path, bbox_inches="tight")
    plt.close(fig)
    log(f"Figure saved to: {figure_path}")
except Exception as e:
    log(f"ERROR: Failed to save figure: {e}")
    plt.close(fig)
    analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")
    raise

# Final validation and summary
log("Validation summary:")
log(f"  Data matrix used for plotting: shape = {data.shape}")
log(f"  Row labels range: {np.nanmin(y):.6g} to {np.nanmax(y):.6g}")
log(f"  Column labels range: {np.nanmin(x):.6g} to {np.nanmax(x):.6g}")
log("  Orientation decision: data interpreted as rows x columns directly from the spreadsheet, with row indices in the first column and column indices in the first row.")
log("  No peak analysis was required for this visualization task.")
log("  No data were fabricated or inferred beyond the explicit spreadsheet structure.")

analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")
print(f"Saved figure: {figure_path}")
print(f"Saved analysis: {analysis_path}")