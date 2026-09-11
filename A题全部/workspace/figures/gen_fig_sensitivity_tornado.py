# -*- coding: utf-8 -*-
"""图15 龙卷风图：各假设扰动对 t* 的相对影响（P3/P4 并列）。"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _figbase import *  # noqa: F401,F403
import numpy as np

s = results("sens")
allr = results("all")
p3 = results("p3")

t_p3 = s["p3_hold_h"]
t_p4 = s["p4_hold_h"]

# 每项：名称, 负向变化%, 正向变化%, 适用问题
iface = p3["p3_interface_t_star_h"]
d_arith = (iface["arithmetic"] - t_p3) / t_p3 * 100.0
d_domain = (allr["t_star_fixed_domain_p4_hours"] - t_p4) / t_p4 * 100.0
d_latent = s["p3_latent_rel_pct"]

rows = [
    ("H7 固定域退化\n（省略动边界）", 0.0, d_domain),
    ("H4 蒸发潜热\n（$L$=2.4 MJ·kg$^{-1}$）", 0.0, d_latent),
    ("M3 界面平均\n（Kirchhoff→算术）", d_arith, 0.0),
    ("H3 环境外推\n（P3 hold→mean/linear）",
     s["p3_linear_rel_pct"], s["p3_mean_rel_pct"]),
    ("H3 环境外推\n（P4 hold→mean/linear）",
     s["p4_linear_rel_pct"], s["p4_mean_rel_pct"]),
]
rows.sort(key=lambda r: max(abs(r[1]), abs(r[2])))

names = [r[0] for r in rows]
neg = np.array([r[1] for r in rows])
pos = np.array([r[2] for r in rows])
y = np.arange(len(rows))

fig, ax = panel(height_fraction=0.64, width_fraction=0.96)
ax.barh(y, pos, height=0.56, color=COLORS["up"], alpha=0.88,
        edgecolor=COLORS["dark"], linewidth=0.55, label="使 $t^*$ 增大", zorder=3)
ax.barh(y, neg, height=0.56, color=COLORS["down"], alpha=0.88,
        edgecolor=COLORS["dark"], linewidth=0.55, label="使 $t^*$ 减小", zorder=3)
ax.axvline(0.0, color=COLORS["dark"], lw=1.0, zorder=4)

span = max(abs(neg).max(), abs(pos).max())
for yi, (n_, p_) in enumerate(zip(neg, pos)):
    if abs(p_) > 1e-9:
        ax.text(p_ + span * 0.02, yi, f"{p_:+.2f}%", va="center",
                fontsize=8.0, color=COLORS["dark"])
    if abs(n_) > 1e-9:
        ax.text(n_ - span * 0.02, yi, f"{n_:+.2f}%", va="center", ha="right",
                fontsize=8.0, color=COLORS["dark"])

ax.set_yticks(y)
ax.set_yticklabels(names, fontsize=8.0)
ax.set_xlabel("$t^*$ 相对变化 / %")
ax.set_xlim(min(neg.min() * 1.35, -span * 0.30), span * 1.30)
ax.set_ylim(-0.6, len(rows) - 0.4)
ax.legend(loc="lower right", fontsize=8.0, frameon=True, framealpha=0.92)
declutter_axes(ax, grid=True, grid_axis="x")
finish(fig, "fig_sensitivity_tornado.pdf")
