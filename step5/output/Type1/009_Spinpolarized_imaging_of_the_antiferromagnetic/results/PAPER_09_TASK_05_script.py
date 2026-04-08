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

dataset_path = Path(r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/009_Spinpolarized_imaging_of_the_antiferromagnetic/type1_data/Figure 5(e,f).xlsx")
figure_path = Path(r"C:/UCLEAP/UC_LEAP/step5/output/Type1/009_Spinpolarized_imaging_of_the_antiferromagnetic/results/PAPER_09_TASK_05_figure.png")
analysis_path = Path(r"C:/UCLEAP/UC_LEAP/step5/output/Type1/009_Spinpolarized_imaging_of_the_antiferromagnetic/results/PAPER_09_TASK_05_Analysis.txt")

figure_path.parent.mkdir(parents=True, exist_ok=True)
analysis_path.parent.mkdir(parents=True, exist_ok=True)

analysis_lines = []

def log(msg):
    analysis_lines.append(msg)

log("Task PAPER_09_TASK_05 Analysis")
log("Step 0: Open workbook and identify sheets.")
log(f"Loaded workbook: {dataset_path}")
xls = pd.ExcelFile(dataset_path)
log(f"Sheets found: {xls.sheet_names}")

# Inspect sheet e
df_e_raw = pd.read_excel(dataset_path, sheet_name='e', header=None)
log(f"Sheet 'e' raw shape: {df_e_raw.shape}")
log("Observed structure in sheet 'e':")
for i in range(min(8, len(df_e_raw))):
    log(f"  Row {i}: {df_e_raw.iloc[i].tolist()}")

# Parse sheet e
# Row 0: repeated dI/dV headers, Row 1: units, Row 2: field labels
bias = pd.to_numeric(df_e_raw.iloc[3:, 0], errors='coerce')
field_labels = [str(x) for x in df_e_raw.iloc[2, 1:].tolist()]
spectra = {}
for idx, fld in enumerate(field_labels, start=1):
    spectra[fld] = pd.to_numeric(df_e_raw.iloc[3:, idx], errors='coerce').to_numpy()

bias_vals = bias.to_numpy()
valid_mask = np.isfinite(bias_vals)
bias_vals = bias_vals[valid_mask]

log("Step 1: Parse Bias axis and dI/dV traces.")
log(f"Bias range: {np.nanmin(bias_vals):.6g} to {np.nanmax(bias_vals):.6g} mV")
log(f"Field labels preserved exactly as workbook entries: {field_labels}")

# Inspect sheet f
df_f_raw = pd.read_excel(dataset_path, sheet_name='f', header=None)
log(f"Sheet 'f' raw shape: {df_f_raw.shape}")
log("Observed structure in sheet 'f':")
for i in range(min(8, len(df_f_raw))):
    log(f"  Row {i}: {df_f_raw.iloc[i].tolist()}")

# Parse sheet f
# Row 0: Peak Postion / Error
# Row 1: dI/dV units
# Row 2: T units
# Data from row 3 onward
B_vals = pd.to_numeric(df_f_raw.iloc[3:, 0], errors='coerce').to_numpy()
peak_pos = pd.to_numeric(df_f_raw.iloc[3:, 1], errors='coerce').to_numpy()
peak_err = pd.to_numeric(df_f_raw.iloc[3:, 2], errors='coerce').to_numpy()

valid_f = np.isfinite(B_vals) & np.isfinite(peak_pos)
B_vals = B_vals[valid_f]
peak_pos = peak_pos[valid_f]
peak_err = peak_err[valid_f] if peak_err is not None else None

log("Step 3: Extract peak position and uncertainty values from summary sheet.")
log(f"Number of valid peak-tracking points: {len(B_vals)}")
for b, p, e in zip(B_vals, peak_pos, peak_err):
    log(f"  B = {b:g} T, peak position = {p:.6g} a.u., error = {e:.6g} a.u.")

# Validate spectra
log("Validation of sheet 'e' spectra:")
for fld in field_labels:
    y = spectra[fld]
    finite = np.isfinite(y)
    if finite.sum() < 3:
        log(f"  Field {fld}: insufficient finite points for plotting.")
    else:
        log(f"  Field {fld}: {finite.sum()} finite points, min={np.nanmin(y):.6g}, max={np.nanmax(y):.6g}")

# Plotting
plt.style.use('default')
fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2), constrained_layout=True)

# Panel e: field-dependent spectra
ax = axes[0]
cmap = plt.get_cmap('viridis')
n = len(field_labels)
for i, fld in enumerate(field_labels):
    y = spectra[fld]
    color = cmap(i / max(n - 1, 1))
    ax.plot(bias_vals, y, lw=1.5, color=color, label=f"B = {fld} T")
ax.set_xlabel("Bias (mV)")
ax.set_ylabel("dI/dV (a.u.)")
ax.set_title("Fig. 5e: Field-dependent spectra")
ax.legend(frameon=False, fontsize=8, ncol=2, loc='best')
ax.tick_params(direction='out')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Panel f: peak position vs field
ax = axes[1]
ax.errorbar(B_vals, peak_pos, yerr=peak_err, fmt='o-', color='black', ecolor='gray',
            elinewidth=1.2, capsize=3, markersize=5, lw=1.5)
ax.set_xlabel("B (T)")
ax.set_ylabel("Peak Position (a.u.)")
ax.set_title("Fig. 5f: Peak position vs field")
ax.tick_params(direction='out')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Ensure exact field labels are preserved in panel e legend order
log("Step 4: Verify field labels and axis units.")
log(f"Panel e legend labels used: {[f'B = {fld} T' for fld in field_labels]}")
log("Axis labels used: Bias (mV), dI/dV (a.u.), B (T), Peak Position (a.u.)")

# Save figure
fig.savefig(figure_path, dpi=300, bbox_inches='tight')
plt.close(fig)

log("Step 5: Assemble publication-style figure and export result.")
log(f"Figure saved to: {figure_path}")

analysis_text = "\n".join(analysis_lines)
analysis_path.write_text(analysis_text, encoding='utf-8')

print(f"Saved figure to: {figure_path}")
print(f"Saved analysis to: {analysis_path}")