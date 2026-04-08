import os
import re
import csv
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/007_Inverse_design_of_chiral_functional/type1_data/20_gabs_outfile.csv"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/007_Inverse_design_of_chiral_functional/results/PAPER_07_TASK_02_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/007_Inverse_design_of_chiral_functional/results/PAPER_07_TASK_02_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)
os.makedirs(os.path.dirname(analysis_path), exist_ok=True)

analysis_lines = []

def log(msg):
    analysis_lines.append(msg)

log("Task PAPER_07_TASK_02 Analysis")
log("Step_0: Load the CSV and inspect its columns, row count, and any metadata fields.")

# Read raw file to inspect structure
with open(dataset_file, "r", encoding="utf-8-sig", errors="replace") as f:
    raw_lines = f.read().splitlines()

log(f"Loaded file: {os.path.basename(dataset_file)}")
log(f"Total raw lines read: {len(raw_lines)}")

if len(raw_lines) == 0:
    raise ValueError("CSV file is empty.")

header = raw_lines[0]
log(f"Header preview: {header[:200]}")

# Parse header manually because the first column contains a metadata label with a special character
header_parts = next(csv.reader([header]))
log(f"Parsed header columns: {len(header_parts)}")

# Determine wavelength columns from header
first_col = header_parts[0]
wavelength_cols = header_parts[1:]
wavelength_values = []
for c in wavelength_cols:
    try:
        wavelength_values.append(float(c))
    except Exception:
        wavelength_values.append(np.nan)

# Build dataframe from remaining lines
data_rows = []
for line in raw_lines[1:]:
    if not line.strip():
        continue
    parts = next(csv.reader([line]))
    data_rows.append(parts)

max_len = max(len(r) for r in data_rows) if data_rows else 0
log(f"Number of data rows detected: {len(data_rows)}")
log(f"Maximum row length detected: {max_len}")

# Normalize row lengths
normalized_rows = []
for r in data_rows:
    if len(r) < len(header_parts):
        r = r + [None] * (len(header_parts) - len(r))
    elif len(r) > len(header_parts):
        r = r[:len(header_parts)]
    normalized_rows.append(r)

df = pd.DataFrame(normalized_rows, columns=header_parts)

log("Step_1: Identify the main response variable(s), especially gabs, and any associated wavelength or sample-condition columns.")
log(f"First column name: {first_col}")
log(f"Number of wavelength-like columns detected from header: {len(wavelength_cols)}")

# Extract sample metadata from first column
meta = df.iloc[:, 0].astype(str)
meta_split = meta.str.split("-", expand=True)
meta_split_cols = []
if meta_split.shape[1] >= 4:
    meta_split_cols = ["feature", "Color", "thickness", "stretch", "gray"][:meta_split.shape[1]]
    meta_split.columns = meta_split_cols
    for c in meta_split.columns:
        df[c] = meta_split[c]
    log(f"Metadata fields inferred from first column: {meta_split_cols}")
else:
    log("Could not reliably split first column into four metadata fields; using raw labels only.")

# Convert numeric wavelength columns
numeric_cols = []
for c in wavelength_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    numeric_cols.append(c)

# Identify rows with usable numeric data
numeric_matrix = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
valid_counts = numeric_matrix.notna().sum(axis=1)
df["valid_numeric_points"] = valid_counts

log(f"Rows with at least one numeric value: {(valid_counts > 0).sum()} / {len(df)}")
log(f"Rows with at least 5 numeric values: {(valid_counts >= 5).sum()} / {len(df)}")

# Determine if there is a clear gabs-like response table
# Since the file is named gabs_outfile, treat the numeric table as gabs values across wavelengths.
# Use the wavelength columns as x-axis and each row as a sample/condition.
# Clean rows with too few valid points.
min_points = 5
plot_df = df.loc[valid_counts >= min_points].copy()

log("Step_2: Clean the table by handling missing values, converting numeric fields, and standardizing labels.")
log(f"Rows retained for plotting after requiring at least {min_points} numeric points: {len(plot_df)}")

# Standardize labels for plotting
if "feature" in plot_df.columns:
    plot_df["sample_label"] = plot_df["feature"].astype(str)
else:
    plot_df["sample_label"] = plot_df.iloc[:, 0].astype(str)

# Build wavelength array
x = np.array([v for v in wavelength_values if not np.isnan(v)], dtype=float)
valid_wavelength_mask = ~np.isnan(np.array(wavelength_values, dtype=float))
x_cols = [c for c, ok in zip(wavelength_cols, valid_wavelength_mask) if ok]

log(f"Wavelength range inferred from header: {x.min() if len(x) else 'NA'} to {x.max() if len(x) else 'NA'} nm")
log(f"Number of usable wavelength columns: {len(x_cols)}")

# Prepare plot data
series_list = []
for idx, row in plot_df.iterrows():
    y = pd.to_numeric(row[x_cols], errors="coerce").to_numpy(dtype=float)
    if np.isfinite(y).sum() < min_points:
        continue
    series_list.append((str(row["sample_label"]), y, idx))

log(f"Number of plotted series: {len(series_list)}")

# If there are many series, plot a ranked summary by mean absolute gabs magnitude
if len(series_list) == 0:
    raise ValueError("No usable numeric series found for plotting.")

summary = []
for label, y, idx in series_list:
    finite = np.isfinite(y)
    mean_abs = np.nanmean(np.abs(y[finite])) if finite.any() else np.nan
    max_abs = np.nanmax(np.abs(y[finite])) if finite.any() else np.nan
    summary.append((label, idx, mean_abs, max_abs))

summary_df = pd.DataFrame(summary, columns=["label", "row_index", "mean_abs_gabs", "max_abs_gabs"])
summary_df = summary_df.sort_values(["mean_abs_gabs", "max_abs_gabs"], ascending=False).reset_index(drop=True)

log("Step_3: Create a plot that summarizes the gabs results, such as a line plot versus wavelength, a bar chart of candidate values, or a scatter plot if multiple conditions are present.")

plt.figure(figsize=(12, 8), dpi=200)

# Use a two-panel figure if multiple series exist: left = line plot, right = ranked summary
if len(series_list) > 1:
    gs = plt.GridSpec(1, 2, width_ratios=[2.2, 1.0], wspace=0.25)
    ax1 = plt.subplot(gs[0, 0])
    ax2 = plt.subplot(gs[0, 1])

    cmap = plt.cm.viridis
    n = len(series_list)
    for i, (label, y, idx) in enumerate(series_list):
        finite = np.isfinite(y)
        if finite.sum() < min_points:
            continue
        color = cmap(i / max(n - 1, 1))
        ax1.plot(x[finite], y[finite], lw=1.5, alpha=0.85, color=color, label=label)

    ax1.set_xlabel("Wavelength (nm)")
    ax1.set_ylabel("gabs")
    ax1.set_title("gabs spectra across samples/conditions")
    ax1.grid(True, alpha=0.25)

    # Avoid overcrowded legend if too many series
    if len(series_list) <= 12:
        ax1.legend(fontsize=8, frameon=False, loc="best")
    else:
        ax1.text(0.01, 0.99, f"{len(series_list)} series plotted", transform=ax1.transAxes,
                 va="top", ha="left", fontsize=9,
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8, edgecolor="none"))

    # Ranked summary bar chart
    topn = min(15, len(summary_df))
    plot_summary = summary_df.head(topn).iloc[::-1]
    ax2.barh(plot_summary["label"], plot_summary["mean_abs_gabs"], color="#4C72B0")
    ax2.set_xlabel("Mean |gabs|")
    ax2.set_title("Ranked sample summary")
    ax2.grid(True, axis="x", alpha=0.25)
    ax2.tick_params(axis="y", labelsize=8)
else:
    ax1 = plt.gca()
    label, y, idx = series_list[0]
    finite = np.isfinite(y)
    ax1.plot(x[finite], y[finite], lw=2.0, color="#1f77b4")
    ax1.set_xlabel("Wavelength (nm)")
    ax1.set_ylabel("gabs")
    ax1.set_title(f"gabs spectrum: {label}")
    ax1.grid(True, alpha=0.25)

plt.suptitle("Dissymmetry-factor summary from gabs output table", y=0.98, fontsize=14)
plt.tight_layout(rect=[0, 0, 1, 0.96])

log("Step_4: Add axis labels, units, and a legend or annotations so the plot is publication-ready.")
log("Figure includes wavelength in nm, gabs on the y-axis, gridlines, and either a legend or ranked summary panel.")

plt.savefig(figure_path, bbox_inches="tight")
plt.close()

log("Step_5: Verify that the visualization faithfully represents the CSV contents and is suitable for direct comparison with the paper’s corresponding result panel.")
log(f"Figure saved to: {figure_path}")
log("Verification notes:")
log("- The CSV contains a metadata-like first column with sample descriptors and many numeric wavelength columns.")
log("- The numeric table is consistent with a gabs summary table across wavelengths/conditions.")
log("- The plot uses only numeric values parsed directly from the CSV; missing values are ignored rather than imputed.")
log("- No peak fitting or model-based inference was performed.")
log("Limitations:")
log("- The file does not explicitly label a separate 'gabs' column; gabs is inferred from the file name and the numeric response table.")
log("- If the intended paper panel used a different aggregation, that cannot be reconstructed without additional metadata.")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure: {figure_path}")
print(f"Saved analysis: {analysis_path}")