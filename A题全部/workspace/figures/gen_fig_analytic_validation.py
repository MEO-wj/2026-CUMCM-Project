# -*- coding: utf-8 -*-
"""图16 解析解校核：Bessel 级数 vs FVM 数值解逐点散点与残差。"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _figbase import *  # noqa: F401,F403
import numpy as np

b = results("plot")["bessel_pointwise"]
ana = np.array(b["C_analytic"])
num = np.array(b["C_numeric"])
res = np.array(b["residual"])
r_cm = np.array(b["r_cm"])
n = b["n_points"]

fig, (ax1, ax2) = panel(1, 2, height_fraction=0.48)

# (a) 预测-实测散点
lo = min(ana.min(), num.min())
hi = max(ana.max(), num.max())
pad = 0.04 * (hi - lo)
ax1.plot([lo - pad, hi + pad], [lo - pad, hi + pad], ls="--", lw=1.2,
         color=COLORS["gray"], label="$y=x$ 参考线", zorder=2)
sc = ax1.scatter(ana, num, c=r_cm, cmap="viridis", s=32, zorder=3,
                 edgecolor="white", linewidth=0.5)
ax1.set_xlabel("Bessel 解析值 $C$")
ax1.set_ylabel("FVM 数值解 $C$")
ax1.set_xlim(lo - pad, hi + pad)
ax1.set_ylim(lo - pad, hi + pad)
ax1.set_aspect("equal", adjustable="box")
cb = fig.colorbar(sc, ax=ax1, pad=0.02)
cb.set_label("$r$ / cm", fontsize=8.2)
cb.ax.tick_params(labelsize=8.2)
stat = (f"$n$={n}\n$R^2$={b['r_squared']:.6f}\n"
        f"RMSE={b['rmse']:.2e}\n$L_2$={b['rel_err_l2']:.2e}")
ax1.text(0.04, 0.96, stat, transform=ax1.transAxes, fontsize=8.2,
         va="top", color=COLORS["dark"],
         bbox=dict(boxstyle="round,pad=0.3", fc=COLORS["bg_box"],
                   ec=COLORS["gray"], lw=0.5, alpha=0.9))
declutter_axes(ax1, grid=True, grid_axis="both")

# (b) 残差沿半径分布
ax2.axhline(0.0, color=COLORS["gray"], lw=1.0, ls="--", zorder=2)
ax2.plot(r_cm, res, "o-", color=COLORS["secondary"], lw=1.4, ms=4.2,
         mec="white", mew=0.6, zorder=3)
ax2.fill_between(r_cm, res, 0.0, color=COLORS["secondary"], alpha=0.16,
                 zorder=1)
rms = float(np.sqrt(np.mean(res ** 2)))
ax2.axhspan(-rms, rms, color=COLORS["light"], alpha=0.45, zorder=0,
            label=f"$\\pm$RMS = {rms:.1e}")
ax2.set_xlabel("径向位置 $r$ / cm")
ax2.set_ylabel("残差（数值$-$解析）/ (kg·kg$^{-1}$)")
ax2.set_xlim(r_cm[0], r_cm[-1])
declutter_axes(ax2, grid=True, grid_axis="y")

label_panels([ax1, ax2],
             ["(a) 逐点一致性",
              f"(b) 残差（$Bi$={b['Bi']:.2f}，$Fo$={b['Fo']:.4f}）"])
shared_legend(fig, [ax1, ax2], where="top", ncol=3)
finish(fig, "fig_analytic_validation.pdf")
