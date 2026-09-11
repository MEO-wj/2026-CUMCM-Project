# -*- coding: utf-8 -*-
"""问题4 驱动：收缩域烘干至中心达标（附录4 变物性，动边界 Landau 定域）。

R(t) 由附件2 PCHIP 保形插值给定；ξ=r/R(t) 定域，不变量 ρ_s R²=σ，
漂移相消后余 1/R(t)² 因子（M7）。终点反演 t*≈50.90 h。
步长 60 s；导出 result4.xlsx（单表，末列=药材表面；ξ>1 处空单元）。
P4-C2 证据：R(t) 复现附件2<1e-8、单调非增、R(t*)=1.2 cm(CK6)、
CK12 每 6 h 中心值、加密步长 t* 等价(<0.2%)。
"""
from __future__ import annotations
import json
import numpy as np
import params as P
import utils

ROOT = P.FIG_DIR.parent
RESULT_XLSX = ROOT / "result4.xlsx"
JSON_OUT = P.FIG_DIR / "problem_4_results.json"
T_CAP = 80.0 * P.H_TO_S


def run_problem4(write=True):
    env = utils.load_environment()
    pchip, t_arr, R_arr = utils.build_radius_interp()
    R_tmax = float(t_arr[-1])

    r = utils.solve_coupled(utils.PROPS_P4, T_CAP, P.DT_P34, env, mode="hold",
                            R_interp=pchip, R_tmax=R_tmax,
                            endpoint_stop=True, record_full=True)
    cross_step = len(r["C_hist"]) - 1
    times, C_mat = utils.build_output_matrix(
        r["C_hist"], r["t"], r["R_hist"], shrinking=True,
        t_star_s=r["t_star_s"], cross_step=cross_step)

    # P4-C2 falsifiable：PCHIP 复现附件2 节点、单调非增、R(t*)（CK6）
    R_pred = pchip(t_arr)
    r_interp_err = float(np.max(np.abs(R_pred - R_arr) / np.abs(R_arr)))
    r_max_pos_diff = float(np.max(np.diff(R_arr)))          # 应 ≤0（非增）
    R_tstar_cm = utils.radius_at(pchip, r["t_star_s"], R_tmax) / P.CM_TO_M

    # CK12 每 6 h 中心含水率；加密步长 t* 等价性（PCHIP vs 更密输出）
    marks_h, c_center = utils.center_every_6h(r["C_hist"], r["t"], r["t_star_s"])
    r_dense = utils.solve_coupled(utils.PROPS_P4, T_CAP, P.DT_P34 / 2.0, env,
                                  mode="hold", R_interp=pchip, R_tmax=R_tmax,
                                  endpoint_stop=True)
    t_star_dense_h = float(r_dense["t_star_h"])

    if write:
        utils.write_one_sheet(RESULT_XLSX, times, C_mat, last_surface=True)
    out = {
        "problem": 4,
        "p4_t_star_h": round(float(r["t_star_h"]), 6),
        "p4_t_star_dense_h": round(t_star_dense_h, 6),
        "p4_cmax_cross": float(r["cmax_cross"]),
        "p4_cmax_prev": float(r["cmax_prev"]),
        "p4_argmax_r_end": int(r["argmax_r_end"]),
        "p4_R_tstar_cm": round(float(R_tstar_cm), 4),
        "p4_R_interp_rel_error_max": r_interp_err,
        "p4_R_max_positive_diff": r_max_pos_diff,
        "p4_rho_s_R2_invariant": float(r["rho_s_R2"]),
        "p4_conservation_residual": r["cons_residual"],
        "p4_picard_residual_max": r["picard_res_max"],
        "p4_center_6h_marks_h": marks_h,
        "p4_center_6h_values": [round(v, 6) for v in c_center],
        "p4_n_rows": int(times.shape[0]),
        "p4_discrete_measure_sum_error": float(abs(r["grid"]["w_j"].sum() - 1.0)),
    }
    if write:
        P.FIG_DIR.mkdir(parents=True, exist_ok=True)
        JSON_OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2),
                            encoding="utf-8")
    out["_solve"] = r
    return out


if __name__ == "__main__":
    o = run_problem4()
    print("P4 done:", {k: v for k, v in o.items()
                       if k not in ("_solve", "p4_center_6h_values",
                                    "p4_center_6h_marks_h")})
