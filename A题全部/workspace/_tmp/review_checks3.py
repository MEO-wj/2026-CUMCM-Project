# -*- coding: utf-8 -*-
"""独立复核脚本 3：模板表头一致性、params 与 PROBLEM_FACTS 对表、result4 表面列位置。只读。"""
import json
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, "code")
import params as P


def sec(t):
    print("\n===== " + t + " =====", flush=True)


sec("L. 交付文件表头 vs 附件3 原始模板（user_data/result*.xlsx）")
for n in [1, 2, 3, 4]:
    tpl = "user_data/result%d.xlsx" % n
    out = "result%d.xlsx" % n
    xt, xo = pd.ExcelFile(tpl), pd.ExcelFile(out)
    print("\n-- result%d  模板sheets=%s  产出sheets=%s  一致=%s"
          % (n, xt.sheet_names, xo.sheet_names, xt.sheet_names == xo.sheet_names))
    for sh in xt.sheet_names:
        dt = xt.parse(sh)
        do = xo.parse(sh) if sh in xo.sheet_names else None
        print("   [%s] 模板 shape=%s 表头前3=%s 末列=%r"
              % (sh, dt.shape, list(dt.columns[:3]), dt.columns[-1]))
        if do is not None:
            print("        产出 shape=%s 表头前3=%s 末列=%r"
                  % (do.shape, list(do.columns[:3]), do.columns[-1]))
            print("        表头完全一致=%s" % (list(dt.columns) == list(do.columns)))

sec("M. params.py 关键常数 vs PROBLEM_FACTS.json")
F = json.load(open("PROBLEM_FACTS.json", encoding="utf-8"))
a2, a3, a4 = (F["appendix2_constant_properties"], F["appendix3_variable_properties"],
              F["appendix4_variable_properties"])
checks = [
    ("附录2 rho", P.rho_a2(1.0), a2["density_kg_per_m3"]),
    ("附录2 cp", P.cp_a2(1.0), a2["specific_heat_J_per_kgK"]),
    ("附录2 k", P.k_a2(1.0), a2["thermal_conductivity_W_per_mK"]),
    ("h", P.H_CONV, a2["convective_heat_transfer_coeff_W_per_m2K"]),
    ("hm", P.HM_CONV, 8e-7),
    ("附录2 D 前因子", P.D_PRE_A2, 7e-9),
    ("附录2 D 指数", P.D_EXP_A2, a2["diffusivity_formula"]["activation_coeff"]),
    ("附录3 rho(C=1)", P.rho_a3(1.0), a3["density"]["a"] + a3["density"]["b"] * 1.0),
    ("附录3 cp(C=1)", P.cp_a3(1.0),
     a3["specific_heat"]["a"] + a3["specific_heat"]["b"] * 0.5),
    ("附录3 k(C=1)", P.k_a3(1.0),
     a3["thermal_conductivity"]["a"] + a3["thermal_conductivity"]["b"] * 0.5),
    ("附录3 D 前因子", P.D_PRE_A3, 2.4e-3),
    ("附录3 D 指数", P.D_EXP_A3, a3["diffusivity_formula"]["moisture_coeff"]),
    ("附录4 rho(C=1)", P.rho_a4(1.0), a4["density"]["a"] + a4["density"]["b"] * 1.0),
    ("附录4 cp(C=1)", P.cp_a4(1.0),
     a4["specific_heat"]["a"] + a4["specific_heat"]["b"] * 0.5),
    ("附录4 k(C=1)", P.k_a4(1.0),
     a4["thermal_conductivity"]["a"] + a4["thermal_conductivity"]["b"] * 0.5),
    ("附录4 D 前因子", P.D_PRE_A4, 4.2e-4),
    ("附录4 D 指数", P.D_EXP_A4, a4["diffusivity_formula"]["moisture_coeff"]),
    ("Arrhenius", P.ARR_T, a3["diffusivity_formula"]["arrhenius_coeff"]),
    ("阈值", P.C_TH, F["drying_criterion"]["threshold_kg_per_kg"]),
    ("R0/m", P.R0, F["geometry"]["radius_cm"] * 0.01),
    ("C0", P.C0, F["initial_state"]["moisture_dry_basis_kg_per_kg"]),
    ("T0", P.T0, F["initial_state"]["temperature_degC"]),
]
bad = 0
for name, got, exp in checks:
    ok = abs(got - exp) <= 1e-12 * max(1.0, abs(exp))
    if not ok:
        bad += 1
    print("%-18s code=%-12g facts=%-12g %s" % (name, got, exp, "OK" if ok else "*** 不一致"))
print("不一致项数 =", bad)

sec("N. result4「药材表面」列位置随时间的实际落位")
d4 = pd.read_excel("result4.xlsx", sheet_name="Sheet1")
tt = d4.iloc[:, 0].to_numpy(float)
for th in [0, 4, 8, 16, 30, 50.8975]:
    k = int(np.argmin(np.abs(tt - th * 3600)))
    row = d4.iloc[k, 1:].to_numpy(float)
    fixed = row[:20]
    filled = np.where(~np.isnan(fixed))[0]
    rightmost = filled[-1] if len(filled) else -1
    print("t=%7.3fh 固定列最右非空=%s(%.1fcm) 值=%.4f | 末列(药材表面)=%.4f | 相等=%s"
          % (tt[k] / 3600, rightmost, rightmost * 0.1, fixed[rightmost],
             row[20], abs(fixed[rightmost] - row[20]) < 5e-5))
