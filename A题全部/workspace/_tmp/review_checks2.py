# -*- coding: utf-8 -*-
"""独立复核脚本 2：守恒残差可证伪性、R(t)-Cbar 自洽性、P1 独立复算。只读。"""
import sys
import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator
from scipy.integrate import solve_ivp

sys.path.insert(0, "code")
import params as P
import utils


def sec(t):
    print("\n===== " + t + " =====", flush=True)


env = utils.load_environment()

sec("G. 守恒残差对 R(t) 正确性是否有鉴别力（可证伪性检验）")
# 真实收缩
pch_true, t_r, R_true = utils.build_radius_interp()
cases = {
    "真实 R(t) 收缩 2.0->1.198cm": (pch_true, t_r[-1]),
    "荒谬 R(t) 膨胀 2.0->4.0cm": (PchipInterpolator(
        np.array([0.0, 259200.0]), np.array([0.02, 0.04])), 259200.0),
    "荒谬 R(t) 骤缩 2.0->0.5cm": (PchipInterpolator(
        np.array([0.0, 259200.0]), np.array([0.02, 0.005])), 259200.0),
}
for name, (pch, tmax) in cases.items():
    r = utils.solve_coupled(utils.PROPS_P4, 5 * 3600.0, 60.0, env,
                            R_interp=pch, R_tmax=tmax)
    print("%-30s 守恒残差=%.3e  Cbar_end=%.6f" % (name, r["cons_residual"], r["cbar_end"]))
print("→ 若三者残差同为机器精度量级，则该残差不含 R(t) 物理正确性的信息（构造性恒等）")

sec("H. 附件2 半径平台期 vs 模型仍在脱水的时段")
R_cm = R_true / P.CM_TO_M
i_flat = int(np.argmax(R_cm <= 1.1985))
print("R 首次到达 1.198cm 平台: t=%.0f s = %.2f h" % (t_r[i_flat], t_r[i_flat] / 3600))
print("P4 模型烘干终点 t*=50.8975 h；P3 终点 57.2621 h")

sec("I. R(t) 与模型 Cbar(t) 的体积自洽性（附录4 密度式）")
d4 = pd.read_excel("result4.xlsx", sheet_name="Sheet1")
tt = d4.iloc[:, 0].to_numpy(float)
body = d4.iloc[:, 1:].to_numpy(float)
r_cols = np.array([i * 0.1 for i in range(20)])
rho4 = lambda C: 760.0 + 90.0 * C
C0 = 2.55
v_per_dry0 = (1 + C0) / rho4(C0)
print(" t/h   R_att2/cm  Cbar     R_pred/cm  偏差%")
for k in range(0, len(tt), max(1, len(tt) // 12)):
    R_now = float(pch_true(min(tt[k], t_r[-1]))) / P.CM_TO_M
    row = body[k]
    ok = ~np.isnan(row[:20])
    xi = np.concatenate([r_cols[ok] / R_now, [1.0]])
    Cv = np.concatenate([row[:20][ok], [row[20]]])
    o = np.argsort(xi)
    Cbar = 2.0 * np.trapezoid(Cv[o] * xi[o], xi[o])
    R_pred = 2.0 * np.sqrt(((1 + Cbar) / rho4(Cbar)) / v_per_dry0)
    print("%5.1f  %8.4f  %7.4f  %8.4f  %+7.2f"
          % (tt[k] / 3600, R_now, Cbar, R_pred, (R_pred - R_now) / R_now * 100))

sec("J. 被抵消掉的映射漂移项量级（Pe = |Rdot| R / D）")
for th in [0.5, 2, 6, 12, 24, 48]:
    ts = th * 3600.0
    Rn = float(pch_true(min(ts, t_r[-1])))
    Rd = float(pch_true.derivative()(min(ts, t_r[-1])))
    k = int(np.argmin(np.abs(tt - ts)))
    row = body[k]
    Cmid = np.nanmean(row[:20])
    D = P.D_PRE_A4 * np.exp(-P.D_EXP_A4 / max(Cmid, 1e-6)) * np.exp(-P.ARR_T / (50 + 273.15))
    print("t=%5.1fh  R=%.5fm  Rdot=%+.3e m/s  C~%.3f  D=%.3e  Pe=%.2f"
          % (th, Rn, Rd, Cmid, D, abs(Rd) * Rn / D))
print("→ Pe>>1 说明被『解析抵消』的漂移项在早期是主导项，抵消是否精确非常关键")

sec("K. P1 独立复算（物理坐标 + Radau，独立实现）")
N = 101
R0 = P.R0
r = np.linspace(0.0, R0, N)
dr = r[1] - r[0]
r_half = 0.5 * (r[:-1] + r[1:])
r_faces = np.concatenate(([0.0], r_half, [R0]))
Vol = 0.5 * (r_faces[1:] ** 2 - r_faces[:-1] ** 2)
tE, TaE, CaE = env
D_of = lambda C: 7e-9 * np.exp(-0.89 / np.maximum(C, 1e-8))


def rhs(t, y):
    T, C = y[:N], y[N:]
    Tair = np.interp(t, tE, TaE)
    Cair = np.interp(t, tE, CaE)
    Dn = D_of(C)
    Df = 0.5 * (Dn[:-1] + Dn[1:])
    fC = r_half * Df * (C[1:] - C[:-1]) / dr
    fT = r_half * 0.36 * (T[1:] - T[:-1]) / dr
    dC = np.zeros(N)
    dT = np.zeros(N)
    dC[1:-1] = (fC[1:] - fC[:-1]) / Vol[1:-1]
    dT[1:-1] = (fT[1:] - fT[:-1]) / Vol[1:-1]
    dC[0] = fC[0] / Vol[0]
    dT[0] = fT[0] / Vol[0]
    dC[-1] = (-fC[-1] - R0 * 8e-7 * (C[-1] - Cair)) / Vol[-1]
    dT[-1] = (-fT[-1] - R0 * 25.0 * (T[-1] - Tair)) / Vol[-1]
    return np.concatenate([dT / (820.0 * 2600.0), dC])


y0 = np.concatenate([np.full(N, 28.0), np.full(N, 2.55)])
sol = solve_ivp(rhs, (0, 1800), y0, method="Radau", t_eval=[1800.0],
                rtol=1e-10, atol=1e-12)
Tn, Cn = sol.y[:N, -1], sol.y[N:, -1]
d1t = pd.read_excel("result1.xlsx", sheet_name="温度")
d1c = pd.read_excel("result1.xlsx", sheet_name="水分浓度")
print("r/cm  T_indep   T_result1   dT    | C_indep   C_result1   dC")
for rc in [0.0, 0.5, 1.0, 1.5, 2.0]:
    ti = np.interp(rc * 0.01, r, Tn)
    ci = np.interp(rc * 0.01, r, Cn)
    col = "%.1f" % rc
    tr = float(d1t[col].iloc[-1])
    cr = float(d1c[col].iloc[-1])
    print("%4.1f  %8.4f  %8.4f  %+.4f | %8.4f  %8.4f  %+.5f"
          % (rc, ti, tr, ti - tr, ci, cr, ci - cr))
