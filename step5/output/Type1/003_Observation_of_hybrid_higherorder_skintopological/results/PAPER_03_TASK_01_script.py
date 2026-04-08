import os
import sys
import json
import math
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/003_Observation_of_hybrid_higherorder_skintopological/type1_data/41467_2021_26414_MOESM2_ESM_8.xls"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/003_Observation_of_hybrid_higherorder_skintopological/results/PAPER_03_TASK_01_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/003_Observation_of_hybrid_higherorder_skintopological/results/PAPER_03_TASK_01_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)
os.makedirs(os.path.dirname(analysis_path), exist_ok=True)

analysis_lines = []

def log(msg):
    analysis_lines.append(msg)

def safe_read_excel(path):
    ext = Path(path).suffix.lower()
    if ext == ".xls":
        try:
            return pd.read_excel(path, sheet_name=None, engine="xlrd")
        except Exception as e:
            raise RuntimeError(f"Failed to read legacy .xls file with xlrd: {e}")
    else:
        return pd.read_excel(path, sheet_name=None)

log("Task PAPER_03_TASK_01 Analysis")
log(f"Step_0: Loading dataset from: {dataset_file}")
try:
    sheets = safe_read_excel(dataset_file)
    log(f"Loaded workbook successfully. Number of sheets: {len(sheets)}")
except Exception as e:
    log(f"ERROR: Could not load workbook. Reason: {e}")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise

sheet_summaries = []
for sname, df in sheets.items():
    summary = {
        "sheet": sname,
        "shape": df.shape,
        "columns": list(df.columns.astype(str)),
    }
    sheet_summaries.append(summary)
    log(f"Step_1: Sheet '{sname}' shape={df.shape}")
    log(f"  Columns: {summary['columns'][:12]}{' ...' if len(summary['columns']) > 12 else ''}")
    log("  Sample rows:")
    if df.shape[0] > 0:
        sample = df.head(5)
        log(sample.to_string(index=False))
    else:
        log("  [Empty sheet]")

# Heuristic inspection to identify likely figure structure
# Prefer sheets with numeric grids or paired x-y data.
candidate_info = []
for sname, df in sheets.items():
    numeric_cols = []
    for c in df.columns:
        ser = pd.to_numeric(df[c], errors="coerce")
        if ser.notna().sum() > 0:
            numeric_cols.append(c)
    candidate_info.append((sname, len(numeric_cols), df.shape[0], df.shape[1]))

candidate_info_sorted = sorted(candidate_info, key=lambda x: (x[1], x[2], x[3]), reverse=True)
log("Step_2: Heuristic assessment of sheet types based on numeric content:")
for item in candidate_info_sorted:
    log(f"  Sheet '{item[0]}': numeric_columns={item[1]}, rows={item[2]}, cols={item[3]}")

# Try to infer a plot type from the workbook structure
plot_mode = None
selected_sheet = None
selected_df = None

# First, look for long-form x-y data with 2-4 columns
for sname, df in sheets.items():
    if df.shape[1] >= 2 and df.shape[0] >= 3:
        # Count numeric columns
        num_mask = [pd.to_numeric(df[c], errors="coerce").notna().sum() > max(2, int(0.5 * len(df))) for c in df.columns]
        nnum = sum(num_mask)
        if nnum >= 2:
            selected_sheet = sname
            selected_df = df.copy()
            if df.shape[1] <= 5:
                plot_mode = "xy"
            else:
                plot_mode = "heatmap_or_multi"
            break

if selected_df is None:
    # fallback to first sheet
    selected_sheet = list(sheets.keys())[0]
    selected_df = sheets[selected_sheet].copy()
    plot_mode = "unknown"

log(f"Selected sheet for plotting: '{selected_sheet}'")
log(f"Inferred plot mode: {plot_mode}")

# Clean dataframe
df = selected_df.copy()
df.columns = [str(c).strip() for c in df.columns]

# Attempt to detect a header row issue if first row contains strings and columns are generic
if all(str(c).startswith("Unnamed") or str(c).isdigit() for c in df.columns):
    log("Detected generic/unnamed columns; attempting to use first row as headers if appropriate.")
    if df.shape[0] > 1:
        new_headers = df.iloc[0].astype(str).tolist()
        df2 = df.iloc[1:].copy()
        df2.columns = [h.strip() for h in new_headers]
        df = df2
        log(f"Reassigned headers from first row: {list(df.columns)}")

# Convert columns to numeric where possible
numeric_df = pd.DataFrame(index=df.index)
for c in df.columns:
    numeric_df[c] = pd.to_numeric(df[c], errors="coerce")

# Determine if there is a likely x-axis and one or more y-series
numeric_cols = [c for c in numeric_df.columns if numeric_df[c].notna().sum() > 0]
log(f"Numeric-like columns detected: {numeric_cols}")

fig = plt.figure(figsize=(8.5, 6.5), dpi=300)

# Plotting logic
if len(numeric_cols) >= 2 and plot_mode == "xy":
    xcol = numeric_cols[0]
    ycols = numeric_cols[1:]
    x = numeric_df[xcol].to_numpy()
    valid_x = np.isfinite(x)
    x = x[valid_x]
    log(f"Using '{xcol}' as x-axis.")
    ax = fig.add_subplot(1, 1, 1)
    for yc in ycols:
        y = numeric_df[yc].to_numpy()[valid_x]
        valid = np.isfinite(y) & np.isfinite(x)
        if valid.sum() == 0:
            continue
        ax.plot(x[valid], y[valid], marker="o", ms=3.5, lw=1.5, label=str(yc))
        log(f"Plotted series '{yc}' with {valid.sum()} points.")
    ax.set_xlabel(str(xcol))
    ax.set_ylabel("Value")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(True, alpha=0.25)
    ax.set_title(f"Reconstructed plot from sheet '{selected_sheet}'")
elif len(numeric_cols) >= 3 and plot_mode == "heatmap_or_multi":
    # Try to detect a matrix-like table: first column labels, remaining numeric grid
    # If there are many columns and rows, plot as heatmap.
    if df.shape[1] >= 4 and df.shape[0] >= 4:
        # Use numeric matrix from all numeric columns
        mat = numeric_df[numeric_cols].to_numpy(dtype=float)
        # Remove rows/cols that are all NaN
        row_mask = np.isfinite(mat).any(axis=1)
        col_mask = np.isfinite(mat).any(axis=0)
        mat = mat[row_mask][:, col_mask]
        if mat.size > 0 and mat.shape[0] > 1 and mat.shape[1] > 1:
            ax = fig.add_subplot(1, 1, 1)
            im = ax.imshow(mat, aspect="auto", origin="lower", cmap="viridis")
            cbar = fig.colorbar(im, ax=ax, pad=0.02)
            cbar.set_label("Intensity / amplitude")
            ax.set_xlabel("Column index")
            ax.set_ylabel("Row index")
            ax.set_title(f"Heatmap-like reconstruction from sheet '{selected_sheet}'")
            log(f"Plotted heatmap from numeric matrix with shape {mat.shape}.")
        else:
            ax = fig.add_subplot(1, 1, 1)
            for yc in numeric_cols[1:]:
                y = numeric_df[yc].to_numpy()
                x = np.arange(len(y))
                valid = np.isfinite(y)
                if valid.sum() == 0:
                    continue
                ax.plot(x[valid], y[valid], marker="o", ms=3, lw=1.2, label=str(yc))
                log(f"Fallback line plot for '{yc}' with {valid.sum()} points.")
            ax.set_xlabel("Index")
            ax.set_ylabel("Value")
            ax.legend(frameon=False, fontsize=8)
            ax.grid(True, alpha=0.25)
    else:
        ax = fig.add_subplot(1, 1, 1)
        for yc in numeric_cols[1:]:
            y = numeric_df[yc].to_numpy()
            x = np.arange(len(y))
            valid = np.isfinite(y)
            if valid.sum() == 0:
                continue
            ax.plot(x[valid], y[valid], marker="o", ms=3, lw=1.2, label=str(yc))
            log(f"Fallback line plot for '{yc}' with {valid.sum()} points.")
        ax.set_xlabel("Index")
        ax.set_ylabel("Value")
        ax.legend(frameon=False, fontsize=8)
        ax.grid(True, alpha=0.25)
        ax.set_title(f"Reconstructed plot from sheet '{selected_sheet}'")
else:
    ax = fig.add_subplot(1, 1, 1)
    # Generic fallback: plot all numeric columns against row index
    plotted = 0
    for c in numeric_cols:
        y = numeric_df[c].to_numpy()
        x = np.arange(len(y))
        valid = np.isfinite(y)
        if valid.sum() == 0:
            continue
        ax.plot(x[valid], y[valid], marker="o", ms=3, lw=1.2, label=str(c))
        plotted += 1
        log(f"Generic fallback plot for '{c}' with {valid.sum()} points.")
    ax.set_xlabel("Index")
    ax.set_ylabel("Value")
    if plotted > 0:
        ax.legend(frameon=False, fontsize=8)
    ax.grid(True, alpha=0.25)
    ax.set_title(f"Generic reconstruction from sheet '{selected_sheet}'")

# Add a note about limitations and mapping
log("Step_3: Data cleaning and reshaping were limited to numeric coercion and header normalization.")
log("Step_4: Figure recreated using publication-style formatting where supported by the detected data structure.")
log("Step_5: Saving outputs.")

fig.tight_layout()
fig.savefig(figure_path, bbox_inches="tight")
plt.close(fig)

# Write analysis text
log("")
log("Interpretation note:")
log("The workbook structure was inspected directly. The figure type was inferred from the available sheet layout and numeric content.")
log("If the file contains a more specific panel organization than detected here, that organization could not be confirmed without clearer headers or explicit labels in the data.")
log(f"Figure saved to: {figure_path}")
log(f"Analysis saved to: {analysis_path}")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure to: {figure_path}")
print(f"Saved analysis to: {analysis_path}")