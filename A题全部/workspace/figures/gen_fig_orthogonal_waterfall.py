# -*- coding: utf-8 -*-
"""图12 瀑布图：P3→P4 的 2x2 正交分解（物性效应 vs 收缩效应）。"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _figbase import *  # noqa: F401,F403
import numpy as np

allr = results("all")
t_p3 = allr["t_star_p3_hours"]            # 附录3 + 固定域
t_fix = allr["t_star_fixed_domain_p4_hours"]  # 附录4 + 固定域
t_p4 = allr["t_star_p4_hours"]            # 附录4 + 收缩域

d_prop = t_fix - t_p3
d_shrink = t_p4 - t_fix

labels = ["P3 基线\n附录3+固定域", "物性效应\n附录3→4", "收缩效应\n固定→$R(t)$",
          "P4 结果\n附录4+收缩域"]
bases = [0.0, t_p3, t_fix, 0.0]
heights = [t_p3, d_prop, d_shrink, t_p4]
kinds = ["total", "up", "down", "total"]

fig, ax = panel(height_fraction=0.6)
xs = np.arange(4)
for x, b, h, k in zip(xs, bases, heights, kinds):
    col = {"total": COLORS["primary"], "up": COLORS["up"],
           "down": COLORS["down"]}[k]
    ax.bar(x, h, bottom=b, width=0.56, color=col, alpha=0.88,
           edgecolor=COLORS["dark"], linewidth=0.6, zorder=3)

# 连接虚线
for x, (b, h) in enumerate(zip(bases[:-1], heights[:-1])):
    top = b + h
    ax.plot([x + 0.28, x + 1 - 0.28], [top, top], ls=":", lw=0.9,
            color=COLORS["gray"], zorder=2)

# 数值标注
ann = [(0, t_p3, f"{t_p3:.2f} h"),
       (1, t_fix, f"+{d_prop:.2f} h ({d_prop / t_p3 * 100:+.1f}%)"),
       (2, t_p4, f"{d_shrink:.2f} h ({d_shrink / t_fix * 100:+.1f}%)"),
       (3, t_p4, f"{t_p4:.2f} h")]
for x, ytop, txt in ann:
    if x == 2:      # 下行柱：标注放到柱底之下，避开柱体
        ax.annotate(txt, xy=(x, ytop), xytext=(0, -8),
                    textcoords="offset points", ha="center", va="top",
                    fontsize=8.3, color=COLORS["dark"], zorder=5)
    else:
        ax.annotate(txt, xy=(x, ytop), xytext=(0, 7),
                    textcoords="offset points", ha="center", va="bottom",
                    fontsize=8.3, color=COLORS["dark"], zorder=5)

net = (t_p4 - t_p3) / t_p3 * 100.0
ax.axhline(t_p3, color=COLORS["gray"], lw=0.9, ls="--", zorder=1,
           label=f"P3 基线（净差 {net:+.2f}%）")
ax.legend(loc="upper left", fontsize=8.3, frameon=True, framealpha=0.92)

ax.set_xticks(xs)
ax.set_xticklabels(labels, fontsize=8.2)
ax.set_ylabel("烘干时长 $t^*$ / h")
ax.set_ylim(0, t_fix * 1.16)
declutter_axes(ax, grid=True, grid_axis="y")
finish(fig, "fig_orthogonal_waterfall.pdf")
