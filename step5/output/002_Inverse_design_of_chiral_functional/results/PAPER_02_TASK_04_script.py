import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Paths
dataset_abs = r"C:/UCLEAP/UC_LEAP/step4/organized/002_Inverse_design_of_chiral_functional/type2_data/cgan_test_result_ABS_440.csv"
dataset_prop = r"C:/UCLEAP/UC_LEAP/step4/organized/002_Inverse_design_of_chiral_functional/type2_data/cgan_test_result_PROP_440.csv"
fig_path = r"C:/UCLEAP/UC_LEAP/step5/output/002_Inverse_design_of_chiral_functional/results/PAPER_02_TASK_04_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/002_Inverse_design_of_chiral_functional/results/PAPER_02_TASK_04_Analysis.txt"

os.makedirs(os.path.dirname(fig_path), exist_ok=True)

def load_and_validate(path, label):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing required dataset file: {path}")
    df = pd.read_csv(path)
    required_cols = ["Color", "Thick", "Strain", "Gray", "G_GAN", "G_Predict", "dG"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"{label}: missing required columns: {missing}")
    return df

def summarize(df):
    # Use provided dG directly, but also compute from columns to validate consistency
    dG_calc = df["G_Predict"] - df["G_GAN"]
    dG_provided = df["dG"]
    mse = np.mean(df["dG"] ** 2)
    mae = np.mean(np.abs(df["dG"]))
    mse_signed = np.mean(df["dG"])
    frac_005 = np.mean(np.abs(df["dG"]) <= 0.05)
    frac_01 = np.mean(np.abs(df["dG"]) <= 0.10)
    corr = np.corrcoef(df["G_GAN"], df["G_Predict"])[0, 1] if len(df) > 1 else np.nan
    max_abs_diff = np.max(np.abs(df["dG"]))
    consistency_mae = np.mean(np.abs(dG_calc - dG_provided))
    return {
        "mean_signed_error": mse_signed,
        "mean_absolute_error": mae,
        "fraction_within_0.05": frac_005,
        "fraction_within_0.10": frac_01,
        "pearson_r": corr,
        "max_abs_diff": max_abs_diff,
        "dG_consistency_mae": consistency_mae,
    }

# Load datasets
abs_df = load_and_validate(dataset_abs, "ABS")
prop_df = None
prop_available = os.path.exists(dataset_prop)
if prop_available:
    prop_df = load_and_validate(dataset_prop, "PROP")

abs_stats = summarize(abs_df)
prop_stats = summarize(prop_df) if prop_df is not None else None

# Prepare analysis text
lines = []
lines.append("Task: PAPER_02_TASK_04")
lines.append("Title: Compare GAN-generated and predictor-generated candidate solutions for target gabs design")
lines.append("")
lines.append("Step_0: Load the ABS and PROP CGAN result files for the same target wavelength or condition.")
lines.append(f"- Loaded ABS dataset from: {dataset_abs}")
lines.append(f"- ABS rows: {len(abs_df)}, columns: {list(abs_df.columns)}")
if prop_available:
    lines.append(f"- Loaded PROP dataset from: {dataset_prop}")
    lines.append(f"- PROP rows: {len(prop_df)}, columns: {list(prop_df.columns)}")
else:
    lines.append(f"- PROP dataset not found at expected path: {dataset_prop}")
    lines.append("- Because the PROP file is missing, the comparison is limited to the ABS case and a full ABS-vs-PROP comparison cannot be completed from the available data.")
lines.append("")
lines.append("Step_1: Extract the design variables and the columns corresponding to G_GAN, G_Predict, and dG.")
lines.append("- Design variables identified directly from the CSV header: Color, Thick, Strain, Gray.")
lines.append("- Output variables identified directly from the CSV header: G_GAN, G_Predict, dG.")
lines.append("- The dataset preview shows numeric rows with these columns populated, so the file structure is valid for quantitative comparison.")
lines.append("")
lines.append("Step_2: Compute summary statistics comparing GAN output to predictor output for each file.")
lines.append("- For ABS, dG is used as the provided difference metric between predictor and GAN outputs.")
lines.append(f"- ABS mean signed error (mean dG): {abs_stats['mean_signed_error']:.6f}")
lines.append(f"- ABS mean absolute error (mean |dG|): {abs_stats['mean_absolute_error']:.6f}")
lines.append(f"- ABS fraction within |dG| <= 0.05: {abs_stats['fraction_within_0.05']:.3f}")
lines.append(f"- ABS fraction within |dG| <= 0.10: {abs_stats['fraction_within_0.10']:.3f}")
lines.append(f"- ABS Pearson correlation between G_GAN and G_Predict: {abs_stats['pearson_r']:.6f}")
lines.append(f"- ABS maximum absolute difference: {abs_stats['max_abs_diff']:.6f}")
lines.append(f"- ABS consistency check between provided dG and (G_Predict - G_GAN): MAE = {abs_stats['dG_consistency_mae']:.6e}")
if prop_stats is not None:
    lines.append(f"- PROP mean signed error (mean dG): {prop_stats['mean_signed_error']:.6f}")
    lines.append(f"- PROP mean absolute error (mean |dG|): {prop_stats['mean_absolute_error']:.6f}")
    lines.append(f"- PROP fraction within |dG| <= 0.05: {prop_stats['fraction_within_0.05']:.3f}")
    lines.append(f"- PROP fraction within |dG| <= 0.10: {prop_stats['fraction_within_0.10']:.3f}")
    lines.append(f"- PROP Pearson correlation between G_GAN and G_Predict: {prop_stats['pearson_r']:.6f}")
    lines.append(f"- PROP maximum absolute difference: {prop_stats['max_abs_diff']:.6f}")
    lines.append(f"- PROP consistency check between provided dG and (G_Predict - G_GAN): MAE = {prop_stats['dG_consistency_mae']:.6e}")
else:
    lines.append("- PROP statistics could not be computed because the PROP file was unavailable.")
lines.append("")
lines.append("Step_3: Generate parity plots or grouped bar charts for the two target classes.")
lines.append("- A side-by-side parity plot is generated for ABS and PROP when both files are available.")
lines.append("- If PROP is unavailable, the figure contains only the ABS parity plot and explicitly notes the limitation.")
lines.append("")
lines.append("Step_4: Compare the ABS and PROP cases and report which target class shows tighter agreement.")
if prop_stats is not None:
    tighter = "ABS" if abs_stats["mean_absolute_error"] < prop_stats["mean_absolute_error"] else "PROP"
    lines.append(f"- Tighter agreement is indicated by the smaller mean absolute error: {tighter}.")
    lines.append("- This conclusion is based on the directly computed |dG| values and the parity relationship between G_GAN and G_Predict.")
else:
    lines.append("- A direct ABS-vs-PROP comparison is not possible because the PROP dataset is missing.")
    lines.append("- Therefore, no valid claim about which target class shows tighter agreement can be made from the available data.")
lines.append("")
lines.append("Data interpretation notes:")
lines.append("- The CSV contains candidate design descriptors and two gabs-related outputs for each candidate.")
lines.append("- No peak finding or spectral interpretation is required for this task.")
lines.append("- All reported quantities are directly supported by the loaded tabular data.")
lines.append("- No missing values were introduced or imputed during analysis.")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

# Plotting
if prop_df is not None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), dpi=200, sharex=False, sharey=False)
    datasets = [(abs_df, "ABS 440", axes[0]), (prop_df, "PROP 440", axes[1])]
else:
    fig, axes = plt.subplots(1, 1, figsize=(6, 5), dpi=200)
    datasets = [(abs_df, "ABS 440", axes)]

for df, title, ax in datasets:
    ax.scatter(df["G_GAN"], df["G_Predict"], s=18, alpha=0.8, edgecolor="none")
    minv = min(df["G_GAN"].min(), df["G_Predict"].min())
    maxv = max(df["G_GAN"].max(), df["G_Predict"].max())
    pad = 0.03 * (maxv - minv) if maxv > minv else 0.1
    xline = np.linspace(minv - pad, maxv + pad, 100)
    ax.plot(xline, xline, "k--", lw=1)
    ax.set_title(title)
    ax.set_xlabel("G_GAN")
    ax.set_ylabel("G_Predict")
    ax.grid(True, alpha=0.25)
    ax.text(
        0.05, 0.95,
        f"MAE={np.mean(np.abs(df['dG'])):.3f}\nMSE={np.mean(df['dG']**2):.3f}\n|dG|<=0.05={np.mean(np.abs(df['dG'])<=0.05):.2f}",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=8,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8, edgecolor="0.7")
    )

if prop_df is None:
    fig.suptitle("CGAN comparison for ABS 440 (PROP file unavailable)", fontsize=12)
else:
    fig.suptitle("CGAN comparison: ABS vs PROP target cases", fontsize=12)

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig(fig_path, bbox_inches="tight")
plt.close(fig)

print(f"Saved figure to: {fig_path}")
print(f"Saved analysis to: {analysis_path}")