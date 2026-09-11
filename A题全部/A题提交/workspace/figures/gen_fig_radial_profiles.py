# -*- coding: utf-8 -*-
"""图7 径向剖面族：问题1 温度剖面与问题2 含水率剖面随时间推进。"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _figbase import *  # noqa: F401,F403
import numpy as np
import matplotlib.pyplot as plt

t1, r_cm, T1 = field_matrix("result1.xlsx", "温度")
t2, _, C2 = field_matrix("result2.xlsx", "水分浓度")

fig, (ax1, ax2) = panel(1, 2, height_fraction=0.46)

# (a) 问题1 温度剖面：0,5,10,20,30 min
marks_min = [0.0, 5.0, 10.0, 20.0, 30.0]
cmap1 = plt.get_cmap("plasma")
for i, mm in enumerate(marks_min):
    j = int(np.argmin(np.abs(t1 * 60.0 - mm)))
    ax1.plot(r_cm, T1[j], lw=1.7, color=cmap1(0.10 + 0.78 * i / (len(marks_min) - 1)),
             label=f"{mm:.0f} min")
ax1.set_xlabel("径向位置 $r$ / cm")
ax1.set_ylabel("温度 $T$ / ℃")
ax1.legend(fontsize=8.2, loc="upper left", frameon=True, framealpha=0.9,
           title="问题1", title_fontsize=8.2, ncol=2)
declutter_axes(ax1, grid=True, grid_axis="y")

# (b) 问题2 含水率剖面：0,0.5,1,2,3 h
marks_h = [0.0, 0.5, 1.0, 2.0, 3.0]
cmap2 = plt.get_cmap("viridis")
for i, mh in enumerate(marks_h):
    j = int(np.argmin(np.abs(t2 - mh)))
    ax2.plot(r_cm, C2[j], lw=1.7, color=cmap2(0.08 + 0.80 * i / (len(marks_h) - 1)),
             label=f"{mh:g} h")
ax2.set_xlabel("径向位置 $r$ / cm")
ax2.set_ylabel("含水率 / (kg·kg$^{-1}$)")
ax2.legend(fontsize=8.2, loc="lower left", frameon=True, framealpha=0.9,
           title="问题2", title_fontsize=8.2, ncol=2)
declutter_axes(ax2, grid=True, grid_axis="y")

for ax in (ax1, ax2):
    ax.set_xlim(r_cm[0], r_cm[-1])

label_panels([ax1, ax2], ["(a) 温度剖面", "(b) 含水率剖面"])
finish(fig, "fig_radial_profiles.pdf")
