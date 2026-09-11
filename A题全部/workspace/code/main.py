# -*- coding: utf-8 -*-
"""总驱动：运行 P1--P4 + 灵敏度，汇总合同标量与方向探针，导出 all_results.json。

方向探针（logic_probes）全部由「按合同扰动重算」真算得到符号，不写死：
  bounds  —— t* 固定域上界（放开收缩→减小,sign<0）、忽略潜热下界（计入→增大,sign>0）；
  monotonic —— T_air↑ / h_m↑ / R0↑ / C0↑ 对 t* 的实测变化符号。
合同命名标量仅存于本文件（单一真源），各问 JSON 用 p1_/p2_/p3_/p4_ 前缀避免撞名冲突。
"""
from __future__ import annotations
import json
import numpy as np
import params as P
import utils
from problem1 import run_problem1
from problem2 import run_problem2
from problem3 import run_problem3
from problem4 import run_problem4
from sensitivity_analysis import run_sensitivity

JSON_OUT = P.FIG_DIR / "all_results.json"
T_CAP_P3 = 400.0 * P.H_TO_S
T_CAP_P4 = 80.0 * P.H_TO_S


def _p3_tstar(env, *, T_shift=0.0, hm_scale=1.0, R0=P.R0, C0=P.C0):
    """P3 固定域基准上做单参扰动重算，返回 t*(h)。h_m 经临时改 P.HM_CONV 实现。"""
    if T_shift != 0.0:
        t, Ta, Ca = env
        env = (t, Ta + T_shift, Ca)
    old_hm = P.HM_CONV
    try:
        if hm_scale != 1.0:
            P.HM_CONV = old_hm * hm_scale
        r = utils.solve_coupled(utils.PROPS_P23, T_CAP_P3, P.DT_P34, env,
                                mode="hold", R0=R0, C0=C0, endpoint_stop=True)
    finally:
        P.HM_CONV = old_hm
    return float(r["t_star_h"])


def _sign(x, eps=1e-9):
    return 1 if x > eps else (-1 if x < -eps else 0)


def run_all(write=True):
    env = utils.load_environment()
    o1 = run_problem1(write=write)
    o2 = run_problem2(write=write)
    o3 = run_problem3(write=write)
    o4 = run_problem4(write=write)
    sens = run_sensitivity(write=write)
    r3 = o3["_solve"]

    # ---- 方向探针①：固定域 t* 上界（P4 物性，R 固定 R0，放开收缩后应减小）----
    r_fixed = utils.solve_coupled(utils.PROPS_P4, 400.0 * P.H_TO_S, P.DT_P34,
                                  env, mode="hold", endpoint_stop=True)
    t_fixed_p4 = float(r_fixed["t_star_h"])
    t_shrink_p4 = o4["p4_t_star_h"]
    sign_bound_fixed = _sign(t_shrink_p4 - t_fixed_p4)     # 期望 <0（upper）

    # ---- 方向探针②：忽略潜热 t* 下界（计入潜热后应增大）----
    sign_bound_latent = _sign(sens["p3_latent_h"] - sens["p3_hold_h"])  # 期望 >0

    # ---- 单调探针：T_air↑ / h_m↑ / R0↑ / C0↑ 对 t* 的符号（P3 基准）----
    base = _p3_tstar(env)
    s_Tair = _sign(_p3_tstar(env, T_shift=+2.0) - base)
    s_hm = _sign(_p3_tstar(env, hm_scale=1.05) - base)
    s_R0 = _sign(_p3_tstar(env, R0=P.R0 * 1.05) - base)
    s_C0 = _sign(_p3_tstar(env, C0=P.C0 + 0.10) - base)

    logic_probes = {
        "bounds": [
            {"quantity": "t_star_fixed_domain_hours", "claim": "upper",
             "probe_delta_sign": sign_bound_fixed},
            {"quantity": "t_star_no_latent_heat_hours", "claim": "lower",
             "probe_delta_sign": sign_bound_latent},
        ],
        "monotonic": [
            {"more": "T_air_hot_air_temperature", "then": "t_star_drying_time_hours",
             "observed_sign": s_Tair, "expect_sign": -1},
            {"more": "h_m_mass_transfer_coefficient", "then": "t_star_drying_time_hours",
             "observed_sign": s_hm, "expect_sign": -1},
            {"more": "R0_initial_radius", "then": "t_star_drying_time_hours",
             "observed_sign": s_R0, "expect_sign": 1},
            {"more": "C0_initial_moisture", "then": "t_star_drying_time_hours",
             "observed_sign": s_C0, "expect_sign": 1},
        ],
    }

    picard_max = max(o1["p1_picard_residual_max"], o2["p2_picard_residual_max"],
                     o3["p3_picard_residual_max"], o4["p4_picard_residual_max"])
    cmax_at_tstar = max(o3["p3_cmax_cross"], o4["p4_cmax_cross"])
    dmeas = max(o1["p1_discrete_measure_sum_error"], o2["p2_discrete_measure_sum_error"],
                o3["p3_discrete_measure_sum_error"], o4["p4_discrete_measure_sum_error"])

    out = {
        # —— 合同 constraints_with_margin 标量（裸名，单一真源）——
        "C_max_at_t_star": cmax_at_tstar,
        "conservation_residual_p1": float(o1["p1_conservation_residual"]),
        "conservation_residual_p2": float(o2["p2_conservation_residual"]),
        "conservation_residual_p3": float(o3["p3_conservation_residual"]),
        "conservation_residual_p4": float(o4["p4_conservation_residual"]),
        "bdf_cross_check_max_abs_diff": float(o1["p1_bdf_cross_check_max_abs_diff"]),
        "picard_final_residual_max": float(picard_max),
        "discrete_measure_sum_error": float(dmeas),
        "C_surface_minus_C_air_at_t_star_p3": float(o3["p3_C_surface_minus_C_air"]),
        "spatial_convergence_order_p": float(o3["p3_spatial_order_p"]),
        "R_interp_relative_error_max": float(o4["p4_R_interp_rel_error_max"]),
        # —— 合同 equivalence_claims 标量 ——
        "t_star_p4_hours": float(o4["p4_t_star_h"]),
        "t_star_p4_hours_pchip_vs_denser_output": float(o4["p4_t_star_dense_h"]),
        "Cbar_change_p3": float(r3["cbar0"] - r3["cbar_end"]),
        "cumulative_surface_flux_p3": float(r3["cum_flux"]),
        # —— 关键反演/证据标量（非合同，供审阅）——
        "t_star_p1_note": "预热平衡阶段,不反演终点",
        "t_star_p3_hours": float(o3["p3_t_star_h"]),
        "t_star_fixed_domain_p4_hours": t_fixed_p4,
        "t_star_shrinking_p4_hours": t_shrink_p4,
        "t_star_latent_p3_hours": float(sens["p3_latent_h"]),
        "t_star_no_latent_p3_hours": float(sens["p3_hold_h"]),
        "R_tstar_cm_p4": float(o4["p4_R_tstar_cm"]),
        "sensitivity": {k: v for k, v in sens.items() if k != "module"},
        # —— 方向/界探针 ——
        "logic_probes": logic_probes,
    }
    if write:
        P.FIG_DIR.mkdir(parents=True, exist_ok=True)
        JSON_OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2),
                            encoding="utf-8")
    return out


if __name__ == "__main__":
    o = run_all()
    print("ALL done. logic_probes:", json.dumps(o["logic_probes"], ensure_ascii=False))
    print("C_max_at_t_star:", o["C_max_at_t_star"],
          "| picard_max:", o["picard_final_residual_max"],
          "| p_order:", o["spatial_convergence_order_p"])
    print("equiv P4:", o["t_star_p4_hours"], "vs", o["t_star_p4_hours_pchip_vs_denser_output"])
    print("equiv Cbar:", o["Cbar_change_p3"], "vs", o["cumulative_surface_flux_p3"])
