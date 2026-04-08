import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/006_Superconductivity_and_nematic_order_in/type1_data/Fig2d.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/006_Superconductivity_and_nematic_order_in/results/PAPER_06_TASK_05_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/006_Superconductivity_and_nematic_order_in/results/PAPER_06_TASK_05_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)

analysis_lines = []

def log(msg):
    analysis_lines.append(msg)

log("Task PAPER_06_TASK_05 Analysis")
log("Objective: Inspect the spreadsheet structure, reconstruct the matrix-style numerical dataset, and visualize it faithfully.")
log("")
log(f"Step 0: Loading spreadsheet from: {dataset_file}")

# Load workbook and inspect structure
xls = pd.ExcelFile(dataset_file)
sheet_names = xls.sheet_names
log(f"Workbook sheets found: {sheet_names}")

df_raw = pd.read_excel(dataset_file, sheet_name=sheet_names[0], header=None)
log(f"Loaded sheet '{sheet_names[0]}' with shape {df_raw.shape[0]} rows x {df_raw.shape[1]} columns.")

# Inspect preview-like structure
log("Observed structure from raw sheet:")
for i in range(min(3, df_raw.shape[0])):
    row_preview = df_raw.iloc[i, :min(20, df_raw.shape[1])].tolist()
    log(f"  Row {i}: {row_preview}")

log("")
log("Step 1: Identifying axis values and table orientation.")
log("The first row contains column-like numeric labels starting at 0, while the first column contains row-like labels starting at 0.")
log("The second row appears to contain x-axis values spanning approximately -2.0 upward in small increments.")
log("The third row contains very small numerical values (~1e-11), indicating the data matrix values.")
log("This suggests a 3-row layout: header row, x-axis row, and data row(s).")

# Determine if first cell is blank and extract axis values
header_row = df_raw.iloc[0, 1:].copy()
x_axis_row = df_raw.iloc[1, 1:].copy()
data_rows = df_raw.iloc[2:, 1:].copy()
y_labels = df_raw.iloc[2:, 0].copy()

# Convert numeric values
x_vals = pd.to_numeric(x_axis_row, errors="coerce").to_numpy()
y_vals = pd.to_numeric(y_labels, errors="coerce").to_numpy()
data_vals = data_rows.apply(pd.to_numeric, errors="coerce").to_numpy()

log(f"Extracted x-axis length: {len(x_vals)}")
log(f"Extracted y-axis length (data rows): {len(y_vals)}")
log(f"Extracted data matrix shape before orientation check: {data_vals.shape}")

# Determine orientation
# If there is only one data row, create a 2D array with one row.
if data_vals.ndim == 1:
    data_vals = data_vals[np.newaxis, :]

# Check if transposition is needed based on axis lengths
transpose_needed = False
if len(y_vals) == data_vals.shape[1] and len(x_vals) == data_vals.shape[0]:
    transpose_needed = True
elif len(x_vals) == data_vals.shape[1]:
    transpose_needed = False
elif len(y_vals) == data_vals.shape[0]:
    transpose_needed = False

log(f"Orientation assessment: transpose_needed={transpose_needed}")

if transpose_needed:
    Z = data_vals.T
    x_plot = y_vals
    y_plot = x_vals
    log("Transposed matrix to align axes with data dimensions.")
else:
    Z = data_vals
    x_plot = x_vals
    y_plot = y_vals
    log("Kept matrix orientation as loaded.")

log(f"Final matrix shape for plotting: {Z.shape}")

# Validate numeric content
finite_mask = np.isfinite(Z)
finite_fraction = finite_mask.sum() / Z.size if Z.size else 0
log(f"Finite data fraction: {finite_fraction:.3f}")

if Z.size == 0 or finite_fraction == 0:
    log("Data validation failed: no finite numerical values available for plotting.")
    raise ValueError("No valid numerical data found in the spreadsheet.")

# Summarize value range
z_min = np.nanmin(Z)
z_max = np.nanmax(Z)
z_mean = np.nanmean(Z)
log(f"Data range: min={z_min:.6e}, max={z_max:.6e}, mean={z_mean:.6e}")

log("")
log("Step 2: Reconstructing the matrix into a 2D numerical array.")
log("The dataset is interpreted as a tabulated matrix with one coordinate axis in small increments near -2 to +2 and another axis indexed by integers.")
log("Because the sheet contains only a small number of rows, the data are treated as a matrix-style table rather than a long line trace.")
log("No peak identification is attempted because this task is a visualization/reconstruction task and the values are not a spectral trace.")

# Prepare plot
fig, ax = plt.subplots(figsize=(10, 4.5), dpi=200)

# Choose extent if axes are numeric and monotonic
use_imshow = True
if np.all(np.isfinite(x_plot)) and np.all(np.isfinite(y_plot)) and len(x_plot) > 1 and len(y_plot) > 1:
    if np.all(np.diff(x_plot) > 0) and np.all(np.diff(y_plot) >= 0):
        extent = [x_plot.min(), x_plot.max(), y_plot.min(), y_plot.max()]
    else:
        extent = None
else:
    extent = None

# Plot with a scale suitable for very small values
vabs = np.nanmax(np.abs(Z))
if not np.isfinite(vabs) or vabs == 0:
    vabs = 1.0

im = ax.imshow(
    Z,
    aspect="auto",
    origin="lower",
    cmap="viridis",
    interpolation="nearest",
    extent=extent,
    vmin=z_min,
    vmax=z_max
)

cbar = plt.colorbar(im, ax=ax, pad=0.02)
cbar.set_label("Value")

log("")
log("Step 3: Visualizing the data.")
log("A heatmap/pseudocolor-style image is used because the dataset is matrix-like and the values are small in magnitude.")
log("This representation is appropriate for revealing any spatial structure across the two axes.")

# Axis labeling
if extent is not None:
    ax.set_xlabel("Axis spanning approximately -2.0 to +2.0")
    ax.set_ylabel("Integer-indexed axis")
else:
    ax.set_xlabel("Column coordinate")
    ax.set_ylabel("Row coordinate")

ax.set_title("Reconstructed matrix-style dataset (Fig2d)")
ax.tick_params(direction="out")

# Add annotation about scale
ax.text(
    0.01, 1.02,
    f"Value range: {z_min:.2e} to {z_max:.2e}",
    transform=ax.transAxes,
    fontsize=9,
    va="bottom",
    ha="left"
)

plt.tight_layout()
plt.savefig(figure_path, bbox_inches="tight")
plt.close(fig)

log("")
log("Step 4: Final validation and output.")
log(f"Figure saved to: {figure_path}")
log("Axes were labeled using the reconstructed coordinates where possible.")
log("The color scale reflects the very small magnitude of the values directly from the data.")
log("No unsupported assumptions were introduced beyond table orientation inference from the sheet layout.")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure to: {figure_path}")
print(f"Saved analysis to: {analysis_path}")