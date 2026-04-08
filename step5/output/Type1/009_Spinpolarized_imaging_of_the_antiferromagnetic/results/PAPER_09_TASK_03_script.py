import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

dataset_file = r"C:/UCLEAP/UC_LEAP/step4/organized/Type1/009_Spinpolarized_imaging_of_the_antiferromagnetic/type1_data/Figure 3(b,c,d,e).xlsx"
out_fig = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/009_Spinpolarized_imaging_of_the_antiferromagnetic/results/PAPER_09_TASK_03_figure.png"
out_txt = r"C:/UCLEAP/UC_LEAP/step5/output/Type1/009_Spinpolarized_imaging_of_the_antiferromagnetic/results/PAPER_09_TASK_03_Analysis.txt"

os.makedirs(os.path.dirname(out_fig), exist_ok=True)

analysis = []
analysis.append("Task PAPER_09_TASK_03 analysis")
analysis.append(f"Loaded workbook: {dataset_file}")

xls = pd.ExcelFile(dataset_file)
analysis.append(f"Detected sheets: {xls.sheet_names}")

# Sheet b: topography line profile
df_b = pd.read_excel(dataset_file, sheet_name='b', header=None)
analysis.append(f"Sheet 'b' raw shape: {df_b.shape}")
analysis.append(f"Sheet 'b' first rows:\n{df_b.head(6).to_string(index=False, header=False)}")

# Parse sheet b
b = df_b.iloc[2:].copy()
b.columns = ['Distance', 'Height']
b['Distance'] = pd.to_numeric(b['Distance'], errors='coerce')
b['Height'] = pd.to_numeric(b['Height'], errors='coerce')
b = b.dropna()
analysis.append(f"Sheet 'b' parsed rows: {len(b)}")
analysis.append(f"Distance range: {b['Distance'].min():.6g} to {b['Distance'].max():.6g}")
analysis.append(f"Height range: {b['Height'].min():.6g} to {b['Height'].max():.6g}")

# Sheet c: spectra
df_c = pd.read_excel(dataset_file, sheet_name='c', header=None)
analysis.append(f"Sheet 'c' raw shape: {df_c.shape}")
analysis.append(f"Sheet 'c' first rows:\n{df_c.head(8).to_string(index=False, header=False)}")

layer_labels = list(df_c.iloc[2, 1:].astype(str))
bias = pd.to_numeric(df_c.iloc[3:, 0], errors='coerce')
spectra = {}
for i, lab in enumerate(layer_labels, start=1):
    y = pd.to_numeric(df_c.iloc[3:, i], errors='coerce')
    tmp = pd.DataFrame({'Bias': bias, 'dI/dV': y}).dropna()
    spectra[lab] = tmp
    analysis.append(f"Layer {lab}: {len(tmp)} points, Bias range {tmp['Bias'].min():.6g} to {tmp['Bias'].max():.6g}, dI/dV range {tmp['dI/dV'].min():.6g} to {tmp['dI/dV'].max():.6g}")

# Sheet d: summary trend
df_d = pd.read_excel(dataset_file, sheet_name='d', header=None)
analysis.append(f"Sheet 'd' raw shape: {df_d.shape}")
analysis.append(f"Sheet 'd' first rows:\n{df_d.head(10).to_string(index=False, header=False)}")

trend = df_d.iloc[2:].copy()
trend.columns = ['Layer', 'dI/dV']
trend['Layer'] = pd.to_numeric(trend['Layer'], errors='coerce')
trend['dI/dV'] = pd.to_numeric(trend['dI/dV'], errors='coerce')
trend = trend.dropna()
analysis.append(f"Sheet 'd' parsed rows: {len(trend)}")
analysis.append(f"Trend layers: {trend['Layer'].tolist()}")
analysis.append(f"Trend dI/dV range: {trend['dI/dV'].min():.6g} to {trend['dI/dV'].max():.6g}")

# Plot
plt.rcParams.update({
    "font.size": 10,
    "axes.linewidth": 1.0,
    "figure.dpi": 200
})

fig = plt.figure(figsize=(12, 8))
gs = GridSpec(2, 2, figure=fig, height_ratios=[1, 1], width_ratios=[1.05, 1.2], hspace=0.35, wspace=0.28)

ax_b = fig.add_subplot(gs[0, 0])
ax_c = fig.add_subplot(gs[0, 1])
ax_d = fig.add_subplot(gs[1, 0])
ax_blank = fig.add_subplot(gs[1, 1])
ax_blank.axis('off')

# Panel b
ax_b.plot(b['Distance'], b['Height'], color='black', lw=1.5)
ax_b.set_xlabel('Distance (nm)')
ax_b.set_ylabel('Height (nm)')
ax_b.set_title('Fig. 3b')
ax_b.tick_params(direction='out')

# Panel c
colors = plt.cm.tab10.colors
for idx, (lab, tmp) in enumerate(spectra.items()):
    ax_c.plot(tmp['Bias'], tmp['dI/dV'], lw=1.2, label=f'{lab}', color=colors[idx % len(colors)])
ax_c.set_xlabel('Bias (mV)')
ax_c.set_ylabel('dI/dV (a.u.)')
ax_c.set_title('Fig. 3c')
ax_c.legend(title='Layer', frameon=False, ncol=3, fontsize=8, title_fontsize=9)
ax_c.tick_params(direction='out')

# Panel d
ax_d.plot(trend['Layer'], trend['dI/dV'], marker='o', color='tab:blue', lw=1.5)
ax_d.set_xlabel('Layer #')
ax_d.set_ylabel('dI/dV (a.u.)')
ax_d.set_title('Fig. 3d/e summary')
ax_d.set_xticks(trend['Layer'].astype(int).tolist())
ax_d.tick_params(direction='out')

fig.suptitle('Replot of Fig. 3(b,c,d,e) from layer-dependent STM/STS data', y=0.98)
fig.tight_layout(rect=[0, 0, 1, 0.96])

fig.savefig(out_fig, bbox_inches='tight')
plt.close(fig)

analysis.append("Figure saved successfully.")
analysis.append(f"Output figure: {out_fig}")
analysis.append("Notes:")
analysis.append("- Sheet 'b' contains a valid height profile with Distance and Height columns after skipping the first two header rows.")
analysis.append("- Sheet 'c' contains layer-resolved spectra with layer labels in row 2 and Bias values in the first column from row 3 onward.")
analysis.append("- Sheet 'd' contains a summary trend of dI/dV versus Layer #.")
analysis.append("- No peak-finding was performed because the task is a replot task and the provided summary values were plotted directly.")
analysis.append("- The workbook does not explicitly separate Fig. 3d and Fig. 3e into distinct sheets; the available summary sheet was plotted as the quantitative trend panel.")

with open(out_txt, 'w', encoding='utf-8') as f:
    f.write("\n".join(analysis))

print(f"Saved figure to: {out_fig}")
print(f"Saved analysis to: {out_txt}")