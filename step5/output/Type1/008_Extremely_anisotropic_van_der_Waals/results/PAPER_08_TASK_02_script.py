import os
import re
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# -----------------------------
# Paths
# -----------------------------
dataset_file = Path(r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/008_Extremely_anisotropic_van_der_Waals/type1_data/41586_2021_3867_MOESM2_ESM_8.xlsx")
figure_path = Path(r"C:/UCLEAP/UC_LEAP/step5/output/Type1/008_Extremely_anisotropic_van_der_Waals/results/PAPER_08_TASK_02_figure.png")
analysis_path = Path(r"C:/UCLEAP/UC_LEAP/step5/output/Type1/008_Extremely_anisotropic_van_der_Waals/results/PAPER_08_TASK_02_Analysis.txt")

figure_path.parent.mkdir(parents=True, exist_ok=True)
analysis_path.parent.mkdir(parents=True, exist_ok=True)

analysis_lines = []

def log(msg):
    analysis_lines.append(msg)

# -----------------------------
# Step 0: Load workbook and inspect structure
# -----------------------------
log("Task PAPER_08_TASK_02 Analysis")
log("Step 0: Open workbook and inspect sheet structure.")
log(f"Dataset file: {dataset_file}")

if not dataset_file.exists():
    log("ERROR: Dataset file does not exist. Task cannot proceed.")
    analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")
    raise FileNotFoundError(f"Dataset file not found: {dataset_file}")

try:
    xls = pd.ExcelFile(dataset_file)
except Exception as e:
    log(f"ERROR: Failed to open workbook: {e}")
    analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")
    raise

log(f"Workbook sheets: {xls.sheet_names}")

# Read all sheets as raw tables
sheets = {}
for s in xls.sheet_names:
    try:
        df = pd.read_excel(dataset_file, sheet_name=s, header=None)
        sheets[s] = df
        log(f"Loaded sheet '{s}' with shape {df.shape}.")
    except Exception as e:
        log(f"WARNING: Could not read sheet '{s}': {e}")

# -----------------------------
# Helper functions
# -----------------------------
def to_numeric_series(series):
    return pd.to_numeric(series, errors="coerce")

def find_header_row(df, keywords):
    for i in range(min(len(df), 20)):
        row = df.iloc[i].astype(str).str.lower().tolist()
        joined = " | ".join(row)
        if all(k.lower() in joined for k in keywords):
            return i
    return None

def extract_block(df, start_row, start_col, ncols):
    block = df.iloc[start_row:, start_col:start_col+ncols].copy()
    block.columns = list(range(ncols))
    return block

# -----------------------------
# Step 1: Identify relevant sheet and extract N / thermal resistance
# -----------------------------
log("Step 1: Identify sheet containing thermal resistance versus layer number.")

target_sheet = None
for s, df in sheets.items():
    text = df.astype(str).fillna("").apply(lambda col: col.str.lower())
    joined = " ".join(text.head(10).astype(str).values.flatten())
    if ("conductance" in joined or "thermal" in joined or "n =" in joined) and ("fig. 3b" in s.lower() or "inset" in joined):
        target_sheet = s
        break

if target_sheet is None and "Fig. 3b" in sheets:
    target_sheet = "Fig. 3b"

log(f"Selected sheet for analysis: {target_sheet}")

df = sheets[target_sheet]

# The sheet contains multiple side-by-side tables:
# N=2, N=3, N=4, N=5, and an inset for D=1 um r-MoS2 conductance vs N.
# We extract the inset table because it contains layer number N and conductance values.
header_row = find_header_row(df, ["x:", "n", "y: conductance"])
if header_row is None:
    # fallback: use known structure from preview
    header_row = 1
log(f"Detected/assumed header row for inset table: {header_row}")

# Inset table appears in columns 16-19 (0-indexed) from preview
inset_block = extract_block(df, header_row, 16, 4)
inset_block = inset_block.dropna(how="all")
inset_block.columns = ["N", "Conductance_uW_per_K", "Uncertainty_uW_per_K", "Extra"]
log(f"Inset block extracted with shape {inset_block.shape}.")

# Clean numeric data
inset_block["N"] = to_numeric_series(inset_block["N"])
inset_block["Conductance_uW_per_K"] = to_numeric_series(inset_block["Conductance_uW_per_K"])
inset_block["Uncertainty_uW_per_K"] = to_numeric_series(inset_block["Uncertainty_uW_per_K"])

inset_block = inset_block.dropna(subset=["N", "Conductance_uW_per_K"])
inset_block = inset_block[inset_block["N"] > 0].copy()

log("Inset table preview after cleaning:")
for _, r in inset_block.head(10).iterrows():
    log(f"  N={r['N']}, Conductance={r['Conductance_uW_per_K']} uW/K, uncertainty={r['Uncertainty_uW_per_K']} uW/K")

# -----------------------------
# Step 2: Convert conductance to thermal resistance equivalent
# -----------------------------
log("Step 2: Convert conductance to thermal resistance equivalent where possible.")

# The task asks for thermal boundary resistance R_TDTR (m^2 K/GW) or equivalent.
# The sheet provides conductance in uW/K. Without area calibration, absolute conversion to m^2 K/GW is not possible.
# Therefore, we report the directly supported quantity and its reciprocal as an equivalent resistance-like trend.
# Reciprocal of conductance gives K/uW, which is a valid derived quantity from the data.
# We do not invent area-normalized R_TDTR.
inset_block["Resistance_K_per_uW"] = 1.0 / inset_block["Conductance_uW_per_K"]
inset_block["Resistance_uncertainty_K_per_uW"] = inset_block["Uncertainty_uW_per_K"] / (inset_block["Conductance_uW_per_K"] ** 2)

log("Derived reciprocal resistance-like quantity computed as 1/Conductance (K/uW).")
log("Note: Absolute R_TDTR in m^2 K/GW cannot be computed from the workbook alone because the area normalization is not provided in the extracted table.")

# -----------------------------
# Step 3: Separate r-MoS2 and r-WS2 series and determine fit availability
# -----------------------------
log("Step 3: Separate r-MoS2 and r-WS2 series and inspect fit information.")

# The provided sheet preview only clearly exposes the inset series for D = 1 um r-MoS2.
# The main table contains N=2,3,4,5 with expt and fit columns for Δω, not thermal resistance.
# Since the workbook preview does not show a second thermal-resistance series for r-WS2 in this sheet,
# we search all sheets for conductance tables or r-WS2 labels.
ws2_found = False
ws2_data = None
for s, sdf in sheets.items():
    txt = sdf.astype(str).fillna("").apply(lambda col: col.str.lower())
    joined = " ".join(txt.head(20).astype(str).values.flatten())
    if "ws2" in joined and ("conductance" in joined or "thermal" in joined):
        ws2_found = True
        ws2_data = sdf
        log(f"Potential r-WS2 thermal data found in sheet '{s}'.")
        break

if not ws2_found:
    log("No explicit r-WS2 thermal resistance/conductance table was identifiable from the workbook preview or sheet scan.")
    log("Only the r-MoS2 inset conductance-vs-N data are directly supported by the extracted sheet content.")

# Fit a simple trend to the supported inset data if enough points exist
fit_available = len(inset_block) >= 2
if fit_available:
    x = inset_block["N"].to_numpy(dtype=float)
    y = inset_block["Conductance_uW_per_K"].to_numpy(dtype=float)
    # Linear fit in conductance vs N
    coeffs = np.polyfit(x, y, 1)
    fit_fn = np.poly1d(coeffs)
    xfit = np.linspace(np.min(x), np.max(x), 200)
    yfit = fit_fn(xfit)
    log(f"Linear fit for r-MoS2 conductance vs N: slope={coeffs[0]:.6g} uW/K per layer, intercept={coeffs[1]:.6g} uW/K.")
else:
    xfit = yfit = None
    log("Insufficient points for a fit to the inset data.")

# -----------------------------
# Step 4: Plot with available supported data
# -----------------------------
log("Step 4: Create publication-quality plot using directly supported data.")

plt.style.use("default")
fig, ax = plt.subplots(figsize=(7.2, 5.2), dpi=300)

# Plot supported r-MoS2 inset data as conductance vs N and reciprocal resistance-like trend on secondary axis
color_mos2 = "#1f77b4"
ax.errorbar(
    inset_block["N"],
    inset_block["Conductance_uW_per_K"],
    yerr=inset_block["Uncertainty_uW_per_K"].fillna(0.0),
    fmt="o",
    ms=6,
    lw=1.2,
    capsize=3,
    color=color_mos2,
    label="r-MoS$_2$ (D = 1 µm), conductance"
)
if fit_available:
    ax.plot(xfit, yfit, "-", color=color_mos2, lw=1.5, alpha=0.85, label="r-MoS$_2$ linear fit")

ax.set_xlabel("Layer number, N")
ax.set_ylabel("Conductance (µW/K)")
ax.tick_params(direction="in", top=True, right=True)
ax.grid(True, alpha=0.2)

# Secondary axis for reciprocal quantity
ax2 = ax.twinx()
ax2.errorbar(
    inset_block["N"],
    inset_block["Resistance_K_per_uW"],
    yerr=inset_block["Resistance_uncertainty_K_per_uW"].fillna(0.0),
    fmt="s",
    ms=5,
    lw=1.0,
    capsize=3,
    color="#d62728",
    label="Reciprocal trend, 1/G"
)
ax2.set_ylabel("Reciprocal conductance (K/µW)")
ax2.tick_params(direction="in", top=True, right=True)

# Build combined legend
handles1, labels1 = ax.get_legend_handles_labels()
handles2, labels2 = ax2.get_legend_handles_labels()
ax.legend(handles1 + handles2, labels1 + labels2, loc="best", frameon=False)

title = "Thermal transport trend vs layer number"
if ws2_found:
    title += " (r-MoS$_2$ and r-WS$_2$)"
else:
    title += " (supported r-MoS$_2$ data only)"
ax.set_title(title)

fig.tight_layout()
fig.savefig(figure_path, bbox_inches="tight")
plt.close(fig)

log(f"Figure saved to: {figure_path}")

# -----------------------------
# Final notes and limitations
# -----------------------------
log("Limitations:")
log("- The workbook sheet 'Fig. 3b' clearly contains an inset table for D = 1 um r-MoS2 with layer number N, conductance, and uncertainty.")
log("- The provided preview does not expose a directly readable r-WS2 thermal resistance table; therefore, a true two-material comparison plot cannot be reconstructed without additional identifiable data.")
log("- The sheet does contain fit columns for Δω in the main table, but those are Raman shift fits, not thermal resistance fits, and were not used for the requested transport plot.")
log("- Absolute R_TDTR (m^2 K/GW) was not computed because the necessary area normalization is not present in the extracted thermal table. A reciprocal conductance trend was plotted as the directly supported equivalent quantity.")

analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")
print(f"Saved figure to: {figure_path}")
print(f"Saved analysis to: {analysis_path}")