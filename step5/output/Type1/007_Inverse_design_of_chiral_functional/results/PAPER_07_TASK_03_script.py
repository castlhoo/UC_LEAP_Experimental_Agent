import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

dataset_path = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/007_Inverse_design_of_chiral_functional/type1_data/cgan_test_result_ABS_440.csv"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/007_Inverse_design_of_chiral_functional/results/PAPER_07_TASK_03_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/007_Inverse_design_of_chiral_functional/results/PAPER_07_TASK_03_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)

analysis_lines = []
analysis_lines.append("Task PAPER_07_TASK_03 Analysis")
analysis_lines.append("")
analysis_lines.append("Step_0: Load the CSV and inspect the schema to identify output, prediction, and error columns.")
try:
    df = pd.read_csv(dataset_path)
    analysis_lines.append(f"Loaded dataset successfully from: {dataset_path}")
    analysis_lines.append(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns")
    analysis_lines.append(f"Columns: {list(df.columns)}")
except Exception as e:
    analysis_lines.append(f"Failed to load dataset: {e}")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise

analysis_lines.append("")
analysis_lines.append("Observed schema indicates a tabular candidate-solution dataset rather than a wavelength-resolved spectrum.")
analysis_lines.append("The filename includes ABS_440, which supports interpretation as a target absorption condition at 440 nm.")
analysis_lines.append("Relevant columns identified directly from the file: G_GAN, G_Predict, and dG.")
analysis_lines.append("Additional columns present: Color, Thick, Strain, Gray, which appear to be design/input descriptors rather than output metrics.")

analysis_lines.append("")
analysis_lines.append("Step_1: Determine whether the table is organized by candidate design, wavelength, or property target, and isolate the 440 nm target entries.")
analysis_lines.append("The file is already specific to ABS_440, so all rows are treated as candidate designs for the 440 nm target.")
analysis_lines.append("No explicit wavelength column is present in the table; therefore, no further wavelength filtering is possible or needed.")
analysis_lines.append("The dataset appears organized by candidate design rows, each containing design descriptors and corresponding generated/predicted values.")

analysis_lines.append("")
analysis_lines.append("Step_2: Clean and standardize the numeric columns, ensuring the generated and predicted values are directly comparable.")
numeric_cols = ["Color", "Thick", "Strain", "Gray", "G_GAN", "G_Predict", "dG"]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    else:
        analysis_lines.append(f"Warning: expected column {col} not found.")
df_clean = df.dropna(subset=[c for c in ["G_GAN", "G_Predict"] if c in df.columns]).copy()
analysis_lines.append(f"Rows retained after numeric coercion and required-column filtering: {len(df_clean)}")
if len(df_clean) == 0:
    analysis_lines.append("No valid rows remain after cleaning; cannot produce a defensible comparison plot.")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise ValueError("No valid data rows for plotting.")

analysis_lines.append("")
analysis_lines.append("Step_3: Create the appropriate replot based on table structure.")
analysis_lines.append("Because the table contains paired generated and predicted values for each candidate design, a parity-style comparison is the most appropriate visualization.")
analysis_lines.append("A parity plot directly shows agreement between G_GAN and G_Predict across candidate rows.")
analysis_lines.append("To make the 440 nm target condition explicit, the figure title and annotations will reference ABS target 440 nm.")
analysis_lines.append("If dG is present, it will be included as a text annotation and optionally used to color points if available.")

analysis_lines.append("")
analysis_lines.append("Step_4: Annotate the figure with the 440 nm target condition and include any reported error metric such as dG if present.")
analysis_lines.append("dG is present in the dataset and is interpreted strictly as a reported difference metric between generated and predicted values, as provided by the file.")
analysis_lines.append("No additional physical calibration is assumed.")

analysis_lines.append("")
analysis_lines.append("Step_5: Export the plot in a publication-ready format matching the style of inverse-design result panels.")
analysis_lines.append("The plot will be saved as a high-resolution PNG with labeled axes, equal aspect parity reference, and a legend.")

# Prepare data
x = df_clean["G_Predict"].to_numpy()
y = df_clean["G_GAN"].to_numpy()
dg = df_clean["dG"].to_numpy() if "dG" in df_clean.columns else None

# Determine plotting range
all_vals = np.concatenate([x, y])
vmin = np.nanmin(all_vals)
vmax = np.nanmax(all_vals)
pad = 0.05 * (vmax - vmin) if vmax > vmin else 1.0
lo = vmin - pad
hi = vmax + pad

# Plot
plt.figure(figsize=(6.5, 6.0), dpi=300)
ax = plt.gca()

if dg is not None and np.isfinite(dg).any():
    sc = ax.scatter(x, y, c=dg, cmap="coolwarm", s=42, edgecolor="black", linewidth=0.4, alpha=0.9)
    cbar = plt.colorbar(sc, ax=ax, pad=0.02)
    cbar.set_label("dG", rotation=90)
else:
    ax.scatter(x, y, s=42, color="#1f77b4", edgecolor="black", linewidth=0.4, alpha=0.9)

ax.plot([lo, hi], [lo, hi], linestyle="--", color="gray", linewidth=1.5, label="Parity line (y = x)")
ax.set_xlim(lo, hi)
ax.set_ylim(lo, hi)
ax.set_aspect("equal", adjustable="box")
ax.set_xlabel("G_Predict")
ax.set_ylabel("G_GAN")
ax.set_title("Inverse-design result for ABS target at 440 nm")
ax.legend(frameon=False, loc="upper left")

# Annotate summary statistics
mae = float(np.mean(np.abs(y - x)))
rmse = float(np.sqrt(np.mean((y - x) ** 2)))
bias = float(np.mean(y - x))
n = len(df_clean)

summary_text = (
    f"N = {n}\n"
    f"MAE = {mae:.4f}\n"
    f"RMSE = {rmse:.4f}\n"
    f"Mean Δ = {bias:.4f}"
)
ax.text(
    0.04, 0.96, summary_text,
    transform=ax.transAxes,
    va="top", ha="left",
    fontsize=9,
    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="gray", alpha=0.9)
)

# Add target note
ax.text(
    0.04, 0.04,
    "Target condition: ABS @ 440 nm",
    transform=ax.transAxes,
    va="bottom", ha="left",
    fontsize=9,
    bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="gray", alpha=0.85)
)

plt.tight_layout()
plt.savefig(figure_path, dpi=300, bbox_inches="tight")
plt.close()

analysis_lines.append("")
analysis_lines.append("Quantitative checks performed on the cleaned data:")
analysis_lines.append(f"Number of candidate rows used: {n}")
analysis_lines.append(f"Mean absolute error between G_GAN and G_Predict: {mae:.6f}")
analysis_lines.append(f"Root-mean-square error between G_GAN and G_Predict: {rmse:.6f}")
analysis_lines.append(f"Mean signed difference (G_GAN - G_Predict): {bias:.6f}")
analysis_lines.append("These quantities are computed directly from the available columns and do not require unsupported assumptions.")

analysis_lines.append("")
analysis_lines.append("Validation and exclusions:")
analysis_lines.append("No peak identification was required because this is not a spectral dataset.")
analysis_lines.append("No rows were excluded beyond standard numeric coercion and removal of rows missing G_GAN or G_Predict.")
analysis_lines.append("No missing wavelength column was inferred; the 440 nm target is taken from the filename and task context.")
analysis_lines.append("The resulting figure is a parity-style comparison suitable for a model-evaluation panel.")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))