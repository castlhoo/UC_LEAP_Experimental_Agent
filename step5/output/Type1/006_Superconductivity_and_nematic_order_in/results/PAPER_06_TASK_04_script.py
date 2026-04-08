import os
import pandas as pd
import matplotlib.pyplot as plt

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/006_Superconductivity_and_nematic_order_in/type1_data/Fig2c.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/006_Superconductivity_and_nematic_order_in/results/PAPER_06_TASK_04_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/006_Superconductivity_and_nematic_order_in/results/PAPER_06_TASK_04_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)

analysis_lines = []
analysis_lines.append("Task PAPER_06_TASK_04 Analysis")
analysis_lines.append("")
analysis_lines.append("Step 0: Load the spreadsheet and inspect how the two current-bias datasets are arranged.")
analysis_lines.append(f"Loaded file: {dataset_file}")

# Load workbook
xls = pd.ExcelFile(dataset_file)
analysis_lines.append(f"Workbook sheets: {xls.sheet_names}")

df_raw = pd.read_excel(dataset_file, sheet_name=0, header=None)
analysis_lines.append(f"Raw sheet shape: {df_raw.shape[0]} rows x {df_raw.shape[1]} cols")
analysis_lines.append("First few raw rows:")
for i in range(min(8, len(df_raw))):
    analysis_lines.append(f"  Row {i}: {df_raw.iloc[i].tolist()}")

# Identify structure
# Expected: row 0 contains repeated column names, row 1 contains current labels, rows 2+ data
analysis_lines.append("")
analysis_lines.append("Step 1: Extract the temperature and resistance columns for each current value.")
analysis_lines.append("The sheet is arranged as two side-by-side traces in four columns:")
analysis_lines.append("  Columns 0-1: Temperature(K), R for 500 μA")
analysis_lines.append("  Columns 2-3: Temperature(K), R for 1000 μA")

# Clean table
analysis_lines.append("")
analysis_lines.append("Step 2: Clean the table by removing any header duplication or non-data entries.")
header_row = df_raw.iloc[0].tolist()
label_row = df_raw.iloc[1].tolist()
analysis_lines.append(f"Header row: {header_row}")
analysis_lines.append(f"Current label row: {label_row}")

df_500 = df_raw.iloc[2:, [0, 1]].copy()
df_1000 = df_raw.iloc[2:, [2, 3]].copy()
df_500.columns = ["Temperature(K)", "R"]
df_1000.columns = ["Temperature(K)", "R"]

df_500["Temperature(K)"] = pd.to_numeric(df_500["Temperature(K)"], errors="coerce")
df_500["R"] = pd.to_numeric(df_500["R"], errors="coerce")
df_1000["Temperature(K)"] = pd.to_numeric(df_1000["Temperature(K)"], errors="coerce")
df_1000["R"] = pd.to_numeric(df_1000["R"], errors="coerce")

df_500 = df_500.dropna().reset_index(drop=True)
df_1000 = df_1000.dropna().reset_index(drop=True)

analysis_lines.append(f"Cleaned 500 μA trace: {len(df_500)} valid points")
analysis_lines.append(f"Cleaned 1000 μA trace: {len(df_1000)} valid points")

analysis_lines.append("Sample cleaned data for 500 μA:")
for i in range(min(5, len(df_500))):
    analysis_lines.append(f"  {df_500.iloc[i].to_dict()}")
analysis_lines.append("Sample cleaned data for 1000 μA:")
for i in range(min(5, len(df_1000))):
    analysis_lines.append(f"  {df_1000.iloc[i].to_dict()}")

# Validate data ranges
analysis_lines.append("")
analysis_lines.append("Data validation:")
analysis_lines.append(f"  500 μA temperature range: {df_500['Temperature(K)'].min():.6g} to {df_500['Temperature(K)'].max():.6g} K")
analysis_lines.append(f"  500 μA resistance range: {df_500['R'].min():.6g} to {df_500['R'].max():.6g}")
analysis_lines.append(f"  1000 μA temperature range: {df_1000['Temperature(K)'].min():.6g} to {df_1000['Temperature(K)'].max():.6g} K")
analysis_lines.append(f"  1000 μA resistance range: {df_1000['R'].min():.6g} to {df_1000['R'].max():.6g}")

analysis_lines.append("")
analysis_lines.append("Step 3: Plot resistance versus temperature for both current biases on the same graph.")
analysis_lines.append("The data show a low-temperature transport transition region and are suitable for a comparative line plot.")
analysis_lines.append("No peak-finding or additional quantitative interpretation is required for this task; the figure is a direct replot of the measured traces.")

# Plot
plt.figure(figsize=(7.2, 5.2), dpi=300)
plt.plot(df_500["Temperature(K)"], df_500["R"], color="#1f77b4", lw=1.8, label="500 μA")
plt.plot(df_1000["Temperature(K)"], df_1000["R"], color="#d62728", lw=1.8, label="1000 μA")

analysis_lines.append("")
analysis_lines.append("Step 4: Add a legend identifying the current values and format the axes for a low-temperature transport figure.")

plt.xlabel("Temperature (K)", fontsize=12)
plt.ylabel("Resistance (R)", fontsize=12)
plt.legend(frameon=False, fontsize=11, loc="best")
plt.tick_params(direction="in", top=True, right=True, labelsize=10)
plt.tight_layout()

plt.savefig(figure_path, bbox_inches="tight")
plt.close()

analysis_lines.append(f"Figure saved to: {figure_path}")
analysis_lines.append("The resulting plot contains two curves labeled by current bias and preserves the original temperature-resistance trends.")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))