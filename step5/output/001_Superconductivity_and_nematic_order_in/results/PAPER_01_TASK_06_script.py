import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/001_Superconductivity_and_nematic_order_in/type1_data/Fig2e.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/001_Superconductivity_and_nematic_order_in/results/PAPER_01_TASK_06_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/001_Superconductivity_and_nematic_order_in/results/PAPER_01_TASK_06_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)

analysis_lines = []
analysis_lines.append("Task PAPER_01_TASK_06 Analysis")
analysis_lines.append("")
analysis_lines.append("Step_0: Inspect the workbook to identify the grid structure and any axis/index information.")
analysis_lines.append(f"Loaded workbook: {dataset_file}")
try:
    xls = pd.ExcelFile(dataset_file)
    analysis_lines.append(f"Workbook sheets: {xls.sheet_names}")
    df = pd.read_excel(dataset_file, sheet_name=xls.sheet_names[0], header=None)
    analysis_lines.append(f"Raw sheet shape: {df.shape[0]} rows x {df.shape[1]} columns")
except Exception as e:
    analysis_lines.append(f"Failed to load workbook: {e}")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise

analysis_lines.append("")
analysis_lines.append("Observed structure from preview and loaded sheet:")
analysis_lines.append("The first row contains column index labels as strings/numbers.")
analysis_lines.append("The first column contains row index labels.")
analysis_lines.append("The remaining cells contain numeric grid values.")
analysis_lines.append("This indicates a structured matrix with one header row and one header column.")

# Parse axis labels and matrix
try:
    col_labels = pd.to_numeric(df.iloc[0, 1:], errors="coerce").to_numpy()
    row_labels = pd.to_numeric(df.iloc[1:, 0], errors="coerce").to_numpy()
    matrix = df.iloc[1:, 1:].apply(pd.to_numeric, errors="coerce").to_numpy()
except Exception as e:
    analysis_lines.append(f"Failed during parsing: {e}")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise

analysis_lines.append("")
analysis_lines.append("Step_1: Parse the numeric values into a 2D matrix with correct orientation.")
analysis_lines.append(f"Parsed row labels count: {len(row_labels)}")
analysis_lines.append(f"Parsed column labels count: {len(col_labels)}")
analysis_lines.append(f"Parsed matrix shape: {matrix.shape[0]} x {matrix.shape[1]}")
analysis_lines.append("Orientation decision: use the matrix as stored in the sheet, with rows mapped to the y-axis and columns mapped to the x-axis.")
analysis_lines.append("This is supported by the explicit row/column index headers in the first column and first row.")

# Validate data
valid_numeric = np.isfinite(matrix).all()
analysis_lines.append("")
analysis_lines.append("Validation of data quality:")
analysis_lines.append(f"All matrix entries finite: {valid_numeric}")
analysis_lines.append(f"Row labels finite: {np.isfinite(row_labels).all()}")
analysis_lines.append(f"Column labels finite: {np.isfinite(col_labels).all()}")
analysis_lines.append(f"Matrix value range: min={np.nanmin(matrix):.6e}, max={np.nanmax(matrix):.6e}")
analysis_lines.append("No peak identification is required for this task; the goal is direct 2D visualization of the grid.")

# Plot
analysis_lines.append("")
analysis_lines.append("Step_2: Plot the matrix as a heatmap or image with a colorbar.")
fig, ax = plt.subplots(figsize=(8, 4.5), dpi=200)

extent = [col_labels[0], col_labels[-1], row_labels[0], row_labels[-1]]
im = ax.imshow(
    matrix,
    origin="lower",
    aspect="auto",
    extent=extent,
    cmap="viridis",
    interpolation="nearest"
)
cbar = plt.colorbar(im, ax=ax)
cbar.set_label("Grid value")

analysis_lines.append("Used imshow with origin='lower' to preserve the natural increasing order of the provided indices.")
analysis_lines.append("Used extent derived from the explicit row and column labels so the axes reflect the spreadsheet indexing.")

# Labels only if inferable
analysis_lines.append("")
analysis_lines.append("Step_3: Add labels or annotations only if directly inferable from the file.")
ax.set_xlabel("Column index")
ax.set_ylabel("Row index")
ax.set_title("Reconstructed 2D map from Fig2e.xlsx")

analysis_lines.append("Axis labels were added generically as 'Column index' and 'Row index' because the file provides only numeric indices, not physical units.")
analysis_lines.append("No additional annotations were added because no further metadata is present in the spreadsheet.")

plt.tight_layout()

# Save figure
analysis_lines.append("")
analysis_lines.append("Step_4: Save the reconstructed figure panel.")
fig.savefig(figure_path, bbox_inches="tight")
plt.close(fig)
analysis_lines.append(f"Saved figure to: {figure_path}")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(json.dumps({
    "figure_saved": figure_path,
    "analysis_saved": analysis_path,
    "matrix_shape": matrix.shape
}, indent=2))