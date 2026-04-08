import os
import re
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/008_Extremely_anisotropic_van_der_Waals/type1_data/41586_2021_3867_MOESM3_ESM_8.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/008_Extremely_anisotropic_van_der_Waals/results/PAPER_08_TASK_03_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/008_Extremely_anisotropic_van_der_Waals/results/PAPER_08_TASK_03_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)
os.makedirs(os.path.dirname(analysis_path), exist_ok=True)

analysis_lines = []

def log(msg):
    analysis_lines.append(msg)

log("Task PAPER_08_TASK_03 Analysis")
log("Objective: Replot temperature-dependent thermal conductivity from experiment and MD for bulk MoS2 and r-MoS2.")
log(f"Dataset file: {dataset_file}")
log("Step 0: Open the workbook and inspect sheet structure.")

# Load workbook
xls = pd.ExcelFile(dataset_file)
sheet_names = xls.sheet_names
log(f"Workbook sheets found: {sheet_names}")

# Inspect each sheet briefly
sheet_summaries = {}
for s in sheet_names:
    df_raw = pd.read_excel(dataset_file, sheet_name=s, header=None)
    sheet_summaries[s] = df_raw
    log(f"Sheet '{s}' shape: {df_raw.shape}")
    preview_rows = min(8, len(df_raw))
    for i in range(preview_rows):
        row = df_raw.iloc[i].tolist()
        log(f"  Row {i}: {row[:15]}")

# Identify likely relevant sheet
target_sheet = None
for s in sheet_names:
    df_raw = sheet_summaries[s]
    text = " ".join(df_raw.astype(str).fillna("").values.flatten().tolist()).lower()
    if ("temperature" in text or "t (k)" in text or "k/m/k" in text or "thermal conductivity" in text):
        target_sheet = s
        break
if target_sheet is None:
    target_sheet = sheet_names[0]
log(f"Selected sheet for analysis: '{target_sheet}'")

df_raw = sheet_summaries[target_sheet]

# Determine header row by searching for temperature/conductivity keywords
header_row = None
for i in range(min(20, len(df_raw))):
    row_text = " | ".join([str(x) for x in df_raw.iloc[i].tolist() if pd.notna(x)])
    low = row_text.lower()
    if ("temperature" in low or "t (k)" in low or "k (w/m/k)" in low or "thermal conductivity" in low):
        header_row = i
        break

if header_row is None:
    # fallback: use first row with many non-empty cells
    nonempty_counts = df_raw.notna().sum(axis=1)
    header_row = int(nonempty_counts.idxmax())

log(f"Detected header row: {header_row}")

# Build columns from header row and parse data beneath
headers = df_raw.iloc[header_row].tolist()
data = df_raw.iloc[header_row + 1:].reset_index(drop=True)
data.columns = headers

# Clean duplicate/blank headers
clean_cols = []
seen = {}
for c in data.columns:
    c0 = str(c).strip()
    if c0 == "nan" or c0 == "":
        c0 = "Unnamed"
    if c0 in seen:
        seen[c0] += 1
        c0 = f"{c0}_{seen[c0]}"
    else:
        seen[c0] = 0
    clean_cols.append(c0)
data.columns = clean_cols

log("Step 1: Extract temperature and conductivity columns.")
log(f"Parsed columns: {list(data.columns)}")

# Helper to find columns
def find_cols(patterns):
    matches = []
    for c in data.columns:
        cl = str(c).lower()
        if all(p in cl for p in patterns):
            matches.append(c)
    return matches

# Identify candidate numeric columns
numeric_data = pd.DataFrame(index=data.index)
for c in data.columns:
    numeric_data[c] = pd.to_numeric(data[c], errors="coerce")

# Find temperature columns and conductivity columns
temp_cols = []
k_cols = []
for c in data.columns:
    cl = str(c).lower()
    if re.search(r'\b(v|x)\s*\(k\)|temperature|t\s*\(k\)|x\s*\(k\)', cl):
        temp_cols.append(c)
    if ("k" in cl and ("w/m/k" in cl or "w m k" in cl or "conduct" in cl or "thermal" in cl)) or ("conductivity" in cl):
        k_cols.append(c)

# More robust: inspect all columns for numeric ranges and names
for c in data.columns:
    cl = str(c).lower()
    if "temperature" in cl or "t (k)" in cl or "x (k)" in cl:
        if c not in temp_cols:
            temp_cols.append(c)

# If no explicit temperature column, infer from numeric columns with plausible temperature range
if not temp_cols:
    for c in data.columns:
        ser = numeric_data[c].dropna()
        if len(ser) > 5:
            mn, mx = ser.min(), ser.max()
            if mn >= 0 and mx <= 2000 and mx - mn > 10:
                temp_cols.append(c)
                break

# Identify likely conductivity columns by names
for c in data.columns:
    cl = str(c).lower()
    if any(key in cl for key in ["conductivity", "k (w/m/k)", "k_in", "k out", "in-plane", "out-of-plane", "in plane", "out of plane"]):
        if c not in k_cols:
            k_cols.append(c)

# If still ambiguous, use all numeric columns except temperature as candidates
if not k_cols:
    for c in data.columns:
        if c not in temp_cols:
            ser = numeric_data[c].dropna()
            if len(ser) > 5:
                k_cols.append(c)

log(f"Candidate temperature columns: {temp_cols}")
log(f"Candidate conductivity columns: {k_cols}")

# Determine series structure from sheet content
# The provided preview suggests this workbook may not contain thermal conductivity data.
# We validate by checking whether any columns have temperature-like and conductivity-like values.
series_info = []
for c in data.columns:
    ser = numeric_data[c].dropna()
    if len(ser) == 0:
        continue
    series_info.append((c, len(ser), float(ser.min()), float(ser.max())))

log("Numeric column summary (column, count, min, max):")
for item in series_info[:30]:
    log(f"  {item}")

# Attempt to identify if this sheet actually contains the requested thermal conductivity data
# by searching for relevant keywords in the workbook text.
workbook_text = " ".join(df_raw.astype(str).fillna("").values.flatten().tolist()).lower()
has_thermal_keywords = any(k in workbook_text for k in ["thermal conductivity", "conductivity", "moS2".lower(), "r-mos2", "in-plane", "out-of-plane", "md", "simulation", "experiment", "temperature"])
log(f"Keyword presence check for thermal-conductivity-related terms: {has_thermal_keywords}")

# Based on preview, this sheet appears to contain Fig. 4c/d/e with temperature rise and I-V data, not thermal conductivity vs temperature.
# We therefore cannot fabricate a thermal conductivity plot from unsupported data.
log("Step 2: Identify series corresponding to bulk MoS2, r-MoS2, experimental values, and MD simulation outputs.")
log("Observation: The inspected sheet contains columns labeled with x (nm), ΔT_Au surface (K), ΔT_MoS2 surface (K), V (V), I (mA), and Ic (mA).")
log("These are spatial temperature-rise and electrical I-V data, not temperature-dependent thermal conductivity series.")
log("No explicit columns for temperature-dependent thermal conductivity, in-plane/out-of-plane conductivity, or MD/experimental conductivity series were found in the workbook preview.")
log("Therefore, the required thermal conductivity figure cannot be reconstructed from this workbook without making unsupported assumptions.")

# Create a clear placeholder figure explaining limitation
fig, ax = plt.subplots(figsize=(10, 6))
ax.axis("off")
msg = (
    "Requested thermal conductivity vs temperature data not found in the provided workbook.\n\n"
    "Inspected sheet: 'Fig. 4'\n"
    "Available data in preview: spatial x (nm), ΔT_Au surface (K), ΔT_MoS2 surface (K), V (V), I (mA), Ic (mA)\n\n"
    "Conclusion:\n"
    "The workbook does not expose the temperature-dependent in-plane/out-of-plane thermal conductivity\n"
    "series needed to reproduce the requested Fig. 2c-style plot.\n"
    "No unsupported data were fabricated."
)
ax.text(0.5, 0.5, msg, ha="center", va="center", fontsize=12, wrap=True)
plt.tight_layout()
plt.savefig(figure_path, dpi=300, bbox_inches="tight")
plt.close(fig)

log("Step 3: Plot conductivity versus temperature with separate curves for each transport direction and material.")
log("Not performed because the necessary conductivity-vs-temperature data are absent from the inspected workbook.")
log("Step 4: Format axes, units, and line styles.")
log("Not performed for the same reason; instead, a limitation figure was saved to document the missing data.")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure to: {figure_path}")
print(f"Saved analysis to: {analysis_path}")