# -*- coding: utf-8 -*-
"""图17 传质阻力分区相图：P3 干燥历史在 (Bi_m, C_bar) 平面上的轨迹。"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _figbase import *  # noqa: F401,F403
import numpy as np
import matplotlib.pyplot as plt

b = results("plot")["biot_trace"]
Bi = np.array(b["Bi_mass"])
Cb = np.array(b["C_mean"])
th = np.array(b["t_h"])
t_star = b["t_star_h"]

fig, ax = panel(height_fraction=0.62)

# 分区背景：Bi<0.1 外部控制 / 0.1-10 混合 / >10 内部控制
xlo, xhi = log_floor(Bi, frac=0.5), Bi.max() * 2.2
ylo, yhi = 0.0, Cb.max() * 1.30
bands = [(xlo, 0.1, COLORS["bg_fill"], "外部对流控制"),
         (0.1, 10.0, COLORS["bg_fill2"], "混合控制"),
         (10.0, xhi, COLORS["light"], "内部扩散控制")]
for x0, x1, col, lab in bands:
    if x1 <= xlo or x0 >= xhi:
        continue
    ax.axvspan(max(x0, xlo), min(x1, xhi), color=col, alpha=0.45, zorder=0)
for x in (0.1, 10.0):
    if xlo < x < xhi:
        ax.axvline(x, color=COLORS["gray"], lw=1.0, ls="--", zorder=1)

for x0, x1, col, lab in bands:
    xa, xb = max(x0, xlo), min(x1, xhi)
    if xb <= xa:
        continue
    xm = np.sqrt(xa * xb)
    ax.text(xm, yhi * 0.965, cn(lab), ha="center", va="top", fontsize=8.0,
            color=COLORS["dark"], zorder=4)

# 轨迹：按时间着色
pts = np.column_stack([Bi, Cb])
sc = ax.scatter(Bi, Cb, c=th, cmap="plasma", s=7, zorder=3, linewidth=0)
ax.plot(Bi, Cb, color=COLORS["dark"], lw=0.7, alpha=0.45, zorder=2)

# 起点、阈值点标注
ax.scatter([Bi[0]], [Cb[0]], s=48, marker="o", color=COLORS["up"],
           edgecolor="white", linewidth=0.8, zorder=5,
           label=f"起点 $t$=0，$Bi_m$={Bi[0]:.2f}")
ax.scatter([Bi[-1]], [Cb[-1]], s=62, marker="*", color=COLORS["down"],
           edgecolor="white", linewidth=0.6, zorder=5,
           label=f"终点 $t^*$={t_star:.2f} h，$Bi_m$={Bi[-1]:.0f}")
ax.legend(loc="center left", fontsize=8.0, frameon=True, framealpha=0.92)

ax.set_xscale("log")
ax.set_xlim(xlo, xhi)
ax.set_ylim(ylo, yhi)
ax.set_xlabel("传质 Biot 数 $Bi_m=h_mR_0/D(C_s,T_s)$（对数轴）")
ax.set_ylabel("体积平均含水率 $\\bar{C}$ / (kg·kg$^{-1}$)")
cb = fig.colorbar(sc, ax=ax, pad=0.02)
cb.set_label("时间 $t$ / h", fontsize=8.5)
cb.ax.tick_params(labelsize=8.2)
declutter_axes(ax, grid=True, grid_axis="y")
finish(fig, "fig_biot_regime.pdf")
