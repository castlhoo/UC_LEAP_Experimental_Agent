import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Paths from the task
dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/007_Inverse_design_of_chiral_functional/type1_data/cgan_test_result_PROP_440.csv"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/007_Inverse_design_of_chiral_functional/results/PAPER_07_TASK_04_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/007_Inverse_design_of_chiral_functional/results/PAPER_07_TASK_04_Analysis.txt"

# Ensure output directory exists
os.makedirs(os.path.dirname(figure_path), exist_ok=True)

analysis_lines = []
analysis_lines.append("Task PAPER_07_TASK_04 Analysis")
analysis_lines.append("=" * 40)
analysis_lines.append(f"Dataset file: {dataset_file}")
analysis_lines.append("")

# Step 0: Load the CSV and inspect the column names and data types.
analysis_lines.append("Step 0: Load the CSV and inspect the column names and data types.")
try:
    df = pd.read_csv(dataset_file)
    analysis_lines.append(f"Loaded dataset successfully with shape {df.shape[0]} rows x {df.shape[1]} columns.")
    analysis_lines.append("Column names and dtypes:")
    for col in df.columns:
        analysis_lines.append(f"  - {col}: {df[col].dtype}")
except Exception as e:
    analysis_lines.append(f"Failed to load dataset: {e}")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise

analysis_lines.append("")

# Step 1: Identify the property-related target columns and the generated/predicted outputs for the 440 nm case.
analysis_lines.append("Step 1: Identify the property-related target columns and the generated/predicted outputs for the 440 nm case.")
expected_cols = ["G_GAN", "G_Predict", "dG"]
missing_expected = [c for c in expected_cols if c not in df.columns]
if missing_expected:
    analysis_lines.append(f"Missing expected columns: {missing_expected}")
else:
    analysis_lines.append("Found expected output columns: G_GAN, G_Predict, dG.")

# Identify any target/property columns besides outputs
property_like_cols = [c for c in df.columns if c not in expected_cols]
analysis_lines.append(f"Other columns present (interpreted as input/design variables or target descriptors): {property_like_cols}")
analysis_lines.append("The filename indicates the 440 nm target condition; no separate wavelength column is present, so the entire file is treated as the 440 nm case.")
analysis_lines.append("")

# Step 2: Clean the data and isolate the rows relevant to the 440 nm target condition.
analysis_lines.append("Step 2: Clean the data and isolate the rows relevant to the 440 nm target condition.")
df_clean = df.copy()

# Coerce all columns to numeric where possible
for col in df_clean.columns:
    df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce")

before_rows = len(df_clean)
df_clean = df_clean.dropna(subset=["G_GAN", "G_Predict"])
after_rows = len(df_clean)
analysis_lines.append(f"Dropped rows with missing G_GAN or G_Predict values: {before_rows - after_rows} rows removed, {after_rows} rows retained.")

if "dG" in df_clean.columns:
    # Keep dG as provided; if missing, compute only for reporting if possible
    if df_clean["dG"].isna().any():
        analysis_lines.append("Some dG values are missing; where possible, dG can be computed as G_Predict - G_GAN for validation only.")
        df_clean["dG_calc"] = df_clean["G_Predict"] - df_clean["G_GAN"]
    else:
        df_clean["dG_calc"] = df_clean["G_Predict"] - df_clean["G_GAN"]
        diff = np.nanmax(np.abs(df_clean["dG"] - df_clean["dG_calc"]))
        analysis_lines.append(f"Validated dG against G_Predict - G_GAN. Maximum absolute difference: {diff:.6g}")
else:
    df_clean["dG_calc"] = df_clean["G_Predict"] - df_clean["G_GAN"]
    analysis_lines.append("dG column not found; computed dG_calc = G_Predict - G_GAN for internal validation.")

analysis_lines.append("")

# Step 3: Produce a comparison plot that shows the relationship between generated and predicted property values.
analysis_lines.append("Step 3: Produce a comparison plot that shows the relationship between generated and predicted property values.")
if len(df_clean) == 0:
    analysis_lines.append("No valid rows remain after cleaning; cannot generate a meaningful plot.")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise ValueError("No valid data to plot.")

# Determine plotting ranges
x = df_clean["G_GAN"].to_numpy()
y = df_clean["G_Predict"].to_numpy()

xmin = np.nanmin(x)
xmax = np.nanmax(x)
ymin = np.nanmin(y)
ymax = np.nanmax(y)
pad = 0.05 * max(xmax - xmin, ymax - ymin) if max(xmax - xmin, ymax - ymin) > 0 else 0.1
lo = min(xmin, ymin) - pad
hi = max(xmax, ymax) + pad

# Quantitative summary for analysis
corr = np.corrcoef(x, y)[0, 1] if len(df_clean) > 1 else np.nan
mae = np.mean(np.abs(y - x))
rmse = np.sqrt(np.mean((y - x) ** 2))
bias = np.mean(y - x)

analysis_lines.append(f"Number of plotted candidate solutions: {len(df_clean)}")
analysis_lines.append(f"G_GAN range: {xmin:.6g} to {xmax:.6g}")
analysis_lines.append(f"G_Predict range: {ymin:.6g} to {ymax:.6g}")
analysis_lines.append(f"Pearson correlation between G_GAN and G_Predict: {corr:.6g}")
analysis_lines.append(f"Mean absolute error |G_Predict - G_GAN|: {mae:.6g}")
analysis_lines.append(f"Root mean square error: {rmse:.6g}")
analysis_lines.append(f"Mean signed difference (G_Predict - G_GAN): {bias:.6g}")
analysis_lines.append("")

# Step 4: Add labels, units, and a title indicating the 440 nm property-target condition.
analysis_lines.append("Step 4: Add labels, units, and a title indicating the 440 nm property-target condition.")
analysis_lines.append("The file does not provide explicit physical units for G_GAN/G_Predict, so the plot labels use the variable names directly without inventing units.")
analysis_lines.append("")

# Step 5: Check that the figure is directly usable as a replot of the paper’s property-target inverse-design panel.
analysis_lines.append("Step 5: Check that the figure is directly usable as a replot of the paper’s property-target inverse-design panel.")
analysis_lines.append("A parity plot with a 1:1 reference line is appropriate because it directly compares generated and predicted property values for the 440 nm target case.")
analysis_lines.append("The plot uses all valid rows from the CSV and does not assume any unprovided target column beyond the filename-based 440 nm condition.")
analysis_lines.append("")

# Create publication-style parity plot
plt.figure(figsize=(6.5, 6.0), dpi=200)
ax = plt.gca()

# Scatter plot
sc = ax.scatter(
    x, y,
    c=df_clean["dG_calc"] if "dG_calc" in df_clean.columns else (y - x),
    cmap="coolwarm",
    s=28,
    alpha=0.85,
    edgecolors="none"
)

# 1:1 line
ax.plot([lo, hi], [lo, hi], linestyle="--", color="black", linewidth=1.2, label="1:1 line")

# Optional fit line for visual guidance if enough points
if len(df_clean) >= 2 and np.isfinite(corr):
    coeffs = np.polyfit(x, y, 1)
    xx = np.linspace(lo, hi, 200)
    yy = coeffs[0] * xx + coeffs[1]
    ax.plot(xx, yy, color="#1f77b4", linewidth=1.5, label=f"Linear fit: y={coeffs[0]:.2f}x+{coeffs[1]:.2f}")

ax.set_xlim(lo, hi)
ax.set_ylim(lo, hi)
ax.set_aspect("equal", adjustable="box")

ax.set_xlabel("Generated property, G_GAN")
ax.set_ylabel("Predicted property, G_Predict")
ax.set_title("Inverse-design result at 440 nm: generated vs predicted property")

# Add annotation with summary statistics
stats_text = (
    f"N = {len(df_clean)}\n"
    f"r = {corr:.3f}\n"
    f"MAE = {mae:.3f}\n"
    f"RMSE = {rmse:.3f}"
)
ax.text(
    0.04, 0.96, stats_text,
    transform=ax.transAxes,
    va="top", ha="left",
    fontsize=9,
    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="0.7", alpha=0.9)
)

cbar = plt.colorbar(sc, ax=ax, pad=0.02)
cbar.set_label("dG = G_Predict - G_GAN")

ax.grid(True, linestyle=":", linewidth=0.7, alpha=0.7)
ax.legend(frameon=False, loc="lower right")

plt.tight_layout()
plt.savefig(figure_path, dpi=300, bbox_inches="tight")
plt.close()

analysis_lines.append(f"Figure saved to: {figure_path}")
analysis_lines.append("Figure generation completed successfully.")

# Save analysis text
with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure: {figure_path}")
print(f"Saved analysis: {analysis_path}")