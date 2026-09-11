# -*- coding: utf-8 -*-
"""图5 问题1 时空场热力图：温度与含水率双面板（result1.xlsx, 0-30 min）。"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _figbase import *  # noqa: F401,F403
import numpy as np

t_T, r_cm, T = field_matrix("result1.xlsx", "温度")
t_C, _, C = field_matrix("result1.xlsx", "水分浓度")
t_min_T, t_min_C = t_T * 60.0, t_C * 60.0

fig, (ax1, ax2) = panel(1, 2, height_fraction=0.46)

for ax, tm, Z, cmap, cbl in (
    (ax1, t_min_T, T, "inferno", "温度 / ℃"),
    (ax2, t_min_C, C, "YlGnBu", "含水率 / (kg·kg$^{-1}$)"),
):
    pm = ax.pcolormesh(r_cm, tm, Z, cmap=cmap, shading="auto", rasterized=True)
    cs = ax.contour(r_cm, tm, Z, levels=5, colors="white", linewidths=0.6,
                    alpha=0.7)
    ax.clabel(cs, inline=True, fontsize=8.2, fmt="%.2g")
    ax.set_xlabel("径向位置 $r$ / cm")
    cb = fig.colorbar(pm, ax=ax, pad=0.02)
    cb.set_label(cbl, fontsize=8.5)
    cb.ax.tick_params(labelsize=8.2)

ax1.set_ylabel("时间 / min")
ax2.set_ylabel("")
ax2.tick_params(labelleft=False)
for ax in (ax1, ax2):
    ax.set_xlim(r_cm[0], r_cm[-1])
    ax.set_ylim(0, t_min_T[-1])

label_panels([ax1, ax2], ["(a) 温度场", "(b) 含水率场"])
finish(fig, "fig_field_heatmap_p1.pdf")
