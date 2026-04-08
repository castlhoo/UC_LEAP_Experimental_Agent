import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/001_Superconductivity_and_nematic_order_in/type1_data/Fig2d.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/001_Superconductivity_and_nematic_order_in/results/PAPER_01_TASK_05_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/001_Superconductivity_and_nematic_order_in/results/PAPER_01_TASK_05_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)
os.makedirs(os.path.dirname(analysis_path), exist_ok=True)

analysis_lines = []

def log(line):
    analysis_lines.append(line)

log("Task PAPER_01_TASK_05: Visualize the 2D grid data for the first spectroscopic map")
log("")
log("Step_0: Inspect the sheet to determine the grid dimensions, index columns, and any embedded axis labels.")
log(f"Loaded dataset file: {dataset_file}")

# Load workbook and inspect structure
xls = pd.ExcelFile(dataset_file)
sheet_names = xls.sheet_names
log(f"Workbook sheets: {sheet_names}")

df_raw = pd.read_excel(dataset_file, sheet_name=sheet_names[0], header=None)
log(f"Raw sheet shape: {df_raw.shape[0]} rows x {df_raw.shape[1]} columns")

# Describe preview structure
preview_rows = min(3, df_raw.shape[0])
preview_cols = min(8, df_raw.shape[1])
log("Initial raw preview (top-left corner):")
for r in range(preview_rows):
    vals = [str(df_raw.iat[r, c]) for c in range(preview_cols)]
    log(f"  Row {r}: {vals}")

# Determine whether first row/column are labels
first_row = df_raw.iloc[0, :]
first_col = df_raw.iloc[:, 0]

# Try to parse numeric content
numeric_df = df_raw.copy()
for c in range(numeric_df.shape[1]):
    numeric_df.iloc[:, c] = pd.to_numeric(numeric_df.iloc[:, c], errors='coerce')

# Heuristic: if first row and first column contain labels, use them as axes
has_row_labels = pd.notna(numeric_df.iloc[1:, 0]).any() and pd.isna(numeric_df.iloc[0, 0])
has_col_labels = pd.notna(numeric_df.iloc[0, 1:]).any() and pd.isna(numeric_df.iloc[0, 0])

# More direct inspection based on preview: row 0 has column indices, col 0 has row indices
# Determine if first row contains x-axis labels and first column contains y-axis labels
x_labels = None
y_labels = None
data_matrix = None

# Attempt to parse first row as x-axis labels and first column as y-axis labels
row0_numeric = pd.to_numeric(df_raw.iloc[0, 1:], errors='coerce')
col0_numeric = pd.to_numeric(df_raw.iloc[1:, 0], errors='coerce')
body_numeric = df_raw.iloc[1:, 1:].apply(pd.to_numeric, errors='coerce')

if row0_numeric.notna().all() and col0_numeric.notna().all() and body_numeric.notna().any().any():
    x_labels = row0_numeric.to_numpy(dtype=float)
    y_labels = col0_numeric.to_numpy(dtype=float)
    data_matrix = body_numeric.to_numpy(dtype=float)
    log("Interpretation: first row contains column-axis labels, first column contains row-axis labels, and the remaining cells form the 2D data grid.")
else:
    # Fallback: treat entire table as numeric grid if no labels are present
    full_numeric = df_raw.apply(pd.to_numeric, errors='coerce')
    if full_numeric.notna().any().any():
        data_matrix = full_numeric.to_numpy(dtype=float)
        log("Interpretation: no clear embedded axis labels were identified; using the numeric table as the 2D grid.")
    else:
        raise ValueError("No numeric data could be parsed from the spreadsheet.")

log("")
log("Step_1: Convert the numeric table into a 2D array with the correct orientation.")

if data_matrix is None:
    raise ValueError("Data matrix could not be constructed.")

log(f"Constructed data matrix shape: {data_matrix.shape[0]} rows x {data_matrix.shape[1]} columns")

# Validate matrix content
finite_mask = np.isfinite(data_matrix)
finite_count = int(np.sum(finite_mask))
total_count = data_matrix.size
log(f"Finite values in matrix: {finite_count}/{total_count}")

if finite_count == 0:
    raise ValueError("Data matrix contains no finite values.")

data_min = float(np.nanmin(data_matrix))
data_max = float(np.nanmax(data_matrix))
data_mean = float(np.nanmean(data_matrix))
log(f"Data range: min={data_min:.6g}, max={data_max:.6g}, mean={data_mean:.6g}")

# Determine orientation: for image display, rows map to y and columns to x
# If labels exist, use them directly; otherwise use pixel indices
log("")
log("Step_2: Render the array as an image/heatmap with a suitable colormap and colorbar.")

fig, ax = plt.subplots(figsize=(8, 4.5), dpi=200)

# Choose extent if axes are available
if x_labels is not None and y_labels is not None and len(x_labels) == data_matrix.shape[1] and len(y_labels) == data_matrix.shape[0]:
    extent = [float(np.min(x_labels)), float(np.max(x_labels)), float(np.min(y_labels)), float(np.max(y_labels))]
    im = ax.imshow(
        data_matrix,
        origin='lower',
        aspect='auto',
        cmap='viridis',
        extent=extent,
        interpolation='nearest'
    )
    log("Used inferred axis labels for extent in the heatmap.")
else:
    im = ax.imshow(
        data_matrix,
        origin='lower',
        aspect='auto',
        cmap='viridis',
        interpolation='nearest'
    )
    log("Used pixel indices for axes because explicit axis labels were not fully available or did not match the data dimensions.")

cbar = plt.colorbar(im, ax=ax)
cbar.set_label("Intensity / value")

log("")
log("Step_3: Add axis labels or tick labels if they can be inferred directly from the spreadsheet structure.")

if x_labels is not None and y_labels is not None and len(x_labels) == data_matrix.shape[1] and len(y_labels) == data_matrix.shape[0]:
    ax.set_xlabel("Column index / inferred x-axis")
    ax.set_ylabel("Row index / inferred y-axis")
    # Use a limited number of ticks for readability
    xtick_positions = np.linspace(0, data_matrix.shape[1] - 1, num=min(6, data_matrix.shape[1]), dtype=int)
    ytick_positions = np.linspace(0, data_matrix.shape[0] - 1, num=min(6, data_matrix.shape[0]), dtype=int)
    ax.set_xticks(xtick_positions)
    ax.set_yticks(ytick_positions)
    ax.set_xticklabels([f"{x_labels[i]:.3g}" for i in xtick_positions], rotation=45, ha='right')
    ax.set_yticklabels([f"{y_labels[i]:.3g}" for i in ytick_positions])
    log("Added inferred axis labels and representative tick labels from the spreadsheet header row and index column.")
else:
    ax.set_xlabel("Column index")
    ax.set_ylabel("Row index")
    log("Added generic index labels because explicit axis labels were not reliably inferable.")

ax.set_title("Reconstructed 2D spectroscopic map")
plt.tight_layout()

log("")
log("Step_4: Export the heatmap for figure comparison.")
fig.savefig(figure_path, bbox_inches='tight')
plt.close(fig)
log(f"Saved figure to: {figure_path}")

log("")
log("Validation and exclusions:")
log("- The spreadsheet structure was inspected before plotting.")
log("- The first row and first column were interpreted as axis labels only because they were numeric and aligned with the remaining grid dimensions.")
log("- No peak-finding or downstream physical interpretation was performed, because the task requires only reconstruction of the 2D map.")
log("- No missing or corrupted data prevented visualization; the grid was successfully converted and plotted.")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure: {figure_path}")
print(f"Saved analysis: {analysis_path}")