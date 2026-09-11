# -*- coding: utf-8 -*-
"""图9 干燥曲线与阈值穿越：问题3 中心/均值/表面含水率 + 穿越点局部放大。"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _figbase import *  # noqa: F401,F403
import numpy as np

t_h, r_cm, C = field_matrix("result3.xlsx", "Sheet1")
p3 = results("p3")
t_star = p3["p3_t_star_h"]

# 体积平均（圆柱测度权重 2r/R^2）
xi = r_cm / r_cm[-1]
w = np.gradient(xi ** 2)
w = w / w.sum()
C_bar = C @ w
C_ctr, C_surf, C_max = C[:, 0], C[:, -1], C.max(axis=1)

fig, ax = panel(height_fraction=0.62)
ax.plot(t_h, C_max, color=COLORS["primary"], lw=1.9, label="空间最大值 $C_{\\max}$")
ax.plot(t_h, C_bar, color=COLORS["secondary"], lw=1.6, ls="--", label="体积平均 $\\bar{C}$")
ax.plot(t_h, C_surf, color=COLORS["accent"], lw=1.5, ls="-.", label="表面 $C_s$")
ax.axhline(C_TH, color=COLORS["down"], lw=1.4, ls=":", label="达标阈值 0.15")
ax.axvline(t_star, color=COLORS["gray"], lw=1.0, ls=":")
ax.scatter([t_star], [C_TH], s=34, color=COLORS["down"], zorder=5,
           marker="o", edgecolor="white", linewidth=0.7)
ax.annotate(f"$t^*$={t_star:.2f} h", xy=(t_star, C_TH),
            xytext=(t_star - 24.5, 0.30), color=COLORS["dark"],
            arrowprops=dict(arrowstyle="->", lw=0.9, color=COLORS["gray"]))

ax.set_xlabel("时间 $t$ / h")
ax.set_ylabel("含水率 / (kg·kg$^{-1}$)")
ax.set_xlim(0, t_h[-1])
ax.set_ylim(0, C_max[0] * 1.04)
ax.legend(loc="upper right", fontsize=8.3, frameon=True, framealpha=0.92)
declutter_axes(ax, grid=True, grid_axis="y")

# inset：穿越点邻域放大
axin = ax.inset_axes([0.40, 0.30, 0.32, 0.30])
m = (t_h > t_star - 4.0) & (t_h < min(t_h[-1], t_star + 1.0))
axin.plot(t_h[m], C_max[m], color=COLORS["primary"], lw=1.6)
axin.axhline(C_TH, color=COLORS["down"], lw=1.2, ls=":")
axin.axvline(t_star, color=COLORS["gray"], lw=0.9, ls=":")
axin.scatter([t_star], [C_TH], s=20, color=COLORS["down"], zorder=5)
axin.set_xlim(t_star - 4.0, min(t_h[-1], t_star + 1.0))
axin.tick_params(labelsize=8.2)
axin.set_title("首穿邻域", fontsize=8.2, pad=2)
ax.indicate_inset_zoom(axin, edgecolor=COLORS["gray"], lw=0.8, alpha=0.8)

finish(fig, "fig_drying_curve.pdf")
