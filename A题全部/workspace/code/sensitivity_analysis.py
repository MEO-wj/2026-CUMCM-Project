# -*- coding: utf-8 -*-
"""灵敏度分析：H3 环境外推方式（hold/mean/linear）、H4 表面蒸发潜热汇。

对 P3（固定域）与 P4（收缩域）在末小时外推方式变更下重算 t*，量化相对偏移；
H4 龙卷风图：P3 计入潜热 e^{-3850/T_K}·D 反馈后 t* 变化。全部真算，无编造。
导出 figures/sensitivity_results.json。
"""
from __future__ import annotations
import json
import numpy as np
import params as P
import utils

JSON_OUT = P.FIG_DIR / "sensitivity_results.json"
T_CAP_P3 = 400.0 * P.H_TO_S
T_CAP_P4 = 80.0 * P.H_TO_S
T_CAP_LAT = 200.0 * P.H_TO_S


def _tstar_p3(env, mode, latent=0.0):
    r = utils.solve_coupled(utils.PROPS_P23, T_CAP_LAT if latent else T_CAP_P3,
                            P.DT_P34, env, mode=mode, latent=latent,
                            endpoint_stop=True)
    return float(r["t_star_h"])


def _tstar_p4(env, mode, pchip, R_tmax):
    r = utils.solve_coupled(utils.PROPS_P4, T_CAP_P4, P.DT_P34, env, mode=mode,
                            R_interp=pchip, R_tmax=R_tmax, endpoint_stop=True)
    return float(r["t_star_h"])


def run_sensitivity(write=True):
    env = utils.load_environment()
    pchip, t_arr, _ = utils.build_radius_interp()
    R_tmax = float(t_arr[-1])

    p3_hold = _tstar_p3(env, "hold")
    p3_mean = _tstar_p3(env, "mean")
    p3_lin = _tstar_p3(env, "linear")
    p4_hold = _tstar_p4(env, "hold", pchip, R_tmax)
    p4_mean = _tstar_p4(env, "mean", pchip, R_tmax)
    p4_lin = _tstar_p4(env, "linear", pchip, R_tmax)
    p3_latent = _tstar_p3(env, "hold", latent=P.LATENT_SCENARIO)

    def rel(v, base):
        return round(100.0 * (v - base) / base, 4)

    out = {
        "module": "sensitivity",
        "p3_hold_h": round(p3_hold, 6),
        "p3_mean_h": round(p3_mean, 6),
        "p3_linear_h": round(p3_lin, 6),
        "p3_mean_rel_pct": rel(p3_mean, p3_hold),
        "p3_linear_rel_pct": rel(p3_lin, p3_hold),
        "p4_hold_h": round(p4_hold, 6),
        "p4_mean_h": round(p4_mean, 6),
        "p4_linear_h": round(p4_lin, 6),
        "p4_mean_rel_pct": rel(p4_mean, p4_hold),
        "p4_linear_rel_pct": rel(p4_lin, p4_hold),
        "p3_latent_h": round(p3_latent, 6),
        "p3_latent_rel_pct": rel(p3_latent, p3_hold),
    }
    if write:
        P.FIG_DIR.mkdir(parents=True, exist_ok=True)
        JSON_OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2),
                            encoding="utf-8")
    return out


if __name__ == "__main__":
    o = run_sensitivity()
    print("Sensitivity done:", o)
