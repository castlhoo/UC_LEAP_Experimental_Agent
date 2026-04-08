import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Paths
dataset_path = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/007_Inverse_design_of_chiral_functional/type1_data/final_result_PROP_467.csv"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/007_Inverse_design_of_chiral_functional/results/PAPER_07_TASK_09_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/007_Inverse_design_of_chiral_functional/results/PAPER_07_TASK_09_Analysis.txt"

# Ensure output directory exists
os.makedirs(os.path.dirname(figure_path), exist_ok=True)

analysis_lines = []
analysis_lines.append("Task PAPER_07_TASK_09 Analysis")
analysis_lines.append("=" * 40)
analysis_lines.append(f"Dataset file: {dataset_path}")

# Step 0: Load and inspect
try:
    df = pd.read_csv(dataset_path)
except Exception as e:
    analysis_lines.append(f"Failed to load CSV: {e}")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise

analysis_lines.append(f"Loaded CSV successfully.")
analysis_lines.append(f"Row count: {len(df)}")
analysis_lines.append(f"Columns: {list(df.columns)}")
analysis_lines.append("Preview of first rows:")
analysis_lines.append(df.head(10).to_string(index=False))

# Step 1: Identify relevant columns
cols = list(df.columns)
design_cols = [c for c in cols if c not in ["G_Predict", "G_GAN", "dG", "Target", "target", "Property", "PROP"]]
property_col = None
if "G_GAN" in df.columns:
    property_col = "G_GAN"
elif "G_Predict" in df.columns:
    property_col = "G_Predict"
elif "dG" in df.columns:
    property_col = "dG"

analysis_lines.append("")
analysis_lines.append("Column interpretation:")
analysis_lines.append(f"Design parameter columns inferred: {design_cols}")
analysis_lines.append(f"Property column selected: {property_col if property_col else 'None found'}")

# Step 2: Clean data and isolate 467 target entries
df_clean = df.copy()
for c in df_clean.columns:
    if df_clean[c].dtype == object:
        df_clean[c] = pd.to_numeric(df_clean[c], errors="ignore")

# Since the file is already specific to PROP_467, keep all rows but note absence of explicit target annotation
analysis_lines.append("")
analysis_lines.append("Target isolation:")
analysis_lines.append("The file name indicates the 467 nm target case (PROP_467).")
analysis_lines.append("No explicit target annotation column was present, so all rows are treated as 467 nm target candidates.")

# Remove rows with missing property values if needed
if property_col is None:
    analysis_lines.append("No usable property column found; cannot create quantitative final-result plot.")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise ValueError("No property column found in dataset.")

df_clean = df_clean.dropna(subset=[property_col]).copy()
analysis_lines.append(f"Rows after dropping missing {property_col}: {len(df_clean)}")

# Step 3: Rank candidates
df_clean = df_clean.sort_values(by=property_col, ascending=False).reset_index(drop=True)
df_clean["Rank"] = np.arange(1, len(df_clean) + 1)

analysis_lines.append("")
analysis_lines.append("Ranking by property value:")
analysis_lines.append(df_clean[[c for c in design_cols if c in df_clean.columns] + [property_col, "Rank"]].head(10).to_string(index=False))

# Step 4: Highlight best-performing candidate(s)
best_row = df_clean.iloc[0]
analysis_lines.append("")
analysis_lines.append("Best-performing candidate:")
analysis_lines.append(best_row.to_string())

# Determine if there are multiple identical best values
best_value = best_row[property_col]
best_candidates = df_clean[np.isclose(df_clean[property_col].astype(float), float(best_value))]
analysis_lines.append(f"Number of tied best candidates: {len(best_candidates)}")

# Step 5: Create publication-quality figure
plt.style.use("seaborn-v0_8-whitegrid")
fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

# Use top N candidates for readability if many rows
top_n = min(15, len(df_clean))
plot_df = df_clean.head(top_n).copy()

x = np.arange(len(plot_df))
bars = ax.bar(x, plot_df[property_col].astype(float), color="#4C78A8", edgecolor="black", linewidth=0.6)

# Highlight best candidate(s)
for i, val in enumerate(plot_df[property_col].astype(float)):
    if np.isclose(val, float(best_value)):
        bars[i].set_color("#D62728")

# Annotate bars with rank and key design parameters
def format_design_row(row):
    parts = []
    for c in ["Color", "Thick", "Strain", "Gray"]:
        if c in row.index:
            parts.append(f"{c}={row[c]}")
    return ", ".join(parts)

for i, row in plot_df.iterrows():
    label = f"#{int(row['Rank'])}\n{format_design_row(row)}"
    ax.text(i, float(row[property_col]) + 0.002, label, ha="center", va="bottom", fontsize=7, rotation=90)

# Add property values on top
for i, val in enumerate(plot_df[property_col].astype(float)):
    ax.text(i, float(val) + 0.0005, f"{val:.5f}", ha="center", va="bottom", fontsize=8, fontweight="bold")

ax.set_xticks(x)
ax.set_xticklabels([f"{int(r)}" for r in plot_df["Rank"]], fontsize=9)
ax.set_xlabel("Candidate rank (sorted by predicted property)", fontsize=11)
ax.set_ylabel(property_col, fontsize=11)
ax.set_title("Final screened inverse-design results for 467 nm target", fontsize=13, fontweight="bold")

# Add target label and best candidate note
target_text = "Target: PROP_467 (467 nm)"
ax.text(0.99, 0.98, target_text, transform=ax.transAxes, ha="right", va="top",
        fontsize=10, bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="gray"))

best_note = f"Best candidate: {best_value:.5f}"
ax.text(0.01, 0.98, best_note, transform=ax.transAxes, ha="left", va="top",
        fontsize=10, bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFF2F2", edgecolor="#D62728"))

# Improve layout
ax.margins(x=0.02)
plt.tight_layout()

# Save figure
plt.savefig(figure_path, dpi=300, bbox_inches="tight")
plt.close(fig)

analysis_lines.append("")
analysis_lines.append(f"Figure saved to: {figure_path}")
analysis_lines.append("Figure design:")
analysis_lines.append(f"- Bar chart of top {top_n} ranked candidates by {property_col}.")
analysis_lines.append("- Best-performing candidate highlighted in red.")
analysis_lines.append("- 467 nm target condition labeled explicitly.")
analysis_lines.append("Limitations:")
analysis_lines.append("- No explicit G_GAN or dG columns were present in the provided file preview.")
analysis_lines.append("- The dataset appears to contain only final screened candidate rows for PROP_467, so the plot summarizes the final validation/screening outcome rather than a full training distribution.")

# Write analysis
with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(f"Saved figure: {figure_path}")
print(f"Saved analysis: {analysis_path}")