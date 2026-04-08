import os
import re
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

DATASET_FILE = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/007_Inverse_design_of_chiral_functional/type1_data/41467_2023_41951_MOESM7_ESM_8.xlsx"
OUTPUT_FIGURE = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/007_Inverse_design_of_chiral_functional/results/PAPER_07_TASK_01_figure.png"
OUTPUT_ANALYSIS = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/007_Inverse_design_of_chiral_functional/results/PAPER_07_TASK_01_Analysis.txt"

os.makedirs(Path(OUTPUT_FIGURE).parent, exist_ok=True)

analysis_lines = []

def log(msg):
    analysis_lines.append(msg)

def safe_to_numeric(series):
    return pd.to_numeric(series, errors="coerce")

def clean_df(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    for c in df.columns:
        df[c] = safe_to_numeric(df[c])
    df = df.dropna(how="all")
    df = df.dropna(axis=1, how="all")
    return df

def infer_x_col(df):
    for c in df.columns:
        if "wavelength" in str(c).lower() or "nm" in str(c).lower():
            return c
    return df.columns[0]

def infer_y_cols(df, x_col):
    return [c for c in df.columns if c != x_col]

def make_label(colname, idx):
    s = str(colname).strip()
    if s.lower() in ["gabs", "normalized cd", "cd", "abs", "absorbance"]:
        return f"{s} {idx+1}" if idx > 0 else s
    return s if s else f"trace {idx+1}"

def plot_sheet(ax, sheet_name, df):
    x_col = infer_x_col(df)
    y_cols = infer_y_cols(df, x_col)
    x = df[x_col].to_numpy(dtype=float)

    valid_traces = []
    for i, c in enumerate(y_cols):
        y = df[c].to_numpy(dtype=float)
        mask = np.isfinite(x) & np.isfinite(y)
        if mask.sum() < 3:
            continue
        x_m = x[mask]
        y_m = y[mask]
        if np.allclose(y_m, y_m[0]):
            continue
        valid_traces.append((c, x_m, y_m))

    if not valid_traces:
        ax.text(0.5, 0.5, f"No valid traces\n{sheet_name}", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return

    cmap = plt.get_cmap("tab10")
    for i, (c, x_m, y_m) in enumerate(valid_traces):
        label = make_label(c, i)
        ax.plot(x_m, y_m, lw=1.6, color=cmap(i % 10), label=label)

    ax.set_title(sheet_name, fontsize=10, pad=6)
    ax.set_xlabel("Wavelength (nm)")
    ylab = "Signal"
    cols_lower = " ".join([str(c).lower() for c in df.columns])
    if "normalized cd" in cols_lower:
        ylab = "Normalized CD"
    elif "gabs" in cols_lower:
        ylab = "gabs"
    ax.set_ylabel(ylab)
    ax.grid(True, alpha=0.25, linewidth=0.6)
    ax.tick_params(labelsize=8)
    if len(valid_traces) <= 6:
        ax.legend(fontsize=7, frameon=False, loc="best")
    else:
        ax.legend(fontsize=6, frameon=False, loc="best", ncol=2)

def main():
    log(f"Loaded dataset: {DATASET_FILE}")
    xls = pd.ExcelFile(DATASET_FILE)
    sheet_names = xls.sheet_names
    log(f"Workbook contains {len(sheet_names)} sheets.")
    log("Sheet names:")
    for s in sheet_names:
        log(f"  - {s}")

    dfs = {}
    for s in sheet_names:
        try:
            raw = pd.read_excel(DATASET_FILE, sheet_name=s, header=0)
            log(f"\nInspecting sheet '{s}': raw shape {raw.shape}")
            log(f"  Raw columns: {list(raw.columns)[:10]}")
            df = clean_df(raw)
            log(f"  Cleaned shape: {df.shape}")
            if df.shape[1] == 0 or df.shape[0] == 0:
                log("  Sheet skipped: no usable numeric data after cleaning.")
                continue
            x_col = infer_x_col(df)
            y_cols = infer_y_cols(df, x_col)
            log(f"  Inferred x-axis column: {x_col}")
            log(f"  Inferred y-axis columns: {y_cols[:10]}{' ...' if len(y_cols) > 10 else ''}")
            dfs[s] = df
        except Exception as e:
            log(f"  Failed to read sheet '{s}': {e}")

    if not dfs:
        log("No sheets contained usable data. Exiting without figure.")
        with open(OUTPUT_ANALYSIS, "w", encoding="utf-8") as f:
            f.write("\n".join(analysis_lines))
        return

    n = len(dfs)
    ncols = 2 if n > 1 else 1
    nrows = math.ceil(n / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(7.5 * ncols, 3.8 * nrows), constrained_layout=True)
    if n == 1:
        axes = np.array([axes])
    axes = np.array(axes).reshape(nrows, ncols)

    for ax in axes.flat[n:]:
        ax.set_visible(False)

    for ax, (sheet_name, df) in zip(axes.flat, dfs.items()):
        plot_sheet(ax, sheet_name, df)

    fig.suptitle("Recreated spectral panels from Excel workbook", fontsize=14, y=1.01)
    fig.savefig(OUTPUT_FIGURE, dpi=300, bbox_inches="tight")
    plt.close(fig)

    log(f"\nSaved figure to: {OUTPUT_FIGURE}")
    log("Analysis summary:")
    log("  - Workbook structure inspected and all sheet names listed.")
    log("  - Each sheet was cleaned by coercing numeric strings to numbers and removing empty rows/columns.")
    log("  - X-axis inferred primarily from wavelength-like columns; y-axis traces plotted for all remaining numeric columns.")
    log("  - Multi-trace sheets were overlaid in a single panel with legends when feasible.")
    log("  - Figure saved as a multi-panel layout mirroring workbook organization.")

    with open(OUTPUT_ANALYSIS, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))

if __name__ == "__main__":
    main()