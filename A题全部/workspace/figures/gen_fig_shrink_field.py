# -*- coding: utf-8 -*-
"""图11 问题4 收缩域场图：物理半径坐标下的含水率演化与移动边界。"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _figbase import *  # noqa: F401,F403
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import PchipInterpolator

t_h, r_out, C = field_matrix("result4.xlsx", "Sheet1")
p4 = results("p4")
t_star = p4["p4_t_star_h"]
R_star = p4["p4_R_tstar_cm"]

# 附件2 的半径历史（PCHIP），把 ξ=r/R 网格还原到物理半径
dfa = user_xlsx("附件2.xlsx")
ta = dfa["时间"].to_numpy(dtype=float) / 3600.0
Ra = dfa["半径"].to_numpy(dtype=float)
pch = PchipInterpolator(ta, Ra)
R_t = np.clip(pch(np.clip(t_h, ta[0], ta[-1])), Ra.min(), Ra.max())

xi = r_out / r_out[-1]
stride = max(1, C.shape[0] // 450)
ii = np.arange(0, C.shape[0], stride)
if ii[-1] != C.shape[0] - 1:
    ii = np.append(ii, C.shape[0] - 1)

# 物理坐标网格：每行的 r 上界随 R(t) 收缩
Rphys = np.outer(R_t[ii], xi)
Tgrid = np.repeat(t_h[ii][:, None], xi.size, axis=1)

fig, ax = panel(height_fraction=0.64)
pm = ax.pcolormesh(Rphys, Tgrid, C[ii], cmap="YlGnBu", shading="nearest",
                   rasterized=True)
ax.plot(R_t[ii], t_h[ii], color=COLORS["down"], lw=2.0, label="移动边界 $R(t)$")
ax.fill_betweenx(t_h[ii], R_t[ii], r_out[-1] * 1.02, color=COLORS["light"],
                 alpha=0.55, lw=0, zorder=1)
ax.axhline(t_star, color=COLORS["dark"], lw=1.1, ls="--")
ax.annotate(f"$t^*$={t_star:.2f} h，$R(t^*)$={R_star:.2f} cm",
            xy=(R_star, t_star), xytext=(0.28, t_star + 5.5),
            fontsize=8.4, color=COLORS["dark"],
            arrowprops=dict(arrowstyle="->", lw=0.85, color=COLORS["gray"]))
ax.text(1.62, t_h[ii][-1] * 0.20, "已收缩\n（无物料）", fontsize=8,
        color=COLORS["gray"], ha="center")

ax.set_xlabel("物理径向位置 $r$ / cm")
ax.set_ylabel("时间 $t$ / h")
ax.set_xlim(0, r_out[-1] * 1.02)
ax.set_ylim(0, t_h[ii][-1])
ax.legend(loc="upper right", fontsize=8.3, frameon=True, framealpha=0.92)
cb = fig.colorbar(pm, ax=ax, pad=0.02)
cb.set_label("含水率 / (kg·kg$^{-1}$)", fontsize=8.5)
cb.ax.tick_params(labelsize=8.2)

finish(fig, "fig_shrink_field.pdf")
