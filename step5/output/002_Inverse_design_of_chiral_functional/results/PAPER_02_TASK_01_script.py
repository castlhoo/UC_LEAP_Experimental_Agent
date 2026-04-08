import os
import re
import math
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/002_Inverse_design_of_chiral_functional/type1_data/41467_2023_41951_MOESM7_ESM_5.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/002_Inverse_design_of_chiral_functional/results/PAPER_02_TASK_01_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/002_Inverse_design_of_chiral_functional/results/PAPER_02_TASK_01_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)
os.makedirs(os.path.dirname(analysis_path), exist_ok=True)

analysis_lines = []

def log(msg):
    analysis_lines.append(msg)

def is_numeric_like(x):
    try:
        if pd.isna(x):
            return False
        float(str(x).strip())
        return True
    except Exception:
        return False

def to_numeric_series(s):
    return pd.to_numeric(s.astype(str).str.strip().replace({"": np.nan, "nan": np.nan, "None": np.nan}), errors="coerce")

def clean_headers(df):
    cols = []
    for c in df.columns:
        if isinstance(c, tuple):
            c = " ".join([str(x) for x in c if str(x) != "nan"]).strip()
        c = str(c).strip()
        c = re.sub(r"\s+", " ", c)
        cols.append(c)
    df = df.copy()
    df.columns = cols
    return df

def detect_repeated_header_row(df):
    if df.shape[0] == 0:
        return False
    first = df.iloc[0].astype(str).str.strip().tolist()
    headers = [str(c).strip() for c in df.columns.tolist()]
    score = sum(1 for a, b in zip(first, headers) if a == b or (a.lower() == b.lower()))
    return score >= max(2, len(headers) // 2)

def infer_x_and_y_columns(df):
    cols = list(df.columns)
    x_col = None
    y_cols = []
    for c in cols:
        cl = c.lower()
        if x_col is None and ("wavelength" in cl or cl in ["x", "lambda", "wl"]):
            x_col = c
    if x_col is None:
        for c in cols:
            ser = to_numeric_series(df[c])
            if ser.notna().sum() >= max(10, int(0.5 * len(df))):
                vals = ser.dropna().values
                if len(vals) > 1 and np.nanmax(vals) > np.nanmin(vals):
                    x_col = c
                    break
    for c in cols:
        if c == x_col:
            continue
        ser = to_numeric_series(df[c])
        if ser.notna().sum() >= max(10, int(0.5 * len(df))):
            y_cols.append(c)
    return x_col, y_cols

def split_traces(df, x_col, y_cols):
    traces = []
    if x_col is None or not y_cols:
        return traces
    x = to_numeric_series(df[x_col])
    for y_col in y_cols:
        y = to_numeric_series(df[y_col])
        mask = x.notna() & y.notna()
        if mask.sum() < 5:
            continue
        xx = x[mask].values.astype(float)
        yy = y[mask].values.astype(float)
        order = np.argsort(xx)
        xx = xx[order]
        yy = yy[order]
        traces.append((y_col, xx, yy))
    return traces

def sheet_label(sheet_name):
    return sheet_name.replace("Fugure", "Figure")

xls = pd.ExcelFile(dataset_file)
sheet_names = xls.sheet_names

log(f"Task PAPER_02_TASK_01 analysis")
log(f"Loaded workbook: {dataset_file}")
log(f"Total sheets: {len(sheet_names)}")
log("Step_0: Enumerated sheets, dimensions, and headers.")

sheet_info = []
all_relevant = []

for s in sheet_names:
    raw = pd.read_excel(dataset_file, sheet_name=s, header=None)
    dims = raw.shape
    first_rows = raw.head(3).fillna("").astype(str).values.tolist()
    header_row_idx = None
    if raw.shape[0] > 0:
        for i in range(min(5, raw.shape[0])):
            row = raw.iloc[i].astype(str).str.strip().tolist()
            if any("wavelength" in str(v).lower() for v in row):
                header_row_idx = i
                break
    if header_row_idx is None:
        header_row_idx = 0
    df = pd.read_excel(dataset_file, sheet_name=s, header=header_row_idx)
    df = clean_headers(df)
    if detect_repeated_header_row(df):
        df = df.iloc[1:].reset_index(drop=True)
    df = df.dropna(how="all").reset_index(drop=True)
    x_col, y_cols = infer_x_and_y_columns(df)
    traces = split_traces(df, x_col, y_cols)
    sheet_info.append((s, dims, list(df.columns), x_col, y_cols, len(traces)))
    if traces:
        all_relevant.append((s, df, x_col, y_cols, traces))

    log(f"Sheet '{s}': raw shape {dims[0]} rows x {dims[1]} cols")
    log(f"  Cleaned columns: {list(df.columns)}")
    log(f"  Inferred x-axis column: {x_col}")
    log(f"  Inferred response columns: {y_cols}")
    log(f"  Valid traces detected: {len(traces)}")

log("Step_1: Identified wavelength-resolved tables by searching for wavelength-like x columns and numeric response columns.")
log("Step_2: Cleaned headers, removed repeated header rows when present, and converted numeric columns to arrays.")
log("Step_3: Replotted each valid spectral trace using wavelength on x-axis and response on y-axis.")
log("Step_4: Assembled a multi-panel figure organized by workbook sheet structure.")

if len(all_relevant) == 0:
    fig = plt.figure(figsize=(10, 6))
    ax = fig.add_subplot(111)
    ax.text(0.5, 0.5, "No wavelength-resolved spectra could be identified.", ha="center", va="center", fontsize=14)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(figure_path, dpi=300, bbox_inches="tight")
    log("No valid spectral panels were identified; saved placeholder figure.")
else:
    n = len(all_relevant)
    ncols = 2 if n > 1 else 1
    nrows = math.ceil(n / ncols)
    fig = plt.figure(figsize=(7.5 * ncols, 4.8 * nrows))
    gs = GridSpec(nrows, ncols, figure=fig, hspace=0.35, wspace=0.25)

    cmap = plt.get_cmap("tab10")
    for idx, (s, df, x_col, y_cols, traces) in enumerate(all_relevant):
        ax = fig.add_subplot(gs[idx // ncols, idx % ncols])
        for j, (y_name, xx, yy) in enumerate(traces):
            color = cmap(j % 10)
            label = y_name if len(traces) > 1 else None
            ax.plot(xx, yy, lw=1.8, color=color, label=label)
        ax.set_title(sheet_label(s), fontsize=11, pad=8)
        ax.set_xlabel(x_col if x_col else "Wavelength (nm)")
        ylab = "Response"
        if any("normalized cd" in str(c).lower() for c in y_cols):
            ylab = "Normalized CD"
        elif any("gabs" in str(c).lower() for c in y_cols):
            ylab = "gabs"
        ax.set_ylabel(ylab)
        ax.grid(True, alpha=0.25, linewidth=0.6)
        if len(traces) > 1:
            ax.legend(fontsize=8, frameon=False, loc="best")
        for spine in ax.spines.values():
            spine.set_linewidth(0.8)

    fig.suptitle("Reconstructed supplementary spectral workbook panels", fontsize=15, y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.985])
    fig.savefig(figure_path, dpi=300, bbox_inches="tight")
    log(f"Saved multi-panel figure to: {figure_path}")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure: {figure_path}")
print(f"Saved analysis: {analysis_path}")