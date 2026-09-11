# -*- coding: utf-8 -*-
"""图2 附件2 半径收缩：PCHIP 插值曲线与收缩速率子图。"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _figbase import *  # noqa: F401,F403
import numpy as np
from scipy.interpolate import PchipInterpolator

df = user_xlsx("附件2.xlsx")
t_h = df["时间"].to_numpy(dtype=float) / 3600.0
R = df["半径"].to_numpy(dtype=float)

pch = PchipInterpolator(t_h, R)
tf = np.linspace(t_h[0], t_h[-1], 800)
Rf = pch(tf)
dRf = pch.derivative()(tf)

fig, (ax1, ax2) = panel(2, 1, height_fraction=0.74, sharex=True,
                        gridspec_kw={"height_ratios": [2.0, 1.0], "hspace": 0.12})

ax1.plot(tf, Rf, color=COLORS["primary"], lw=1.9, label="PCHIP 单调插值")
ax1.scatter(t_h[::6], R[::6], s=13, color=COLORS["accent"], zorder=3,
            edgecolor="white", linewidth=0.5, label="附件2 实测点")

# 平台段识别：|dR/dt| < 1% 的最大速率
thresh = 0.01 * np.abs(dRf).max()
flat = np.abs(dRf) < thresh
if flat.any():
    t_flat = tf[np.argmax(flat)]
    ax1.axvspan(t_flat, tf[-1], color=COLORS["bg_fill2"], alpha=0.40, zorder=0)
    ax1.annotate(f"收缩平台 $t\\geq${t_flat:.1f} h\n$R_\\infty$={Rf[-1]:.3f} cm",
                 xy=(t_flat, pch(t_flat)),
                 xytext=(t_flat - 30, R.min() + 0.55 * (R.max() - R.min())),
                 fontsize=8.5, color=COLORS["dark"],
                 arrowprops=dict(arrowstyle="->", lw=0.8, color=COLORS["gray"]))

ax1.set_ylabel("半径 $R$ / cm")
ax1.legend(loc="upper right", fontsize=8.5, frameon=True, framealpha=0.9)
declutter_axes(ax1, grid=True, grid_axis="y")

ax2.plot(tf, dRf, color=COLORS["secondary"], lw=1.6)
ax2.fill_between(tf, dRf, 0.0, color=COLORS["secondary"], alpha=0.16)
ax2.axhline(0.0, color=COLORS["gray"], lw=0.8, ls=":")
ax2.set_xlabel("时间 $t$ / h")
ax2.set_ylabel("收缩速率 (cm/h)")
ax2.set_xlim(t_h[0], t_h[-1])
declutter_axes(ax2, grid=True, grid_axis="y")

label_panels([ax1, ax2])
finish(fig, "fig_radius_shrink.pdf")
