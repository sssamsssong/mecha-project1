# PLOT_GRAPH_PROJ  (provided code: do not modify this file)
# Interactive graph of CSV files from AUTO_CONTROL_PROJ, saved as an HTML file
#   - Each file: position (solid) and its own target (dashed), same color
#     (target may change several times in one file)
#   - Legend (above the graph): PID gains of the file, click to hide / show that file
# Open the HTML file in a web browser:
#   - Mouse over: vertical line, values of all lines at that time (color = file)
#   - Toolbar (top right): zoom, draw line / path / box, erase, save as PNG
#   - Double click legend: show only that file
# Run: python3 PLOT_GRAPH_PROJ.py                -> all CSV files in this folder
#      python3 PLOT_GRAPH_PROJ.py a.csv b.csv    -> only these files
# Needs: numpy, plotly (sudo apt install python3-plotly)

import os
import sys
from datetime import datetime
from pathlib import Path
import numpy as np
import plotly.graph_objects as go
from plotly.colors import qualitative

COLORS = qualitative.Plotly     # 10 colors, used in order

# ===== CSV files to plot =====
files = [Path(f).resolve() for f in sys.argv[1:]]   # From arguments (same as argv in C)

os.chdir(Path(__file__).parent)     # Work in this file's folder (CSV and HTML files)
if len(files) == 0:
    files = sorted(Path(".").glob("*.csv"))         # No argument: all CSV files in this folder

if len(files) == 0:
    print("No CSV file")
    exit()

# ===== Output file name =====
name = input("Enter the HTML file name: ").strip()
if name == "":
    name = datetime.now().strftime("%Y%m%d_%H%M%S")   # ex) 20261101_221500
if not name.endswith(".html"):
    name = name + ".html"

# ===== Plot =====
fig = go.Figure()

for i, file in enumerate(files):
    with open(file) as f:
        if not f.readline().startswith("P gain"):   # Old CSV file (no gain rows): not for this program
            print("Skip (no gain rows):", Path(file).name)
            continue

    gains = np.loadtxt(file, delimiter=",", skiprows=1, max_rows=1)    # Row 2: P, I, D gains
    data = np.loadtxt(file, delimiter=",", skiprows=3)     # skiprows=3: gain rows (2) and header row
    t = data[:, 0]              # Column 0: time (s)
    position = data[:, 1]       # Column 1: position (rev)
    target = data[:, 2]         # Column 2: target (rev)

    label = f"P {gains[0]:g}, I {gains[1]:g}, D {gains[2]:g}"   # Legend: PID gains, ex) P 10, I 0, D 0
    group = Path(file).stem     # File name without .csv (lines of one file: one group)
    color = COLORS[i % len(COLORS)]

    fig.add_scatter(x=t, y=position, name=label,
                    legendgroup=group, line=dict(color=color),
                    hovertemplate="%{y:.3f}<extra></extra>")         # Mouse over: value only
    fig.add_scatter(x=t, y=target, name=label + " target",  # Target: same color, dashed
                    legendgroup=group, showlegend=False,
                    line=dict(color=color, dash="dash"),
                    hovertemplate="target %{y:.3f}<extra></extra>")

fig.update_layout(xaxis_title="Time (s)", yaxis_title="Position (rev)",
                  hovermode="x unified",                # Values of all files at mouse time
                  legend=dict(orientation="h", x=0, y=1.02,           # Legend above the graph
                              xanchor="left", yanchor="bottom"),      # (keeps full graph width)
                  font=dict(size=14),                   # Text size (default 12)
                  hoverlabel=dict(font_size=14))        # Mouse-over text size
fig.update_xaxes(showspikes=True, spikemode="across")  # Vertical line at mouse

# Drawing tools in the toolbar (drawn shapes are not saved in the file)
config = {"modeBarButtonsToAdd": ["drawline", "drawopenpath", "drawrect", "eraseshape"]}
fig.write_html(name, config=config)
print("HTML file created:", name)
