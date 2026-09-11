# -*- coding: utf-8 -*-
"""图3 附录3 扩散系数 D(C,T) 二维填充等高线（对数标度）。"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _figbase import *  # noqa: F401,F403
import numpy as np
import matplotlib.ticker as mticker
import sys, os
sys.path.insert(0, os.path.join(ROOT, "code"))
import params as P  # noqa: E402

Cg = np.linspace(0.10, 2.60, 220)
Tg = np.linspace(28.0, 55.0, 200)
CC, TT = np.meshgrid(Cg, Tg)
D = P.D_PRE_A3 * np.exp(-P.D_EXP_A3 / CC) * np.exp(-P.ARR_T / (TT + P.T_KELVIN))
logD = np.log10(D)

fig, ax = panel(height_fraction=0.62)
cf = ax.contourf(CC, TT, logD, levels=18, cmap="viridis")
ax.contour(CC, TT, logD, levels=8, colors="white", linewidths=0.7, alpha=0.75)

# 阈值线与初始含水率线
ax.axvline(C_TH, color=COLORS["down"], lw=1.6, ls="--")
ax.axvline(2.55, color=COLORS["up"], lw=1.6, ls="-.")
_bb = dict(boxstyle="round,pad=0.20", fc="white", ec="none", alpha=0.88)
ax.text(C_TH + 0.045, 53.4, "达标阈值 0.15", fontsize=8.2,
        color=COLORS["down"], rotation=90, va="top", bbox=_bb)
ax.text(2.55 - 0.10, 53.4, "初始 2.55", fontsize=8.2,
        color=COLORS["up"], rotation=90, va="top", ha="right", bbox=_bb)

ax.set_xlabel("含水率 $C$ / (kg·kg$^{-1}$)")
ax.set_ylabel("温度 $T$ / ℃")
ax.set_xlim(Cg[0], Cg[-1])
ax.set_ylim(Tg[0], Tg[-1])
cb = fig.colorbar(cf, ax=ax, pad=0.02)
cb.set_label("$\\log_{10}(D\\,/\\,\\mathrm{m^2 s^{-1}})$")
cb.locator = mticker.MaxNLocator(6)
cb.update_ticks()

finish(fig, "fig_diffusivity_contour.pdf")
