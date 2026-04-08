import os
import re
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/005_Proximityinduced_chiral_quantum_light_generation/type1_data/41563_2023_1645_MOESM7_ESM_10.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/005_Proximityinduced_chiral_quantum_light_generation/results/PAPER_05_TASK_11_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/005_Proximityinduced_chiral_quantum_light_generation/results/PAPER_05_TASK_11_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)
os.makedirs(os.path.dirname(analysis_path), exist_ok=True)

analysis_lines = []

def log(msg):
    analysis_lines.append(msg)

log("Task PAPER_05_TASK_11: Replot the time-resolved PL decay curve and fit")
log(f"Dataset file: {dataset_file}")
log("Step 0: Inspect workbook structure to locate the decay-curve sheet.")

# Load workbook and inspect sheets
xls = pd.ExcelFile(dataset_file)
sheet_names = xls.sheet_names
log(f"Workbook sheets found: {sheet_names}")

# Read a preview of each sheet to identify time-delay / normalized counts structure
sheet_info = []
for sh in sheet_names:
    df_preview = pd.read_excel(dataset_file, sheet_name=sh, header=None, nrows=8)
    nrows, ncols = pd.read_excel(dataset_file, sheet_name=sh, header=None).shape
    first_row = df_preview.iloc[0].astype(str).tolist() if len(df_preview) > 0 else []
    sheet_info.append((sh, nrows, ncols, first_row))
    log(f"Sheet '{sh}': {nrows} rows x {ncols} cols; first row = {first_row}")

# Heuristic search for decay-like sheet
candidate = None
candidate_reason = ""
for sh in sheet_names:
    df = pd.read_excel(dataset_file, sheet_name=sh, header=None)
    # Look for headers containing time, delay, count, normalized, lifetime, fit
    header_text = " ".join(df.iloc[0].astype(str).tolist()).lower()
    body_text = " ".join(df.head(5).astype(str).fillna("").values.flatten().tolist()).lower()
    text = header_text + " " + body_text
    if any(k in text for k in ["time", "delay", "count", "normalized", "norm", "lifetime", "fit"]):
        candidate = sh
        candidate_reason = f"Matched keywords in sheet text: {text[:200]}"
        break

if candidate is None:
    # Fallback: choose sheet with monotonic numeric first column and one or more signal columns
    for sh in sheet_names:
        df = pd.read_excel(dataset_file, sheet_name=sh, header=None)
        # Try to parse first few rows as numeric
        data = df.copy()
        for c in data.columns:
            data[c] = pd.to_numeric(data[c], errors="coerce")
        if data.shape[1] >= 2:
            x = data.iloc[1:, 0].dropna().values
            if len(x) > 10:
                dx = np.diff(x)
                if np.all(np.isfinite(dx)) and (np.all(dx <= 0) or np.all(dx >= 0)):
                    candidate = sh
                    candidate_reason = "Selected by monotonic numeric first column and multiple numeric columns."
                    break

if candidate is None:
    log("No decay-like sheet could be confidently identified from workbook structure.")
    log("Limitation: workbook preview does not expose a clear time-delay / normalized-count decay panel.")
    # Still save a note and exit gracefully with empty figure
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.text(0.5, 0.5, "Decay sheet not identified\nfrom workbook preview", ha="center", va="center")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(figure_path, dpi=300)
    plt.close(fig)
    log(f"Saved placeholder figure to {figure_path}")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise SystemExit(0)

log(f"Identified candidate decay sheet: '{candidate}'")
log(f"Reason: {candidate_reason}")

# Load candidate sheet with header inference
df_raw = pd.read_excel(dataset_file, sheet_name=candidate, header=None)
log(f"Loaded sheet '{candidate}' with shape {df_raw.shape}")

# Detect header row: first row with at least one non-numeric label and at least 2 columns
header_row = 0
for i in range(min(10, len(df_raw))):
    row = df_raw.iloc[i].astype(str).tolist()
    joined = " ".join(row).lower()
    if any(k in joined for k in ["time", "delay", "count", "norm", "fit", "lifetime"]):
        header_row = i
        break

log(f"Using row {header_row} as header row based on keyword inspection.")

df = pd.read_excel(dataset_file, sheet_name=candidate, header=header_row)
log(f"Parsed dataframe columns: {list(df.columns)}")

# Normalize column names
cols = [str(c).strip() for c in df.columns]
df.columns = cols

# Identify x and y columns
x_col = None
y_col = None
fit_col = None

lower_cols = {c.lower(): c for c in df.columns}
for c in df.columns:
    cl = c.lower()
    if x_col is None and any(k in cl for k in ["time", "delay", "tau", "ns", "ps"]):
        x_col = c
    if y_col is None and any(k in cl for k in ["norm", "count", "intensity", "signal", "pl"]):
        y_col = c
    if fit_col is None and any(k in cl for k in ["fit", "fitted", "model"]):
        fit_col = c

# Fallbacks if headers are not descriptive
numeric_df = df.apply(pd.to_numeric, errors="coerce")
numeric_cols = [c for c in numeric_df.columns if numeric_df[c].notna().sum() > 5]

if x_col is None and len(numeric_cols) >= 1:
    x_col = numeric_cols[0]
if y_col is None and len(numeric_cols) >= 2:
    y_col = numeric_cols[1]
if fit_col is None and len(numeric_cols) >= 3:
    fit_col = numeric_cols[2]

log(f"Selected x column: {x_col}")
log(f"Selected y column: {y_col}")
log(f"Selected fit column: {fit_col}")

if x_col is None or y_col is None:
    log("Could not identify both time-delay and normalized-count columns.")
    log("Limitation: insufficient column labeling / numeric structure for decay reconstruction.")
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.text(0.5, 0.5, "Could not identify decay axes", ha="center", va="center")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(figure_path, dpi=300)
    plt.close(fig)
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise SystemExit(0)

# Extract numeric data
x = pd.to_numeric(df[x_col], errors="coerce").values
y = pd.to_numeric(df[y_col], errors="coerce").values
mask = np.isfinite(x) & np.isfinite(y)
x = x[mask]
y = y[mask]

fit = None
if fit_col is not None:
    fit_candidate = pd.to_numeric(df[fit_col], errors="coerce").values
    fit_mask = np.isfinite(fit_candidate)
    if np.sum(fit_mask) > 5:
        fit = fit_candidate[mask] if len(fit_candidate) == len(mask) else fit_candidate[fit_mask]
        if len(fit) != len(x):
            fit = None

log(f"Valid measured points after cleaning: {len(x)}")
if len(x) < 5:
    log("Insufficient data points for a meaningful decay plot or fit.")
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.text(0.5, 0.5, "Insufficient decay data", ha="center", va="center")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(figure_path, dpi=300)
    plt.close(fig)
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise SystemExit(0)

# Sort by x
order = np.argsort(x)
x = x[order]
y = y[order]
if fit is not None and len(fit) == len(order):
    fit = fit[order]

# Determine if semilog is appropriate
positive_fraction = np.mean(y > 0)
use_semilog = positive_fraction > 0.8 and np.nanmax(y) / max(np.nanmin(y[y > 0]), 1e-12) > 20
log(f"Positive fraction of measured counts: {positive_fraction:.3f}")
log(f"Semilog scale selected: {use_semilog}")

# If no fit provided, attempt a simple exponential fit on positive data
tau = None
fit_curve = None
fit_source = None

if fit is not None:
    fit_curve = fit
    fit_source = "provided fit column"
    log("A fit-like column was found and will be overlaid as provided data.")
else:
    # Fit y = A*exp(-x/tau)+C using log-linear approximation after baseline subtraction
    log("No explicit fit column found; attempting a simple exponential refit on the measured decay.")
    # Estimate baseline from last 10% of points
    n_tail = max(3, int(0.1 * len(y)))
    baseline = np.nanmedian(y[-n_tail:])
    y_adj = y - baseline
    positive = y_adj > 0
    if np.sum(positive) >= 5:
        xx = x[positive]
        yy = np.log(y_adj[positive])
        # linear fit ln(y) = ln(A) - x/tau
        slope, intercept = np.polyfit(xx, yy, 1)
        if slope < 0:
            tau = -1.0 / slope
            A = np.exp(intercept)
            fit_curve = A * np.exp(-x / tau) + baseline
            fit_source = "refit exponential model"
            log(f"Estimated baseline from tail: {baseline:.6g}")
            log(f"Refit result: tau = {tau:.6g} (same x-units as axis), A = {A:.6g}")
        else:
            log("Refit failed because the fitted slope was non-negative; no reliable lifetime extracted.")
    else:
        log("Not enough positive baseline-subtracted points for a reliable exponential refit.")

# If fit column exists but lifetime not directly available, estimate from fit curve if possible
if tau is None and fit_curve is not None:
    # Estimate tau from fit curve by linearizing positive values after baseline subtraction
    n_tail = max(3, int(0.1 * len(fit_curve)))
    baseline = np.nanmedian(fit_curve[-n_tail:])
    fit_adj = fit_curve - baseline
    positive = fit_adj > 0
    if np.sum(positive) >= 5:
        xx = x[positive]
        yy = np.log(fit_adj[positive])
        slope, intercept = np.polyfit(xx, yy, 1)
        if slope < 0:
            tau = -1.0 / slope
            log(f"Lifetime estimated from provided fit curve: tau = {tau:.6g} (same x-units as axis)")
        else:
            log("Provided fit curve did not yield a stable exponential lifetime estimate.")
    else:
        log("Provided fit curve insufficient for lifetime estimation after baseline subtraction.")

# Plot
fig, ax = plt.subplots(figsize=(6.2, 4.6))

if use_semilog:
    ax.semilogy(x, y, "o", ms=3.5, color="#1f77b4", label="Measured decay")
    if fit_curve is not None:
        ax.semilogy(x, fit_curve, "-", lw=2.0, color="#d62728", label="Fit")
else:
    ax.plot(x, y, "o", ms=3.5, color="#1f77b4", label="Measured decay")
    if fit_curve is not None:
        ax.plot(x, fit_curve, "-", lw=2.0, color="#d62728", label="Fit")

ax.set_xlabel(str(x_col))
ax.set_ylabel(str(y_col))
title = "Time-resolved PL decay"
if tau is not None:
    title += f" (τ = {tau:.3g} {str(x_col)})"
ax.set_title(title)

ax.legend(frameon=False, loc="best")
ax.grid(True, alpha=0.25)

# Improve publication-style formatting
for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)

fig.tight_layout()
fig.savefig(figure_path, dpi=300)
plt.close(fig)

log(f"Saved figure to {figure_path}")
if fit_source is not None:
    log(f"Fit source used: {fit_source}")
if tau is not None:
    log(f"Reported lifetime extraction: tau = {tau:.6g} in the same units as the x-axis.")
else:
    log("No defensible lifetime could be extracted from the available data/fit information.")
    log("Limitation: the workbook did not provide a clearly labeled fit parameter or a stable exponential decay suitable for robust lifetime extraction.")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))