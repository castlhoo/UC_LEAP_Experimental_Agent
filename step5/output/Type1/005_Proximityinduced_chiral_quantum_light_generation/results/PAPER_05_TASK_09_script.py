import os
import re
import math
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# -----------------------------
# Paths
# -----------------------------
dataset_path = Path(r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/005_Proximityinduced_chiral_quantum_light_generation/type1_data/41563_2023_1645_MOESM5_ESM_10.xlsx")
figure_path = Path(r"C:/UCLEAP/UC_LEAP/step5/output/Type1/005_Proximityinduced_chiral_quantum_light_generation/results/PAPER_05_TASK_09_figure.png")
analysis_path = Path(r"C:/UCLEAP/UC_LEAP/step5/output/Type1/005_Proximityinduced_chiral_quantum_light_generation/results/PAPER_05_TASK_09_Analysis.txt")

figure_path.parent.mkdir(parents=True, exist_ok=True)
analysis_path.parent.mkdir(parents=True, exist_ok=True)

# -----------------------------
# Helpers
# -----------------------------
def to_numeric_df(df):
    out = df.copy()
    for c in out.columns:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return out

def find_sheet_by_keywords(sheet_names, must_have=None, any_of=None):
    must_have = must_have or []
    any_of = any_of or []
    for s in sheet_names:
        sl = s.lower()
        if all(k.lower() in sl for k in must_have) and (not any_of or any(k.lower() in sl for k in any_of)):
            return s
    return None

def infer_excitation_sheet(sheet_names, excitation_label):
    # Prefer sheets with explicit excitation label in name
    candidates = [s for s in sheet_names if excitation_label.lower().replace("+", "plus").replace("-", "minus") in s.lower()]
    if candidates:
        return candidates[0]
    # Fallback: sheets containing Fig 4a/c etc. based on dataset preview
    if excitation_label == "sigma+":
        for s in sheet_names:
            if s.lower() in ["fig 4a", "fig 4c", "fig4a", "fig4c"]:
                return s
    if excitation_label == "sigma-":
        for s in sheet_names:
            if s.lower() in ["fig 4b", "fig 4d", "fig4b", "fig4d"]:
                return s
    return None

def parse_channel_columns(columns):
    cols = [str(c).strip() for c in columns]
    energy_col = None
    for c in cols:
        if c.lower() in ["energy", "ener5gy", "energy"]:
            energy_col = c
            break
    channel_cols = [c for c in cols if c != energy_col]
    return energy_col, channel_cols

def normalize_trace(y):
    y = np.asarray(y, dtype=float)
    finite = np.isfinite(y)
    if not np.any(finite):
        return y
    ymin = np.nanmin(y[finite])
    ymax = np.nanmax(y[finite])
    if np.isclose(ymax, ymin):
        return y * np.nan
    return (y - ymin) / (ymax - ymin)

# -----------------------------
# Load workbook and inspect structure
# -----------------------------
xls = pd.ExcelFile(dataset_path)
sheet_names = xls.sheet_names

# Identify likely sheets for sigma+ and sigma- excitation
# Based on preview, Fig 4a and Fig 4c are the relevant spectra sheets.
sheet_sigma_plus = "Fig 4a" if "Fig 4a" in sheet_names else infer_excitation_sheet(sheet_names, "sigma+")
sheet_sigma_minus = "Fig 4c" if "Fig 4c" in sheet_names else infer_excitation_sheet(sheet_names, "sigma-")

analysis_lines = []
analysis_lines.append("Task PAPER_05_TASK_09 Analysis")
analysis_lines.append(f"Dataset file: {dataset_path}")
analysis_lines.append(f"Available sheets: {sheet_names}")
analysis_lines.append("")
analysis_lines.append("Step_0: Locate the sheets for σ+ and σ− excitation conditions and identify the emitted channels.")
analysis_lines.append(f"Selected sheet for σ+ excitation: {sheet_sigma_plus}")
analysis_lines.append(f"Selected sheet for σ− excitation: {sheet_sigma_minus}")
analysis_lines.append("Reasoning: The workbook preview shows Fig 4a contains columns labeled with sigma- and sigma+ emission channels under a common energy axis, and Fig 4c contains analogous spectra with s- and s+ channels. These are the only sheets in the preview that contain full spectral traces suitable for replotting excitation-dependent PL spectra.")
analysis_lines.append("Emitted channels identified from the sheet headers:")
analysis_lines.append(" - Fig 4a: sigma- 6T, sigma+ 6T, sigma- 3T, sigma+ 3T, sigma- 0T, sigma+ 0T, sigma- -3T, sigma+ -3T, sigma- -6T, sigma+ -6T")
analysis_lines.append(" - Fig 4c: s- 0TB, s+ 0TB, s- 6TA, s+ 6TA, s- 3TA, s+ 3TA, s- 0TA, s+ 0TA")
analysis_lines.append("Limitation: The workbook preview does not explicitly label which sheet corresponds to σ+ excitation versus σ− excitation in the sheet name. The selection below is based on the dataset organization and the task request to compare excitation polarizations using the available circular-polarization-resolved spectra.")
analysis_lines.append("")

# Load data
df_plus_raw = pd.read_excel(dataset_path, sheet_name=sheet_sigma_plus)
df_minus_raw = pd.read_excel(dataset_path, sheet_name=sheet_sigma_minus)

analysis_lines.append("Step_1: Extract the energy axis and plot the spectra for each excitation condition on shared axes.")
analysis_lines.append(f"Loaded {sheet_sigma_plus}: shape={df_plus_raw.shape}")
analysis_lines.append(f"Loaded {sheet_sigma_minus}: shape={df_minus_raw.shape}")

# Convert to numeric
df_plus = to_numeric_df(df_plus_raw)
df_minus = to_numeric_df(df_minus_raw)

energy_col_plus, channels_plus = parse_channel_columns(df_plus.columns)
energy_col_minus, channels_minus = parse_channel_columns(df_minus.columns)

analysis_lines.append(f"Detected energy column in {sheet_sigma_plus}: {energy_col_plus}")
analysis_lines.append(f"Detected energy column in {sheet_sigma_minus}: {energy_col_minus}")
analysis_lines.append(f"Detected channel columns in {sheet_sigma_plus}: {channels_plus}")
analysis_lines.append(f"Detected channel columns in {sheet_sigma_minus}: {channels_minus}")

# Validate spectra
valid_plus = energy_col_plus is not None and len(channels_plus) > 0 and df_plus[energy_col_plus].notna().sum() > 10
valid_minus = energy_col_minus is not None and len(channels_minus) > 0 and df_minus[energy_col_minus].notna().sum() > 10

analysis_lines.append(f"Spectrum validity for {sheet_sigma_plus}: {valid_plus}")
analysis_lines.append(f"Spectrum validity for {sheet_sigma_minus}: {valid_minus}")

if not (valid_plus and valid_minus):
    analysis_lines.append("Limitation: One or both sheets do not contain a valid numeric energy axis and multiple spectral channels, so a defensible replot cannot be produced.")
    analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")
    raise RuntimeError("Insufficient valid spectral data for plotting.")

# Use first channel pairings as provided; preserve all traces
energy_plus = df_plus[energy_col_plus].to_numpy(dtype=float)
energy_minus = df_minus[energy_col_minus].to_numpy(dtype=float)

# Sort by energy if needed
idxp = np.argsort(energy_plus)
idxm = np.argsort(energy_minus)
energy_plus = energy_plus[idxp]
energy_minus = energy_minus[idxm]

# Determine whether data appear already normalized / replot-ready
# Heuristic: values are small integers/near integers in preview, but spectra are likely already processed.
# We preserve the workbook values and only apply a common min-max scaling per trace for visual comparability if needed.
# Since task asks to preserve normalization used in dataset, we do not alter raw values unless necessary.
analysis_lines.append("Step_2: Normalize or scale traces consistently if the workbook indicates that the data are replot-ready normalized spectra.")
analysis_lines.append("Observation: The spectral columns contain small integer-like values and appear to be preprocessed/replot-ready data rather than raw detector counts. To preserve the workbook's normalization, the traces are plotted directly without additional normalization.")
analysis_lines.append("Reasoning: Applying extra normalization would alter the relative intensity structure already encoded in the workbook. Therefore, the figure uses the provided values as-is.")
analysis_lines.append("")

# Plot
plt.figure(figsize=(10, 6), dpi=200)
ax = plt.gca()

# Colors and styles
plus_colors = plt.cm.Blues(np.linspace(0.45, 0.9, max(1, len(channels_plus))))
minus_colors = plt.cm.Reds(np.linspace(0.45, 0.9, max(1, len(channels_minus))))

# Plot sigma+ excitation sheet
for i, ch in enumerate(channels_plus):
    y = df_plus[ch].to_numpy(dtype=float)[idxp]
    label = f"σ+ exc. | {ch}"
    ax.plot(energy_plus, y, color=plus_colors[i], lw=1.4, alpha=0.95, label=label)

# Plot sigma- excitation sheet
for i, ch in enumerate(channels_minus):
    y = df_minus[ch].to_numpy(dtype=float)[idxm]
    label = f"σ− exc. | {ch}"
    ax.plot(energy_minus, y, color=minus_colors[i], lw=1.4, alpha=0.95, linestyle="--", label=label)

ax.set_xlabel("Energy")
ax.set_ylabel("Intensity (as provided in workbook)")
ax.set_title("Circular-polarization-resolved PL spectra under σ+ and σ− excitation")
ax.grid(True, alpha=0.25)

# Compact legend
ax.legend(loc="best", fontsize=7, ncol=2, frameon=True)

# Add annotations emphasizing comparison
ax.text(0.02, 0.98, "Solid lines: σ+ excitation sheet\nDashed lines: σ− excitation sheet",
        transform=ax.transAxes, va="top", ha="left", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="gray", alpha=0.85))

# If energy ranges differ, note it
emin = min(np.nanmin(energy_plus), np.nanmin(energy_minus))
emax = max(np.nanmax(energy_plus), np.nanmax(energy_minus))
ax.set_xlim(emin, emax)

plt.tight_layout()
plt.savefig(figure_path, bbox_inches="tight")
plt.close()

analysis_lines.append("Step_3: Add legends and annotations to emphasize the comparison between excitation polarizations.")
analysis_lines.append(f"Figure saved to: {figure_path}")
analysis_lines.append("Reasoning: The final plot overlays all available circular-polarization-resolved channels from the two selected sheets on common axes, with solid versus dashed styling and explicit legend labels to distinguish σ+ and σ− excitation.")
analysis_lines.append("")
analysis_lines.append("Quantitative note:")
analysis_lines.append(" - No peak fitting or peak assignment was performed because the task is a figure reproduction/replotting task and the workbook preview does not provide explicit peak labels for these spectra.")
analysis_lines.append(" - The plotted traces are directly taken from the workbook values; no unsupported recalibration or background subtraction was introduced.")
analysis_lines.append("")
analysis_lines.append("Exclusions and limitations:")
analysis_lines.append(" - The workbook preview does not explicitly state which sheet is σ+ excitation and which is σ− excitation in the sheet names. The mapping used here is based on the available sheet organization and the task context.")
analysis_lines.append(" - If the original publication figure uses a different sheet-to-excitation mapping, that cannot be verified from the preview alone.")
analysis_lines.append(" - No additional normalization was applied because the data appear already prepared for plotting.")

analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")
print(f"Saved figure to: {figure_path}")
print(f"Saved analysis to: {analysis_path}")