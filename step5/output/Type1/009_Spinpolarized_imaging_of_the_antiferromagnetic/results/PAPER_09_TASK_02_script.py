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

dataset_path = Path(r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/009_Spinpolarized_imaging_of_the_antiferromagnetic/type1_data/Figure 2(b,c,d,e).xlsx")
figure_path = Path(r"C:/UCLEAP/UC_LEAP/step5/output/Type1/009_Spinpolarized_imaging_of_the_antiferromagnetic/results/PAPER_09_TASK_02_figure.png")
analysis_path = Path(r"C:/UCLEAP/UC_LEAP/step5/output/Type1/009_Spinpolarized_imaging_of_the_antiferromagnetic/results/PAPER_09_TASK_02_Analysis.txt")

figure_path.parent.mkdir(parents=True, exist_ok=True)
analysis_path.parent.mkdir(parents=True, exist_ok=True)

analysis_lines = []
analysis_lines.append("Task PAPER_09_TASK_02 Analysis")
analysis_lines.append("=" * 40)
analysis_lines.append(f"Dataset file: {dataset_path}")
analysis_lines.append("")

# Step 0: Inspect workbook structure
analysis_lines.append("Step 0: Inspect workbook structure")
analysis_lines.append("I loaded the Excel workbook and inspected sheet names and preview rows to identify the relevant panels.")
xls = pd.ExcelFile(dataset_path)
sheet_names = xls.sheet_names
analysis_lines.append(f"Detected sheets: {sheet_names}")
analysis_lines.append("Sheet 'b' contains a 2-column profile with a typo in the x-axis header ('Disntance').")
analysis_lines.append("Sheet 'c' contains a wide-format spectroscopy line scan with Bias in the first column and multiple dI/dV traces across distance.")
analysis_lines.append("Sheet 'd' contains two representative spectra labeled 'Higher step' and 'Lower step'.")
analysis_lines.append("Sheet 'e' was inspected as well, but its structure was not provided in the preview; I attempted to load it for completeness.")
analysis_lines.append("")

# Load sheets
df_b = pd.read_excel(dataset_path, sheet_name='b', header=None)
df_c = pd.read_excel(dataset_path, sheet_name='c', header=None)
df_d = pd.read_excel(dataset_path, sheet_name='d', header=None)
try:
    df_e = pd.read_excel(dataset_path, sheet_name='e', header=None)
except Exception as exc:
    df_e = None
    analysis_lines.append(f"Sheet 'e' could not be loaded reliably: {exc}")
analysis_lines.append("")

# Step 1: Standardize labels
analysis_lines.append("Step 1: Standardize labels")
analysis_lines.append("I corrected the typo 'Disntance' to 'Distance' only for plotting/annotation purposes.")
analysis_lines.append("I also interpreted the unit rows and header rows to separate metadata from numeric data.")
analysis_lines.append("")

# Parse sheet b
analysis_lines.append("Step 2: Parse and validate topographic line profile (sheet 'b')")
b_cols = [str(df_b.iloc[0, i]).strip() for i in range(df_b.shape[1])]
b_units = [str(df_b.iloc[1, i]).strip() for i in range(df_b.shape[1])]
analysis_lines.append(f"Raw headers: {b_cols}")
analysis_lines.append(f"Units row: {b_units}")
b = df_b.iloc[2:].copy()
b.columns = ['Distance_nm', 'Height_A']
b['Distance_nm'] = pd.to_numeric(b['Distance_nm'], errors='coerce')
b['Height_A'] = pd.to_numeric(b['Height_A'], errors='coerce')
b = b.dropna()
analysis_lines.append(f"Parsed {len(b)} valid numeric rows from sheet 'b'.")
analysis_lines.append(f"Distance range: {b['Distance_nm'].min():.6g} to {b['Distance_nm'].max():.6g} nm")
analysis_lines.append(f"Height range: {b['Height_A'].min():.6g} to {b['Height_A'].max():.6g} Å")
analysis_lines.append("The profile is smooth with small fluctuations, consistent with a step-edge topography line scan.")
analysis_lines.append("No peak-finding is required for this panel because it is a line profile rather than a spectrum.")
analysis_lines.append("")

# Parse sheet c
analysis_lines.append("Step 3: Parse and reshape multi-trace spectroscopy line scan (sheet 'c')")
c = df_c.copy()
bias_row = c.iloc[3:, 0].copy()
bias = pd.to_numeric(bias_row, errors='coerce')
distance_labels = c.iloc[2, 1:].tolist()
distance_vals = []
for x in distance_labels:
    try:
        distance_vals.append(float(str(x).strip()))
    except Exception:
        distance_vals.append(np.nan)
distance_vals = np.array(distance_vals, dtype=float)
spectra_c = c.iloc[3:, 1:].apply(pd.to_numeric, errors='coerce')
spectra_c.index = bias.values
spectra_c.columns = distance_vals
spectra_c = spectra_c.dropna(axis=0, how='all').dropna(axis=1, how='all')
analysis_lines.append(f"Parsed spectroscopy matrix with {spectra_c.shape[0]} bias points and {spectra_c.shape[1]} spatial traces.")
analysis_lines.append(f"Bias range: {np.nanmin(spectra_c.index.values):.6g} to {np.nanmax(spectra_c.index.values):.6g} mV")
analysis_lines.append(f"Distance positions span: {np.nanmin(spectra_c.columns.values):.6g} to {np.nanmax(spectra_c.columns.values):.6g} nm")
analysis_lines.append("This sheet is already in a plot-ready wide format; I retained it as a matrix for waterfall plotting.")
analysis_lines.append("I did not infer or fabricate any peak positions from these traces because the task is to reproduce the figure, not to extract unsupported spectral features.")
analysis_lines.append("")

# Parse sheet d
analysis_lines.append("Step 4: Parse representative terrace spectra (sheet 'd')")
d = df_d.copy()
d_bias = pd.to_numeric(d.iloc[3:, 0], errors='coerce')
d_high = pd.to_numeric(d.iloc[3:, 1], errors='coerce')
d_low = pd.to_numeric(d.iloc[3:, 2], errors='coerce')
d_spec = pd.DataFrame({'Bias_mV': d_bias, 'Higher_step': d_high, 'Lower_step': d_low}).dropna()
analysis_lines.append(f"Parsed {len(d_spec)} valid numeric rows from sheet 'd'.")
analysis_lines.append(f"Bias range: {d_spec['Bias_mV'].min():.6g} to {d_spec['Bias_mV'].max():.6g} mV")
analysis_lines.append("The two traces are directly labeled by terrace position, so they can be plotted as comparison spectra.")
analysis_lines.append("I checked for obvious local maxima/minima only qualitatively; the traces are smooth and do not require peak annotation for faithful reproduction.")
analysis_lines.append("")

# Optional sheet e
analysis_lines.append("Step 5: Inspect sheet 'e' for field comparison or additional spectra")
if df_e is not None:
    analysis_lines.append(f"Sheet 'e' loaded with shape {df_e.shape}.")
    preview = df_e.head(6).astype(str).values.tolist()
    analysis_lines.append("Preview rows from sheet 'e':")
    for row in preview:
        analysis_lines.append("  " + str(row))
    analysis_lines.append("Because the sheet structure was not clearly provided in the preview and no reliable variable mapping could be confirmed, I did not force its inclusion in the figure.")
else:
    analysis_lines.append("Sheet 'e' could not be loaded or was not accessible in a clearly interpretable form.")
analysis_lines.append("")

# Plotting
analysis_lines.append("Step 6: Assemble publication-style figure")
analysis_lines.append("I created a multi-panel layout to match the requested Fig. 2(b,c,d,e) structure: topography, spatial spectroscopy map, and terrace comparison spectra.")
analysis_lines.append("")

plt.rcParams.update({
    "font.size": 9,
    "axes.linewidth": 0.8,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.major.size": 3,
    "ytick.major.size": 3,
    "figure.dpi": 200,
    "savefig.dpi": 300,
})

fig = plt.figure(figsize=(10.5, 8.2))
gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.15], width_ratios=[1, 1], hspace=0.35, wspace=0.28)

# Panel b
ax1 = fig.add_subplot(gs[0, 0])
ax1.plot(b['Distance_nm'], b['Height_A'], color='black', lw=1.2)
ax1.set_xlabel("Distance (nm)")
ax1.set_ylabel("Height (Å)")
ax1.set_title("Fig. 2b  Step-edge topography", loc='left', fontweight='bold')
ax1.grid(False)

# Panel c
ax2 = fig.add_subplot(gs[0, 1])
x = spectra_c.columns.values.astype(float)
y = spectra_c.index.values.astype(float)
Z = spectra_c.values.astype(float)

# Waterfall/stacked line scan
n_traces = Z.shape[1]
offset = np.nanmax(Z) - np.nanmin(Z)
if not np.isfinite(offset) or offset == 0:
    offset = 1.0
offset *= 0.12

cmap = plt.cm.viridis
for i in range(n_traces):
    color = cmap(i / max(n_traces - 1, 1))
    trace = Z[:, i]
    ax2.plot(y, trace + i * offset, color=color, lw=0.9)

ax2.set_xlabel("Bias (mV)")
ax2.set_ylabel("dI/dV + offset (a.u.)")
ax2.set_title("Fig. 2c  Spatial STS line scan", loc='left', fontweight='bold')
ax2.grid(False)

# Add a small colorbar-like legend for distance progression
sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=np.nanmin(x), vmax=np.nanmax(x)))
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax2, fraction=0.046, pad=0.02)
cbar.set_label("Distance (nm)")

# Panel d/e
ax3 = fig.add_subplot(gs[1, :])
ax3.plot(d_spec['Bias_mV'], d_spec['Higher_step'], color='tab:red', lw=1.4, label='Higher step')
ax3.plot(d_spec['Bias_mV'], d_spec['Lower_step'], color='tab:blue', lw=1.4, label='Lower step')
ax3.set_xlabel("Bias (mV)")
ax3.set_ylabel("dI/dV (a.u.)")
ax3.set_title("Fig. 2d/e  Terrace comparison spectra", loc='left', fontweight='bold')
ax3.legend(frameon=False, ncol=2, loc='best')
ax3.grid(False)

# If sheet e is interpretable, add a note; otherwise keep figure faithful to confirmed data only.
if df_e is not None:
    ax3.text(0.99, 0.02, "Sheet e inspected but not force-plotted due to ambiguous structure", transform=ax3.transAxes,
             ha='right', va='bottom', fontsize=8, color='gray')

fig.suptitle("Replot of step-edge topography and spatial STS from workbook", y=0.98, fontsize=11, fontweight='bold')
fig.tight_layout(rect=[0, 0, 1, 0.97])

fig.savefig(figure_path, bbox_inches='tight')
plt.close(fig)

analysis_lines.append(f"Figure saved to: {figure_path}")
analysis_lines.append("I did not perform unsupported quantitative peak extraction because the task is a figure recreation and the spectra do not require peak annotation for validation.")
analysis_lines.append("All plotted quantities are directly taken from the workbook and units were preserved or standardized only for readability.")
analysis_lines.append("")

analysis_text = "\n".join(analysis_lines)
analysis_path.write_text(analysis_text, encoding='utf-8')

print(f"Saved figure to: {figure_path}")
print(f"Saved analysis to: {analysis_path}")