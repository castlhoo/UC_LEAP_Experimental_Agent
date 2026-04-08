import os
import json
import numpy as np
import matplotlib.pyplot as plt

base_dir = r"C:/UCLEAP/UC_LEAP/step4/organized/002_Inverse_design_of_chiral_functional/type2_data"
idx_file = os.path.join(base_dir, "train_idx.npy")

out_dir = r"C:/UCLEAP/UC_LEAP/step5/output/002_Inverse_design_of_chiral_functional/results"
fig_path = os.path.join(out_dir, "PAPER_02_TASK_03_figure.png")
analysis_path = os.path.join(out_dir, "PAPER_02_TASK_03_Analysis.txt")

os.makedirs(out_dir, exist_ok=True)

analysis_lines = []
analysis_lines.append("Task PAPER_02_TASK_03 Analysis")
analysis_lines.append("=" * 40)
analysis_lines.append(f"Loaded index file: {idx_file}")

# Load index file
try:
    train_idx = np.load(idx_file)
except Exception as e:
    analysis_lines.append(f"ERROR: Failed to load train_idx.npy: {e}")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_lines))
    raise

analysis_lines.append(f"Array shape: {train_idx.shape}")
analysis_lines.append(f"Array dtype: {train_idx.dtype}")
analysis_lines.append(f"First 20 indices: {train_idx[:20].tolist()}")

# Basic validation
train_idx = np.asarray(train_idx).astype(int)
unique_train_idx = np.unique(train_idx)
n_train = train_idx.size
n_unique_train = unique_train_idx.size
analysis_lines.append(f"Total training indices listed: {n_train}")
analysis_lines.append(f"Unique training indices: {n_unique_train}")
if n_unique_train != n_train:
    analysis_lines.append("NOTE: Duplicate indices detected in the training index file.")
else:
    analysis_lines.append("No duplicate indices detected in the training index file.")

# Attempt to infer full dataset size from index range
max_idx = int(train_idx.max()) if train_idx.size > 0 else None
min_idx = int(train_idx.min()) if train_idx.size > 0 else None
analysis_lines.append(f"Minimum training index: {min_idx}")
analysis_lines.append(f"Maximum training index: {max_idx}")

# Infer whether indices are 0-based and estimate full dataset size from max index
# Since only the training index file is provided, the held-out count can only be estimated
# if the full dataset size is known or inferable. Here we infer the minimum possible full size
# as max_idx + 1, and report the limitation explicitly.
if max_idx is not None:
    inferred_full_size_min = max_idx + 1
    heldout_min = inferred_full_size_min - n_unique_train
    split_ratio_min = n_unique_train / inferred_full_size_min
    analysis_lines.append("")
    analysis_lines.append("Full dataset size is not explicitly provided in the available files.")
    analysis_lines.append(
        f"Minimum possible full dataset size inferred from max index (assuming 0-based indexing): {inferred_full_size_min}"
    )
    analysis_lines.append(
        f"Corresponding minimum possible held-out count: {heldout_min}"
    )
    analysis_lines.append(
        f"Corresponding training fraction under this minimum-size assumption: {split_ratio_min:.4f}"
    )
    analysis_lines.append(
        "Limitation: exact held-out count and exact 80:20 verification require the full dataset size or a dataset table, which is not present in the provided input."
    )
else:
    analysis_lines.append("No indices available to infer dataset size.")

# Check if a companion dataset file exists in the same directory
candidate_files = []
for fn in os.listdir(base_dir):
    if fn.lower().endswith((".npy", ".npz", ".csv", ".txt", ".json")) and fn != "train_idx.npy":
        candidate_files.append(fn)

analysis_lines.append("")
analysis_lines.append("Companion files detected in the dataset directory:")
if candidate_files:
    for fn in sorted(candidate_files):
        analysis_lines.append(f"  - {fn}")
else:
    analysis_lines.append("  - None")

# Since no forward-model dataset file is explicitly provided, we cannot compare descriptors.
analysis_lines.append("")
analysis_lines.append("Descriptor comparison:")
analysis_lines.append(
    "No forward-model dataset table or descriptor matrix was provided alongside train_idx.npy, so sample-level descriptor distributions cannot be compared."
)

# Prepare figure: split counts and a placeholder distribution panel explaining limitation
fig, axes = plt.subplots(1, 2, figsize=(12, 5), dpi=200)

# Panel 1: split counts under minimum-size assumption
if max_idx is not None:
    train_count = n_unique_train
    heldout_count = max(inferred_full_size_min - train_count, 0)
    axes[0].bar(["Training", "Held-out\n(min. inferred)"], [train_count, heldout_count], color=["#1f77b4", "#ff7f0e"])
    axes[0].set_ylabel("Count")
    axes[0].set_title("Split counts")
    for i, v in enumerate([train_count, heldout_count]):
        axes[0].text(i, v + max(1, 0.01 * max(train_count, heldout_count)), str(v), ha="center", va="bottom", fontsize=9)
    axes[0].text(
        0.5, 0.95,
        "Exact held-out count unavailable\nwithout full dataset size",
        transform=axes[0].transAxes,
        ha="center", va="top",
        fontsize=9,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8, edgecolor="gray")
    )
else:
    axes[0].text(0.5, 0.5, "No indices available", ha="center", va="center")
    axes[0].set_axis_off()

# Panel 2: descriptor comparison limitation
axes[1].axis("off")
axes[1].text(
    0.5, 0.7,
    "Descriptor comparison not performed",
    ha="center", va="center", fontsize=12, fontweight="bold"
)
axes[1].text(
    0.5, 0.5,
    "No forward-model dataset table or\nsample-level descriptors were provided.",
    ha="center", va="center", fontsize=10
)
axes[1].text(
    0.5, 0.28,
    "Only the training index file is available.",
    ha="center", va="center", fontsize=10
)

fig.suptitle("PAPER_02_TASK_03: Training split reconstruction", fontsize=14)
fig.tight_layout(rect=[0, 0, 1, 0.95])

# Save figure
fig.savefig(fig_path, bbox_inches="tight")
plt.close(fig)

# Write analysis file
analysis_lines.append("")
analysis_lines.append("Figure saved to:")
analysis_lines.append(fig_path)
analysis_lines.append("")
analysis_lines.append("Conclusion:")
analysis_lines.append(
    f"The training index file contains {n_unique_train} unique training samples. "
    "An exact 80:20 split cannot be verified from the provided files alone because the full dataset size and descriptor table are unavailable."
)

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

print(json.dumps({
    "train_indices": int(n_unique_train),
    "min_index": min_idx,
    "max_index": max_idx,
    "figure": fig_path,
    "analysis": analysis_path
}, indent=2))