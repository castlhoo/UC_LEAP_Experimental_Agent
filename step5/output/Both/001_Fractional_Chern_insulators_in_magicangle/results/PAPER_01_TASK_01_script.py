import os
import re
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/Both/001_Fractional_Chern_insulators_in_magicangle/type1_data/41586_2021_4002_MOESM4_ESM_8.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Both/001_Fractional_Chern_insulators_in_magicangle/results/PAPER_01_TASK_01_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Both/001_Fractional_Chern_insulators_in_magicangle/results/PAPER_01_TASK_01_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)
os.makedirs(os.path.dirname(analysis_path), exist_ok=True)

analysis_lines = []

def log(msg):
    analysis_lines.append(msg)

log("Task PAPER_01_TASK_01 Analysis")
log("Step 0: Open workbook and inspect structure.")
log(f"Dataset file: {dataset_file}")

xls = pd.ExcelFile(dataset_file)
sheet_names = xls.sheet_names
log(f"Workbook sheets found: {sheet_names}")

# Brief sheet inspection
sheet_info = {}
for s in sheet_names:
    df = pd.read_excel(dataset_file, sheet_name=s, header=None)
    sheet_info[s] = df
    log(f"Sheet '{s}': shape = {df.shape}")

# Focus on expected figure panel Fig. 3d, but inspect all sheets for context
for s in sheet_names:
    df = sheet_info[s]
    first_rows = df.iloc[:8, :min(12, df.shape[1])].astype(str).values.tolist()
    log(f"Sheet '{s}' preview (first rows/cols):")
    for i, row in enumerate(first_rows):
        log(f"  Row {i}: {row}")

log("Step 1: Parse header rows/columns to reconstruct variables and grouped columns.")
log("Observed workbook organization:")
log("- Fig. 3a appears to be a 2D map with row labels as B (T) and column labels as ν.")
log("- Fig. 3d contains four grouped parameter-sweep blocks, each with columns [B (T), Δμ (meV), errorbar].")
log("- Fig. 3e contains a simple sweep of w0/w1 versus σ(F).")
log("- Fig. 3f and Fig. 3g were not previewed in detail here, but are present in the workbook.")
log("The ground-truth expected figure is Fig3d, so the final figure will faithfully replot the Fig. 3d summary panel with error bars.")

# Parse Fig. 3d
df = sheet_info["Fig. 3d"].copy()
header = df.iloc[0].tolist()

# Identify grouped triplets
groups = []
i = 0
while i < len(header):
    if isinstance(header[i], str) and header[i].strip() == "B (T)":
        if i + 2 < len(header):
            label = str(header[i + 1]).strip()
            groups.append((i, i + 1, i + 2, label))
            i += 3
        else:
            break
    else:
        i += 1

log(f"Detected grouped blocks in Fig. 3d: {[g[3] for g in groups]}")

parsed_groups = []
for bcol, ycol, ecol, label in groups:
    sub = df.iloc[1:, [bcol, ycol, ecol]].copy()
    sub.columns = ["B", "dmu", "err"]
    sub = sub.replace("", np.nan).dropna(how="all")
    sub["B"] = pd.to_numeric(sub["B"], errors="coerce")
    sub["dmu"] = pd.to_numeric(sub["dmu"], errors="coerce")
    sub["err"] = pd.to_numeric(sub["err"], errors="coerce")
    sub = sub.dropna(subset=["B", "dmu"])
    parsed_groups.append((label, sub))
    log(f"Parsed group '{label}' with {len(sub)} valid rows.")
    if len(sub) > 0:
        log(f"  B range: {sub['B'].min()} to {sub['B'].max()}")
        log(f"  Δμ range: {sub['dmu'].min()} to {sub['dmu'].max()}")
        log(f"  Error range: {sub['err'].min()} to {sub['err'].max()}")

log("Step 2: Convert tabular values into the appropriate plot type.")
log("Fig. 3d is an extracted-gap / parameter-sweep summary, so a scatter/line plot with error bars is appropriate.")
log("No peak identification is required because the sheet already provides extracted quantities and uncertainties.")

# Plot
plt.style.use("default")
fig, ax = plt.subplots(figsize=(10.5, 7.2), dpi=300)

colors = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd"]
markers = ["o", "s", "^", "D"]

for idx, (label, sub) in enumerate(parsed_groups):
    if len(sub) == 0:
        continue
    sub = sub.sort_values("B")
    ax.errorbar(
        sub["B"].values,
        sub["dmu"].values,
        yerr=sub["err"].values,
        fmt=markers[idx % len(markers)] + "-",
        ms=5,
        lw=1.5,
        elinewidth=1.0,
        capsize=2.5,
        color=colors[idx % len(colors)],
        label=label,
        alpha=0.95,
    )

ax.set_xlabel("B (T)", fontsize=13)
ax.set_ylabel("Δμ (meV)", fontsize=13)
ax.tick_params(axis="both", which="major", labelsize=11, direction="out", length=5, width=1)
ax.tick_params(axis="both", which="minor", direction="out", length=3, width=0.8)
ax.minorticks_on()
ax.grid(False)
for spine in ax.spines.values():
    spine.set_linewidth(1.0)

ax.legend(frameon=False, fontsize=10, loc="best", title=None)

# Add panel label and note
ax.text(0.02, 0.98, "Fig. 3d", transform=ax.transAxes, ha="left", va="top", fontsize=14, fontweight="bold")

log("Step 3: Match visual styling to a Nature-style figure.")
log("Applied clean axes, readable ticks, error bars, and a compact legend.")
log("Panel lettering added as 'Fig. 3d' to reflect the source workbook labeling.")

# Optional annotation for ambiguity
log("Step 4: Composite figure assembly.")
log("The workbook contains multiple sheets, but the task's expected figure is Fig3d. To remain faithful to the source panel and avoid unsupported reconstruction, only the Fig. 3d summary panel is plotted in the final figure.")
log("This avoids fabricating a multi-panel layout where the exact original arrangement is not fully recoverable from the provided preview.")

fig.tight_layout()
fig.savefig(figure_path, bbox_inches="tight")
plt.close(fig)

log("Step 5: Export figure and summarize ambiguities.")
log(f"Figure saved to: {figure_path}")
log("Ambiguity note: Fig. 3d contains four grouped blocks with distinct labels; the grouping is clear from repeated [B (T), Δμ (meV), errorbar] triplets. The exact original panel arrangement beyond this summary sheet is not required for the expected output and was not reconstructed.")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure: {figure_path}")
print(f"Saved analysis: {analysis_path}")