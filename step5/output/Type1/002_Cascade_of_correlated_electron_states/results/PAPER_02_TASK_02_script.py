import os
import pandas as pd
import matplotlib.pyplot as plt

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/002_Cascade_of_correlated_electron_states/type1_data/41586_2021_3946_MOESM4_ESM_10.xlsx"
figure_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/002_Cascade_of_correlated_electron_states/results/PAPER_02_TASK_02_figure.png"
analysis_path = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/002_Cascade_of_correlated_electron_states/results/PAPER_02_TASK_02_Analysis.txt"

os.makedirs(os.path.dirname(figure_path), exist_ok=True)

# Brief inspection of workbook structure
xls = pd.ExcelFile(dataset_file)
sheet_names = xls.sheet_names

analysis_lines = []
analysis_lines.append("Task PAPER_02_TASK_02 Analysis")
analysis_lines.append("")
analysis_lines.append(f"Workbook loaded: {dataset_file}")
analysis_lines.append(f"Available sheets: {sheet_names}")
analysis_lines.append("")

# The workbook preview indicates two sheets:
# - Fig 3e: q vs intensity at multiple temperatures
# - Fig 3f: q vs intensity for qa, qb, qc
# Neither sheet contains bias voltage or dI/dV labels.
# Therefore, the provided spreadsheet does not appear to contain the tunneling differential conductance inset data requested.
analysis_lines.append("Step_0: Open the Excel workbook and locate the sheet corresponding to the inset spectrum.")
analysis_lines.append("Inspection of the workbook shows only two sheets: 'Fig 3e' and 'Fig 3f'.")
analysis_lines.append("These sheets contain q/fraction of Qbragg axes and intensity traces, not bias voltage or dI/dV data.")
analysis_lines.append("Conclusion: the workbook does not contain an identifiable inset tunneling spectrum sheet.")
analysis_lines.append("")

analysis_lines.append("Step_1: Determine which columns contain bias and dI/dV values, accounting for any multi-row headers or embedded labels.")
analysis_lines.append("Sheet 'Fig 3e' has a multi-row header with q and multiple intensity columns labeled by temperature (4.5K to 58.7K).")
analysis_lines.append("Sheet 'Fig 3f' has q and intensity columns labeled qa, qb, and qc.")
analysis_lines.append("No column or embedded label indicates bias voltage or dI/dV.")
analysis_lines.append("")

analysis_lines.append("Step_2: Extract the intended inset-range data and remove any non-data rows.")
analysis_lines.append("Because no bias/dI/dV data are present, no inset-range extraction can be performed.")
analysis_lines.append("The available rows are q-dependent intensity data, which are not suitable for the requested tunneling spectrum inset.")
analysis_lines.append("")

analysis_lines.append("Step_3: Plot dI/dV versus bias using a line plot with clear axis labels and a zoomed-in view if indicated by the data.")
analysis_lines.append("This step cannot be completed faithfully because the required variables (Bias and dI/dV) are absent.")
analysis_lines.append("No unsupported substitution was made using q/intensity data.")
analysis_lines.append("")

analysis_lines.append("Step_4: Confirm that the output matches the inset-style presentation implied by the digitized dataset.")
analysis_lines.append("The dataset does not support an inset-style tunneling spectrum reconstruction.")
analysis_lines.append("Therefore, no figure was generated to avoid fabricating an incorrect panel.")
analysis_lines.append("")
analysis_lines.append("Final assessment: task cannot be completed from the provided workbook because the necessary bias-voltage and dI/dV data are missing.")

with open(analysis_path, "w", encoding="utf-8") as f:
    f.write("\n".join(analysis_lines))

# Create a minimal placeholder figure explaining the limitation, since no valid spectrum exists.
fig, ax = plt.subplots(figsize=(7, 4.5), dpi=200)
ax.axis("off")
msg = (
    "Requested inset dI/dV spectrum could not be reconstructed.\n\n"
    "Reason:\n"
    "• Workbook contains only q vs intensity data (Fig 3e, Fig 3f)\n"
    "• No bias-voltage axis or dI/dV signal is present\n"
    "• No defensible inset spectrum can be plotted without assumptions"
)
ax.text(0.02, 0.95, msg, va="top", ha="left", fontsize=11)
plt.tight_layout()
plt.savefig(figure_path, bbox_inches="tight")
plt.close(fig)