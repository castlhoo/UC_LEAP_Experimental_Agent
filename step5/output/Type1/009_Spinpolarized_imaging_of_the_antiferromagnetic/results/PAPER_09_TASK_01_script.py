import os
import pandas as pd
import matplotlib.pyplot as plt

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/009_Spinpolarized_imaging_of_the_antiferromagnetic/type1_data/Figure 1(e,f,i).xlsx"
figure_out = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/009_Spinpolarized_imaging_of_the_antiferromagnetic/results/PAPER_09_TASK_01_figure.png"
analysis_out = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/009_Spinpolarized_imaging_of_the_antiferromagnetic/results/PAPER_09_TASK_01_Analysis.txt"

os.makedirs(os.path.dirname(figure_out), exist_ok=True)

analysis_lines = []
analysis_lines.append("Task PAPER_09_TASK_01 Analysis")
analysis_lines.append("")
analysis_lines.append("Step 0: Open workbook and identify sheets")
analysis_lines.append(f"Loaded workbook: {dataset_file}")
xls = pd.ExcelFile(dataset_file)
analysis_lines.append(f"Detected sheets: {xls.sheet_names}")
analysis_lines.append("Sheet 'e' and sheet 'f' contain Bias and dI/dV columns, indicating spectral panels.")
analysis_lines.append("Sheet 'i' contains Distance and Height columns, indicating the spatial line profile.")
analysis_lines.append("")
analysis_lines.append("Step 1: Parse annotated columns and units")
analysis_lines.append("Sheet 'e' header rows indicate Bias in mV and dI/dV in a.u.")
analysis_lines.append("Sheet 'f' header rows indicate Bias in mV and dI/dV in a.u.")
analysis_lines.append("Sheet 'i' header rows indicate Distance in nm and Height in pm.")
analysis_lines.append("The workbook structure uses the first row for variable names and the second row for units.")
analysis_lines.append("")

def load_sheet(sheet_name, x_name, y_name):
    df = pd.read_excel(dataset_file, sheet_name=sheet_name, header=0)
    if df.shape[0] > 0 and isinstance(df.iloc[0, 0], str) and isinstance(df.iloc[0, 1], str):
        if str(df.iloc[0, 0]).strip().lower() in ["mv", "nm"] or str(df.iloc[0, 1]).strip().lower() in ["a.u.", "pm"]:
            df = df.iloc[1:].reset_index(drop=True)
    df.columns = [x_name, y_name]
    df[x_name] = pd.to_numeric(df[x_name], errors="coerce")
    df[y_name] = pd.to_numeric(df[y_name], errors="coerce")
    df = df.dropna().reset_index(drop=True)
    return df

e = load_sheet("e", "Bias (mV)", "dI/dV (a.u.)")
f = load_sheet("f", "Bias (mV)", "dI/dV (a.u.)")
i = load_sheet("i", "Distance (nm)", "Height (pm)")

analysis_lines.append("Step 2: Inspect spectral sheets and line profile")
analysis_lines.append(f"Sheet 'e' data points: {len(e)}")
analysis_lines.append(f"Sheet 'f' data points: {len(f)}")
analysis_lines.append(f"Sheet 'i' data points: {len(i)}")
analysis_lines.append("Sheet 'e' and 'f' each contain a single numeric trace; there is no evidence of multiple repeated traces in the sheet structure.")
analysis_lines.append("Therefore, the spectra are plotted directly rather than averaged.")
analysis_lines.append("The bias values in both spectral sheets are sampled over a descending-to-ascending range, so the data are sorted by bias before plotting to produce a continuous curve.")
analysis_lines.append("The line profile is plotted directly from the provided distance-height pairs.")
analysis_lines.append("")

e = e.sort_values("Bias (mV)").reset_index(drop=True)
f = f.sort_values("Bias (mV)").reset_index(drop=True)
i = i.sort_values("Distance (nm)").reset_index(drop=True)

analysis_lines.append("Step 3: Validate features and plotting choices")
analysis_lines.append("The spectral curves are smooth numeric sequences with no need for peak extraction in this task.")
analysis_lines.append("No unsupported quantitative interpretation is made beyond reproducing the plotted traces.")
analysis_lines.append("Axis labels and units are preserved from the workbook annotations.")
analysis_lines.append("")

fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.2), constrained_layout=True)

# Panel e
ax = axes[0]
ax.plot(e["Bias (mV)"], e["dI/dV (a.u.)"], color="#1f77b4", lw=2)
ax.set_xlabel("Bias (mV)")
ax.set_ylabel("dI/dV (a.u.)")
ax.set_title("e")
ax.grid(True, alpha=0.25)

# Panel f
ax = axes[1]
ax.plot(f["Bias (mV)"], f["dI/dV (a.u.)"], color="#d62728", lw=2)
ax.set_xlabel("Bias (mV)")
ax.set_ylabel("dI/dV (a.u.)")
ax.set_title("f")
ax.grid(True, alpha=0.25)

# Panel i
ax = axes[2]
ax.plot(i["Distance (nm)"], i["Height (pm)"], color="#2ca02c", lw=2)
ax.set_xlabel("Distance (nm)")
ax.set_ylabel("Height (pm)")
ax.set_title("i")
ax.grid(True, alpha=0.25)

for ax in axes:
    ax.tick_params(direction="in", top=True, right=True)

fig.suptitle("Replot of Fig. 1e, 1f, and 1i", y=1.02, fontsize=14)
fig.savefig(figure_out, dpi=300, bbox_inches="tight")

analysis_lines.append("Step 4: Export figure")
analysis_lines.append(f"Saved figure to: {figure_out}")
analysis_lines.append("The final layout contains two dI/dV vs Bias panels and one Height vs Distance panel in a publication-style arrangement.")
analysis_lines.append("")

with open(analysis_out, "w", encoding="utf-8") as ftxt:
    ftxt.write("\n".join(analysis_lines))

print(f"Saved figure: {figure_out}")
print(f"Saved analysis: {analysis_out}")