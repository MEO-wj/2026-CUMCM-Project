# -*- coding: utf-8 -*-
"""图10 山脊图：问题3 各时刻径向含水率剖面的堆叠演化。"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _figbase import *  # noqa: F401,F403
import numpy as np
import matplotlib.pyplot as plt

t_h, r_cm, C = field_matrix("result3.xlsx", "Sheet1")
marks = [0.0, 3.0, 6.0, 12.0, 18.0, 24.0, 30.0, 36.0, 42.0, 48.0, 54.0,
         float(results("p3")["p3_t_star_h"])]
idx = [int(np.argmin(np.abs(t_h - m))) for m in marks]

n = len(idx)
gap = 0.36                       # 相邻脊线基线间距（含水率单位）
cmap = plt.get_cmap("mako" if "mako" in plt.colormaps() else "viridis")

fig, ax = panel(height_fraction=1.05, width_fraction=0.82)
for k, (j, m) in enumerate(zip(idx, marks)):
    base = (n - 1 - k) * gap
    y = C[j] + base
    col = cmap(0.08 + 0.82 * k / (n - 1))
    ax.fill_between(r_cm, base, y, color=col, alpha=0.72, lw=0, zorder=n - k)
    ax.plot(r_cm, y, color="white", lw=1.05, zorder=n - k + 0.5)
    ax.plot(r_cm, y, color=col, lw=0.75, zorder=n - k + 0.6)
    lab = f"{m:.2f} h" if k == n - 1 else f"{m:g} h"
    ax.text(r_cm[-1] + 0.055, base + 0.02, lab, fontsize=8.2,
            color=COLORS["dark"], va="bottom")

ax.set_xlabel("径向位置 $r$ / cm")
ax.set_ylabel("含水率剖面（偏移 0.36 堆叠）")
ax.set_xlim(0, r_cm[-1] + 0.42)
ax.set_ylim(-0.10, (n - 1) * gap + C[idx[0]].max() * 1.06)
ax.set_yticks([])
ax.spines["left"].set_visible(False)
ax.grid(axis="x", alpha=0.25, lw=0.5)
finish(fig, "fig_ridgeline_profile.pdf")
