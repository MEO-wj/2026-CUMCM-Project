# -*- coding: utf-8 -*-
"""图14 棒棒糖图：守恒/收敛类校核残差量级总览（对数横轴）。"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _figbase import *  # noqa: F401,F403
import numpy as np

allr = results("all")
p1, p2 = results("p1"), results("p2")

items = [
    ("问题1 质量守恒残差", allr["conservation_residual_p1"]),
    ("问题2 质量守恒残差", allr["conservation_residual_p2"]),
    ("问题3 质量守恒残差", allr["conservation_residual_p3"]),
    ("问题4 质量守恒残差", allr["conservation_residual_p4"]),
    ("Picard 迭代终残差", allr["picard_final_residual_max"]),
    ("问题1 表面控制体残差", p1["p1_surface_cv_residual"]),
    ("问题2 表面控制体残差", p2["p2_surface_cv_residual"]),
    ("Bessel 解析对照 $L_2$", p1["p1_bessel_rel_err_l2"]),
    ("BDF 交叉校核最大偏差", allr["bdf_cross_check_max_abs_diff"]),
]
names = [i[0] for i in items]
vals = np.array([abs(float(i[1])) for i in items])

TOL = 1e-8   # 机器精度类残差的判定线
y = np.arange(len(items))[::-1]

fig, ax = panel(height_fraction=0.76, width_fraction=0.94)
for yi, v in zip(y, vals):
    col = COLORS["up"] if v < TOL else COLORS["accent"]
    ax.hlines(yi, log_floor(vals), v, color=col, lw=1.5, alpha=0.75, zorder=2)
    ax.plot(v, yi, "o", ms=7.0, color=col, mec="white", mew=0.8, zorder=3)
    ax.annotate(f"{v:.2e}", xy=(v, yi), xytext=(9, 0),
                textcoords="offset points", va="center", fontsize=8.2,
                color=COLORS["dark"])

ax.axvline(TOL, color=COLORS["gray"], lw=1.2, ls="--", zorder=1)

ax.set_xscale("log")
ax.set_yticks(y)
ax.set_yticklabels(names, fontsize=8.2)
ax.set_xlim(log_floor(vals, frac=0.35), vals.max() * 400)
ax.set_xlabel("残差绝对值（虚线为 $10^{-8}$）")
declutter_axes(ax, grid=True, grid_axis="x")
finish(fig, "fig_conservation.pdf")
