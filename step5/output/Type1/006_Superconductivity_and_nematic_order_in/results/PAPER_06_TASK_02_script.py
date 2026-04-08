import os
import re
import math
import pandas as pd
import matplotlib.pyplot as plt

dataset_path = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/006_Superconductivity_and_nematic_order_in/type1_data/Fig2a.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/006_Superconductivity_and_nematic_order_in/results/PAPER_06_TASK_02_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/006_Superconductivity_and_nematic_order_in/results/PAPER_06_TASK_02_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)
os.makedirs(os.path.dirname(analysis_path), exist_ok=True)

analysis_lines = []

def log(line=""):
    analysis_lines.append(line)

log("Task PAPER_06_TASK_02 Analysis")
log("Objective: Replot zero-field-cooled magnetization versus temperature under multiple applied fields.")
log("")
log("Step_0: Load the spreadsheet and determine how repeated temperature/magnetization pairs are arranged.")
try:
    xl = pd.ExcelFile(dataset_path)
    log(f"Loaded Excel file successfully: {dataset_path}")
    log(f"Available sheets: {xl.sheet_names}")
    df_raw = pd.read_excel(dataset_path, sheet_name=xl.sheet_names[0], header=None)
    log(f"Read sheet '{xl.sheet_names[0]}' with shape {df_raw.shape[0]} rows x {df_raw.shape[1]} columns.")
except Exception as e:
    log(f"Failed to load spreadsheet: {e}")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise

log("")
log("Step_1: Identify the field labels associated with each trace and map them to the corresponding columns.")
header_row_0 = df_raw.iloc[0].tolist()
header_row_1 = df_raw.iloc[1].tolist()

pairs = []
col = 0
while col < df_raw.shape[1] - 1:
    temp_label = str(header_row_0[col]).strip() if pd.notna(header_row_0[col]) else ""
    m_label = str(header_row_0[col + 1]).strip() if pd.notna(header_row_0[col + 1]) else ""
    field_label = str(header_row_1[col + 1]).strip() if pd.notna(header_row_1[col + 1]) else ""
    if temp_label == "Temperature (K)" and m_label == "M":
        pairs.append((col, col + 1, field_label))
        col += 2
    else:
        col += 1

log(f"Identified {len(pairs)} temperature/magnetization pairs from the header structure.")
for i, (tcol, mcol, field) in enumerate(pairs, start=1):
    log(f"  Pair {i}: Temperature column {tcol}, M column {mcol}, field label '{field}'")

log("")
log("Step_2: Clean the data by removing blank rows, duplicated headers, or metadata rows if present.")
data_start_row = 2
cleaned_traces = []
for i, (tcol, mcol, field) in enumerate(pairs, start=1):
    sub = df_raw.iloc[data_start_row:, [tcol, mcol]].copy()
    sub.columns = ["Temperature (K)", "M"]
    sub["Temperature (K)"] = pd.to_numeric(sub["Temperature (K)"], errors="coerce")
    sub["M"] = pd.to_numeric(sub["M"], errors="coerce")
    before = len(sub)
    sub = sub.dropna(subset=["Temperature (K)", "M"])
    after = len(sub)
    sub = sub.sort_values("Temperature (K)")
    sub = sub.drop_duplicates(subset=["Temperature (K)", "M"])
    cleaned_traces.append((field if field else f"Trace {i}", sub))
    log(f"  Trace {i} ('{field if field else f'Trace {i}'}'): kept {len(sub)} rows after cleaning from {before} raw rows; removed {before - after} non-numeric/blank rows.")

log("")
log("Step_3: Plot magnetization versus temperature for all field values on the same axes.")
plt.figure(figsize=(8.2, 6.2), dpi=300)

colors = plt.cm.viridis([i / max(1, len(cleaned_traces) - 1) for i in range(len(cleaned_traces))])

for idx, ((field, trace), color) in enumerate(zip(cleaned_traces, colors), start=1):
    if trace.empty:
        log(f"  Trace '{field}' is empty after cleaning and will be excluded from plotting.")
        continue
    tmin = trace["Temperature (K)"].min()
    tmax = trace["Temperature (K)"].max()
    mmin = trace["M"].min()
    mmax = trace["M"].max()
    log(f"  Trace '{field}': temperature range {tmin:.6g} K to {tmax:.6g} K; M range {mmin:.6g} to {mmax:.6g}.")
    plt.plot(trace["Temperature (K)"], trace["M"], lw=1.8, color=color, label=field)

log("")
log("Step_4: Add legend/annotations and format the plot for publication-quality comparison.")
plt.xlabel("Temperature (K)", fontsize=12)
plt.ylabel("Magnetization, M", fontsize=12)
plt.title("Zero-field-cooled magnetization vs temperature under applied fields", fontsize=13)
plt.legend(title="Applied field", fontsize=9, title_fontsize=10, frameon=False, ncol=2)
plt.grid(True, alpha=0.25, linewidth=0.6)
plt.tight_layout()

try:
    plt.savefig(figure_path, dpi=300, bbox_inches="tight")
    log(f"Saved figure to: {figure_path}")
except Exception as e:
    log(f"Failed to save figure: {e}")
    raise

plt.close()

log("")
log("Validation and interpretation notes:")
log("  - The sheet structure contains repeated Temperature (K)/M column pairs with field labels in the second header row.")
log("  - No additional metadata rows were needed beyond the first two header rows.")
log("  - The data were suitable for direct plotting after numeric coercion and removal of blank/non-numeric entries.")
log("  - The resulting figure preserves the field ordering as encountered in the spreadsheet and distinguishes each curve with a legend.")
log("  - No peak-finding or derived quantitative analysis was required for this task; only direct visualization of the measured traces was performed.")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))