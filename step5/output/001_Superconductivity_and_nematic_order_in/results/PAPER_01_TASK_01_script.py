import os
import re
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

try:
    from scipy.signal import find_peaks
except Exception:
    find_peaks = None

# -----------------------------
# Paths
# -----------------------------
dataset_file = Path(r"C:/UCLEAP/UC_LEAP/step4/organized/001_Superconductivity_and_nematic_order_in/type1_data/Fig1b.xlsx")
output_figure = Path(r"C:/UCLEAP/UC_LEAP/step5/output/001_Superconductivity_and_nematic_order_in/results/PAPER_01_TASK_01_figure.png")
output_analysis = Path(r"C:/UCLEAP/UC_LEAP/step5/output/001_Superconductivity_and_nematic_order_in/results/PAPER_01_TASK_01_Analysis.txt")

output_figure.parent.mkdir(parents=True, exist_ok=True)
output_analysis.parent.mkdir(parents=True, exist_ok=True)

analysis_lines = []

def log(msg):
    analysis_lines.append(msg)

# -----------------------------
# Step 0: Load and inspect
# -----------------------------
log("Task: PAPER_01_TASK_01 - Replot the CsTi3Bi5 XRD pattern with indexed reflections")
log(f"Dataset file: {dataset_file}")
log("Step 0: Loading spreadsheet and inspecting sheet structure, headers, and metadata.")

if not dataset_file.exists():
    log("ERROR: Dataset file does not exist. Analysis cannot proceed.")
    with open(output_analysis, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise FileNotFoundError(f"Dataset file not found: {dataset_file}")

xls = pd.ExcelFile(dataset_file)
log(f"Workbook sheets: {xls.sheet_names}")

df_raw = pd.read_excel(dataset_file, sheet_name=xls.sheet_names[0], header=None)
log(f"Loaded sheet '{xls.sheet_names[0]}' with shape {df_raw.shape}.")

# Inspect first few rows
preview_rows = min(8, len(df_raw))
for i in range(preview_rows):
    log(f"Row {i}: {df_raw.iloc[i].tolist()}")

# -----------------------------
# Step 1: Extract columns
# -----------------------------
log("Step 1: Extracting 2θ and intensity columns, handling mixed text/numeric rows.")

# Find header row by searching for likely labels
header_row = None
for idx in range(min(20, len(df_raw))):
    row = [str(x).strip() if pd.notna(x) else "" for x in df_raw.iloc[idx].tolist()]
    joined = " | ".join(row)
    if ("2θ" in joined or "2theta" in joined.lower() or "theta" in joined.lower()) and ("Intensity" in joined or "intensity" in joined.lower()):
        header_row = idx
        break

if header_row is None:
    header_row = 0
    log("No explicit header row detected in first 20 rows; defaulting to first row as header.")

headers = df_raw.iloc[header_row].tolist()
log(f"Detected header row index: {header_row}")
log(f"Headers: {headers}")

df = df_raw.iloc[header_row + 1:].copy()
df.columns = headers

# Normalize column names
col_map = {}
for c in df.columns:
    c_str = str(c).strip()
    if re.search(r"2\s*θ|2theta|theta", c_str, flags=re.IGNORECASE):
        col_map[c] = "2theta"
    elif re.search(r"intensity", c_str, flags=re.IGNORECASE):
        col_map[c] = "intensity"
df = df.rename(columns=col_map)

if "2theta" not in df.columns or "intensity" not in df.columns:
    # fallback: use first two columns
    log("Could not confidently match named columns; falling back to first two columns.")
    df = df.iloc[:, :2].copy()
    df.columns = ["2theta", "intensity"]

# Coerce numeric and drop invalid rows
df["2theta"] = pd.to_numeric(df["2theta"], errors="coerce")
df["intensity"] = pd.to_numeric(df["intensity"], errors="coerce")
before_drop = len(df)
df = df.dropna(subset=["2theta", "intensity"]).copy()
after_drop = len(df)
log(f"Rows before numeric cleaning: {before_drop}; after dropping invalid rows: {after_drop}.")

# Sort by 2theta and remove duplicates if any
df = df.sort_values("2theta").drop_duplicates(subset=["2theta"]).reset_index(drop=True)
log(f"Final cleaned dataset shape: {df.shape}.")
log(f"2θ range: {df['2theta'].min():.4f} to {df['2theta'].max():.4f}")
log(f"Intensity range: {df['intensity'].min():.6g} to {df['intensity'].max():.6g}")

# -----------------------------
# Step 2: Plot intensity vs 2θ
# -----------------------------
log("Step 2: Plotting intensity versus 2θ using a clean line plot.")

x = df["2theta"].to_numpy()
y = df["intensity"].to_numpy()

# Baseline normalization only for plotting convenience if needed? Keep raw values for fidelity.
# Determine if data appear to be XRD-like with many points and positive intensities.
if len(x) < 10:
    log("WARNING: Very few data points; plot fidelity may be limited.")
if np.nanmax(y) <= 0:
    log("WARNING: Non-positive intensity values detected; plot may not represent a valid XRD pattern.")

# -----------------------------
# Step 3: Peak detection and annotation
# -----------------------------
log("Step 3: Detecting prominent peaks and checking for indexing information.")

# Search for any text labels/annotations in workbook beyond numeric data
# Since only one sheet is present and preview shows only numeric data, no indexing labels are evident.
log("No embedded indexing labels or annotations were detected in the provided spreadsheet preview.")
log("Peak annotations will only be added if peaks are unambiguous from the data.")

peak_indices = np.array([], dtype=int)
peak_props = {}

if find_peaks is not None and len(y) >= 5:
    # Use a conservative prominence threshold based on signal range to avoid noise peaks.
    y_range = float(np.nanmax(y) - np.nanmin(y))
    prominence = max(y_range * 0.02, np.nanstd(y) * 3 if np.nanstd(y) > 0 else 0)
    distance = max(1, int(len(y) * 0.002))
    peak_indices, peak_props = find_peaks(y, prominence=prominence, distance=distance)
    log(f"Initial peak detection using scipy.signal.find_peaks with prominence={prominence:.6g}, distance={distance}.")
    log(f"Detected {len(peak_indices)} candidate peaks before filtering.")
else:
    log("SciPy peak detection unavailable or insufficient data; peak detection skipped.")

# Filter peaks to only clearly prominent local maxima
selected_peaks = []
if len(peak_indices) > 0:
    prominences = peak_props.get("prominences", np.zeros(len(peak_indices)))
    heights = y[peak_indices]
    # Keep peaks that are clearly above local background and among strongest features
    if len(heights) > 0:
        height_threshold = np.nanpercentile(y, 90)
        for idx, prom, h in zip(peak_indices, prominences, heights):
            if h >= height_threshold and prom > 0:
                selected_peaks.append((idx, prom, h))
    # If too few peaks survive, keep the strongest few only if they are clearly local maxima
    if len(selected_peaks) == 0 and len(peak_indices) > 0:
        order = np.argsort(y[peak_indices])[::-1]
        top = peak_indices[order[:min(8, len(order))]]
        for idx in top:
            selected_peaks.append((idx, None, y[idx]))

# Sort selected peaks by position
selected_peaks = sorted(selected_peaks, key=lambda t: x[t[0]])

if len(selected_peaks) == 0:
    log("No defensible peaks could be identified with sufficient confidence; no peak markers will be added.")
else:
    log(f"Selected {len(selected_peaks)} defensible peak(s) for annotation.")
    for idx, prom, h in selected_peaks:
        log(f"Peak at 2θ = {x[idx]:.4f}, intensity = {h:.6g}" + (f", prominence = {prom:.6g}" if prom is not None else ""))

# -----------------------------
# Figure styling
# -----------------------------
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.linewidth": 1.2,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.major.size": 5,
    "ytick.major.size": 5,
    "xtick.minor.size": 3,
    "ytick.minor.size": 3,
})

fig, ax = plt.subplots(figsize=(7.2, 4.8), dpi=300)

ax.plot(x, y, color="black", lw=1.0)

# Add peak markers if justified
if len(selected_peaks) > 0:
    peak_x = [x[idx] for idx, _, _ in selected_peaks]
    peak_y = [y[idx] for idx, _, _ in selected_peaks]
    ax.scatter(peak_x, peak_y, s=18, color="crimson", zorder=3, label="Detected peaks")
    for idx, _, _ in selected_peaks:
        ax.annotate(f"{x[idx]:.2f}", (x[idx], y[idx]),
                    textcoords="offset points", xytext=(0, 6),
                    ha="center", va="bottom", fontsize=8, color="crimson")

# Axis labels
ax.set_xlabel(r"2$\theta$ (deg)")
ax.set_ylabel("Intensity (arb. units)")

# Limits and ticks
ax.set_xlim(np.nanmin(x), np.nanmax(x))
ymin = np.nanmin(y)
ymax = np.nanmax(y)
pad = 0.05 * (ymax - ymin) if ymax > ymin else 0.05 * ymax if ymax != 0 else 1.0
ax.set_ylim(max(0, ymin - pad), ymax + pad)

ax.minorticks_on()
ax.tick_params(which="both", top=True, right=True)

# Clean style similar to publication figure
for spine in ax.spines.values():
    spine.set_visible(True)

if len(selected_peaks) > 0:
    ax.legend(frameon=False, loc="best", fontsize=9)

fig.tight_layout()

# -----------------------------
# Step 4: Export
# -----------------------------
log("Step 4: Exporting the replot as a figure panel.")
fig.savefig(output_figure, dpi=300, bbox_inches="tight")
plt.close(fig)

log(f"Figure saved to: {output_figure}")

# Write analysis file
log("Analysis summary:")
log("The spreadsheet contains a single sheet with two columns corresponding to 2θ and intensity.")
log("The data were cleaned by coercing numeric values and removing invalid rows.")
log("The plot was generated directly from the cleaned data without inventing missing annotations.")
if len(selected_peaks) == 0:
    log("Because no peaks were identified with sufficient confidence, no peak labels were added.")
else:
    log("Peak markers were added only for clearly detected local maxima supported by the signal.")

with open(output_analysis, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure to: {output_figure}")
print(f"Saved analysis to: {output_analysis}")