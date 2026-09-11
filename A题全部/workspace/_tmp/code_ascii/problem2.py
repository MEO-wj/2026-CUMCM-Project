# -*- coding: utf-8 -*-
"""问题2 驱动：预热+恒温全过程（附录3 变物性，D(C,T) Arrhenius，开尔文）。

时程 3 h、步长 1 s；导出 result2.xlsx（温度/水分浓度两表，10801x21）。
锚点：CK3/CK4（t=3 h 五点场）。P2-C2 证据：k 径向离散、Picard 单调下降、开尔文入口。
"""
from __future__ import annotations
import json
import numpy as np
import params as P
import utils

ROOT = P.FIG_DIR.parent
RESULT_XLSX = ROOT / "result2.xlsx"
JSON_OUT = P.FIG_DIR / "problem_2_results.json"


def run_problem2(write=True):
    env = utils.load_environment()
    r = utils.solve_coupled(utils.PROPS_P23, P.T_END_P2, P.DT_P2, env,
                            mode="hold", record_full=True)
    times, C_mat = utils.build_output_matrix(r["C_hist"], r["t"], r["R_hist"])
    _, T_mat = utils.build_output_matrix(r["T_hist"], r["t"], r["R_hist"])

    # P2-C2 falsifiable：Picard 残差单调下降、k 逐点随 C 变、开尔文入口
    resids, n_iter, k_disp = utils.picard_residual_trace(
        utils.PROPS_P23, env, P.DT_P2, n_warm=60)
    monotone = all(resids[i] >= resids[i + 1] for i in range(len(resids) - 1))
    # 终点场 k 径向离散度（同一时刻不同 r 处 k 不等 -> 排除冻结常数）
    kv = np.broadcast_to(utils.PROPS_P23.k(r["C_hist"][-1]), (P.M_GRID + 1,))
    k_disp_end = float((kv.max() - kv.min()) / abs(kv.mean()))
    surf_res = utils.surface_cv_residual(
        r["C_hist"][-1], r["C_hist"][-2], r["T_hist"][-1], utils.PROPS_P23,
        env, P.DT_P2, P.T_END_P2)

    if write:
        utils.write_two_sheet(RESULT_XLSX, times, T_mat, C_mat)
    out = {
        "problem": 2,
        "p2_T_3h_5pt": [round(float(T_mat[-1, i]), 4) for i in (0, 5, 10, 15, 20)],
        "p2_C_3h_5pt": [round(float(C_mat[-1, i]), 4) for i in (0, 5, 10, 15, 20)],
        "p2_conservation_residual": r["cons_residual"],
        "p2_picard_residual_max": r["picard_res_max"],
        "p2_picard_trace": resids,
        "p2_picard_n_iter": n_iter,
        "p2_picard_monotone": bool(monotone),
        "p2_k_radial_dispersion": k_disp_end,
        "p2_surface_cv_residual": float(surf_res),
        "p2_n_rows": int(times.shape[0]),
        "p2_discrete_measure_sum_error": float(abs(r["grid"]["w_j"].sum() - 1.0)),
    }
    if write:
        P.FIG_DIR.mkdir(parents=True, exist_ok=True)
        JSON_OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2),
                            encoding="utf-8")
    out["_solve"] = r
    return out


if __name__ == "__main__":
    o = run_problem2()
    print("P2 done:", {k: v for k, v in o.items()
                       if k not in ("_solve", "p2_picard_trace")})
