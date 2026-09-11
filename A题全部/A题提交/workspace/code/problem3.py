# -*- coding: utf-8 -*-
"""问题3 驱动：恒温烘干至中心达标（附录3 变物性，固定域）。

终点反演：空间最大含水率首次 <0.15 kg/kg（§7.6 首穿判据），t*≈57.26 h。
步长 60 s；导出 result3.xlsx（单表水分浓度，末行=t* 线性插值场）。
P3-C2 证据：首穿在原始解上、argmax 近中心、C_max 单调降、C_surf≥C_air；
CK7 界面平均对照（算术/调和），CK8 空间收敛阶（Richardson），CK11 每 6 h 中心值。
"""
from __future__ import annotations
import json
import numpy as np
import params as P
import utils

ROOT = P.FIG_DIR.parent
RESULT_XLSX = ROOT / "result3.xlsx"
JSON_OUT = P.FIG_DIR / "problem_3_results.json"
T_CAP = 400.0 * P.H_TO_S


def run_problem3(write=True):
    env = utils.load_environment()
    r = utils.solve_coupled(utils.PROPS_P23, T_CAP, P.DT_P34, env,
                            mode="hold", endpoint_stop=True, record_full=True)
    cross_step = len(r["C_hist"]) - 1
    times, C_mat = utils.build_output_matrix(
        r["C_hist"], r["t"], r["R_hist"],
        t_star_s=r["t_star_s"], cross_step=cross_step)

    # P3-C2 falsifiable：C_max 逐步单调降（首穿唯一）、argmax 近中心、表面≥环境
    cmax_series = [float(np.max(f)) for f in r["C_hist"]]
    cmax_monotone = all(cmax_series[i] >= cmax_series[i + 1]
                        for i in range(len(cmax_series) - 1))
    c_surf_minus_air = float(r["Cs_end"] - r["Cair_end"])

    # CK11 每 6 h 中心含水率；CK8 空间收敛阶；CK7 界面平均对照
    marks_h, c_center = utils.center_every_6h(r["C_hist"], r["t"], r["t_star_s"])
    sconv = utils.spatial_convergence(utils.PROPS_P23, env, P.DT_P34,
                                      t_cap=T_CAP)
    iface = utils.interface_comparison(utils.PROPS_P23, env, P.DT_P34,
                                       t_cap=700.0 * P.H_TO_S)

    if write:
        utils.write_one_sheet(RESULT_XLSX, times, C_mat)
    out = {
        "problem": 3,
        "p3_t_star_h": round(float(r["t_star_h"]), 6),
        "p3_cmax_cross": float(r["cmax_cross"]),
        "p3_cmax_prev": float(r["cmax_prev"]),
        "p3_argmax_r_end": int(r["argmax_r_end"]),
        "p3_cmax_monotone": bool(cmax_monotone),
        "p3_C_surface_minus_C_air": c_surf_minus_air,
        "p3_Cs_end": float(r["Cs_end"]),
        "p3_Cair_end": float(r["Cair_end"]),
        "p3_conservation_residual": r["cons_residual"],
        "p3_picard_residual_max": r["picard_res_max"],
        "p3_center_6h_marks_h": marks_h,
        "p3_center_6h_values": [round(v, 6) for v in c_center],
        "p3_spatial_order_p": round(float(sconv["order_p"]), 4),
        "p3_spatial_t_star_h": {str(k): round(float(v), 6)
                                for k, v in sconv["t_star_h"].items()},
        "p3_interface_t_star_h": {k: round(float(v), 4)
                                  for k, v in iface.items()},
        "p3_n_rows": int(times.shape[0]),
        "p3_discrete_measure_sum_error": float(abs(r["grid"]["w_j"].sum() - 1.0)),
    }
    if write:
        P.FIG_DIR.mkdir(parents=True, exist_ok=True)
        JSON_OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2),
                            encoding="utf-8")
    out["_solve"] = r
    return out


if __name__ == "__main__":
    o = run_problem3()
    print("P3 done:", {k: v for k, v in o.items()
                       if k not in ("_solve", "p3_center_6h_values",
                                    "p3_center_6h_marks_h")})
