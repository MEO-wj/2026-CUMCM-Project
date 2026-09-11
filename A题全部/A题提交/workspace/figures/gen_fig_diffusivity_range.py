# -*- coding: utf-8 -*-
"""图4 三附录扩散系数量级对比：D(C) 半对数曲线。"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _figbase import *  # noqa: F401,F403
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(ROOT, "code"))
import params as P  # noqa: E402

Cg = np.logspace(np.log10(0.10), np.log10(2.60), 300)
T_ref = 50.0
fT = np.exp(-P.ARR_T / (T_ref + P.T_KELVIN))

series = [
    ("附录2（问题1，无温度项）",
     P.D_PRE_A2 * np.exp(-P.D_EXP_A2 / Cg), COLORS["primary"], "-"),
    (f"附录3（问题2/3，$T$={T_ref:.0f}℃）",
     P.D_PRE_A3 * np.exp(-P.D_EXP_A3 / Cg) * fT, COLORS["secondary"], "--"),
    (f"附录4（问题4，$T$={T_ref:.0f}℃）",
     P.D_PRE_A4 * np.exp(-P.D_EXP_A4 / Cg) * fT, COLORS["accent"], "-."),
]

fig, ax = panel(height_fraction=0.58)
for name, D, col, ls in series:
    ax.plot(Cg, D, color=col, lw=1.9, ls=ls, label=name)

ax.axvline(C_TH, color=COLORS["gray"], lw=1.2, ls=":")
ax.text(C_TH * 1.06, 0.0, "", fontsize=8)

ax.set_xscale("log")
ax.set_yscale("log")
lo = log_floor(*[s[1] for s in series], frac=0.6)
hi = max(float(s[1].max()) for s in series) * 1.8
ax.set_ylim(lo, hi)
ax.set_xlim(Cg[0], Cg[-1])
ax.set_xlabel("含水率 $C$ / (kg·kg$^{-1}$)（对数轴）")
ax.set_ylabel("$D$ / (m$^2$·s$^{-1}$)（对数轴）")

# 标注阈值处的量级差
for name, D, col, ls in series:
    Dth = float(np.interp(C_TH, Cg, D))
    ax.scatter([C_TH], [Dth], s=22, color=col, zorder=4,
               edgecolor="white", linewidth=0.6)
ax.annotate("$C$=0.15",
            xy=(C_TH, lo * 6), xytext=(0.30, lo * 3.0),
            fontsize=8.4, color=COLORS["dark"],
            arrowprops=dict(arrowstyle="->", lw=0.8, color=COLORS["gray"]))

ax.legend(loc="lower right", fontsize=8.3, frameon=True, framealpha=0.9)
declutter_axes(ax, grid=True, grid_axis="both")
finish(fig, "fig_diffusivity_range.pdf")
