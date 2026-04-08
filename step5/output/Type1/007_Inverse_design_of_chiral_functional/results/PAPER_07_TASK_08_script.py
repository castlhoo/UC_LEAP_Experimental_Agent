import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Paths
dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/007_Inverse_design_of_chiral_functional/type1_data/cgan_test_result_PROP_467.csv"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/007_Inverse_design_of_chiral_functional/results/PAPER_07_TASK_08_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/007_Inverse_design_of_chiral_functional/results/PAPER_07_TASK_08_Analysis.txt"

# Ensure output directory exists
os.makedirs(os.path.dirname(figure_path), exist_ok=True)

analysis_lines = []
analysis_lines.append("Task PAPER_07_TASK_08 Analysis")
analysis_lines.append("Replot the property-target inverse-design results at 467 nm")
analysis_lines.append("")

# Step 0: Load and inspect schema
analysis_lines.append("Step 0: Load the CSV and inspect the schema.")
try:
    df = pd.read_csv(dataset_file)
    analysis_lines.append(f"Loaded file successfully: {os.path.basename(dataset_file)}")
    analysis_lines.append(f"Data shape: {df.shape[0]} rows x {df.shape[1]} columns")
    analysis_lines.append(f"Columns found: {list(df.columns)}")
except Exception as e:
    analysis_lines.append(f"Failed to load CSV: {e}")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise

# Step 1: Determine how 467 nm target is encoded and isolate relevant rows
analysis_lines.append("")
analysis_lines.append("Step 1: Determine how the 467 nm target is encoded and isolate relevant rows.")
analysis_lines.append("The filename 'cgan_test_result_PROP_467.csv' indicates the 467 nm target condition is encoded in the file name rather than as a separate column.")
analysis_lines.append("No explicit target-wavelength column is present in the previewed schema, so all rows in this file are treated as candidate solutions for the 467 nm case.")

# Step 2: Clean data and standardize numeric fields
analysis_lines.append("")
analysis_lines.append("Step 2: Clean the data and standardize numeric fields for plotting.")
numeric_cols = ["Color", "Thick", "Strain", "Gray", "G_GAN", "G_Predict", "dG"]
missing_cols = [c for c in numeric_cols if c not in df.columns]
if missing_cols:
    analysis_lines.append(f"Missing expected columns: {missing_cols}")
    analysis_lines.append("Cannot complete the intended comparison plot without the required columns.")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise ValueError(f"Missing expected columns: {missing_cols}")

for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

before_drop = len(df)
df_clean = df.dropna(subset=["G_GAN", "G_Predict", "dG"]).copy()
after_drop = len(df_clean)
analysis_lines.append(f"Rows before numeric cleaning: {before_drop}")
analysis_lines.append(f"Rows after dropping rows with invalid G_GAN/G_Predict/dG values: {after_drop}")
analysis_lines.append("Numeric conversion was applied to all relevant columns to ensure consistent plotting.")

if df_clean.empty:
    analysis_lines.append("No valid rows remain after cleaning; cannot generate a defensible comparison plot.")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise ValueError("No valid rows remain after cleaning.")

# Step 3: Create comparison plot
analysis_lines.append("")
analysis_lines.append("Step 3: Create a comparison plot.")
analysis_lines.append("A generated-vs-predicted scatter plot is appropriate because the file contains paired model outputs (G_GAN and G_Predict) for each candidate solution.")
analysis_lines.append("To make deviations easy to interpret, the plot includes a 1:1 reference line and point labels by candidate index.")

# Sort by predicted value for a cleaner ranked presentation
df_plot = df_clean.sort_values(by="G_Predict", ascending=False).reset_index(drop=True)
df_plot["Candidate"] = np.arange(1, len(df_plot) + 1)

# Quantitative summary for annotation
mae = np.mean(np.abs(df_plot["G_GAN"] - df_plot["G_Predict"]))
rmse = np.sqrt(np.mean((df_plot["G_GAN"] - df_plot["G_Predict"]) ** 2))
mean_abs_dG = np.mean(np.abs(df_plot["dG"]))
analysis_lines.append(f"Mean absolute deviation |G_GAN - G_Predict|: {mae:.6f}")
analysis_lines.append(f"RMSE between G_GAN and G_Predict: {rmse:.6f}")
analysis_lines.append(f"Mean absolute dG: {mean_abs_dG:.6f}")
analysis_lines.append("These summary values are directly computed from the cleaned data and are used only as descriptive support for the figure.")

# Step 4: Add labels, units, and title
analysis_lines.append("")
analysis_lines.append("Step 4: Add labels, units, and a title indicating the 467 nm property-target case.")
analysis_lines.append("The plot title explicitly states the 467 nm target condition.")
analysis_lines.append("Axis labels use the variable names from the dataset because no physical unit metadata is provided in the file.")

# Step 5: Publication-ready styling
analysis_lines.append("")
analysis_lines.append("Step 5: Ensure the output is publication-ready and aligned with the paper’s inverse-design result style.")
analysis_lines.append("The figure uses a clean white background, readable fonts, a 1:1 reference line, and a colorbar for dG to communicate deviation magnitude.")
analysis_lines.append("Because the file contains multiple candidate solutions, each point is shown as a ranked candidate to make target matching and deviations easy to interpret.")

plt.style.use("default")
fig, ax = plt.subplots(figsize=(7.2, 6.2), dpi=300)

# Scatter plot with dG as color
sc = ax.scatter(
    df_plot["G_Predict"],
    df_plot["G_GAN"],
    c=df_plot["dG"],
    cmap="coolwarm",
    s=70,
    edgecolor="black",
    linewidth=0.6,
    alpha=0.95
)

# 1:1 line
all_vals = np.concatenate([df_plot["G_Predict"].values, df_plot["G_GAN"].values])
vmin = np.nanmin(all_vals)
vmax = np.nanmax(all_vals)
pad = 0.05 * (vmax - vmin) if vmax > vmin else 0.1
line_min = vmin - pad
line_max = vmax + pad
ax.plot([line_min, line_max], [line_min, line_max], linestyle="--", color="gray", linewidth=1.2, label="1:1 reference")

# Annotate candidate indices
for _, row in df_plot.iterrows():
    ax.annotate(
        str(int(row["Candidate"])),
        (row["G_Predict"], row["G_GAN"]),
        textcoords="offset points",
        xytext=(5, 5),
        fontsize=8,
        color="black"
    )

ax.set_xlim(line_min, line_max)
ax.set_ylim(line_min, line_max)
ax.set_xlabel("G_Predict", fontsize=11)
ax.set_ylabel("G_GAN", fontsize=11)
ax.set_title("cGAN inverse-design comparison at 467 nm", fontsize=13, pad=10)

cbar = plt.colorbar(sc, ax=ax, pad=0.02)
cbar.set_label("dG", fontsize=10)

# Add summary text box
summary_text = (
    f"N = {len(df_plot)}\n"
    f"MAE = {mae:.4f}\n"
    f"RMSE = {rmse:.4f}\n"
    f"mean |dG| = {mean_abs_dG:.4f}"
)
ax.text(
    0.03, 0.97, summary_text,
    transform=ax.transAxes,
    va="top",
    ha="left",
    fontsize=9,
    bbox=dict(boxstyle="round,pad=0.35", facecolor="white", edgecolor="black", alpha=0.9)
)

ax.legend(loc="lower right", frameon=True)
ax.grid(True, linestyle=":", linewidth=0.7, alpha=0.7)
fig.tight_layout()

# Save figure
fig.savefig(figure_path, bbox_inches="tight")
plt.close(fig)

analysis_lines.append("")
analysis_lines.append(f"Figure saved to: {figure_path}")
analysis_lines.append("No unsupported assumptions were made beyond using the filename-encoded 467 nm target condition and the explicitly available columns.")

# Save analysis
with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))