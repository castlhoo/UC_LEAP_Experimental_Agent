import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

dataset_path = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/007_Inverse_design_of_chiral_functional/type1_data/final_result_PROP_440.csv"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/007_Inverse_design_of_chiral_functional/results/PAPER_07_TASK_05_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/007_Inverse_design_of_chiral_functional/results/PAPER_07_TASK_05_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)

analysis_lines = []

def log(msg):
    analysis_lines.append(msg)

# Step 0: Load CSV and inspect structure
log("Task PAPER_07_TASK_05 Analysis")
log("Step 0: Load the CSV and inspect the available columns and row count.")
try:
    df = pd.read_csv(dataset_path)
    log(f"Loaded dataset successfully from: {dataset_path}")
    log(f"Dataset shape: {df.shape[0]} rows x {df.shape[1]} columns")
    log(f"Columns found: {list(df.columns)}")
except Exception as e:
    log(f"Failed to load dataset: {e}")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise

# Step 1: Identify columns
log("Step 1: Identify which columns represent the final selected design parameters and which represent the achieved or predicted property values.")
design_cols = [c for c in df.columns if c.lower() in ["color", "thick", "strain", "gray"]]
property_cols = [c for c in df.columns if c.lower() in ["g_predict", "g_gan", "dg", "g_final", "g"]]

log(f"Identified design parameter columns: {design_cols}")
log(f"Identified property-related columns: {property_cols}")

# Determine target column
target_col = None
for c in ["G_Predict", "G_GAN", "dG", "G_Final", "G"]:
    if c in df.columns:
        target_col = c
        break

if target_col is None:
    log("No explicit property column found among expected names. Cannot create a performance plot reliably.")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise ValueError("No property column found.")

log(f"Using '{target_col}' as the final property/performance column for visualization.")

# Step 2: Clean data and isolate 440 nm target entries
log("Step 2: Clean the data and isolate the 440 nm target entries.")
df_clean = df.copy()

# Drop rows with missing target values
before_rows = len(df_clean)
df_clean = df_clean.dropna(subset=[target_col])
after_rows = len(df_clean)
log(f"Dropped {before_rows - after_rows} rows with missing values in '{target_col}'. Remaining rows: {after_rows}")

# Ensure numeric sorting for property values
df_clean[target_col] = pd.to_numeric(df_clean[target_col], errors="coerce")
df_clean = df_clean.dropna(subset=[target_col])
log(f"After coercing '{target_col}' to numeric, remaining rows: {len(df_clean)}")

# Sort by performance descending
df_sorted = df_clean.sort_values(by=target_col, ascending=False).reset_index(drop=True)

# Step 3: Create final-result visualization
log("Step 3: Create a final-result visualization suitable for the file structure.")
log("Given the table-like structure with design parameters and a predicted property value, a ranked bar chart is appropriate.")
log("This communicates the final recommended candidates and their associated predicted performance clearly.")

# Build labels from design parameters
def make_label(row):
    parts = []
    for c in design_cols:
        val = row[c]
        if pd.isna(val):
            continue
        if isinstance(val, float) and val.is_integer():
            val = int(val)
        parts.append(f"{c}={val}")
    return ", ".join(parts) if parts else f"Candidate {row.name + 1}"

labels = [make_label(row) for _, row in df_sorted.iterrows()]
values = df_sorted[target_col].values

# Step 4: Highlight best-performing candidate(s) and include 440 nm target in title/annotation
log("Step 4: Highlight the best-performing candidate(s) and include the 440 nm target in the title or annotation.")
best_idx = int(np.argmax(values))
best_value = values[best_idx]
best_label = labels[best_idx]
log(f"Best-performing candidate identified at sorted index {best_idx} with {target_col} = {best_value:.5f}.")
log(f"Best candidate design parameters: {best_label}")

# Step 5: Publication-ready formatting
log("Step 5: Format the output as a publication-ready figure suitable for direct comparison with the paper’s final-design panel.")

plt.style.use("seaborn-v0_8-whitegrid")
fig, ax = plt.subplots(figsize=(10, max(4, 0.45 * len(df_sorted) + 1.5)))

x = np.arange(len(df_sorted))
colors = ["#d62728" if i == best_idx else "#1f77b4" for i in range(len(df_sorted))]
bars = ax.bar(x, values, color=colors, edgecolor="black", linewidth=0.6)

ax.set_title("Final inverse-design results for 440 nm target", fontsize=14, pad=12)
ax.set_ylabel(target_col, fontsize=12)
ax.set_xlabel("Candidate designs ranked by predicted performance", fontsize=12)

ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)

# Annotate values
for i, (bar, val) in enumerate(zip(bars, values)):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{val:.3f}",
            ha="center", va="bottom", fontsize=9, rotation=0)

# Highlight best candidate
ax.annotate(
    f"Best: {best_value:.3f}",
    xy=(best_idx, best_value),
    xytext=(best_idx, best_value + (max(values) - min(values)) * 0.08 if len(values) > 1 else best_value * 1.05),
    ha="center",
    arrowprops=dict(arrowstyle="->", color="#d62728", lw=1.5),
    fontsize=10,
    color="#d62728",
    fontweight="bold"
)

# Add a concise summary box
summary_text = (
    f"Rows: {len(df_sorted)}\n"
    f"Best {target_col}: {best_value:.5f}\n"
    f"Best design: {best_label}"
)
ax.text(
    0.99, 0.98, summary_text,
    transform=ax.transAxes,
    ha="right", va="top",
    fontsize=9,
    bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="gray", alpha=0.9)
)

plt.tight_layout()
plt.savefig(figure_path, dpi=300, bbox_inches="tight")
plt.close(fig)

log(f"Figure saved to: {figure_path}")
log("Analysis completed successfully.")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))