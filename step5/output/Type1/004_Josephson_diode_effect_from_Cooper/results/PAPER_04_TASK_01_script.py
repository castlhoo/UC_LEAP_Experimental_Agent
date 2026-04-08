import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/004_Josephson_diode_effect_from_Cooper/type1_data/41567_2022_1699_MOESM2_ESM_10.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/004_Josephson_diode_effect_from_Cooper/results/PAPER_04_TASK_01_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/004_Josephson_diode_effect_from_Cooper/results/PAPER_04_TASK_01_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)

analysis_lines = []

def log(msg):
    analysis_lines.append(msg)

log("Task PAPER_04_TASK_01 Analysis")
log("Step 0: Workbook inspection")
log(f"Loaded dataset file: {dataset_file}")

xls = pd.ExcelFile(dataset_file)
sheet_names = xls.sheet_names
log(f"Workbook sheets found: {sheet_names}")

# Identify relevant sheets
main_sheet = None
inset_sheet = None
for s in sheet_names:
    if s == "Fig_1d":
        main_sheet = s
    if s == "Fig_1d_inset":
        inset_sheet = s

log(f"Identified main temperature-dependent sheet: {main_sheet}")
log(f"Identified inset sheet: {inset_sheet}")

# Step 1: Clean and interpret data
main_df_raw = pd.read_excel(dataset_file, sheet_name=main_sheet, header=0)
log("Step 1: Data cleaning and column interpretation for main panel")
log(f"Main sheet raw shape: {main_df_raw.shape}")
log(f"Main sheet columns: {list(main_df_raw.columns)}")

main_df = main_df_raw.copy()
main_df.columns = ["Temperature (K)", "Voltage (uV)"]
main_df["Temperature (K)"] = pd.to_numeric(main_df["Temperature (K)"], errors="coerce")
main_df["Voltage (uV)"] = pd.to_numeric(main_df["Voltage (uV)"], errors="coerce")
main_df = main_df.dropna(subset=["Temperature (K)", "Voltage (uV)"]).reset_index(drop=True)

log(f"Main sheet numeric rows retained: {len(main_df)}")
log(f"Main sheet temperature range: {main_df['Temperature (K)'].min():.4f} K to {main_df['Temperature (K)'].max():.4f} K")
log(f"Main sheet voltage range: {main_df['Voltage (uV)'].min():.4f} uV to {main_df['Voltage (uV)'].max():.4f} uV")

inset_df_raw = pd.read_excel(dataset_file, sheet_name=inset_sheet, header=0)
log("Step 1: Data cleaning and column interpretation for inset")
log(f"Inset sheet raw shape: {inset_df_raw.shape}")
log(f"Inset sheet columns: {list(inset_df_raw.columns)}")

inset_df = inset_df_raw.copy()
inset_df.columns = ["d (nm)", "T_J (K)", "T_SC (K)"]
for c in inset_df.columns:
    inset_df[c] = pd.to_numeric(inset_df[c], errors="coerce")
inset_df = inset_df.dropna(subset=["d (nm)", "T_J (K)", "T_SC (K)"]).reset_index(drop=True)

log(f"Inset numeric rows retained: {len(inset_df)}")
log(f"Inset spacing values: {inset_df['d (nm)'].tolist()}")
log(f"Inset T_J values: {inset_df['T_J (K)'].tolist()}")
log(f"Inset T_SC values: {inset_df['T_SC (K)'].tolist()}")

# Step 2: Plot main curve
log("Step 2: Plotting main temperature-dependent transport curve")
fig = plt.figure(figsize=(7.2, 5.6), dpi=300)
ax = fig.add_axes([0.12, 0.12, 0.78, 0.78])

# Sort by temperature for a clean line plot
main_df_sorted = main_df.sort_values("Temperature (K)").reset_index(drop=True)

ax.plot(
    main_df_sorted["Temperature (K)"],
    main_df_sorted["Voltage (uV)"],
    color="black",
    lw=1.6,
    label="Voltage (uV)"
)

ax.set_xlabel("Temperature (K)", fontsize=12)
ax.set_ylabel("Voltage (uV)", fontsize=12)

# Infer axis ranges from data with modest padding
x_min, x_max = main_df_sorted["Temperature (K)"].min(), main_df_sorted["Temperature (K)"].max()
y_min, y_max = main_df_sorted["Voltage (uV)"].min(), main_df_sorted["Voltage (uV)"].max()
x_pad = 0.03 * (x_max - x_min) if x_max > x_min else 1
y_pad = 0.08 * (y_max - y_min) if y_max > y_min else 1
ax.set_xlim(x_min - x_pad, x_max + x_pad)
ax.set_ylim(y_min - y_pad, y_max + y_pad)

ax.tick_params(direction="in", top=True, right=True, length=5, width=1)
ax.tick_params(which="minor", direction="in", top=True, right=True, length=3, width=0.8)
ax.xaxis.set_minor_locator(AutoMinorLocator())
ax.yaxis.set_minor_locator(AutoMinorLocator())

for spine in ax.spines.values():
    spine.set_linewidth(1.0)

# Add annotations for transition temperatures if supported by inset data
# Use the exact values from the inset sheet as labels, without inventing extra interpretation.
if len(inset_df) > 0:
    # Annotate the first row values as representative of the figure's transition temperatures
    tj = inset_df.loc[0, "T_J (K)"]
    tsc = inset_df.loc[0, "T_SC (K)"]
    ax.text(
        0.03, 0.95,
        f"T_J = {tj:g} K\nT_SC = {tsc:g} K",
        transform=ax.transAxes,
        fontsize=10,
        va="top",
        ha="left",
        bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="none", alpha=0.8)
    )
    log(f"Added annotation using inset values from first row: T_J={tj}, T_SC={tsc}")
else:
    log("Inset data unavailable for annotation; no transition temperature annotation added.")

# Step 3: Plot inset
log("Step 3: Plotting inset characteristic temperatures versus junction spacing")
ax_in = inset_axes(ax, width="38%", height="38%", loc="upper right", borderpad=1.2)

ax_in.plot(
    inset_df["d (nm)"],
    inset_df["T_J (K)"],
    marker="o",
    ms=4.5,
    lw=1.2,
    color="#1f77b4",
    label="T_J (K)"
)
ax_in.plot(
    inset_df["d (nm)"],
    inset_df["T_SC (K)"],
    marker="s",
    ms=4.5,
    lw=1.2,
    color="#d62728",
    label="T_SC (K)"
)

ax_in.set_xlabel("d (nm)", fontsize=9)
ax_in.set_ylabel("T (K)", fontsize=9)
ax_in.tick_params(direction="in", top=True, right=True, labelsize=8, length=4, width=0.9)
ax_in.tick_params(which="minor", direction="in", top=True, right=True, length=2.5, width=0.7)
ax_in.xaxis.set_minor_locator(AutoMinorLocator())
ax_in.yaxis.set_minor_locator(AutoMinorLocator())

for spine in ax_in.spines.values():
    spine.set_linewidth(0.9)

# Tight inset limits based on data
dx_min, dx_max = inset_df["d (nm)"].min(), inset_df["d (nm)"].max()
ty_min = min(inset_df["T_J (K)"].min(), inset_df["T_SC (K)"].min())
ty_max = max(inset_df["T_J (K)"].max(), inset_df["T_SC (K)"].max())
dx_pad = 0.08 * (dx_max - dx_min) if dx_max > dx_min else 1
ty_pad = 0.12 * (ty_max - ty_min) if ty_max > ty_min else 0.5
ax_in.set_xlim(dx_min - dx_pad, dx_max + dx_pad)
ax_in.set_ylim(ty_min - ty_pad, ty_max + ty_pad)

ax_in.legend(frameon=False, fontsize=7, loc="best", handlelength=1.5)

# Step 4: Formatting and publication-style adjustments
log("Step 4: Applying publication-style formatting")
fig.patch.set_facecolor("white")
ax.set_facecolor("white")
ax_in.set_facecolor("white")

# Step 5: Export figure
log("Step 5: Exporting figure")
fig.savefig(figure_path, dpi=300, bbox_inches="tight")
plt.close(fig)
log(f"Figure saved to: {figure_path}")

# Write analysis file
with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure: {figure_path}")
print(f"Saved analysis: {analysis_path}")