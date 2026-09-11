# -*- coding: utf-8 -*-
"""派生绘图数据：时间步长收敛序列、Bessel 逐点对照、Biot 数轨迹。

结果写入 figures/_plot_data.json，供 fig_convergence / fig_analytic_validation
/ fig_biot_regime 使用。所有物性取 code/params.py（PROBLEM_FACTS.json 权威值）。
"""
from __future__ import annotations
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "code"))

import params as P          # noqa: E402
import utils                # noqa: E402

T_CAP_P3 = 400.0 * P.H_TO_S
OUT = os.path.join(HERE, "_plot_data.json")


def temporal_convergence(env):
    """t* 对时间步长的收敛：dt=240/120/60/30 s，以最细为参考解。"""
    dts = [240.0, 120.0, 60.0, 30.0]
    ts = {}
    for dt in dts:
        r = utils.solve_coupled(utils.PROPS_P23, T_CAP_P3, dt, env,
                               mode="hold", endpoint_stop=True)
        ts[dt] = float(r["t_star_h"])
        print(f"  dt={dt:6.1f} s  t*={ts[dt]:.6f} h")
    ref = ts[dts[-1]]
    err = {dt: abs(ts[dt] - ref) for dt in dts[:-1]}
    # Richardson 观测阶（相邻两次加倍细化）
    e1, e2 = err[dts[0]], err[dts[1]]
    order = float(np.log(e1 / e2) / np.log(2.0)) if e2 > 0 else float("nan")
    return {
        "dt_s": dts,
        "t_star_h": [ts[d] for d in dts],
        "abs_err_h": [err.get(d, 0.0) for d in dts],
        "ref_t_star_h": ref,
        "observed_order_p": order,
    }


def bessel_pointwise(D_const=5e-9, t_end=3600.0, dt=1.0, C0=2.55, Cair=0.05,
                     n_roots=60, M=P.M_GRID):
    """常物性退化算例：FVM 逐点值 vs Bessel 级数解析值（排除表面节点）。"""
    props = utils.Properties(P.rho_a2, P.cp_a2, P.k_a2, D_const, 0.0, 0.0)
    env = utils.const_env(P.T0, Cair, t_end)
    r = utils.solve_coupled(props, t_end, dt, env, mode="hold", R0=P.R0,
                            C0=C0, T0=P.T0, M=M, record_full=True,
                            interface="arithmetic")
    C_num = np.asarray(r["C_hist"][-1], dtype=float)
    xi = np.linspace(0.0, 1.0, M + 1)
    Bi = P.HM_CONV * P.R0 / D_const
    Fo = D_const * t_end / (P.R0 * P.R0)
    C_ana = Cair + (C0 - Cair) * utils.bessel_series_solution(xi, Fo, Bi, n_roots)
    interior = slice(0, M)
    num, ana = C_num[interior], C_ana[interior]
    resid = num - ana
    ss_res = float(np.sum(resid ** 2))
    ss_tot = float(np.sum((ana - ana.mean()) ** 2))
    return {
        "xi": xi[interior].tolist(),
        "r_cm": (xi[interior] * P.R0 * 100.0).tolist(),
        "C_numeric": num.tolist(),
        "C_analytic": ana.tolist(),
        "residual": resid.tolist(),
        "Bi": float(Bi), "Fo": float(Fo),
        "D_const": float(D_const), "t_end_s": float(t_end),
        "n_points": int(num.size),
        "max_abs_err": float(np.abs(resid).max()),
        "rel_err_l2": float(np.linalg.norm(resid) / np.linalg.norm(ana)),
        "r_squared": float(1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan"),
        "rmse": float(np.sqrt(ss_res / num.size)),
    }


def biot_trace(env):
    """P3 全历史的传质/传热 Biot 数与 Fourier 数轨迹（需温度场）。"""
    r = utils.solve_coupled(utils.PROPS_P23, T_CAP_P3, P.DT_P34, env,
                            mode="hold", endpoint_stop=True, record_full=True)
    props = utils.PROPS_P23
    t = np.asarray(r["t"], dtype=float)
    grid = r["grid"]
    w = grid["w_j"]
    Bi_m, Bi_h, D_surf, D_bar, Cbar, Tbar, Csurf, Tsurf = ([] for _ in range(8))
    for C, T in zip(r["C_hist"], r["T_hist"]):
        C = np.asarray(C, dtype=float)
        T = np.asarray(T, dtype=float)
        Cc = np.maximum(C, P.CFLOOR)
        D_node = (props.d_pre * utils.arrhenius_factor(T, props.arr_T)
                  * np.exp(-props.d_exp / Cc))
        k_node = props.k(C)
        Ds = float(D_node[-1])
        D_surf.append(Ds)
        D_bar.append(float(np.sum(w * D_node)))
        Bi_m.append(float(P.HM_CONV * P.R0 / Ds))
        Bi_h.append(float(P.H_CONV * P.R0 / k_node[-1]))
        Cbar.append(float(np.sum(w * C)))
        Tbar.append(float(np.sum(w * T)))
        Csurf.append(float(C[-1]))
        Tsurf.append(float(T[-1]))
    D_bar_arr = np.asarray(D_bar)
    Fo = D_bar_arr * t / (P.R0 * P.R0)
    return {
        "t_h": (t / P.H_TO_S).tolist(),
        "Bi_mass": Bi_m,
        "Bi_heat": Bi_h,
        "D_surface": D_surf,
        "D_volavg": D_bar,
        "Fo_mass": Fo.tolist(),
        "C_mean": Cbar,
        "C_surface": Csurf,
        "T_mean": Tbar,
        "T_surface": Tsurf,
        "t_star_h": float(r["t_star_h"]),
        "n_samples": int(t.size),
        "Bi_mass_min": float(np.min(Bi_m)),
        "Bi_mass_max": float(np.max(Bi_m)),
        "Bi_heat_min": float(np.min(Bi_h)),
        "Bi_heat_max": float(np.max(Bi_h)),
    }


def p3_temperature_field(env):
    """P3 温度场（result3.xlsx 只存水分，热力图/剖面图需要它）。"""
    r = utils.solve_coupled(utils.PROPS_P23, T_CAP_P3, P.DT_P34, env,
                            mode="hold", endpoint_stop=True, record_full=True)
    t = np.asarray(r["t"], dtype=float)
    stride = max(1, int(t.size // 400))
    idx = list(range(0, t.size, stride))
    if idx[-1] != t.size - 1:
        idx.append(t.size - 1)
    T = np.array([np.asarray(r["T_hist"][i], dtype=float) for i in idx])
    return {
        "t_h": (t[idx] / P.H_TO_S).tolist(),
        "xi": np.linspace(0.0, 1.0, T.shape[1]).tolist(),
        "r_cm": (np.linspace(0.0, 1.0, T.shape[1]) * P.R0 * 100.0).tolist(),
        "T": T.tolist(),
        "stride": stride,
    }


def main():
    env = utils.load_environment()
    print("[1/4] temporal convergence ...")
    tconv = temporal_convergence(env)
    print("[2/4] Bessel pointwise ...")
    bess = bessel_pointwise()
    print("[3/4] Biot trace ...")
    biot = biot_trace(env)
    print("[4/4] P3 temperature field ...")
    tfield = p3_temperature_field(env)
    data = {
        "_source": "figures/prep_plot_data.py (imports code/params.py, code/utils.py)",
        "temporal_convergence": tconv,
        "bessel_pointwise": bess,
        "biot_trace": biot,
        "p3_temperature_field": tfield,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    print("written", OUT)
    print("  t* order_p =", tconv["observed_order_p"])
    print("  Bessel R2 =", bess["r_squared"], "rmse =", bess["rmse"])
    print("  Bi_mass range =", biot["Bi_mass_min"], biot["Bi_mass_max"])


if __name__ == "__main__":
    main()
