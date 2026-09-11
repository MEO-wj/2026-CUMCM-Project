# -*- coding: utf-8 -*-
"""集中常量模块：全部物性/几何/初值一律从 PROBLEM_FACTS.json 读取，代码正文禁止裸数字。

注意（附录3 口径澄清，见 RESULTS.md）：MODELING_REPORT.md sec.5.2/sec.9.1 的附录3 抄写有误
（把类附录4 的 760+90C / 0.18+0.12 / e^{-0.89/C} 误填），而报告自身的 CK9 锚点
（D_app3 初=5.6417e-9、终=8.0012e-10）恰由 PROBLEM_FACTS.json 的正确式复算得到：
    rho=650+128C, cp=1450+2736 C/(C+1), k=0.21+0.38 C/(C+1),
    D=2.4e-3 * exp(-0.45/C) * exp(-3850/T_K)
本模块以 OCR SHA256 核验过的 PROBLEM_FACTS.json 为权威来源，保留 M1--M9 全部方法学。
"""
from __future__ import annotations
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_FACTS = json.loads((_ROOT / "PROBLEM_FACTS.json").read_text(encoding="utf-8"))
_PROFILE = json.loads((_ROOT / "DATA_PROFILE.json").read_text(encoding="utf-8"))

# ---- 单位换算与物理偏置（实现配置，非题面数据；说明见 PARAMS_RAW.md）----
CM_TO_M = 0.01            # cm -> m
H_TO_S = 3600.0           # h  -> s
T_KELVIN = 273.15         # deg C -> K 偏置


def _sci(formula: dict) -> float:
    """把 facts 里 {prefactor_mantissa, prefactor_exponent} 组回浮点前因子。"""
    return float(f"{formula['prefactor_mantissa']}e{formula['prefactor_exponent']}")


# ---- 几何（题面：长 25 cm、半径 2 cm）----
_geo = _FACTS["geometry"]
R0 = _geo["radius_cm"] * CM_TO_M          # 0.02 m
LEN = _geo["length_cm"] * CM_TO_M         # 0.25 m

# ---- 初值与烘干标准 ----
_init = _FACTS["initial_state"]
T0 = float(_init["temperature_degC"])                       # 28 ?
C0 = float(_init["moisture_dry_basis_kg_per_kg"])           # 2.55 kg/kg
C_TH = float(_FACTS["drying_criterion"]["threshold_kg_per_kg"])  # 0.15 kg/kg

# ---- 附录2 常物性（问题1）----
_a2 = _FACTS["appendix2_constant_properties"]
RHO_A2 = float(_a2["density_kg_per_m3"])                    # 820
CP_A2 = float(_a2["specific_heat_J_per_kgK"])               # 2600
K_A2 = float(_a2["thermal_conductivity_W_per_mK"])          # 0.36
H_CONV = float(_a2["convective_heat_transfer_coeff_W_per_m2K"])  # 25
HM_CONV = float(_a2["convective_mass_transfer_coeff_m_per_s"]["value_expr"])  # 8e-7
D_PRE_A2 = _sci(_a2["diffusivity_formula"])                # 7e-9
D_EXP_A2 = float(_a2["diffusivity_formula"]["activation_coeff"])  # 0.89
# ---- 附录3 变物性（问题2、问题3）----
_a3 = _FACTS["appendix3_variable_properties"]
RHO_A3_A = float(_a3["density"]["a"])                      # 650
RHO_A3_B = float(_a3["density"]["b"])                      # 128
CP_A3_A = float(_a3["specific_heat"]["a"])                 # 1450
CP_A3_B = float(_a3["specific_heat"]["b"])                 # 2736
K_A3_A = float(_a3["thermal_conductivity"]["a"])           # 0.21
K_A3_B = float(_a3["thermal_conductivity"]["b"])           # 0.38
D_PRE_A3 = _sci(_a3["diffusivity_formula"])                # 2.4e-3
D_EXP_A3 = float(_a3["diffusivity_formula"]["moisture_coeff"])   # 0.45
ARR_T = float(_a3["diffusivity_formula"]["arrhenius_coeff"])     # 3850 K

# ---- 附录4 变物性 + 动边界（问题4）----
_a4 = _FACTS["appendix4_variable_properties"]
RHO_A4_A = float(_a4["density"]["a"])                      # 760
RHO_A4_B = float(_a4["density"]["b"])                      # 90
CP_A4_A = float(_a4["specific_heat"]["a"])                 # 1850
CP_A4_B = float(_a4["specific_heat"]["b"])                 # 2150
K_A4_A = float(_a4["thermal_conductivity"]["a"])           # 0.12
K_A4_B = float(_a4["thermal_conductivity"]["b"])           # 0.20
D_PRE_A4 = _sci(_a4["diffusivity_formula"])                # 4.2e-4
D_EXP_A4 = float(_a4["diffusivity_formula"]["moisture_coeff"])   # 0.30

# ---- 数值方法配置（sec.7 方法唯一性；实现配置常量）----
M_GRID = 20               # 网格区间数，节点与 21 个输出列严格重合
N_COLS = M_GRID + 1       # 21 个径向输出列
THETA = 1.0               # 向后欧拉 backward_euler，L-稳定
PICARD_TOL = 1e-11        # Picard 内迭代容差
PICARD_MAX = 40           # Picard 内迭代上限
CONS_TOL = 1e-10          # 守恒残差门
MONO_TOL = 1e-12          # 单调性容差
CFLOOR = 1e-6             # Phi(C) 浓度下限，防 E1 溢出
DINTERP_TOL = 1e-12       # |C_{j+1}-C_j| 阈值，以下改中点值
DT_P1 = 1.0               # 问题1 时间步/输出步 (s)
DT_P2 = 1.0               # 问题2 时间步/输出步 (s)
DT_P34 = 60.0             # 问题3/4 时间步/输出步 (s)
T_END_P1 = 1800.0         # 问题1 时程 1800 s
T_END_P2 = 3.0 * H_TO_S   # 问题2 时程 3 h
LATENT = 0.0              # 潜热汇，题面未给；灵敏度情景取 2.4e6 J/kg
LATENT_SCENARIO = 2.4e6

# ---- 输出径向列（0,0.1,...,2.0 cm）----
DR_OUT_CM = _FACTS["output_specs"]["problem1"]["full_radial_step_cm"]  # 0.1
R_OUT_CM = [round(i * DR_OUT_CM, 4) for i in range(N_COLS)]            # 0..2.0 cm
DECIMALS = int(_FACTS["output_specs"]["decimals"])                    # 4

# ---- 输入数据文件 ----
DATA_DIR = _ROOT / "user_data"
ENV_FILE = DATA_DIR / "附件1.xlsx"        # T_air(t), C_air(t)
RADIUS_FILE = DATA_DIR / "附件2.xlsx"     # R(t)
ENV_SHEET = "Sheet1"
RADIUS_SHEET = "Sheet1"

# ---- 结果输出目录 ----
FIG_DIR = _ROOT / "figures"


def rho_a2(C):
    return RHO_A2

def cp_a2(C):
    return CP_A2

def k_a2(C):
    return K_A2

def rho_a3(C):
    return RHO_A3_A + RHO_A3_B * C

def cp_a3(C):
    return CP_A3_A + CP_A3_B * C / (C + 1.0)

def k_a3(C):
    return K_A3_A + K_A3_B * C / (C + 1.0)

def rho_a4(C):
    return RHO_A4_A + RHO_A4_B * C

def cp_a4(C):
    return CP_A4_A + CP_A4_B * C / (C + 1.0)

def k_a4(C):
    return K_A4_A + K_A4_B * C / (C + 1.0)


# ---- 单位一致性与锚点断言（导入即校验，写错立即暴露）----
import numpy as _np

assert abs(R0 - 0.02) < 1e-12 and abs(LEN - 0.25) < 1e-12, "几何换算错误"
assert 200.0 < (T0 + T_KELVIN) < 500.0, "初温开尔文越界"
# CK9 扩散锚点（附录2 无温度项；附录3 含 Arrhenius，T 取开尔文）
_D2 = D_PRE_A2 * _np.exp(-D_EXP_A2 / C0)
assert abs(_D2 - 4.9377e-9) < 5e-13, f"CK9 D_app2(C0) 失配: {_D2:.4e}"
_D3i = D_PRE_A3 * _np.exp(-D_EXP_A3 / C0) * _np.exp(-ARR_T / (T0 + T_KELVIN))
assert abs(_D3i - 5.6417e-9) < 5e-13, f"CK9 D_app3 初始失配: {_D3i:.4e}"
_D3t = D_PRE_A3 * _np.exp(-D_EXP_A3 / C_TH) * _np.exp(-ARR_T / (50.0 + T_KELVIN))
assert abs(_D3t - 8.0012e-10) < 5e-13, f"CK9 D_app3 终点失配: {_D3t:.4e}"
# DATA_PROFILE 行数基准
assert _PROFILE["files"]["附件1.xlsx"]["total_rows"] == 241, "附件1 行数基准变化"
assert _PROFILE["files"]["附件2.xlsx"]["total_rows"] == 145, "附件2 行数基准变化"
