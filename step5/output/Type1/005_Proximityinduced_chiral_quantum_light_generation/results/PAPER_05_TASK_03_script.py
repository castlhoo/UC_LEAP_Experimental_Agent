import os
import re
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/005_Proximityinduced_chiral_quantum_light_generation/type1_data/41563_2023_1645_MOESM12_ESM_10.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/005_Proximityinduced_chiral_quantum_light_generation/results/PAPER_05_TASK_03_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/005_Proximityinduced_chiral_quantum_light_generation/results/PAPER_05_TASK_03_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)
os.makedirs(os.path.dirname(analysis_path), exist_ok=True)

analysis_lines = []
analysis_lines.append("Task PAPER_05_TASK_03 Analysis")
analysis_lines.append("=" * 40)
analysis_lines.append(f"Dataset file: {dataset_file}")
analysis_lines.append("")

# Step 0: inspect workbook structure
analysis_lines.append("Step 0: Locate sheets containing control indentation spectra and excitation-polarization-dependent PL traces.")
analysis_lines.append("I first inspected the workbook structure to identify sheets and infer which one contains the relevant spectra.")
try:
    xls = pd.ExcelFile(dataset_file)
    sheet_names = xls.sheet_names
    analysis_lines.append(f"Workbook sheets found: {sheet_names}")
except Exception as e:
    analysis_lines.append(f"Failed to open workbook: {e}")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise

# Load all sheets and inspect
sheet_data = {}
for sh in sheet_names:
    try:
        df = pd.read_excel(dataset_file, sheet_name=sh)
        sheet_data[sh] = df
        analysis_lines.append(f"Sheet '{sh}': shape={df.shape}, columns={list(df.columns[:8])}{'...' if len(df.columns) > 8 else ''}")
    except Exception as e:
        analysis_lines.append(f"Could not read sheet '{sh}': {e}")

analysis_lines.append("")
analysis_lines.append("Interpretation of workbook organization:")
analysis_lines.append("The provided workbook contains a single sheet ('ED 8'). Based on the column headers and data layout, this sheet appears to contain multiple spectra/traces indexed by condition labels such as '6T sig+', '6T sig-', ..., '0T sig+', '0T sig-', 'n1T sig+', etc.")
analysis_lines.append("No separate sheet for a control indentation spectrum was present in the workbook preview. Therefore, the available data support replotting the excitation-polarization-dependent spectra only; a distinct control indentation spectrum could not be identified from this workbook.")
analysis_lines.append("")

# Identify likely spectral sheet
target_sheet = None
for sh, df in sheet_data.items():
    cols = [str(c).strip() for c in df.columns]
    if any("Energy" == c or c.lower() == "energy" for c in cols):
        target_sheet = sh
        break

if target_sheet is None:
    analysis_lines.append("No sheet with an Energy axis was found. Cannot proceed with spectral plotting.")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise RuntimeError("No spectral sheet found")

df = sheet_data[target_sheet].copy()
analysis_lines.append(f"Selected sheet for analysis: '{target_sheet}'")
analysis_lines.append("")

# Step 1: extract energy axis and channels
analysis_lines.append("Step 1: Extract the energy axis and all polarization/excitation-condition channels.")
analysis_lines.append("I checked the first rows and column structure to determine how the spectra are organized.")
analysis_lines.append(f"Dataframe shape: {df.shape}")
analysis_lines.append(f"First columns: {list(df.columns[:10])}")
analysis_lines.append("")

# Clean columns
df.columns = [str(c).strip() for c in df.columns]
energy_col = None
for c in df.columns:
    if c.lower() == "energy":
        energy_col = c
        break

if energy_col is None:
    analysis_lines.append("Energy column not found explicitly. Cannot proceed.")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise RuntimeError("Energy column missing")

# Convert all columns to numeric where possible
for c in df.columns:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Determine trace pairs from headers
trace_cols = [c for c in df.columns if c != energy_col]
pairs = []
used = set()
for c in trace_cols:
    if c in used:
        continue
    m = re.match(r"^(.*)\s+(sig\+|sig-)$", c, flags=re.IGNORECASE)
    if m:
        base = m.group(1).strip()
        sig = m.group(2).lower()
        partner = f"{base} {'sig-' if sig == 'sig+' else 'sig+'}"
        if partner in df.columns:
            pairs.append((base, f"{base} sig+", f"{base} sig-"))
            used.add(f"{base} sig+")
            used.add(f"{base} sig-")
        else:
            # single channel
            pairs.append((base, c, None))
            used.add(c)
    else:
        used.add(c)

# If pair detection failed due to ordering, build from unique prefixes
if not pairs:
    bases = []
    for c in trace_cols:
        m = re.match(r"^(.*)\s+(sig\+|sig-)$", c, flags=re.IGNORECASE)
        if m:
            bases.append(m.group(1).strip())
    unique_bases = []
    for b in bases:
        if b not in unique_bases:
            unique_bases.append(b)
    for b in unique_bases:
        plus = f"{b} sig+"
        minus = f"{b} sig-"
        if plus in df.columns or minus in df.columns:
            pairs.append((b, plus if plus in df.columns else None, minus if minus in df.columns else None))

analysis_lines.append(f"Identified {len(pairs)} condition groups from column labels.")
for base, plus, minus in pairs:
    analysis_lines.append(f"  Condition '{base}': plus={plus is not None}, minus={minus is not None}")
analysis_lines.append("")

# Step 2: plot spectra
analysis_lines.append("Step 2: Plot the spectra for each condition on shared axes, using consistent normalization if required by the dataset.")
analysis_lines.append("I examined the numeric ranges to determine whether normalization is needed. The traces appear to be already on a comparable count scale, so I preserved the raw values and used a shared energy axis.")
analysis_lines.append("Because the workbook contains multiple traces for different excitation conditions, I overlaid them in a multi-panel format to make comparison clear.")
analysis_lines.append("")

energy = df[energy_col].to_numpy(dtype=float)
valid_energy = np.isfinite(energy)
energy = energy[valid_energy]

# Sort by energy ascending for plotting
sort_idx = np.argsort(energy)
energy = energy[sort_idx]

# Determine plot layout
n_groups = len(pairs)
if n_groups == 0:
    analysis_lines.append("No valid trace groups were identified. Cannot plot spectra.")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise RuntimeError("No trace groups found")

# Create figure
fig, axes = plt.subplots(n_groups, 1, figsize=(10, max(3.0, 2.2 * n_groups)), sharex=True)
if n_groups == 1:
    axes = [axes]

colors = plt.cm.tab20(np.linspace(0, 1, max(2, n_groups)))

for i, (base, plus_col, minus_col) in enumerate(pairs):
    ax = axes[i]
    plotted_any = False

    if plus_col is not None and plus_col in df.columns:
        y = df.loc[valid_energy, plus_col].to_numpy(dtype=float)[sort_idx]
        ax.plot(energy, y, color=colors[i % len(colors)], lw=1.6, label=plus_col)
        plotted_any = True

    if minus_col is not None and minus_col in df.columns:
        y = df.loc[valid_energy, minus_col].to_numpy(dtype=float)[sort_idx]
        ax.plot(energy, y, color=colors[(i + 1) % len(colors)], lw=1.6, ls="--", label=minus_col)
        plotted_any = True

    ax.set_ylabel("Counts")
    ax.set_title(base, loc="left", fontsize=10)
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper right")
    ax.grid(True, alpha=0.2)

    if not plotted_any:
        ax.text(0.5, 0.5, f"No valid data for {base}", transform=ax.transAxes, ha="center", va="center")

axes[-1].set_xlabel("Energy")
fig.suptitle("Excitation-polarization-dependent PL traces from workbook 'ED 8'", y=0.995, fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.985])

# Step 3: annotations and limitations
analysis_lines.append("Step 3: Add annotations or legends that make the invariance or comparison across excitation conditions visually clear.")
analysis_lines.append("I used legends for each trace pair and stacked panels by condition so that differences or invariance can be visually compared across excitation labels.")
analysis_lines.append("")
analysis_lines.append("Validation and limitations:")
analysis_lines.append("1. The workbook contains one sheet only ('ED 8'), which appears to be a multi-trace spectral dataset.")
analysis_lines.append("2. The available columns are labeled by excitation condition and polarization channel (e.g., '6T sig+', '6T sig-').")
analysis_lines.append("3. A distinct control indentation spectrum on WSe2/hBN/PMMA was not identifiable from the provided workbook structure, so I did not fabricate or infer a separate control trace.")
analysis_lines.append("4. The spectra were plotted directly from the numeric values in the workbook without peak fitting or normalization beyond preserving the raw count scale, because the task did not provide a calibration or normalization rule and the data already share a common axis.")
analysis_lines.append("5. No peak assignment was added because the workbook preview does not provide explicit peak labels, and peak identification would require additional validation from the full spectral context.")
analysis_lines.append("")
analysis_lines.append("Output produced:")
analysis_lines.append(f"Figure saved to: {figure_path}")
analysis_lines.append("Analysis completed with the limitation that only the excitation-polarization-dependent spectra could be confidently reconstructed from the workbook.")

# Save figure and analysis
fig.savefig(figure_path, dpi=300, bbox_inches="tight")
plt.close(fig)

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure: {figure_path}")
print(f"Saved analysis: {analysis_path}")