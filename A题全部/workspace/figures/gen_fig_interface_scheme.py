# -*- coding: utf-8 -*-
"""图17 界面平均方式对照：断轴柱状 t* 与界面 D̂ 径向分布。"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _figbase import *  # noqa: F401,F403
import numpy as np
import matplotlib.gridspec as gridspec
import matplotlib.ticker as mticker
import params as P
import utils

iface = results("p3")["p3_interface_t_star_h"]
keys = ["kirchhoff", "arithmetic", "harmonic"]
names = ["Kirchhoff", "算术", "调和"]
vals = np.array([iface[k] for k in keys], dtype=float)
cols = [COLORS["up"], COLORS["primary"], COLORS["down"]]
styles = ["-", "--", "-."]

# 界面 D̂：取 P3 干燥中期的真实 (C,T) 节点剖面
t_h, r_cm, C = field_matrix("result3.xlsx", "Sheet1")
pt = results("plot")["p3_temperature_field"]
Tf = np.asarray(pt["T"], dtype=float)
t_T = np.asarray(pt["t_h"], dtype=float)
j = int(np.argmin(np.abs(t_h - 12.0)))
jT = int(np.argmin(np.abs(t_T - t_h[j])))
Cp, Tp = C[j], Tf[jT]

props = utils.PROPS_P23
Cc = np.maximum(Cp, P.CFLOOR)
D_node = props.d_pre * utils.arrhenius_factor(Tp, props.arr_T) \
    * np.exp(-props.d_exp / Cc)
DL, DR = D_node[:-1], D_node[1:]
D_hat = [utils.interface_diffusivity(Cp, Tp, props),
         0.5 * (DL + DR),
         2.0 * DL * DR / (DL + DR)]
r_face = 0.5 * (r_cm[:-1] + r_cm[1:])

fig = plt.figure(figsize=native_figsize(1.0, 0.56))
gs = gridspec.GridSpec(2, 2, figure=fig, width_ratios=[1.0, 1.15],
                       height_ratios=[1.0, 1.9], hspace=0.10, wspace=0.58)
axl = fig.add_subplot(gs[0, 0])
axu = fig.add_subplot(gs[1, 0])
axd = fig.add_subplot(gs[:, 1])

x = np.arange(3)
for ax in (axl, axu):
    ax.bar(x, vals, width=0.58, color=cols, alpha=0.88,
           edgecolor=COLORS["dark"], linewidth=0.6, zorder=3)

axu.set_ylim(0, 78)
axl.set_ylim(520, 600)
axl.spines["bottom"].set_visible(False)
axu.spines["top"].set_visible(False)
axl.tick_params(bottom=False, labelbottom=False)

for xi, v in zip(x, vals):
    ax = axl if v > 100 else axu
    ax.annotate(f"{v:.1f}", xy=(xi, v), xytext=(0, 3),
                textcoords="offset points", ha="center", color=COLORS["dark"],
                zorder=4)

d = 0.016
kw = dict(transform=axl.transAxes, color=COLORS["gray"], clip_on=False, lw=1.0)
axl.plot((-d, +d), (-d * 2.4, +d * 2.4), **kw)
axl.plot((1 - d, 1 + d), (-d * 2.4, +d * 2.4), **kw)
kw.update(transform=axu.transAxes)
axu.plot((-d, +d), (1 - d * 1.3, 1 + d * 1.3), **kw)
axu.plot((1 - d, 1 + d), (1 - d * 1.3, 1 + d * 1.3), **kw)

axu.set_xticks(x)
axu.set_xticklabels(names)
axu.set_ylabel("达标时刻 $t^*$ / h")
declutter_axes(axu, grid=True, grid_axis="y")
declutter_axes(axl, grid=True, grid_axis="y")

for k, (nm, col, st) in enumerate(zip(names, cols, styles)):
    axd.semilogy(r_face, D_hat[k], st, color=col, lw=1.7, label=nm)
axd.set_xlabel("界面径向位置 $r$ / cm")
axd.set_ylabel("界面 $\\hat{D}$ / (m$^2$·s$^{-1}$)")
axd.set_xlim(0, r_cm[-1])
axd.yaxis.set_major_locator(mticker.LogLocator(base=10.0, numticks=6))
axd.yaxis.set_minor_locator(mticker.NullLocator())
axd.legend(loc="lower left", frameon=True, framealpha=0.92,
           title="12 h 剖面")
declutter_axes(axd, grid=True, grid_axis="y")

label_panels([axl, axd], ["(a) 达标时刻（断轴）", "(b) 界面扩散系数"])
set_paper_placement(fig, 1.0, height_fraction=0.88)
# tight_layout 与断轴的 clip_on=False 标记不兼容（会静默放弃），故显式留边
gs.update(left=0.115, right=0.985, top=0.90, bottom=0.145)
save_fig(fig, os.path.join(HERE, "fig_interface_scheme.pdf"))
plt.close(fig)
print("OK fig_interface_scheme.pdf")
