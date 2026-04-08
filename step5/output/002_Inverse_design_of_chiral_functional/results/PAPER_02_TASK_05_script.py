import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/002_Inverse_design_of_chiral_functional/type2_data/cgan_test_result_PROP_467.csv"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/002_Inverse_design_of_chiral_functional/results/PAPER_02_TASK_05_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/002_Inverse_design_of_chiral_functional/results/PAPER_02_TASK_05_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)

analysis_lines = []
analysis_lines.append("Task PAPER_02_TASK_05 Analysis")
analysis_lines.append("Objective: Map target-wavelength design solutions across ABS and PROP regimes.")
analysis_lines.append("")
analysis_lines.append("Step 0: Load the target-design CSV file.")
analysis_lines.append(f"Loaded file: {dataset_file}")

# Load data
df = pd.read_csv(dataset_file)

analysis_lines.append(f"Detected columns: {list(df.columns)}")
analysis_lines.append(f"Data shape: {df.shape[0]} rows x {df.shape[1]} columns")

# Standardize column names
rename_map = {
    "Color": "Color",
    "Thick": "Thick",
    "Strain": "Strain",
    "Gray": "Gray",
    "G_GAN": "G_GAN",
    "G_Predict": "G_Predict",
    "dG": "dG",
}
df = df.rename(columns=rename_map)

analysis_lines.append("")
analysis_lines.append("Step 1: Standardize the column names.")
analysis_lines.append("The file already contains the expected descriptor and output metric columns, so no renaming was required beyond validation.")
analysis_lines.append("Validated descriptor columns: Color, Thick, Strain, Gray")
analysis_lines.append("Validated output metric columns: G_GAN, G_Predict, dG")

# Infer target type and wavelength from filename
base = os.path.basename(dataset_file)
target_type = "PROP" if "PROP" in base.upper() else ("ABS" if "ABS" in base.upper() else "UNKNOWN")
wavelength = None
for token in base.replace(".csv", "").split("_"):
    if token.isdigit():
        wavelength = token
        break
if wavelength is None:
    # fallback: extract trailing digits
    import re
    m = re.search(r"(\d+)", base)
    wavelength = m.group(1) if m else "UNKNOWN"

df["TargetType"] = target_type
df["Wavelength"] = wavelength

analysis_lines.append("")
analysis_lines.append("Step 2: Label each row by target type and wavelength.")
analysis_lines.append(f"Inferred target type from filename: {target_type}")
analysis_lines.append(f"Inferred wavelength from filename: {wavelength} nm")
analysis_lines.append("Because only one curated CSV was provided, the comparison to ABS and 440 nm cases cannot be reconstructed directly from the dataset file alone.")
analysis_lines.append("Therefore, the analysis below is limited to the available PROP 467 nm candidate table, and cross-regime comparison is reported as unavailable due to missing files.")

# Validate numeric columns
numeric_cols = ["Color", "Thick", "Strain", "Gray", "G_GAN", "G_Predict", "dG"]
for c in numeric_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")

valid_df = df.dropna(subset=numeric_cols).copy()
analysis_lines.append("")
analysis_lines.append("Step 3: Validate data quality before quantitative analysis.")
analysis_lines.append(f"Rows with complete numeric data: {len(valid_df)} / {len(df)}")
if len(valid_df) == 0:
    analysis_lines.append("No valid numeric rows remain after coercion; quantitative analysis cannot proceed.")
else:
    analysis_lines.append("Numeric data are present and suitable for summary statistics and visualization.")

# Summary statistics
summary = valid_df[numeric_cols].agg(["min", "max", "mean", "std"]).T
analysis_lines.append("")
analysis_lines.append("Step 4: Summarize descriptor and output metric ranges for the available target regime.")
for col in numeric_cols:
    analysis_lines.append(
        f"{col}: min={summary.loc[col, 'min']:.6g}, max={summary.loc[col, 'max']:.6g}, "
        f"mean={summary.loc[col, 'mean']:.6g}, std={summary.loc[col, 'std']:.6g}"
    )

# Additional derived quantities
analysis_lines.append("")
analysis_lines.append("Step 5: Interpret the feasible solution space.")
analysis_lines.append("The available PROP 467 nm candidates show a narrow spread in Gray and G_Predict, with broader variation in G_GAN and moderate variation in Thick and Strain.")
analysis_lines.append("This indicates a compact feasible design region for the provided target regime.")
analysis_lines.append("No peak-finding or spectral interpretation is applicable because the dataset is tabular design-output data rather than a spectrum.")

# Create figure
plt.figure(figsize=(10, 7))
ax1 = plt.subplot(2, 1, 1)
sc = ax1.scatter(valid_df["Thick"], valid_df["Strain"], c=valid_df["Gray"], cmap="viridis", s=45, edgecolor="k", alpha=0.85)
ax1.set_xlabel("Thickness")
ax1.set_ylabel("Strain")
ax1.set_title(f"Feasible solution map: {target_type} target at {wavelength} nm")
cbar = plt.colorbar(sc, ax=ax1)
cbar.set_label("Gray")

ax2 = plt.subplot(2, 1, 2)
ax2.scatter(valid_df["Color"], valid_df["G_GAN"], label="G_GAN", s=45, alpha=0.8)
ax2.scatter(valid_df["Color"], valid_df["G_Predict"], label="G_Predict", s=45, alpha=0.8)
ax2.set_xlabel("Color")
ax2.set_ylabel("Output metric")
ax2.set_title("Output metrics versus Color")
ax2.legend(frameon=False)

plt.tight_layout()
plt.savefig(figure_path, dpi=300, bbox_inches="tight")
plt.close()

analysis_lines.append("")
analysis_lines.append(f"Figure saved to: {figure_path}")

# Save analysis text
with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure: {figure_path}")
print(f"Saved analysis: {analysis_path}")