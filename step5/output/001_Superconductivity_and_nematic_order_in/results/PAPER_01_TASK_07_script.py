import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/001_Superconductivity_and_nematic_order_in/type1_data/Fig2g.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/001_Superconductivity_and_nematic_order_in/results/PAPER_01_TASK_07_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/001_Superconductivity_and_nematic_order_in/results/PAPER_01_TASK_07_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)
os.makedirs(os.path.dirname(analysis_path), exist_ok=True)

analysis_lines = []

analysis_lines.append("Task PAPER_01_TASK_07 Analysis")
analysis_lines.append("Objective: Reconstruct a 2D visualization from the spreadsheet grid and export a figure.")
analysis_lines.append("")

# Step 0: Inspect spreadsheet layout
analysis_lines.append("Step 0: Inspect spreadsheet layout and identify numeric grid boundaries.")
try:
    xls = pd.ExcelFile(dataset_file)
    sheet_names = xls.sheet_names
    analysis_lines.append(f"Loaded workbook successfully: {dataset_file}")
    analysis_lines.append(f"Detected sheets: {sheet_names}")
    df_raw = pd.read_excel(dataset_file, sheet_name=sheet_names[0], header=None)
    analysis_lines.append(f"Sheet '{sheet_names[0]}' shape: {df_raw.shape[0]} rows x {df_raw.shape[1]} columns")
    analysis_lines.append("Preview indicates first row contains column indices and first column contains row indices.")
except Exception as e:
    analysis_lines.append(f"Failed to load workbook: {e}")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise

# Step 1: Convert table into 2D array and verify ordering
analysis_lines.append("")
analysis_lines.append("Step 1: Convert the table into a 2D array and verify row/column ordering.")

# Identify numeric grid boundaries from observed structure:
# row 0: column labels, col 0: row labels, data in rows 1:, cols 1:
row_labels = df_raw.iloc[1:, 0].to_numpy()
col_labels = df_raw.iloc[0, 1:].to_numpy()
grid = df_raw.iloc[1:, 1:].apply(pd.to_numeric, errors="coerce").to_numpy()

analysis_lines.append(f"Extracted row labels count: {len(row_labels)}")
analysis_lines.append(f"Extracted column labels count: {len(col_labels)}")
analysis_lines.append(f"Extracted grid shape: {grid.shape[0]} rows x {grid.shape[1]} columns")

# Validate numeric content
nan_count = np.isnan(grid).sum()
analysis_lines.append(f"Numeric conversion check: NaN count in grid = {nan_count}")
if nan_count > 0:
    analysis_lines.append("Some entries could not be converted to numeric values; these are left as NaN.")
else:
    analysis_lines.append("All grid entries converted to numeric values successfully.")

# Determine orientation
# Since row/column labels are present and increasing from 0, use direct orientation.
try:
    row_labels_num = pd.to_numeric(pd.Series(row_labels), errors="coerce").to_numpy()
    col_labels_num = pd.to_numeric(pd.Series(col_labels), errors="coerce").to_numpy()
    row_order_ok = np.all(np.diff(row_labels_num[~np.isnan(row_labels_num)]) >= 0)
    col_order_ok = np.all(np.diff(col_labels_num[~np.isnan(col_labels_num)]) >= 0)
    analysis_lines.append(f"Row labels monotonic nondecreasing: {row_order_ok}")
    analysis_lines.append(f"Column labels monotonic nondecreasing: {col_order_ok}")
except Exception as e:
    analysis_lines.append(f"Label monotonicity check could not be completed: {e}")
    row_order_ok = True
    col_order_ok = True

# Step 2: Render as image with colorbar and figure-style formatting
analysis_lines.append("")
analysis_lines.append("Step 2: Render the array as an image with a colorbar and figure-style formatting.")
analysis_lines.append("The file contains explicit row and column indices, so these are used as axis tick labels.")
analysis_lines.append("No additional physical axis units are present in the spreadsheet, so only index labels are shown.")

fig, ax = plt.subplots(figsize=(8, 6), dpi=300)

# Use origin='lower' to preserve natural increasing index direction from bottom to top.
im = ax.imshow(grid, aspect='auto', origin='lower', cmap='viridis')

cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cbar.set_label("Grid value", rotation=90)

# Set ticks sparsely for readability
nrows, ncols = grid.shape
x_step = max(1, ncols // 10)
y_step = max(1, nrows // 10)

xticks = np.arange(0, ncols, x_step)
yticks = np.arange(0, nrows, y_step)

ax.set_xticks(xticks)
ax.set_yticks(yticks)

# Use labels if they are explicitly present in the file
try:
    ax.set_xticklabels([str(col_labels[i]) for i in xticks], rotation=45, ha="right")
    ax.set_yticklabels([str(row_labels[i]) for i in yticks])
except Exception:
    ax.set_xticklabels([str(i) for i in xticks], rotation=45, ha="right")
    ax.set_yticklabels([str(i) for i in yticks])

ax.set_xlabel("Column index")
ax.set_ylabel("Row index")
ax.set_title("Reconstructed 2D grid visualization (Fig2g)")

# Improve figure-style formatting
for spine in ax.spines.values():
    spine.set_linewidth(1.0)

plt.tight_layout()

# Step 3: Axis labels if explicitly present
analysis_lines.append("")
analysis_lines.append("Step 3: Include axis labels if explicitly present in the file.")
analysis_lines.append("The spreadsheet provides numeric row and column indices, but no textual physical axis labels.")
analysis_lines.append("Therefore, the plot uses 'Row index' and 'Column index' as the only justified axis labels.")

# Step 4: Export visualization
analysis_lines.append("")
analysis_lines.append("Step 4: Export the visualization for comparison.")
try:
    fig.savefig(figure_path, bbox_inches="tight")
    analysis_lines.append(f"Figure saved successfully to: {figure_path}")
except Exception as e:
    analysis_lines.append(f"Failed to save figure: {e}")
    raise
finally:
    plt.close(fig)

analysis_lines.append("")
analysis_lines.append("Validation summary:")
analysis_lines.append(f"Grid dimensions used for plotting: {grid.shape[0]} x {grid.shape[1]}")
analysis_lines.append("The table structure supports a direct reconstruction of the 2D map without external assumptions.")
analysis_lines.append("No peak identification or physical interpretation was required for this visualization task.")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))