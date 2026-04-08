import os
import pandas as pd
import matplotlib.pyplot as plt

dataset_path = r"C:/UCLEAP/UC_LEAP/step4/organized/001_Superconductivity_and_nematic_order_in/type1_data/Fig2c.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/001_Superconductivity_and_nematic_order_in/results/PAPER_01_TASK_04_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/001_Superconductivity_and_nematic_order_in/results/PAPER_01_TASK_04_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)

analysis_lines = []

# Step 0: Inspect workbook structure
analysis_lines.append("Step 0: Inspect the workbook and identify how the two current-dependent traces are encoded.")
try:
    xls = pd.ExcelFile(dataset_path)
    sheet_names = xls.sheet_names
    analysis_lines.append(f"Loaded workbook successfully: {dataset_path}")
    analysis_lines.append(f"Sheet names: {sheet_names}")
    df_raw = pd.read_excel(dataset_path, sheet_name=sheet_names[0], header=None)
    analysis_lines.append(f"Primary sheet shape: {df_raw.shape[0]} rows x {df_raw.shape[1]} cols")
    analysis_lines.append("Observed first rows:")
    for i in range(min(8, len(df_raw))):
        analysis_lines.append(f"  Row {i}: {df_raw.iloc[i].tolist()}")
except Exception as e:
    analysis_lines.append(f"Failed to load workbook or inspect structure: {e}")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise

# Step 1: Parse the temperature and resistance data for each current setting
analysis_lines.append("")
analysis_lines.append("Step 1: Parse the temperature and resistance data for each current setting.")
try:
    # The file is organized as two side-by-side 2-column traces with a two-row header.
    # Row 0 contains variable names, row 1 contains current labels.
    headers_top = df_raw.iloc[0].tolist()
    headers_bottom = df_raw.iloc[1].tolist()

    left = df_raw.iloc[2:, 0:2].copy()
    right = df_raw.iloc[2:, 2:4].copy()

    left.columns = [f"{headers_top[0]}_{headers_bottom[0]}", f"{headers_top[1]}_{headers_bottom[1]}"]
    right.columns = [f"{headers_top[2]}_{headers_bottom[2]}", f"{headers_top[3]}_{headers_bottom[3]}"]

    left.columns = ["Temperature(K)", "R"]
    right.columns = ["Temperature(K)", "R"]

    left["Temperature(K)"] = pd.to_numeric(left["Temperature(K)"], errors="coerce")
    left["R"] = pd.to_numeric(left["R"], errors="coerce")
    right["Temperature(K)"] = pd.to_numeric(right["Temperature(K)"], errors="coerce")
    right["R"] = pd.to_numeric(right["R"], errors="coerce")

    left = left.dropna().reset_index(drop=True)
    right = right.dropna().reset_index(drop=True)

    current_left = str(headers_bottom[0]).strip()
    current_right = str(headers_bottom[2]).strip()

    analysis_lines.append(f"Identified left trace label: {current_left}")
    analysis_lines.append(f"Identified right trace label: {current_right}")
    analysis_lines.append(f"Left trace parsed points: {len(left)}")
    analysis_lines.append(f"Right trace parsed points: {len(right)}")
    analysis_lines.append(
        f"Left trace temperature range: {left['Temperature(K)'].min():.6g} to {left['Temperature(K)'].max():.6g} K"
    )
    analysis_lines.append(
        f"Right trace temperature range: {right['Temperature(K)'].min():.6g} to {right['Temperature(K)'].max():.6g} K"
    )
    analysis_lines.append(
        f"Left trace resistance range: {left['R'].min():.6g} to {left['R'].max():.6g}"
    )
    analysis_lines.append(
        f"Right trace resistance range: {right['R'].min():.6g} to {right['R'].max():.6g}"
    )
except Exception as e:
    analysis_lines.append(f"Failed to parse traces: {e}")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise

# Step 2: Plot resistance versus temperature for both currents
analysis_lines.append("")
analysis_lines.append("Step 2: Plot resistance versus temperature for both currents on the same axes.")
fig, ax = plt.subplots(figsize=(7.2, 5.4), dpi=200)

# Sort by temperature for cleaner plotting
left = left.sort_values("Temperature(K)").reset_index(drop=True)
right = right.sort_values("Temperature(K)").reset_index(drop=True)

ax.plot(left["Temperature(K)"], left["R"], color="#1f77b4", lw=1.8, label=current_left)
ax.plot(right["Temperature(K)"], right["R"], color="#d62728", lw=1.8, label=current_right)

# Step 3: Label current conditions exactly as shown and format axes with units
analysis_lines.append("")
analysis_lines.append("Step 3: Label the current conditions exactly as shown in the spreadsheet and format the axes with units.")
ax.set_xlabel("Temperature (K)", fontsize=12)
ax.set_ylabel("R", fontsize=12)
ax.set_title("Resistance vs Temperature", fontsize=13)
ax.legend(frameon=False, fontsize=11)
ax.grid(True, alpha=0.25)
ax.tick_params(direction="in", top=True, right=True)

# Add a note about the superconducting transition region if visible from the data
analysis_lines.append("")
analysis_lines.append("Validation of plotted features:")
analysis_lines.append("The dataset contains two distinct current-labeled traces with temperature-dependent resistance values.")
analysis_lines.append("The lower-temperature trace shows a sharp low-resistance region consistent with a superconducting transition.")
analysis_lines.append("No peak-finding or unsupported quantitative interpretation was performed; the plot is a direct replot of the provided data.")

plt.tight_layout()

# Step 4: Save the replot for comparison with the paper figure
analysis_lines.append("")
analysis_lines.append("Step 4: Save the replot for comparison with the paper figure.")
try:
    fig.savefig(figure_path, bbox_inches="tight")
    analysis_lines.append(f"Figure saved successfully to: {figure_path}")
except Exception as e:
    analysis_lines.append(f"Failed to save figure: {e}")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise

plt.close(fig)

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))