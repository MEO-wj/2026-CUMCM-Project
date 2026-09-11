# -*- coding: utf-8 -*-
"""图13 收敛性验证：空间网格 Richardson 收敛阶与时间步长收敛（双对数）。"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _figbase import *  # noqa: F401,F403
import numpy as np

p3 = results("p3")
pd_ = results("plot")["temporal_convergence"]

# (a) 空间：M=20/40/80，以 M=80 为参考
sp = p3["p3_spatial_t_star_h"]
Ms = np.array(sorted(int(k) for k in sp))
ts_sp = np.array([sp[str(m)] for m in Ms])
ref_sp = ts_sp[-1]
h = 1.0 / Ms
err_sp = np.abs(ts_sp - ref_sp)
order_sp = p3["p3_spatial_order_p"]

# (b) 时间：dt=240/120/60，以 dt=30 为参考
dts = np.array(pd_["dt_s"][:-1], dtype=float)
err_dt = np.array(pd_["abs_err_h"][:-1], dtype=float)
order_dt = pd_["observed_order_p"]

fig, (ax1, ax2) = panel(1, 2, height_fraction=0.46)

def _slope_guide(ax, x, y, p, color, txt):
    x0, y0 = x[0], y[0]
    xg = np.array([x.min(), x.max()])
    ax.plot(xg, y0 * (xg / x0) ** p, ls="--", lw=1.1, color=color, alpha=0.85,
            label=txt)

m = err_sp > 0
ax1.loglog(h[m], err_sp[m], "o-", color=COLORS["primary"], lw=1.7, ms=5.5,
           mec="white", mew=0.7, label="$|t^*(M)-t^*(80)|$")
_slope_guide(ax1, h[m], err_sp[m], 2.0, COLORS["gray"], "二阶参考斜率")
ax1.set_xticks(h[m])
ax1.set_xticklabels([str(mm) for mm in Ms[m]])
ax1.minorticks_off()
ax1.set_xlabel("网格数 $M$（$h=1/M$）")
ax1.set_ylabel("$t^*$ 绝对误差 / h")
ax1.text(0.04, 0.06, f"观测阶 $p$={order_sp:.3f}", transform=ax1.transAxes,
         fontsize=8.6, color=COLORS["dark"])
ax1.legend(loc="upper left", fontsize=8.2, frameon=True, framealpha=0.9)
declutter_axes(ax1, grid=True, grid_axis="both")

ax2.loglog(dts, err_dt, "s-", color=COLORS["secondary"], lw=1.7, ms=5.5,
           mec="white", mew=0.7, label="$|t^*(\\Delta t)-t^*(30\\,\\mathrm{s})|$")
_slope_guide(ax2, dts, err_dt, 1.0, COLORS["gray"], "一阶参考斜率")
ax2.axvline(60.0, color=COLORS["accent"], lw=1.2, ls=":",
            label="主算步长 60 s")
ax2.set_xticks(dts)
ax2.set_xticklabels([f"{d:.0f}" for d in dts])
ax2.minorticks_off()
ax2.set_xlabel("时间步长 $\\Delta t$ / s")
ax2.set_ylabel("$t^*$ 绝对误差 / h")
ax2.text(0.04, 0.06, f"观测阶 $p$={order_dt:.3f}", transform=ax2.transAxes,
         fontsize=8.6, color=COLORS["dark"])
ax2.legend(loc="upper left", fontsize=8.2, frameon=True, framealpha=0.9)
declutter_axes(ax2, grid=True, grid_axis="both")

label_panels([ax1, ax2], ["(a) 空间收敛", "(b) 时间收敛"])
finish(fig, "fig_convergence.pdf")
