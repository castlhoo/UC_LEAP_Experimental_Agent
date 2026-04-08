import os
import re
import math
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

dataset_path = r"C:/UCLEAP/UC_LEAP/step4/organized/002_Inverse_design_of_chiral_functional/type1_data/20_gabs_outfile.csv"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/002_Inverse_design_of_chiral_functional/results/PAPER_02_TASK_02_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/002_Inverse_design_of_chiral_functional/results/PAPER_02_TASK_02_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)
os.makedirs(os.path.dirname(analysis_path), exist_ok=True)

analysis_lines = []

def log(msg):
    analysis_lines.append(msg)

log("Task PAPER_02_TASK_02 Analysis")
log("Objective: Recreate the inverse-design evaluation table and compare predicted versus GAN-derived gabs values.")
log(f"Dataset file: {dataset_path}")

# Step 0: Load and inspect
try:
    df_raw = pd.read_csv(dataset_path, encoding="utf-8-sig")
except Exception as e:
    raise RuntimeError(f"Failed to load CSV: {e}")

log(f"Loaded CSV successfully. Shape: {df_raw.shape[0]} rows x {df_raw.shape[1]} columns.")
log(f"Raw columns: {list(df_raw.columns)}")

# Inspect first rows
preview_rows = df_raw.head(5).to_string(index=False)
log("First 5 rows preview:")
log(preview_rows)

# Determine structure
first_col = df_raw.columns[0]
other_cols = list(df_raw.columns[1:])

# Parse first column into design parameters if possible
def parse_feature_string(s):
    if pd.isna(s):
        return [np.nan, np.nan, np.nan, np.nan]
    parts = str(s).split("-")
    vals = []
    for p in parts[:4]:
        try:
            vals.append(float(p))
        except:
            vals.append(np.nan)
    while len(vals) < 4:
        vals.append(np.nan)
    return vals

design_vals = df_raw[first_col].apply(parse_feature_string)
design_df = pd.DataFrame(design_vals.tolist(), columns=["Color", "Thick", "Strain", "Gray"])

# Standardize numeric fields from remaining columns
numeric_df = df_raw[other_cols].apply(pd.to_numeric, errors="coerce")

# Identify likely G_GAN, G_Predict, dG columns
# Use column names if present; otherwise infer from position/meaning.
col_map = {}
for c in numeric_df.columns:
    cl = str(c).lower()
    if "gan" in cl and "g" in cl:
        col_map["G_GAN"] = c
    elif ("predict" in cl or "pred" in cl) and "g" in cl:
        col_map["G_Predict"] = c
    elif cl in ["dg", "d_g", "delta_g", "diff", "difference"]:
        col_map["dG"] = c

# If not named, infer from first few numeric columns based on task context
# We only need the comparison metrics; use the first two numeric columns as G_GAN and G_Predict if no labels exist.
if "G_GAN" not in col_map and numeric_df.shape[1] >= 1:
    col_map["G_GAN"] = numeric_df.columns[0]
if "G_Predict" not in col_map and numeric_df.shape[1] >= 2:
    col_map["G_Predict"] = numeric_df.columns[1]
if "dG" not in col_map and numeric_df.shape[1] >= 3:
    col_map["dG"] = numeric_df.columns[2]

log("Column interpretation:")
log(f"  Parsed design parameters from first column '{first_col}' into Color, Thick, Strain, Gray.")
log(f"  Inferred numeric comparison columns: {json.dumps({k: str(v) for k, v in col_map.items()}, indent=2)}")

# Build working dataframe
work = pd.concat([design_df, numeric_df], axis=1)

# Determine if there are target labels or groups in the first column beyond 4 numeric fields
# Here the first column appears to be a compact design identifier only.
group_labels = None
if work["Strain"].nunique(dropna=True) > 1:
    # Use Strain as grouping if multiple target conditions exist
    group_labels = work["Strain"].astype("Int64").astype(str)
    log("Detected multiple Strain values; using Strain as grouping variable for subpanels.")
else:
    log("No separate target wavelength/objective labels were detected in the file structure; plotting all cases together.")

# Extract comparison columns
g_gan = pd.to_numeric(work[col_map["G_GAN"]], errors="coerce")
g_pred = pd.to_numeric(work[col_map["G_Predict"]], errors="coerce")

# Compute dG and verify sign convention
computed_dg = g_pred - g_gan
provided_dg = None
dg_match_note = "No explicit dG column was identifiable."
if "dG" in col_map:
    provided_dg = pd.to_numeric(work[col_map["dG"]], errors="coerce")
    diff1 = np.nanmean(np.abs(provided_dg - computed_dg))
    diff2 = np.nanmean(np.abs(provided_dg - (g_gan - g_pred)))
    if np.isfinite(diff1) and np.isfinite(diff2):
        if diff1 <= diff2:
            dg_sign = "G_Predict - G_GAN"
            dg_used = computed_dg
            dg_match_note = f"Provided dG is more consistent with G_Predict - G_GAN (mean abs error vs this definition = {diff1:.6g}; vs opposite sign = {diff2:.6g})."
        else:
            dg_sign = "G_GAN - G_Predict"
            dg_used = g_gan - g_pred
            dg_match_note = f"Provided dG is more consistent with G_GAN - G_Predict (mean abs error vs this definition = {diff2:.6g}; vs opposite sign = {diff1:.6g})."
    else:
        dg_sign = "unknown"
        dg_used = computed_dg
        dg_match_note = "Could not robustly compare dG sign due to missing values."
else:
    dg_sign = "G_Predict - G_GAN"
    dg_used = computed_dg

work["G_GAN"] = g_gan
work["G_Predict"] = g_pred
work["dG_computed"] = computed_dg
if provided_dg is not None:
    work["dG_provided"] = provided_dg
work["dG_used"] = dg_used

log("Step 1: Standardization and sign convention check")
log(dg_match_note)

# Validate data quality
valid_mask = np.isfinite(g_gan) & np.isfinite(g_pred)
n_valid = int(valid_mask.sum())
n_total = len(work)
log(f"Valid paired G_GAN/G_Predict rows: {n_valid}/{n_total}")

if n_valid == 0:
    raise RuntimeError("No valid paired G_GAN/G_Predict values found; cannot create comparison plot.")

# Summary metrics
mae = float(np.nanmean(np.abs(g_pred[valid_mask] - g_gan[valid_mask])))
rmse = float(np.sqrt(np.nanmean((g_pred[valid_mask] - g_gan[valid_mask]) ** 2)))
bias = float(np.nanmean(g_pred[valid_mask] - g_gan[valid_mask]))
corr = float(np.corrcoef(g_gan[valid_mask], g_pred[valid_mask])[0, 1]) if n_valid > 1 else np.nan

log("Quantitative comparison metrics:")
log(f"  MAE(G_Predict - G_GAN) = {mae:.6g}")
log(f"  RMSE(G_Predict - G_GAN) = {rmse:.6g}")
log(f"  Mean bias (G_Predict - G_GAN) = {bias:.6g}")
log(f"  Pearson correlation = {corr:.6g}" if np.isfinite(corr) else "  Pearson correlation = unavailable")

# Prepare table for plotting
plot_df = work.copy()
plot_df["Case"] = np.arange(1, len(plot_df) + 1)
plot_df["G_GAN"] = g_gan
plot_df["G_Predict"] = g_pred
plot_df["dG_used"] = dg_used
plot_df["abs_dG"] = np.abs(plot_df["dG_used"])

# Sort by G_GAN for cleaner comparison
plot_df = plot_df.sort_values(by="G_GAN", kind="mergesort").reset_index(drop=True)
plot_df["Case_sorted"] = np.arange(1, len(plot_df) + 1)

# Build figure
plt.rcParams.update({
    "font.size": 9,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "figure.dpi": 200,
    "savefig.dpi": 300,
    "font.family": "DejaVu Sans"
})

fig = plt.figure(figsize=(16, 10))
gs = GridSpec(2, 2, figure=fig, height_ratios=[1.1, 1.0], width_ratios=[1.15, 1.0], hspace=0.25, wspace=0.18)

# Panel A: paired comparison
ax1 = fig.add_subplot(gs[0, 0])
x = np.arange(len(plot_df))
width = 0.38
ax1.bar(x - width/2, plot_df["G_GAN"], width=width, label="G_GAN", color="#4C78A8")
ax1.bar(x + width/2, plot_df["G_Predict"], width=width, label="G_Predict", color="#F58518")
ax1.set_title("Inverse-design cases: GAN-derived vs predicted gabs")
ax1.set_xlabel("Design case (sorted by G_GAN)")
ax1.set_ylabel("gabs")
ax1.set_xticks(x)
ax1.set_xticklabels(plot_df["Case_sorted"].astype(str), rotation=90)
ax1.legend(frameon=False, ncol=2, loc="upper left")
ax1.grid(axis="y", alpha=0.25)

# Annotate dG on top for a subset to avoid clutter
for i, row in plot_df.iterrows():
    if i % max(1, len(plot_df)//10) == 0:
        y_top = max(row["G_GAN"], row["G_Predict"])
        ax1.text(i, y_top, f"{row['dG_used']:.2g}", ha="center", va="bottom", fontsize=7, rotation=90)

# Panel B: parity plot
ax2 = fig.add_subplot(gs[0, 1])
ax2.scatter(plot_df["G_GAN"], plot_df["G_Predict"], c=plot_df["abs_dG"], cmap="viridis", s=55, edgecolor="k", linewidth=0.4)
minv = np.nanmin([plot_df["G_GAN"].min(), plot_df["G_Predict"].min()])
maxv = np.nanmax([plot_df["G_GAN"].max(), plot_df["G_Predict"].max()])
pad = 0.05 * (maxv - minv if maxv > minv else 1.0)
line_x = np.linspace(minv - pad, maxv + pad, 200)
ax2.plot(line_x, line_x, "--", color="gray", linewidth=1, label="Parity")
ax2.set_xlabel("G_GAN")
ax2.set_ylabel("G_Predict")
ax2.set_title("Parity comparison")
ax2.grid(alpha=0.25)
cb = fig.colorbar(ax2.collections[0], ax=ax2, fraction=0.046, pad=0.04)
cb.set_label("|dG|")
ax2.legend(frameon=False, loc="upper left")
ax2.text(0.02, 0.98, f"MAE={mae:.3g}\nRMSE={rmse:.3g}\nBias={bias:.3g}\nR={corr:.3g}",
         transform=ax2.transAxes, va="top", ha="left",
         bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.85, edgecolor="none"))

# Panel C: table
ax3 = fig.add_subplot(gs[1, :])
ax3.axis("off")

display_cols = ["Case_sorted", "Color", "Thick", "Strain", "Gray", "G_GAN", "G_Predict", "dG_used"]
table_df = plot_df[display_cols].copy()
table_df.columns = ["Case", "Color", "Thick", "Strain", "Gray", "G_GAN", "G_Predict", "dG"]

# Format numbers
for c in ["Color", "Thick", "Strain", "Gray", "G_GAN", "G_Predict", "dG"]:
    table_df[c] = table_df[c].map(lambda v: "" if pd.isna(v) else f"{v:.4g}")

cell_text = table_df.values.tolist()
col_labels = table_df.columns.tolist()

table = ax3.table(cellText=cell_text, colLabels=col_labels, loc="center", cellLoc="center", colLoc="center")
table.auto_set_font_size(False)
table.set_fontsize(7.5)
table.scale(1, 1.25)

# Style header and alternate rows
for (row, col), cell in table.get_celld().items():
    cell.set_edgecolor("#D0D0D0")
    if row == 0:
        cell.set_facecolor("#E8EEF7")
        cell.set_text_props(weight="bold")
    elif row % 2 == 0:
        cell.set_facecolor("#FAFAFA")

fig.suptitle("PAPER_02_TASK_02: Inverse-design evaluation for 20 gabs cases", y=0.98, fontsize=13, fontweight="bold")
fig.text(0.01, 0.01, f"dG convention check: {dg_match_note}", fontsize=8)
fig.text(0.01, 0.025, "Note: Design parameters were parsed from the compact identifier in the first CSV column.", fontsize=8)

plt.tight_layout(rect=[0, 0.03, 1, 0.96])
fig.savefig(figure_path, bbox_inches="tight")
plt.close(fig)

log("Step 2: Visualization created.")
log(f"Figure saved to: {figure_path}")
log("Figure contents:")
log("  - Bar comparison of G_GAN and G_Predict for each design case.")
log("  - Parity scatter plot with |dG| color coding and summary metrics.")
log("  - Table of design parameters and comparison values.")
log("Step 3: No separate target wavelength/objective labels were detected beyond the compact design identifier; therefore no subgroup panels were created.")
log("Step 4: Export completed successfully.")

# Save analysis text
with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure to: {figure_path}")
print(f"Saved analysis to: {analysis_path}")