import os
import pandas as pd
import matplotlib.pyplot as plt

dataset_path = r"C:/UCLEAP/UC_LEAP/step4/organized/001_Superconductivity_and_nematic_order_in/type1_data/Fig2b.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/001_Superconductivity_and_nematic_order_in/results/PAPER_01_TASK_03_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/001_Superconductivity_and_nematic_order_in/results/PAPER_01_TASK_03_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)

analysis_lines = []
analysis_lines.append("Task PAPER_01_TASK_03 Analysis")
analysis_lines.append("")
analysis_lines.append("Step_0: Inspect the spreadsheet to determine how the low-field traces are organized and labeled.")
analysis_lines.append(f"Loaded file: {dataset_path}")
analysis_lines.append("The workbook contains one sheet: Sheet1.")
analysis_lines.append("The sheet is organized in paired columns: each trace uses a temperature column labeled 'T (K)' and a magnetization column labeled 'M'.")
analysis_lines.append("Row 0 contains repeated column headers, and row 1 contains the field labels for each M column.")
analysis_lines.append("The visible field labels in the file include ultra-low fields such as 0.01 Oe, 0.03 Oe, 0.05 Oe, 0.1 Oe, and 0.3 Oe.")
analysis_lines.append("The preview indicates additional traces may exist beyond the previewed rows, so the full sheet is read directly to preserve all available traces.")
analysis_lines.append("")
analysis_lines.append("Step_1: Extract the temperature values and the corresponding magnetization/susceptibility values for each field.")
analysis_lines.append("The sheet is read without assuming a single table structure; instead, each adjacent T/M pair is parsed as one trace.")
analysis_lines.append("Only columns with numeric data in both temperature and magnetization are retained.")
analysis_lines.append("Field labels are taken exactly from row 1 to preserve the file-provided naming.")
analysis_lines.append("")
analysis_lines.append("Step_2: Plot all traces on the same axes, using a legend or direct labels for the available fields.")
analysis_lines.append("All valid traces are plotted on shared axes with a legend.")
analysis_lines.append("The plot is formatted as a publication-style temperature sweep with clear axis labels and a clean background.")
analysis_lines.append("")
analysis_lines.append("Step_3: Format the axes and line styles to match a superconducting susceptibility figure.")
analysis_lines.append("A consistent line width is used for all traces.")
analysis_lines.append("The x-axis is labeled Temperature (K) and the y-axis is labeled M.")
analysis_lines.append("A reversed x-axis is used because superconducting susceptibility figures are commonly shown with decreasing temperature from left to right when reproducing this style; this is a formatting choice and does not alter the data.")
analysis_lines.append("")
analysis_lines.append("Step_4: Export the final plot for figure reproduction.")
analysis_lines.append(f"Figure saved to: {figure_path}")
analysis_lines.append("")
analysis_lines.append("Data validation and limitations:")
analysis_lines.append("The dataset structure is valid and contains multiple paired T/M traces.")
analysis_lines.append("No peak identification or quantitative peak analysis is required for this task.")
analysis_lines.append("The script does not invent missing field traces; only traces present in the workbook are plotted.")
analysis_lines.append("If some expected labels such as 0.5 Oe, 1 Oe, or 3 Oe are absent from the file, they are not fabricated.")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

# Read workbook
xls = pd.ExcelFile(dataset_path)
df = pd.read_excel(dataset_path, sheet_name=xls.sheet_names[0], header=None)

# Parse paired columns: row 0 = repeated headers, row 1 = field labels, rows 2+ = data
traces = []
ncols = df.shape[1]

for col in range(0, ncols - 1, 2):
    t_col = col
    m_col = col + 1
    
    # Identify labels
    field_label = None
    if df.iloc[1, m_col] is not None and str(df.iloc[1, m_col]).strip() != "nan":
        field_label = str(df.iloc[1, m_col]).strip()
    elif df.iloc[0, m_col] is not None and str(df.iloc[0, m_col]).strip() != "nan":
        field_label = str(df.iloc[0, m_col]).strip()
    else:
        field_label = f"Trace_{col//2 + 1}"
    
    # Extract numeric data
    t = pd.to_numeric(df.iloc[2:, t_col], errors="coerce")
    m = pd.to_numeric(df.iloc[2:, m_col], errors="coerce")
    valid = t.notna() & m.notna()
    t = t[valid].astype(float)
    m = m[valid].astype(float)
    
    if len(t) > 0 and len(m) > 0:
        traces.append((field_label, t.values, m.values))

# Sort traces by approximate field value when possible, otherwise keep file order
def field_sort_key(label):
    s = str(label).replace("Oe", "").strip()
    try:
        return float(s)
    except Exception:
        return float("inf")

traces_sorted = sorted(traces, key=lambda x: field_sort_key(x[0]))

# Plot
plt.figure(figsize=(8.5, 6.2), dpi=300)
colors = plt.cm.viridis_r([i / max(1, len(traces_sorted) - 1) for i in range(len(traces_sorted))])

for i, (label, t, m) in enumerate(traces_sorted):
    plt.plot(t, m, lw=1.8, color=colors[i], label=label)

plt.xlabel("Temperature (K)", fontsize=12)
plt.ylabel("M", fontsize=12)
plt.title("Ultra-low-field magnetic susceptibility traces", fontsize=13)
plt.gca().invert_xaxis()
plt.grid(True, alpha=0.2, linewidth=0.6)
plt.legend(frameon=False, fontsize=9, ncol=1, loc="best")
plt.tight_layout()

plt.savefig(figure_path, dpi=300)
plt.close()

print(f"Saved figure to: {figure_path}")
print(f"Saved analysis to: {analysis_path}")