# -*- coding: utf-8 -*-
"""图6b 问题2 温度场等值线：3 h 内趋于均匀（result2.xlsx 温度表）。"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _figbase import *  # noqa: F401,F403
import numpy as np
from matplotlib.lines import Line2D

t_h, r_cm, T = field_matrix("result2.xlsx", "温度")

# 抽稀到 ~300 行，等值线足够光滑又不臃肿
st = max(1, len(t_h) // 300)
t_h, T = t_h[::st], T[::st]
RR, TT = np.meshgrid(r_cm, t_h)

span = T.max(axis=1) - T.min(axis=1)      # 每时刻全径向温差

fig, ax = panel(height_fraction=0.62)

levels = np.linspace(T.min(), T.max(), 12)
cf = ax.contourf(RR, TT, T, levels=levels, cmap="inferno", alpha=0.92)
ax.contour(RR, TT, T, levels=levels[::3], colors="white",
           linewidths=0.6, alpha=0.75)
ax.contour(RR, TT, T, levels=[49.9], colors=[COLORS["up"]], linewidths=1.9)
iso_proxy = Line2D([], [], color=COLORS["up"], lw=1.9, label="49.9 ℃ 等温线")

cb = fig.colorbar(cf, ax=ax, pad=0.02, fraction=0.046)
cb.set_label("温度 $T$ / ℃")

ax.set_xlabel("径向位置 $r$ / cm")
ax.set_ylabel("时间 $t$ / h")
ax.set_xlim(0, r_cm[-1])
ax.set_ylim(t_h[0], t_h[-1])
span_proxy = Line2D([], [], ls="none",
                    label=f"终点全径向温差 {span[-1]:.2f} K")
ax.legend(handles=[iso_proxy, span_proxy], loc="lower left",
          frameon=True, framealpha=0.94)
declutter_axes(ax, grid=False)
finish(fig, "fig_temp_contour_p2.pdf")
