# -*- coding: utf-8 -*-
"""图6 问题2 Hovmöller 图：含水率时空演化 + 边缘剖面（result2.xlsx, 0-3 h）。"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _figbase import *  # noqa: F401,F403
import numpy as np
import matplotlib.gridspec as gridspec
import matplotlib.ticker as mticker
import matplotlib.pyplot as plt

t_h, r_cm, C = field_matrix("result2.xlsx", "水分浓度")
t_hT, _, T = field_matrix("result2.xlsx", "温度")

stride = max(1, C.shape[0] // 600)
t_s, C_s = t_h[::stride], C[::stride]

fig = plt.figure(figsize=native_figsize(1.0, 0.62))
gs = gridspec.GridSpec(2, 2, figure=fig, width_ratios=[3.0, 1.0],
                       height_ratios=[1.0, 3.0], wspace=0.06, hspace=0.08)
axm = fig.add_subplot(gs[1, 0])
axt = fig.add_subplot(gs[0, 0], sharex=axm)
axr = fig.add_subplot(gs[1, 1], sharey=axm)

pm = axm.pcolormesh(r_cm, t_s, C_s, cmap="YlGnBu", shading="auto",
                    rasterized=True)
cs = axm.contour(r_cm, t_s, C_s, levels=6, colors=COLORS["dark"],
                 linewidths=0.55, alpha=0.55)
axm.clabel(cs, inline=True, fontsize=8.2, fmt="%.2f")
axm.set_xlabel("径向位置 $r$ / cm")
axm.set_ylabel("时间 $t$ / h")
axm.set_xlim(r_cm[0], r_cm[-1])
axm.set_ylim(t_s[0], t_s[-1])

# 顶：终态径向剖面；右：中心/表面时间轨迹
axt.plot(r_cm, C[-1], color=COLORS["primary"], lw=1.6)
axt.fill_between(r_cm, C[-1], C[-1].min(), color=COLORS["primary"], alpha=0.15)
axt.set_ylabel("3 h 剖面", fontsize=8.2)
axt.tick_params(labelbottom=False, labelsize=8.2)
axt.yaxis.set_major_locator(mticker.MaxNLocator(3))
declutter_axes(axt, grid=True, grid_axis="y")

lc, = axr.plot(C[:, 0], t_h, color=COLORS["secondary"], lw=1.5, label="中心")
ls_, = axr.plot(C[:, -1], t_h, color=COLORS["accent"], lw=1.5, ls="--",
                label="表面")
axr.tick_params(labelleft=False, labelsize=8.2)
axr.set_xlabel("$C$", fontsize=8.2)
axr.xaxis.set_major_locator(mticker.MaxNLocator(3))
declutter_axes(axr, grid=True, grid_axis="x")

# 右上空白格作为图例专用位，避免遮挡数据
axl = fig.add_subplot(gs[0, 1])
axl.axis("off")
axl.legend(handles=[lc, ls_], loc="center", fontsize=8.2, frameon=False)

cb = fig.colorbar(pm, ax=[axm, axt, axr, axl], pad=0.02, fraction=0.045)
cb.set_label("含水率 / (kg·kg$^{-1}$)", fontsize=8.2)
cb.ax.tick_params(labelsize=8.2)

set_paper_placement(fig, 1.0, height_fraction=0.88)
fit_layout(fig)
save_fig(fig, os.path.join(HERE, "fig_field_heatmap_p2.pdf"))
plt.close(fig)
print("OK fig_field_heatmap_p2.pdf")
