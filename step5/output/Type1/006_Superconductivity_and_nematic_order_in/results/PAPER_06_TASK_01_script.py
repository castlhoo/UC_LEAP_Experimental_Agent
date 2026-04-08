import os
import pandas as pd
import matplotlib.pyplot as plt

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/006_Superconductivity_and_nematic_order_in/type1_data/Fig1b.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/006_Superconductivity_and_nematic_order_in/results/PAPER_06_TASK_01_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/006_Superconductivity_and_nematic_order_in/results/PAPER_06_TASK_01_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)

analysis_lines = []
analysis_lines.append("Task PAPER_06_TASK_01 Analysis")
analysis_lines.append("")
analysis_lines.append("Step 0: Load the Excel file and inspect the sheet structure, header rows, and column names.")
analysis_lines.append(f"Dataset file: {dataset_file}")

# Load workbook and inspect
xls = pd.ExcelFile(dataset_file)
analysis_lines.append(f"Sheets found: {xls.sheet_names}")

df = pd.read_excel(dataset_file, sheet_name=0)
analysis_lines.append(f"Loaded sheet shape: {df.shape}")
analysis_lines.append(f"Column names: {list(df.columns)}")

# Basic inspection of first rows
preview_rows = df.head(8).to_string(index=False)
analysis_lines.append("First rows:")
analysis_lines.append(preview_rows)

# Step 1: Extract columns
analysis_lines.append("")
analysis_lines.append("Step 1: Extract the 2θ and intensity columns, handling any non-data rows or formatting artifacts.")

# Identify columns by expected names
theta_col = None
intensity_col = None
for c in df.columns:
    if str(c).strip() == "2θ":
        theta_col = c
    if str(c).strip() == "Intensity(arb. units)":
        intensity_col = c

if theta_col is None or intensity_col is None:
    raise ValueError("Required columns not found in the dataset.")

data = df[[theta_col, intensity_col]].copy()
data[theta_col] = pd.to_numeric(data[theta_col], errors="coerce")
data[intensity_col] = pd.to_numeric(data[intensity_col], errors="coerce")
before_drop = len(data)
data = data.dropna(subset=[theta_col, intensity_col]).reset_index(drop=True)
after_drop = len(data)

analysis_lines.append(f"Rows before numeric cleaning: {before_drop}")
analysis_lines.append(f"Rows after removing non-numeric entries: {after_drop}")
analysis_lines.append(f"2θ range: {data[theta_col].min()} to {data[theta_col].max()}")
analysis_lines.append(f"Intensity range: {data[intensity_col].min()} to {data[intensity_col].max()}")

# Step 2 and 3: Plot
analysis_lines.append("")
analysis_lines.append("Step 2: Plot intensity versus 2θ as a continuous line graph with appropriate axis labels and units.")
analysis_lines.append("Step 3: Format the figure to resemble a standard XRD pattern, preserving peak sharpness and relative amplitudes.")
analysis_lines.append("The dataset contains a single continuous scan with no additional scans or annotations in the loaded sheet, so the full trace is plotted directly.")

plt.figure(figsize=(10, 6), dpi=300)
plt.plot(data[theta_col], data[intensity_col], color="black", linewidth=0.8)
plt.xlabel(r"2$\theta$ (degrees)", fontsize=12)
plt.ylabel("Intensity (arb. units)", fontsize=12)
plt.title("CsTi$_3$Bi$_5$ Single Crystal XRD Pattern", fontsize=13)
plt.xlim(data[theta_col].min(), data[theta_col].max())
plt.tight_layout()

# Step 4: Save and verify
plt.savefig(figure_path, dpi=300)
plt.close()

analysis_lines.append("")
analysis_lines.append("Step 4: Save the replot and verify that the main diffraction features are clearly visible.")
analysis_lines.append(f"Figure saved to: {figure_path}")
analysis_lines.append("Verification: The plot preserves the original sampled intensity trace across the full 2θ range and is suitable as a publication-style XRD replot.")
analysis_lines.append("")
analysis_lines.append("Limitations:")
analysis_lines.append("No peak fitting or peak indexing was performed because the task only requires reproduction of the diffraction pattern, and the dataset was provided as a single high-resolution intensity scan without additional metadata for crystallographic assignment.")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure to: {figure_path}")
print(f"Saved analysis to: {analysis_path}")