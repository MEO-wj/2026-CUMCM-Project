# -*- coding: utf-8 -*-
"""问题1 驱动：预热平衡阶段（附录2 常物性，D 无温度项）。

时程 1800 s、步长 1 s；导出 result1.xlsx（温度/水分浓度两表，1801×21）。
锚点：CK1/CK2（t=1800 s 五点场）；解析退化（Bessel）与 BDF 独立复算（CK10）。
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import params as P
import utils

ROOT = P.FIG_DIR.parent
RESULT_XLSX = ROOT / "result1.xlsx"
JSON_OUT = P.FIG_DIR / "problem_1_results.json"


def run_problem1(write=True):
    env = utils.load_environment()
    r = utils.solve_coupled(utils.PROPS_P1, P.T_END_P1, P.DT_P1, env,
                            mode="hold", record_full=True)
    times, C_mat = utils.build_output_matrix(r["C_hist"], r["t"], r["R_hist"])
    _, T_mat = utils.build_output_matrix(r["T_hist"], r["t"], r["R_hist"])

    # 结构性验证：表面控制体离散平衡残差、常物性对 T/C 偏导（P1-C2/P1-C3）
    flux_res = utils.surface_cv_residual(
        r["C_hist"][-1], r["C_hist"][-2], r["T_hist"][-1], utils.PROPS_P1,
        env, P.DT_P1, P.T_END_P1)
    d_lo = utils.PROPS_P1.d_pre * np.exp(-utils.PROPS_P1.d_exp / P.C0) \
        * utils.arrhenius_factor(P.T0 - 10.0, utils.PROPS_P1.arr_T)
    d_hi = utils.PROPS_P1.d_pre * np.exp(-utils.PROPS_P1.d_exp / P.C0) \
        * utils.arrhenius_factor(P.T0 + 10.0, utils.PROPS_P1.arr_T)
    dD_dT_rel = abs(d_hi - d_lo) / d_lo                 # P1-C3：应 ~0
    D_C0 = utils.PROPS_P1.d_pre * np.exp(-utils.PROPS_P1.d_exp / P.C0)

    # 解析退化 + BDF 独立复算
    av = utils.analytic_verify()
    bdf_diff = utils.bdf_cross_check(utils.PROPS_P1, P.T_END_P1, env,
                                     r["C_hist"], r["t"])

    if write:
        utils.write_two_sheet(RESULT_XLSX, times, T_mat, C_mat)
    out = {
        "problem": 1,
        "p1_T_1800_5pt": [round(float(T_mat[-1, i]), 4) for i in (0, 5, 10, 15, 20)],
        "p1_C_1800_5pt": [round(float(C_mat[-1, i]), 4) for i in (0, 5, 10, 15, 20)],
        "p1_conservation_residual": r["cons_residual"],
        "p1_picard_residual_max": r["picard_res_max"],
        "p1_surface_cv_residual": float(flux_res),
        "p1_dD_dT_rel_perturb": float(dD_dT_rel),
        "p1_D_at_C0": float(D_C0),
        "p1_bessel_rel_err_l2": av["rel_err_l2"],
        "p1_bessel_max_abs_err": av["max_abs_err"],
        "p1_bdf_cross_check_max_abs_diff": float(bdf_diff),
        "p1_n_rows": int(times.shape[0]),
        "p1_discrete_measure_sum_error": float(abs(r["grid"]["w_j"].sum() - 1.0)),
    }
    if write:
        P.FIG_DIR.mkdir(parents=True, exist_ok=True)
        JSON_OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2),
                            encoding="utf-8")
    out["_solve"] = r
    return out


if __name__ == "__main__":
    o = run_problem1()
    print("P1 done:", {k: v for k, v in o.items() if k != "_solve"})
