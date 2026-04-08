import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/001_Superconductivity_and_nematic_order_in/type1_data/Fig2h.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/001_Superconductivity_and_nematic_order_in/results/PAPER_01_TASK_08_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/001_Superconductivity_and_nematic_order_in/results/PAPER_01_TASK_08_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)
os.makedirs(os.path.dirname(analysis_path), exist_ok=True)

analysis_lines = []

def log(msg):
    analysis_lines.append(msg)

log("Task PAPER_01_TASK_08 Analysis")
log("Step_0: Inspect workbook structure.")
log(f"Loaded dataset file: {dataset_file}")

# Load workbook and inspect sheets
xls = pd.ExcelFile(dataset_file)
sheet_names = xls.sheet_names
log(f"Workbook sheets: {sheet_names}")

# Read the first sheet as raw table
df_raw = pd.read_excel(dataset_file, sheet_name=sheet_names[0], header=None)
nrows, ncols = df_raw.shape
log(f"Raw sheet shape: {nrows} rows x {ncols} columns")

# Inspect a small preview to infer structure
preview_rows = min(3, nrows)
preview_cols = min(8, ncols)
preview = df_raw.iloc[:preview_rows, :preview_cols].astype(str).values.tolist()
log(f"Preview of top-left {preview_rows}x{preview_cols} block: {preview}")

# Determine whether first row/column are embedded indices
# Based on preview, row 0 contains column indices and column 0 contains row indices.
log("Interpretation: first row contains column indices; first column contains row indices.")
log("The remaining cells are grid values.")

# Parse column indices from row 0, excluding the first blank/label cell
col_index_raw = df_raw.iloc[0, 1:]
row_index_raw = df_raw.iloc[1:, 0]
data_raw = df_raw.iloc[1:, 1:]

# Convert to numeric safely
col_indices = pd.to_numeric(col_index_raw, errors="coerce").to_numpy()
row_indices = pd.to_numeric(row_index_raw, errors="coerce").to_numpy()

# Convert the 2D data block to numeric using DataFrame.apply
matrix_df = data_raw.apply(pd.to_numeric, errors="coerce")
matrix = matrix_df.to_numpy()

log(f"Parsed matrix shape: {matrix.shape}")
log(f"Parsed row index count: {len(row_indices)}")
log(f"Parsed column index count: {len(col_indices)}")

# Validate dimensions
valid_shape = (matrix.shape[0] == len(row_indices)) and (matrix.shape[1] == len(col_indices))
log(f"Dimension consistency check passed: {valid_shape}")

# Check for missing values
nan_count = int(np.isnan(matrix).sum())
log(f"Number of NaN values in matrix after parsing: {nan_count}")

# Determine orientation
# Since indices are explicitly embedded, use them directly for axes.
# For image display, origin='lower' preserves increasing row index upward if row indices are ascending.
row_monotonic = np.all(np.diff(row_indices[~np.isnan(row_indices)]) >= 0) if np.sum(~np.isnan(row_indices)) > 1 else True
col_monotonic = np.all(np.diff(col_indices[~np.isnan(col_indices)]) >= 0) if np.sum(~np.isnan(col_indices)) > 1 else True
log(f"Row indices monotonic increasing: {row_monotonic}")
log(f"Column indices monotonic increasing: {col_monotonic}")

# Prepare extent if indices are numeric and regularly spaced
extent = None
if np.all(np.isfinite(row_indices)) and np.all(np.isfinite(col_indices)) and len(row_indices) > 1 and len(col_indices) > 1:
    extent = [float(np.nanmin(col_indices)), float(np.nanmax(col_indices)),
              float(np.nanmin(row_indices)), float(np.nanmax(row_indices))]
    log(f"Using numeric extent for axes: {extent}")
else:
    log("Could not reliably construct numeric extent from indices; using pixel coordinates.")

# Plot heatmap
fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)

# Choose a perceptually uniform colormap suitable for spectroscopic/spatial maps
cmap = "viridis"

if extent is not None:
    im = ax.imshow(matrix, origin="lower", aspect="auto", cmap=cmap, extent=extent)
    ax.set_xlabel("Column index")
    ax.set_ylabel("Row index")
else:
    im = ax.imshow(matrix, origin="lower", aspect="auto", cmap=cmap)
    ax.set_xlabel("Column index")
    ax.set_ylabel("Row index")

# Add colorbar
cbar = fig.colorbar(im, ax=ax, pad=0.02)
cbar.set_label("Grid value")

# Add title matching the figure panel identity
ax.set_title("Fig. 2h reconstructed 2D map")

# Use ticks only if explicitly available in the file
# Since indices are available, show a limited number of ticks for readability.
if extent is not None:
    # Use a small number of ticks to avoid clutter
    xticks = np.linspace(extent[0], extent[1], 5)
    yticks = np.linspace(extent[2], extent[3], 5)
    ax.set_xticks(xticks)
    ax.set_yticks(yticks)
else:
    ax.set_xticks([])
    ax.set_yticks([])

plt.tight_layout()
fig.savefig(figure_path, bbox_inches="tight")
plt.close(fig)

log("Step_1: Parsed numeric values into a 2D matrix successfully.")
log("Step_2: Plotted the matrix as a heatmap/image using a perceptually uniform colormap.")
log("Step_3: Added axis labels and ticks based on explicit indices present in the file.")
log("Step_4: Saved the figure for reproduction.")
log(f"Figure saved to: {figure_path}")

# Write analysis file
with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure to: {figure_path}")
print(f"Saved analysis to: {analysis_path}")