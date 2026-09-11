# -*- coding: utf-8 -*-
"""独立复核脚本（comp-review）：只读校核，不修改任何交付物。"""
import numpy as np
import pandas as pd


def sec(t):
    print("\n===== " + t + " =====")


sec("A. 附件1 环境覆盖范围与末小时统计")
df = pd.read_excel("user_data/附件1.xlsx", sheet_name="Sheet1")
t = df.iloc[:, 0].to_numpy(float)
Ta = df.iloc[:, 1].to_numpy(float)
Ca = df.iloc[:, 2].to_numpy(float)
print("t: %.0f..%.0f s = %.3f h, rows=%d" % (t.min(), t.max(), t.max() / 3600, len(t)))
print("T_air range: %.4f .. %.4f" % (Ta.min(), Ta.max()))
print("C_air range: %.5f .. %.5f" % (Ca.min(), Ca.max()))
win = t >= (t.max() - 3600)
print("last-hour mean T=%.4f  mean C=%.6f" % (Ta[win].mean(), Ca[win].mean()))
print("last-hour slope T=%.3e K/s  slope C=%.3e /s"
      % (np.polyfit(t[win], Ta[win], 1)[0], np.polyfit(t[win], Ca[win], 1)[0]))
print("末值 T=%.4f C=%.6f" % (Ta[-1], Ca[-1]))
print("t=1800s: T_air=%.4f C_air=%.6f" % (np.interp(1800, t, Ta), np.interp(1800, t, Ca)))

sec("B. rho_s*R^2 不变量实测漂移（附录4 rho=760+90C）")
rho4 = lambda C: 760.0 + 90.0 * C
rhos = lambda C: rho4(C) / (1.0 + C)
base = rhos(2.55) * 2.0 ** 2
for C, R in [(2.55, 2.000), (1.00, 1.500), (0.15, 1.198), (0.00, 1.198)]:
    v = rhos(C) * R * R
    print("C=%.2f R=%.3fcm  rho_s=%8.3f  rho_s*R^2=%9.3f  相对初态 %+7.2f%%"
          % (C, R, rhos(C), v, (v / base - 1) * 100))

sec("C. 收缩几何独立检验（§8.9 复算）")
C0 = 2.55
V0 = (1 + C0) / rho4(C0)
Vinf = 1.0 / rho4(0.0)
ratio = Vinf / V0
R0, obs = 2.0, 1.198
print("V_inf/V_0 = %.6f" % ratio)
for name, R_pred, formula in [
        ("纯径向 R0*sqrt(ratio)", R0 * np.sqrt(ratio), "R0*sqrt"),
        ("各向同性 R0*ratio^(1/3)", R0 * ratio ** (1 / 3), "R0*cbrt")]:
    print("%-26s = %.4f cm  | 报告写的 2*%s = %.4f cm | 与附件2 实测 1.198 偏差 %.2f%%"
          % (name, R_pred, formula, 2 * R_pred, abs(R_pred - obs) / obs * 100))

sec("D. 交付文件结构核对")
spec = {"result1.xlsx": ["温度", "水分浓度"], "result2.xlsx": ["温度", "水分浓度"],
        "result3.xlsx": ["Sheet1"], "result4.xlsx": ["Sheet1"]}
for f, sheets in spec.items():
    xl = pd.ExcelFile(f)
    print("\n-- %s sheets=%s (期望%s)" % (f, xl.sheet_names, sheets))
    for sh in xl.sheet_names:
        d = xl.parse(sh)
        tc = d.iloc[:, 0].to_numpy(float)
        print("   [%s] shape=%s 首列 %.4f..%.4f 步长%s"
              % (sh, d.shape, tc.min(), tc.max(),
                 np.unique(np.round(np.diff(tc), 4))[:3]))
        print("   表头首末: %r ... %r" % (d.columns[0], d.columns[-1]))
        body = d.iloc[:, 1:].to_numpy(float)
        print("   NaN 单元=%d  末行 NaN=%d  数据范围 %.4f..%.4f"
              % (np.isnan(body).sum(), np.isnan(body[-1]).sum(),
                 np.nanmin(body), np.nanmax(body)))
        if "水分" in sh or sh == "Sheet1":
            print("   末行 max C=%.6f (阈值0.15)  末行值=%s"
                  % (np.nanmax(body[-1]), np.round(body[-1][:6], 4)))

sec("E. result4 末行留空形态（表面列语义）")
d4 = pd.read_excel("result4.xlsx", sheet_name="Sheet1")
last = d4.iloc[-1].to_numpy(float)
print("列名:", list(d4.columns))
print("末行:", np.round(last, 4))
row = d4.iloc[-1, 1:].to_numpy(float)
filled = [i for i, v in enumerate(row) if not np.isnan(v)]
print("末行非空列索引:", filled, " -> 是否连续:", filled == list(range(len(filled))))

sec("F. 空间非均匀性 -> rho_s 是否可视为空间常数")
for tq_h in [6, 24, 48]:
    tq = tq_h * 3600.0
    k = int(np.argmin(np.abs(d4.iloc[:, 0].to_numpy(float) - tq)))
    r = d4.iloc[k, 1:].to_numpy(float)
    c_ctr, c_srf = r[0], r[~np.isnan(r)][-1]
    print("t=%2dh  C_center=%.4f C_surface=%.4f -> rho_s 中心=%.1f 表面=%.1f 比值=%.3f"
          % (tq_h, c_ctr, c_srf, rhos(c_ctr), rhos(c_srf), rhos(c_srf) / rhos(c_ctr)))
