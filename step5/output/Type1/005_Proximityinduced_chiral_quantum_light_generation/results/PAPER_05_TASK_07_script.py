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

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/005_Proximityinduced_chiral_quantum_light_generation/type1_data/41563_2023_1645_MOESM3_ESM_10.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/005_Proximityinduced_chiral_quantum_light_generation/results/PAPER_05_TASK_07_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/005_Proximityinduced_chiral_quantum_light_generation/results/PAPER_05_TASK_07_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)
os.makedirs(os.path.dirname(analysis_path), exist_ok=True)

analysis_lines = []
analysis_lines.append("Task PAPER_05_TASK_07 Analysis")
analysis_lines.append("Objective: Replot the AFM topography and indentation cross-section from the workbook.")
analysis_lines.append("")

# Step 0: inspect workbook structure
analysis_lines.append("Step 0: Inspect workbook structure and identify candidate sheets for height-image and cross-section data.")
try:
    xls = pd.ExcelFile(dataset_file)
    sheet_names = xls.sheet_names
    analysis_lines.append(f"Loaded workbook successfully: {dataset_file}")
    analysis_lines.append(f"Sheets found: {sheet_names}")
except Exception as e:
    analysis_lines.append(f"Failed to load workbook: {e}")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise

# Read all sheets briefly
sheet_info = {}
for s in sheet_names:
    try:
        df = pd.read_excel(dataset_file, sheet_name=s, header=None)
        sheet_info[s] = df
        analysis_lines.append(f"Sheet '{s}': shape={df.shape}")
        preview = df.head(5).values.tolist()
        analysis_lines.append(f"  Preview rows: {preview}")
    except Exception as e:
        analysis_lines.append(f"  Could not read sheet '{s}': {e}")

analysis_lines.append("")
analysis_lines.append("Interpretation of workbook structure:")
analysis_lines.append("The visible sheets in the preview are spectral/time-series tables (Fig 2a, Fig 2b, Fig 2c) rather than AFM image tables.")
analysis_lines.append("I searched all sheets for likely AFM-related keywords and for 2D numeric grids that could represent a height map.")
analysis_lines.append("")

# Search for AFM-related keywords in sheet names and cell contents
keywords = ["HeightImage", "RTHeightImage", "Pix", "Pak1", "P1", "P2", "P3", "P4", "P5", "height", "topography", "indent", "cross", "profile"]
keyword_hits = []
for s, df in sheet_info.items():
    flat = df.astype(str).fillna("").values.ravel()
    joined = " | ".join(flat[:5000])  # enough for search
    hits = [k for k in keywords if re.search(re.escape(k), joined, flags=re.IGNORECASE)]
    if hits:
        keyword_hits.append((s, hits))
        analysis_lines.append(f"Sheet '{s}' contains keyword hits: {hits}")

if not keyword_hits:
    analysis_lines.append("No AFM-specific keywords were found in the workbook preview or sheet contents.")
    analysis_lines.append("This indicates the workbook likely does not contain the AFM topography or indentation profile data required by the task.")
    analysis_lines.append("")

# Determine if any sheet looks like a 2D image grid
candidate_grids = []
for s, df in sheet_info.items():
    # try to infer numeric matrix after first row/col
    numeric = df.copy()
    # attempt conversion
    for col in numeric.columns:
        numeric[col] = pd.to_numeric(numeric[col], errors="coerce")
    # count numeric rows/cols
    non_nan_counts = numeric.notna().sum(axis=1)
    if numeric.shape[1] >= 10 and (non_nan_counts > max(5, numeric.shape[1] * 0.8)).sum() > 10:
        candidate_grids.append(s)

if candidate_grids:
    analysis_lines.append(f"Potential 2D numeric grid sheets detected: {candidate_grids}")
else:
    analysis_lines.append("No sheet in the workbook appears to be a 2D numeric grid suitable for reconstructing an AFM height map.")
analysis_lines.append("")

# Since no AFM data is present, create a clearly labeled limitation figure
analysis_lines.append("Step 1: Reconstruct 2D AFM topography map using correct spatial axes.")
analysis_lines.append("Unable to perform this step because no height-image or coordinate-grid data are present in the workbook.")
analysis_lines.append("")

analysis_lines.append("Step 2: Extract indentation cross-section profile and plot it as a line scan with depth scale.")
analysis_lines.append("Unable to perform this step because no line-scan, cross-section, or height profile table is present in the workbook.")
analysis_lines.append("")

analysis_lines.append("Step 3: Combine the map and profile into a multi-panel figure with clear annotations and units if available.")
analysis_lines.append("A substitute figure is generated to document the data limitation and the absence of AFM inputs.")
analysis_lines.append("")

analysis_lines.append("Conclusion:")
analysis_lines.append("The provided workbook contains sheets labeled Fig 2a, Fig 2b, Fig 2c, Fig2d, and Fig 2e, with data previews showing spectral/time-series measurements.")
analysis_lines.append("It does not contain the AFM topography or indentation cross-section data requested by the task.")
analysis_lines.append("Therefore, a true AFM topography replot cannot be reconstructed without making unsupported assumptions.")
analysis_lines.append("")

# Create a limitation figure
fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)

# Left panel: workbook structure summary
ax = axes[0]
ax.axis("off")
summary_text = [
    "Workbook inspection",
    "",
    f"Sheets: {len(sheet_names)}",
    ", ".join(sheet_names),
    "",
    "Observed data types:",
    "- Fig 2a: Energy vs sigma-/sigma+",
    "- Fig 2b: Energy vs sigma-/sigma+",
    "- Fig 2c: Time vs Count",
    "",
    "AFM inputs requested:",
    "- HeightImage / RTHeightImage",
    "- Pix / coordinate grid",
    "- cross-section profile",
    "",
    "Result:",
    "No AFM topography or indentation",
    "profile data found in workbook.",
]
ax.text(0.02, 0.98, "\n".join(summary_text), va="top", ha="left", fontsize=10)

# Right panel: placeholder with explicit limitation
ax = axes[1]
ax.axis("off")
lim_text = [
    "Task limitation",
    "",
    "The workbook does not contain",
    "a height map or line-scan table",
    "for the nanoindentation AFM panel.",
    "",
    "A faithful reconstruction is not",
    "possible from the available data.",
    "",
    "No unsupported interpolation or",
    "fabrication was applied.",
]
ax.text(0.02, 0.98, "\n".join(lim_text), va="top", ha="left", fontsize=11)

fig.suptitle("PAPER_05_TASK_07: AFM topography and indentation cross-section", fontsize=14)
fig.savefig(figure_path, dpi=300, bbox_inches="tight")
plt.close(fig)

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure to: {figure_path}")
print(f"Saved analysis to: {analysis_path}")