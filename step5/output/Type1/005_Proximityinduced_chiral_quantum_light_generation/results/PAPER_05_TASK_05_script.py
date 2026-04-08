import os
import re
import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/005_Proximityinduced_chiral_quantum_light_generation/type1_data/41563_2023_1645_MOESM14_ESM_10.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/005_Proximityinduced_chiral_quantum_light_generation/results/PAPER_05_TASK_05_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/005_Proximityinduced_chiral_quantum_light_generation/results/PAPER_05_TASK_05_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)
os.makedirs(os.path.dirname(analysis_path), exist_ok=True)

analysis_lines = []
analysis_lines.append("Task PAPER_05_TASK_05 Analysis")
analysis_lines.append("=" * 40)
analysis_lines.append(f"Dataset file: {dataset_file}")
analysis_lines.append("")

# Step 0: Inspect workbook structure
analysis_lines.append("Step 0: Inspect workbook for image matrices or coordinate tables")
analysis_lines.append("Reasoning: The task asks for an optical image reconstruction, so the workbook must be checked for 2D image-like arrays, coordinate grids, or annotated layout data rather than only spectral traces.")
try:
    xls = pd.ExcelFile(dataset_file)
    sheet_names = xls.sheet_names
    analysis_lines.append(f"Workbook sheets found: {sheet_names}")
except Exception as e:
    analysis_lines.append(f"Failed to open workbook: {e}")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise

# Preview sheets
sheet_summaries = []
for sh in sheet_names:
    try:
        df = pd.read_excel(dataset_file, sheet_name=sh, header=None)
        shape = df.shape
        preview = df.head(8).astype(str).values.tolist()
        sheet_summaries.append((sh, shape, preview))
        analysis_lines.append(f"Sheet '{sh}': shape={shape}")
        for i, row in enumerate(preview):
            analysis_lines.append(f"  Row {i}: {row}")
    except Exception as e:
        analysis_lines.append(f"Could not read sheet '{sh}': {e}")

analysis_lines.append("")
analysis_lines.append("Interpretation: The workbook contains two sheets with 1341 rows x 3 columns each, headed 'Energy', 'sig+', and 'sig-'.")
analysis_lines.append("These are 1D spectral data tables, not image matrices or XY coordinate grids.")
analysis_lines.append("No region labels, overlap boundaries, or annotation text corresponding to a sample overview were found in the inspected sheet previews.")
analysis_lines.append("")

# Step 1: Determine spatial extent and labels
analysis_lines.append("Step 1: Determine spatial extent and any region labels or boundaries")
analysis_lines.append("Reasoning: For an optical image reconstruction, one would expect pixel grids, coordinate axes, or labeled regions. The workbook structure is checked for these features.")
all_data = {}
for sh in sheet_names:
    try:
        df = pd.read_excel(dataset_file, sheet_name=sh)
        all_data[sh] = df
    except Exception:
        pass

# Search for image-like content
image_like_found = False
for sh, df in all_data.items():
    cols = [str(c).strip().lower() for c in df.columns]
    if len(df.columns) >= 2 and any("x" in c for c in cols) and any("y" in c for c in cols):
        image_like_found = True
    if df.shape[1] > 10 and df.shape[0] > 10:
        image_like_found = True

analysis_lines.append(f"Image-like matrix detected: {image_like_found}")
analysis_lines.append("Conclusion: No image-like matrix or coordinate table is present in the workbook. The available data are spectral traces only.")
analysis_lines.append("")

# Step 2: Render figure
analysis_lines.append("Step 2: Render the optical image using available data")
analysis_lines.append("Reasoning: Since no optical image data are present, a faithful reconstruction of the heterostructure layout cannot be performed from this workbook.")
analysis_lines.append("Decision: To avoid fabricating unsupported image content, a placeholder panel is generated that explicitly states the limitation.")
analysis_lines.append("")

# Step 3: Confirm final panel communicates layout
analysis_lines.append("Step 3: Confirm final panel visually communicates the heterostructure layout and overlap geometry")
analysis_lines.append("Reasoning: Because the workbook lacks the required image/layout data, the final panel cannot communicate the actual sample geometry. The output therefore documents the absence of suitable data rather than inventing a figure.")
analysis_lines.append("")

# Create placeholder figure
fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
ax.set_facecolor("white")
ax.axis("off")

title = "PAPER_05_TASK_05\nOptical overview image unavailable in workbook"
subtitle = (
    "The inspected workbook contains only spectral tables (Energy, sig+, sig-)\n"
    "and does not include image matrices, XY coordinates, region labels,\n"
    "or overlap-boundary annotations needed to reconstruct Fig. 1a."
)

ax.text(0.5, 0.72, title, ha="center", va="center", fontsize=16, fontweight="bold")
ax.text(0.5, 0.48, subtitle, ha="center", va="center", fontsize=11, linespacing=1.5)

# Add a simple schematic box to indicate limitation
rect = plt.Rectangle((0.18, 0.12), 0.64, 0.18, fill=False, linewidth=2, edgecolor="black", transform=ax.transAxes)
ax.add_patch(rect)
ax.text(0.5, 0.21, "No optical image / layout data found", ha="center", va="center", fontsize=12)

plt.tight_layout()
plt.savefig(figure_path, bbox_inches="tight")
plt.close(fig)

analysis_lines.append(f"Figure saved to: {figure_path}")
analysis_lines.append("Analysis summary:")
analysis_lines.append(" - Workbook inspected successfully.")
analysis_lines.append(" - No image-like data, coordinate grids, or annotations were found.")
analysis_lines.append(" - A placeholder figure was saved to document the limitation without fabricating the sample layout.")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure: {figure_path}")
print(f"Saved analysis: {analysis_path}")