# -*- coding: utf-8 -*-
"""图19 收缩假设独立检验：干骨架体积比反推的终态半径 vs 附件2 实测。"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _figbase import *  # noqa: F401,F403
import numpy as np
import params as P
from matplotlib.lines import Line2D

# 独立于 PDE：仅用附录4 密度式 rho=760+90C 与干物质守恒
C0, Cth = P.C0, P.C_TH
rho_dry = lambda C: (P.RHO_A4_A + P.RHO_A4_B * C) / (1.0 + C)   # 干骨架密度
V_ratio = rho_dry(C0) / rho_dry(0.0)          # V_inf / V_0
R0_cm = P.R0 / P.CM_TO_M

R_radial = R0_cm * np.sqrt(V_ratio)           # 纯径向收缩
R_iso = R0_cm * V_ratio ** (1.0 / 3.0)        # 各向同性收缩

df = user_xlsx("附件2.xlsx")
R_meas = float(df["半径"].to_numpy(dtype=float)[-1])
t_meas = df["时间"].to_numpy(dtype=float) / 3600.0
R_series = df["半径"].to_numpy(dtype=float)

e_radial = abs(R_radial - R_meas) / R_meas * 100.0
e_iso = abs(R_iso - R_meas) / R_meas * 100.0

fig, (ax1, ax2) = panel(1, 2, height_fraction=0.48,
                        gridspec_kw={"width_ratios": [1.35, 1.0]})

# (a) 实测收缩轨迹 + 两条假设预测的终态水平线
ax1.plot(t_meas, R_series, "-", color=COLORS["primary"], lw=1.8,
         label="附件2 实测 $R(t)$")
ax1.scatter(t_meas[::12], R_series[::12], s=14, color=COLORS["accent"],
            zorder=3, edgecolor="white", linewidth=0.5)
ax1.axhline(R_radial, color=COLORS["up"], lw=1.5, ls="--",
            label=f"纯径向预测 {R_radial:.4f} cm")
ax1.axhline(R_iso, color=COLORS["down"], lw=1.5, ls="-.",
            label=f"各向同性预测 {R_iso:.4f} cm")
ax1.axhline(R_meas, color=COLORS["dark"], lw=1.0, ls=":",
            label=f"实测终态 {R_meas:.4f} cm")
ax1.set_xlabel("时间 $t$ / h")
ax1.set_ylabel("半径 $R$ / cm")
ax1.set_xlim(t_meas[0], t_meas[-1])
ax1.set_ylim(min(R_meas, R_radial) - 0.10, R0_cm + 0.12)
ax1.legend(loc="upper right", frameon=True, framealpha=0.92)
declutter_axes(ax1, grid=True, grid_axis="y")

# (b) 偏差对比
xb = np.arange(2)
errs = np.array([e_radial, e_iso])
bars = ax2.bar(xb, errs, width=0.52, color=[COLORS["up"], COLORS["down"]],
               alpha=0.88, edgecolor=COLORS["dark"], linewidth=0.6, zorder=3)
for b, e in zip(bars, errs):
    ax2.annotate(f"{e:.2f}%", xy=(b.get_x() + b.get_width() / 2, e),
                 xytext=(0, 3), textcoords="offset points", ha="center", color=COLORS["dark"])
ax2.set_xticks(xb)
ax2.set_xticklabels(["纯径向", "各向同性"])
ax2.set_ylabel("相对实测偏差 / %")
ax2.set_ylim(0, errs.max() * 1.22)
vr = Line2D([], [], ls="none", label=f"$V_\\infty/V_0$={V_ratio:.4f}")
ax2.legend(handles=[vr], loc="upper left", frameon=True,
           framealpha=0.92)
declutter_axes(ax2, grid=True, grid_axis="y")

label_panels([ax1, ax2], ["(a) 收缩轨迹与预测终态", "(b) 假设偏差"])
finish(fig, "fig_shrink_evidence.pdf")
