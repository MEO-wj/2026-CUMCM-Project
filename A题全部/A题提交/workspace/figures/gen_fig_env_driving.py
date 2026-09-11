# -*- coding: utf-8 -*-
"""图1 环境驱动条件：附件1 热风温度与空气含湿量双轴时序。"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _figbase import *  # noqa: F401,F403
import numpy as np

df = user_xlsx("附件1.xlsx")
t_h = df["时间"].to_numpy(dtype=float) / 3600.0
T = df["温度"].to_numpy(dtype=float)
C = df["水分浓度"].to_numpy(dtype=float)

fig, ax = panel(height_fraction=0.52)
ax2 = ax.twinx()

l1, = ax.plot(t_h, T, color=COLORS["primary"], lw=1.9, label="热风温度 $T_a$")
l2, = ax2.plot(t_h, C, color=COLORS["secondary"], lw=1.9, ls="--",
               label="空气含湿量 $C_a$")

# 升温段 / 稳态段分界：温度达到 99% 终值处
T_final = T[-1]
i_sat = int(np.argmax(T >= 0.99 * T_final))
t_sat = t_h[i_sat]
ax.axvspan(t_h[0], t_sat, color=COLORS["bg_fill"], alpha=0.35, zorder=0)
ax.axvline(t_sat, color=COLORS["gray"], lw=1.0, ls=":", zorder=1)
ax.annotate(f"升温段 {t_sat:.2f} h", xy=(t_sat, T[i_sat]),
            xytext=(t_sat + 0.35, T.min() + 0.42 * (T.max() - T.min())),
            fontsize=8.5, color=COLORS["dark"],
            arrowprops=dict(arrowstyle="->", lw=0.8, color=COLORS["gray"]))

ax.set_xlabel("时间 $t$ / h")
ax.set_ylabel("热风温度 / ℃", color=COLORS["primary"])
ax2.set_ylabel("空气含湿量 / (kg·kg$^{-1}$)", color=COLORS["secondary"])
ax.tick_params(axis="y", colors=COLORS["primary"])
ax2.tick_params(axis="y", colors=COLORS["secondary"])
ax.set_xlim(t_h[0], t_h[-1])
declutter_axes(ax, grid=True, grid_axis="y")
ax2.grid(False)
ax.legend(handles=[l1, l2], loc="lower right", fontsize=8.5, frameon=True,
          framealpha=0.9)

finish(fig, "fig_env_driving.pdf")
