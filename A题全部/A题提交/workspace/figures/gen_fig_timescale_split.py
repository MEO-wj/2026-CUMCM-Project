# -*- coding: utf-8 -*-
"""图7b 时间尺度分离：问题2 全径向温差（对数右轴）与含水率中心-表面差。"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _figbase import *  # noqa: F401,F403
import numpy as np
from matplotlib.lines import Line2D

t_h, r_cm, T = field_matrix("result2.xlsx", "温度")
_, _, C = field_matrix("result2.xlsx", "水分浓度")

dT = T.max(axis=1) - T.min(axis=1)        # 全径向温差 / K
dC = C[:, 0] - C[:, -1]                   # 中心 - 表面 含水率差

fig, ax = panel(height_fraction=0.58)
ax2 = ax.twinx()

l1, = ax.plot(t_h, dC, color=COLORS["primary"], lw=1.9,
              label="含水率差 $C_0-C_s$")
l2, = ax2.plot(t_h, dT, color=COLORS["secondary"], lw=1.7, ls="--",
               label="温差 $\\max T-\\min T$")
ax2.set_yscale("log")

ax.set_xlabel("时间 $t$ / h")
ax.set_ylabel("含水率差 / (kg·kg$^{-1}$)", color=COLORS["primary"])
ax2.set_ylabel("全径向温差 / K（对数轴）", color=COLORS["secondary"])
ax.tick_params(axis="y", colors=COLORS["primary"])
ax2.tick_params(axis="y", colors=COLORS["secondary"])
ax.set_xlim(t_h[0], t_h[-1])
ax.set_ylim(0, dC.max() * 1.18)

end = Line2D([], [], ls="none",
             label=f"终点：温差 {dT[-1]:.2f} K，含水率差 {dC[-1]:.2f}")
ax.legend(handles=[l1, l2, end], loc="lower right",
          frameon=True, framealpha=0.92)
declutter_axes(ax, grid=True, grid_axis="y")
ax2.spines["top"].set_visible(False)
ax2.grid(False)
finish(fig, "fig_timescale_split.pdf")
