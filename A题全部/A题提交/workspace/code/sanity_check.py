# -*- coding: utf-8 -*-
"""物理/结构合理性自检：在真解上核对不违反基本物理与离散结构约束。

检查项：含水率有界非负 [0,C0]、中心含水率随时间单调非增（脱水）、中心温度单调升、
终点空间最大在中心（内慢外快）、表面最干、R(t) 单调非增（P4）、离散测度和=1、
守恒残差达机器精度。任一违反即 FAIL。导出 figures/sanity_check.json。
"""
from __future__ import annotations
import json
import sys
import numpy as np
import params as P
import utils

JSON_OUT = P.FIG_DIR / "sanity_check.json"


def _fields_ok(C_hist, C0):
    arr = np.vstack(C_hist)
    return bool(arr.min() > -1e-6 and arr.max() < C0 + 1e-6)


def _center_monotone(C_hist):
    c0 = np.array([f[0] for f in C_hist])
    return bool(np.all(np.diff(c0) <= 1e-9))


def _center_temp_rises(T_hist):
    t0 = np.array([f[0] for f in T_hist])
    return bool(np.all(np.diff(t0) >= -1e-6))


def run_sanity_check(write=True):
    env = utils.load_environment()
    checks = {}

    # P1 预热（常物性，全场记录）
    r1 = utils.solve_coupled(utils.PROPS_P1, P.T_END_P1, P.DT_P1, env,
                             mode="hold", record_full=True)
    checks["p1_C_bounded"] = _fields_ok(r1["C_hist"], P.C0)
    checks["p1_center_monotone_down"] = _center_monotone(r1["C_hist"])
    checks["p1_center_temp_up"] = _center_temp_rises(r1["T_hist"])
    checks["p1_measure_sum_unit"] = bool(abs(r1["grid"]["w_j"].sum() - 1.0) < 1e-14)

    # P3 恒温至达标（变物性固定域）
    r3 = utils.solve_coupled(utils.PROPS_P23, 400.0 * P.H_TO_S, P.DT_P34, env,
                             mode="hold", endpoint_stop=True, record_full=True)
    checks["p3_C_bounded"] = _fields_ok(r3["C_hist"], P.C0)
    checks["p3_center_monotone_down"] = _center_monotone(r3["C_hist"])
    checks["p3_argmax_center"] = bool(r3["argmax_r_end"] == 0)
    checks["p3_surface_driest"] = bool(r3["C_hist"][-1][-1] <= r3["C_hist"][-1].min() + 1e-12)
    checks["p3_conservation_tiny"] = bool(r3["cons_residual"] < 1e-10)

    # P4 收缩域至达标（附件2 R(t)）
    pchip, t_arr, R_arr = utils.build_radius_interp()
    R_tmax = float(t_arr[-1])
    r4 = utils.solve_coupled(utils.PROPS_P4, 80.0 * P.H_TO_S, P.DT_P34, env,
                             mode="hold", R_interp=pchip, R_tmax=R_tmax,
                             endpoint_stop=True, record_full=True)
    checks["p4_C_bounded"] = _fields_ok(r4["C_hist"], P.C0)
    checks["p4_center_monotone_down"] = _center_monotone(r4["C_hist"])
    checks["p4_argmax_center"] = bool(r4["argmax_r_end"] == 0)
    checks["p4_R_monotone_down"] = bool(np.all(np.diff(R_arr) <= 1e-12))
    checks["p4_R_hist_monotone"] = bool(np.all(np.diff(r4["R_hist"]) <= 1e-9))
    checks["p4_conservation_tiny"] = bool(r4["cons_residual"] < 1e-10)

    verdict = "PASS" if all(checks.values()) else "FAIL"
    failed = [k for k, v in checks.items() if not v]
    out = {"verdict": verdict, "n_checks": len(checks), "failed": failed,
           "checks": checks}
    if write:
        P.FIG_DIR.mkdir(parents=True, exist_ok=True)
        JSON_OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2),
                            encoding="utf-8")
    return out


if __name__ == "__main__":
    o = run_sanity_check()
    print(f"Sanity check: {o['verdict']} ({o['n_checks']} checks)")
    for k, v in o["checks"].items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    sys.exit(0 if o["verdict"] == "PASS" else 1)
