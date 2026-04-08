import os
import re
import json
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/005_Proximityinduced_chiral_quantum_light_generation/type1_data/41563_2023_1645_MOESM2_ESM_10.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/005_Proximityinduced_chiral_quantum_light_generation/results/PAPER_05_TASK_06_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/005_Proximityinduced_chiral_quantum_light_generation/results/PAPER_05_TASK_06_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)

xl = pd.ExcelFile(dataset_file)
sheet_names = xl.sheet_names

analysis_lines = []
analysis_lines.append("Task PAPER_05_TASK_06 Analysis")
analysis_lines.append(f"Dataset file: {dataset_file}")
analysis_lines.append(f"Available sheets: {sheet_names}")
analysis_lines.append("")
analysis_lines.append("Step_0: Locate the wide-field PL image data and any spatial coordinate tables.")
analysis_lines.append("I inspected the workbook structure first. The file contains three sheets: 'Fig. 1D', 'Fig. 1e', and 'Fig. 1f'.")
analysis_lines.append("The preview indicates each sheet is a 3-column numeric table with headers 'Energy' and two repeated 'sigma +' columns, which is consistent with spectral line data rather than a 2D image matrix.")
analysis_lines.append("I did not find any sheet names or previewed columns corresponding to HeightImage, MagneticFieldImage, RTHeightImage, RTMagneticFieldImage, XY positions, pixel coordinates, or PL intensity image grids.")
analysis_lines.append("Therefore, the workbook does not appear to contain the wide-field PL image matrix needed to directly reconstruct Fig. 1b from image data.")
analysis_lines.append("")
analysis_lines.append("Step_1: Reconstruct the 2D PL intensity map with appropriate contrast scaling.")
analysis_lines.append("This step could not be performed because no 2D PL intensity matrix or coordinate table was present in the workbook.")
analysis_lines.append("The available data are 1D energy-dependent traces only, so any attempt to render a spatial PL map would require unsupported assumptions.")
analysis_lines.append("")
analysis_lines.append("Step_2: Add region annotations or outlines for the overlap area and indentation points if available.")
analysis_lines.append("No spatial annotations, masks, outlines, or coordinate references for overlap regions or nanoindentation sites were found in the workbook.")
analysis_lines.append("Because the necessary spatial metadata are absent, no valid annotation can be added.")
analysis_lines.append("")
analysis_lines.append("Step_3: Format the panel as a publication-style image with a colorbar and clear spatial axes.")
analysis_lines.append("A publication-style spatial image cannot be generated from the available data because the underlying image is missing.")
analysis_lines.append("I therefore did not fabricate a figure or infer a spatial field from the spectral tables.")
analysis_lines.append("")
analysis_lines.append("Conclusion:")
analysis_lines.append("The dataset does not contain the required wide-field PL image or spatial coordinate information for Fig. 1b reconstruction.")
analysis_lines.append("The task cannot be completed faithfully from this workbook alone.")
analysis_lines.append("No figure was saved because any image would be speculative and unsupported by the data.")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

fig, ax = plt.subplots(figsize=(8, 4.5))
ax.axis("off")
msg = (
    "Wide-field PL image not available in workbook.\n\n"
    "The provided Excel file contains only 1D energy-dependent tables\n"
    "('Fig. 1D', 'Fig. 1e', 'Fig. 1f') and no 2D PL image matrix,\n"
    "pixel coordinates, or spatial annotations needed to reconstruct\n"
    "the overlap-region / nanoindentation PL map."
)
ax.text(0.5, 0.5, msg, ha="center", va="center", fontsize=12)
plt.tight_layout()
plt.savefig(figure_path, dpi=300, bbox_inches="tight")
plt.close(fig)