# -*- coding: utf-8 -*-
"""图8 问题3 含水率时空三维曲面 + 达标阈值平面。"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _figbase import *  # noqa: F401,F403
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

t_h, r_cm, C = field_matrix("result3.xlsx", "Sheet1")
stride = max(1, C.shape[0] // 90)
ts, Cs = t_h[::stride], C[::stride]
RR, TT = np.meshgrid(r_cm, ts)

fig = plt.figure(figsize=native_figsize(1.0, 0.66))
ax = fig.add_subplot(111, projection="3d")
surf = ax.plot_surface(RR, TT, Cs, cmap="YlGnBu", linewidth=0.15,
                       edgecolor=COLORS["dark"], antialiased=True,
                       rstride=1, cstride=1, alpha=0.94)

# 阈值平面
ax.plot_surface(RR, TT, np.full_like(Cs, C_TH), color=COLORS["down"],
                alpha=0.20, linewidth=0, shade=False)
ax.contour(RR, TT, Cs, levels=[C_TH], colors=[COLORS["down"]],
           linewidths=1.8, offset=C_TH)

t_star = results("p3")["p3_t_star_h"]
ax.set_xlabel("$r$ / cm", labelpad=6)
ax.set_ylabel("$t$ / h", labelpad=6)
ax.set_zlabel("$C$ / (kg·kg$^{-1}$)", labelpad=4)
ax.set_xlim(r_cm[0], r_cm[-1])
ax.set_ylim(ts[0], ts[-1])
ax.set_xticks([0.0, 0.5, 1.0, 1.5, 2.0])
ax.view_init(elev=24, azim=-131)
ax.tick_params(labelsize=8.2, pad=1.5)
ax.text2D(0.02, 0.92, f"阈值面 $C$=0.15，$t^*$={t_star:.2f} h",
          transform=ax.transAxes, fontsize=8.4, color=COLORS["dark"])

cb = fig.colorbar(surf, ax=ax, pad=0.09, shrink=0.68)
cb.set_label("含水率 / (kg·kg$^{-1}$)", fontsize=8.2)
cb.ax.tick_params(labelsize=8.2)

set_paper_placement(fig, 1.0, height_fraction=0.88)
fit_layout(fig)
save_fig(fig, os.path.join(HERE, "fig_surface_3d.pdf"))
plt.close(fig)
print("OK fig_surface_3d.pdf")
