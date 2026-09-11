# -*- coding: utf-8 -*-
"""图11b 阶段速率：问题3 中心含水率每 6 h 降幅（柱）与剩余含水率（折线）。"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _figbase import *  # noqa: F401,F403
import numpy as np
from matplotlib.lines import Line2D

p3 = results("p3")
marks = np.array(p3["p3_center_6h_marks_h"], dtype=float)   # 6,12,...,54
vals = np.array(p3["p3_center_6h_values"], dtype=float)     # 中心含水率

C0 = float(results("p1")["p1_C_1800_5pt"][0])   # 2.55，初值锚点
prev = np.concatenate(([C0], vals[:-1]))
drop = prev - vals                              # 每 6 h 降幅

x = np.arange(len(marks))
fig, ax = panel(height_fraction=0.58)
ax2 = ax.twinx()

norm = drop / drop.max()
bars = ax.bar(x, drop, width=0.66, color=COLORS["primary"],
              alpha=0.85, edgecolor=COLORS["dark"], linewidth=0.55, zorder=3)
for b, d in zip(bars, drop):
    ax.annotate(f"{d:.3f}", xy=(b.get_x() + b.get_width() / 2, d),
                xytext=(0, 3), textcoords="offset points", ha="center", color=COLORS["dark"])

lr, = ax2.plot(x, vals, "o-", color=COLORS["accent"], lw=1.6, ms=5.0,
               mec="white", mew=0.7, zorder=4, label="区间末中心含水率")
ax2.axhline(C_TH, color=COLORS["down"], lw=1.2, ls=":", zorder=2)
ax2.set_yscale("log")

ax.set_xticks(x)
ax.set_xticklabels([f"{m:.0f}" for m in marks])
ax.set_xlabel("区间终点时刻 / h（每段 6 h）")
ax.set_ylabel("本段中心含水率降幅", color=COLORS["primary"])
ax2.set_ylabel("剩余含水率（对数轴）", color=COLORS["accent"])
ax.tick_params(axis="y", colors=COLORS["primary"])
ax2.tick_params(axis="y", colors=COLORS["accent"])
ax.set_ylim(0, drop.max() * 1.20)

hb = Line2D([], [], color=COLORS["primary"], lw=6, alpha=0.85,
            label="每 6 h 降幅")
ht = Line2D([], [], color=COLORS["down"], lw=1.2, ls=":",
            label="达标阈值 0.15")
ax.legend(handles=[hb, lr, ht], loc="upper right",
          frameon=True, framealpha=0.92)
declutter_axes(ax, grid=True, grid_axis="y")
ax2.spines["top"].set_visible(False)
ax2.grid(False)
finish(fig, "fig_stage_rate.pdf")
