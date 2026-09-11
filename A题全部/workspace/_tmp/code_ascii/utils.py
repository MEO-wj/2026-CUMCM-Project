# -*- coding: utf-8 -*-
"""共享数值内核：柱坐标节点中心守恒型有限体积法 (finite_volume) 求解耦合热-质传递。

方法学锁定（对应 MODELING_REPORT sec.9.5 M1--M9）：
  M1 有限体积 + 柱几何测度 w_j = xi_half^2 之差；M2 中心奇性结构性消去
  (inner_face_area 恒 0)；M3 Kirchhoff 积分平均界面扩散 (kirchhoff_phi, exp1)；
  M4 theta=1 backward_euler；M5 picard 内迭代 (PICARD_TOL)；M6 M_GRID=20；
  M7 干基质量坐标动边界 (one_over_R2, rho_s_R2)；M8 PchipInterpolator；
  M9 solve_ivp / BDF 交叉验证。
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.special import exp1, j0, j1
from scipy.optimize import brentq
from scipy.interpolate import PchipInterpolator
from scipy.integrate import solve_ivp

# 输出表头（与附件3 模板逐字一致：A 列为时间，第 1 行为到药材中心距离）
TIME_HEADER = "时间\\到药材中心的距离"
SURFACE_LABEL = "药材表面"        # result4 末列语义（随收缩变化的物理表面 xi=1）

import params as P


# ============================================================
# 几何：节点中心守恒型有限体积网格 (M1, M2)
# ============================================================
def build_grid(M=P.M_GRID):
    """构造 xi in [0,1] 的 M+1 节点网格与柱几何控制体测度 w_j。

    返回 dict：xi(节点)、xi_half(内部界面 j+1/2, 长 M)、xi_faces(含中心0与表面1)、
    w_j(控制体测度, 长 M+1, 求和=1)、dxi、inner_face_area(最内控制体内侧面积, 恒 0)。
    """
    xi = np.linspace(0.0, 1.0, M + 1)
    dxi = 1.0 / M
    xi_half = 0.5 * (xi[:-1] + xi[1:])           # 界面 j+1/2, j=0..M-1
    # 全部控制体界面：中心 0、内部中点、表面 1
    xi_faces = np.concatenate(([0.0], xi_half, [1.0]))
    inner_face_area = xi_faces[0]                # 结构性消去：最内界面面积严格为 0
    # w_j = xi_{j+1/2}^2 - xi_{j-1/2}^2, 柱几何测度
    w_j = xi_faces[1:] ** 2 - xi_faces[:-1] ** 2
    return {
        "M": M, "xi": xi, "dxi": dxi, "xi_half": xi_half,
        "xi_faces": xi_faces, "w_j": w_j, "inner_face_area": inner_face_area,
    }


# ============================================================
# Kirchhoff 积分平均界面扩散系数 (M3)
# ============================================================
def kirchhoff_phi(C, a_exp):
    """Kirchhoff 势 Phi(C) = C e^{-a/C} - a E_1(a/C)，E_1 由 scipy.special.exp1 提供。

    满足 dPhi/dC = e^{-a/C}，用于界面浓度扩散因子的积分平均。C<CFLOOR 时取下限防溢出。
    """
    Cc = np.maximum(C, P.CFLOOR)
    return Cc * np.exp(-a_exp / Cc) - a_exp * exp1(a_exp / Cc)

# ============================================================
# 物性容器：按附录封装 rho/cp/k 与扩散系数参数 (M3, M7)
# ============================================================
class Properties:
    """按问题封装物性：rho(C)、cp(C)、k(C) 及扩散前因子/浓度指数/Arrhenius 系数。

    arr_T=0 表示扩散系数不含温度项（附录2，问题1）；此时 f(T)=exp(0)=1，
    对温度的偏导恒为零（RC5 断言据此成立）。
    """

    def __init__(self, rho, cp, k, d_pre, d_exp, arr_T):
        self.rho = rho
        self.cp = cp
        self.k = k
        self.d_pre = d_pre        # 扩散前因子 A
        self.d_exp = d_exp        # 浓度指数 a（e^{-a/C}）
        self.arr_T = arr_T        # Arrhenius 系数（K）；0 表示无温度项


PROPS_P1 = Properties(P.rho_a2, P.cp_a2, P.k_a2, P.D_PRE_A2, P.D_EXP_A2, 0.0)
PROPS_P23 = Properties(P.rho_a3, P.cp_a3, P.k_a3, P.D_PRE_A3, P.D_EXP_A3, P.ARR_T)
PROPS_P4 = Properties(P.rho_a4, P.cp_a4, P.k_a4, P.D_PRE_A4, P.D_EXP_A4, P.ARR_T)


def arrhenius_factor(T_degC, arr_T):
    """温度因子 f(T)=e^{-arr_T/T_K}，T_K=T+273.15（开尔文）。arr_T=0 时恒为 1。

    RC4：入口断言 200<T_K<500，摄氏度误传立即暴露（E2）。
    """
    T_K = np.asarray(T_degC, dtype=float) + P.T_KELVIN
    if arr_T != 0.0:
        assert np.all((T_K > 200.0) & (T_K < 500.0)), \
            f"RC4 违反：Arrhenius 入口 T_K 越界（疑似传入摄氏度）min={T_K.min():.3f} max={T_K.max():.3f}"
    return np.exp(-arr_T / T_K)


def interface_diffusivity(C, T, props):
    """界面扩散系数 D_{j+1/2}=A*f_bar(T)*[Phi(C_{j+1})-Phi(C_j)]/(C_{j+1}-C_j)（M3）。

    - 浓度部分：Kirchhoff 积分平均（kirchhoff_phi），保证界面通量与 intD dC 一致；
    - 温度部分：f(T)=e^{-arr_T/T_K} 在界面按算术平均（温度场光滑）；
    - |dC|<DINTERP_TOL 时改用中点值 D((C_j+C_{j+1})/2) 防 0/0（E8）。
    返回长度 M 的界面 D（j=0..M-1，对应 xi_half）。
    禁用调和平均（harmonic）--见 sec.7.2。
    """
    a = props.d_exp
    C = np.asarray(C, dtype=float)
    dC = C[1:] - C[:-1]
    phi = kirchhoff_phi(C, a)
    dphi = phi[1:] - phi[:-1]
    Cmid = 0.5 * (C[1:] + C[:-1])
    conc_factor = np.where(
        np.abs(dC) < P.DINTERP_TOL,
        np.exp(-a / np.maximum(Cmid, P.CFLOOR)),   # 中点值 dPhi/dC=e^{-a/C}
        dphi / np.where(np.abs(dC) < P.DINTERP_TOL, 1.0, dC),
    )
    f_face = 0.5 * (arrhenius_factor(T[1:], props.arr_T)
                    + arrhenius_factor(T[:-1], props.arr_T))
    return props.d_pre * f_face * conc_factor


def interface_conductivity(C, props):
    """界面导热系数 k_{j+1/2}：k(C) 在界面按算术平均（温度方程界面项）。长度 M。

    常物性（附录2）的 k(C) 返回标量，用 broadcast_to 统一成场形式再取界面均值。
    """
    C = np.asarray(C, dtype=float)
    kv = np.broadcast_to(props.k(C), C.shape)
    return 0.5 * (kv[1:] + kv[:-1])


# ============================================================
# 三对角 Thomas 直接解法
# ============================================================
def thomas_solve(a_sub, b_diag, c_sup, d_rhs):
    """求解三对角系统 a_j u_{j-1}+b_j u_j+c_j u_{j+1}=d_j。

    a_sub[0] 与 c_sup[-1] 不参与（边界）。就地拷贝，返回解向量 u。
    theta=1 向后欧拉下对角占优恒成立（E13），无需选主元。
    """
    n = len(b_diag)
    cp = np.empty(n)
    dp = np.empty(n)
    cp[0] = c_sup[0] / b_diag[0]
    dp[0] = d_rhs[0] / b_diag[0]
    for i in range(1, n):
        m = b_diag[i] - a_sub[i] * cp[i - 1]
        cp[i] = c_sup[i] / m if i < n - 1 else 0.0
        dp[i] = (d_rhs[i] - a_sub[i] * dp[i - 1]) / m
    u = np.empty(n)
    u[-1] = dp[-1]
    for i in range(n - 2, -1, -1):
        u[i] = dp[i] - cp[i] * u[i + 1]
    return u

# ============================================================
# 环境驱动 T_air(t), C_air(t)：附件1 读取 + 末值保持外推 (H3, sec.7.4)
# ============================================================
def load_environment():
    """读附件1（sheet_name 显式），返回 (t_arr, Tair_arr, Cair_arr)。逐秒线性插值、
    末值保持外推由 env_at 完成。read_excel 必须写 sheet_name（防静默首表陷阱）。"""
    df = pd.read_excel(P.ENV_FILE, sheet_name=P.ENV_SHEET)
    t = df.iloc[:, 0].to_numpy(dtype=float)
    Tair = df.iloc[:, 1].to_numpy(dtype=float)
    Cair = df.iloc[:, 2].to_numpy(dtype=float)
    return t, Tair, Cair


def env_at(t_query, env, mode="hold"):
    """在 t_query（秒，标量）处取 (T_air, C_air)。

    区间内线性插值；超出附件1 覆盖范围（>t_max）时：
      hold   -- 末值保持（H3 主算）
      mean   -- 取末小时均值（灵敏度对照）
      linear -- 按末小时线性斜率外推（灵敏度对照）
    """
    t, Tair, Cair = env
    tmax = t[-1]
    if t_query <= tmax:
        return float(np.interp(t_query, t, Tair)), float(np.interp(t_query, t, Cair))
    if mode == "hold":
        return float(Tair[-1]), float(Cair[-1])
    # 末小时窗口（3600 s）统计
    win = t >= (tmax - 3600.0)
    if mode == "mean":
        return float(Tair[win].mean()), float(Cair[win].mean())
    if mode == "linear":
        tt = t[win]
        sT = np.polyfit(tt, Tair[win], 1)[0]
        sC = np.polyfit(tt, Cair[win], 1)[0]
        return float(Tair[-1] + sT * (t_query - tmax)), float(Cair[-1] + sC * (t_query - tmax))
    raise ValueError(f"未知外推模式 {mode}")


# ============================================================
# 半径 R(t)：附件2 + PCHIP 单调保形插值 (M8, E9)
# ============================================================
def build_radius_interp():
    """读附件2（sheet_name 显式），构造 PCHIP 单调保形插值 R(t)（cm->m）。

    返回 (pchip_obj, t_arr, R_arr_m)。断言 R 单调非增（RC12）。不用三次样条（会过冲）。
    """
    df = pd.read_excel(P.RADIUS_FILE, sheet_name=P.RADIUS_SHEET)
    t = df.iloc[:, 0].to_numpy(dtype=float)
    R_cm = df.iloc[:, 1].to_numpy(dtype=float)
    R_m = R_cm * P.CM_TO_M
    assert np.all(np.diff(R_m) <= P.MONO_TOL), "RC12 违反：附件2 半径非单调非增"
    pchip = PchipInterpolator(t, R_m, extrapolate=True)
    return pchip, t, R_m


def radius_at(pchip, t_query, tmax):
    """PCHIP 取 R(t_query)（m）；超出附件2 范围按末值保持（收缩已到平台）。"""
    tq = min(t_query, tmax)
    return float(pchip(tq))


# ============================================================
# 组装并求解单场三对角系统（水分 / 温度）--向后欧拉一步
# ============================================================
def _assemble_moisture(C_old, C_it, T_it, props, grid, one_over_R2, R_now,
                       Cair, hm, dt):
    """水分方程 theta=1 向后欧拉的三对角系统（用当前迭代 C_it,T_it 冻结物性）。

    w_j dC/dt = (2/R^2)[xi_{j+1/2}D_{j+1/2}dC/dxi - xi_{j-1/2}D_{j-1/2}dC/dxi]
    表面 j=M 并入 Robin 通量 -(2 h_m/R)(C_M-C_air)。one_over_R2=1/R(t)^2（M7）。
    """
    M = grid["M"]
    w = grid["w_j"]
    dxi = grid["dxi"]
    xi_half = grid["xi_half"]                 # 长 M，界面 j+1/2
    Dhat = interface_diffusivity(C_it, T_it, props)   # 长 M
    # 面导：coef_face[j] = (2/R^2) xi_{j+1/2} D_{j+1/2} / dxi，j=0..M-1
    coef_face = 2.0 * one_over_R2 * xi_half * Dhat / dxi
    a_sub = np.zeros(M + 1)
    b_diag = np.zeros(M + 1)
    c_sup = np.zeros(M + 1)
    d_rhs = np.zeros(M + 1)
    for j in range(M + 1):
        b = w[j] / dt
        rhs = w[j] / dt * C_old[j]
        # 内侧界面 j-1/2：j=0 时结构性消去（inner_face_area=0）
        if j >= 1:
            f_in = coef_face[j - 1]
            a_sub[j] = -f_in
            b += f_in
        # 外侧界面 j+1/2：j=M 为物理表面（Robin），否则内部扩散
        if j <= M - 1:
            f_out = coef_face[j]
            c_sup[j] = -f_out
            b += f_out
        else:
            # 表面 Robin：-(2 h_m/R)(C_M - C_air)
            surf = 2.0 * hm / R_now
            b += surf
            rhs += surf * Cair
        b_diag[j] = b
        d_rhs[j] = rhs
    return a_sub, b_diag, c_sup, d_rhs


def _assemble_temperature(T_old, C_it, T_it, props, grid, one_over_R2, R_now,
                          Tair, h, dt, latent_sink):
    """温度方程 theta=1 向后欧拉三对角系统，除以 (rhoc_p)_j。

    latent_sink（W/m?*s 等效，见 solve）为表面蒸发潜热汇（灵敏度情景，主算=0）。
    """
    M = grid["M"]
    w = grid["w_j"]
    dxi = grid["dxi"]
    xi_half = grid["xi_half"]
    khat = interface_conductivity(C_it, props)        # 长 M
    C_arr = np.asarray(C_it, dtype=float)
    rho_cp = np.broadcast_to(props.rho(C_arr) * props.cp(C_arr), C_arr.shape)  # 长 M+1
    coef_face = 2.0 * one_over_R2 * xi_half * khat / dxi
    a_sub = np.zeros(M + 1)
    b_diag = np.zeros(M + 1)
    c_sup = np.zeros(M + 1)
    d_rhs = np.zeros(M + 1)
    for j in range(M + 1):
        rc = rho_cp[j]
        b = w[j] * rc / dt
        rhs = w[j] * rc / dt * T_old[j]
        if j >= 1:
            f_in = coef_face[j - 1]
            a_sub[j] = -f_in
            b += f_in
        if j <= M - 1:
            f_out = coef_face[j]
            c_sup[j] = -f_out
            b += f_out
        else:
            surf = 2.0 * h / R_now
            b += surf
            rhs += surf * Tair
            rhs -= latent_sink            # 表面蒸发吸热（负源）
        b_diag[j] = b
        d_rhs[j] = rhs
    return a_sub, b_diag, c_sup, d_rhs

# ============================================================
# 主时间推进：theta=1 向后欧拉 + Picard 内迭代（T 与 C 同一循环，M4/M5）
# ============================================================
def solve_coupled(props, t_end, dt, env, *, mode="hold", R_interp=None,
                  R_tmax=None, latent=0.0, R0=P.R0, C0=P.C0, T0=P.T0,
                  M=P.M_GRID, endpoint_stop=False, record_full=False,
                  interface="kirchhoff"):
    """求解耦合热-质传递，向后欧拉 + Picard 内迭代。

    interface: "kirchhoff"(主算) / "arithmetic" / "harmonic"（仅灵敏度对照，sec.8.4）。
    endpoint_stop=True：Cmax 首次 <C_TH 即停（终点反演，省算）。
    record_full=True：记录每步 T、C 全场（导出用）。
    返回 dict：t(输出时刻)、T_hist、C_hist(若 record_full)、t_star_s、t_star_h、
      cmax_cross、cmax_prev、cbar0、cbar_end、cum_flux、cons_residual、
      picard_res_max、n_steps、R_hist、Cs_end、Cair_end。
    """
    grid = build_grid(M)
    w = grid["w_j"]
    C = np.full(M + 1, C0)
    T = np.full(M + 1, T0)
    cbar0 = float(np.dot(w, C))
    n_steps = int(round(t_end / dt))
    t_out = [0.0]
    T_hist = [T.copy()] if record_full else None
    C_hist = [C.copy()] if record_full else None
    R_hist = [R0]
    cbar = cbar0
    cum_flux = 0.0
    cons_res = 0.0
    picard_res_max = 0.0
    cmax_prev = float(C.max())
    t_star_s = None
    cmax_cross = None
    cs_end = float(C[-1])
    cair_end = env_at(0.0, env, mode)[1]
    for n in range(1, n_steps + 1):
        tn1 = n * dt
        Tair, Cair = env_at(tn1, env, mode)
        R_now = R0 if R_interp is None else radius_at(R_interp, tn1, R_tmax)
        one_over_R2 = 1.0 / (R_now * R_now)
        C_old, T_old = C, T
        C_it, T_it = C.copy(), T.copy()
        res = np.inf
        rho_s_R2 = None  # M7 不变量占位（收缩守恒基准）
        for it in range(P.PICARD_MAX):
            if interface == "kirchhoff":
                aC, bC, cC, dC = _assemble_moisture(
                    C_old, C_it, T_it, props, grid, one_over_R2, R_now, Cair, P.HM_CONV, dt)
            else:
                aC, bC, cC, dC = _assemble_moisture_alt(
                    C_old, C_it, T_it, props, grid, one_over_R2, R_now, Cair,
                    P.HM_CONV, dt, interface)
            C_new = thomas_solve(aC, bC, cC, dC)
            if latent != 0.0:
                rho_s = props.rho(C_it[-1]) / (1.0 + C_it[-1])
                latent_sink = 2.0 / R_now * latent * rho_s * P.HM_CONV * (C_it[-1] - Cair)
            else:
                latent_sink = 0.0
            aT, bT, cT, dT = _assemble_temperature(
                T_old, C_it, T_it, props, grid, one_over_R2, R_now, Tair, P.H_CONV, dt, latent_sink)
            T_new = thomas_solve(aT, bT, cT, dT)
            res = max(np.max(np.abs(C_new - C_it)), np.max(np.abs(T_new - T_it)))
            C_it, T_it = C_new, T_new
            if res < P.PICARD_TOL:
                break
        picard_res_max = max(picard_res_max, res)
        C, T = C_it, T_it
        # 守恒审计（构造性精确恒等，逐步核对）
        cbar_new = float(np.dot(w, C))
        step_flux = dt * (2.0 * P.HM_CONV / R_now) * (C[-1] - Cair)
        cum_flux += step_flux
        imbalance = abs((cbar_new - cbar) + step_flux) / cbar0
        cons_res = max(cons_res, imbalance)
        cbar = cbar_new
        # 物理约束
        assert C.min() > -1e-6, f"RC7 违反：出现负含水率 {C.min():.3e} at t={tn1}"
        rho_s_R2 = (props.rho(C0) / (1.0 + C0)) * R_now * R_now  # 记录不变量口径(M7)
        cmax_new = float(C.max())
        if record_full:
            T_hist.append(T.copy())
            C_hist.append(C.copy())
            t_out.append(tn1)
            R_hist.append(R_now)
        # 首次穿越检测（空间最大值判据，sec.7.6）
        if t_star_s is None and cmax_prev >= P.C_TH and cmax_new < P.C_TH:
            frac = (cmax_prev - P.C_TH) / (cmax_prev - cmax_new)
            t_star_s = (n - 1) * dt + dt * frac
            cmax_cross = cmax_new
            cs_end = float(C[-1])
            cair_end = Cair
            if endpoint_stop:
                break
        cmax_prev = cmax_new
    return {
        "t": np.array(t_out), "T_hist": T_hist, "C_hist": C_hist,
        "R_hist": np.array(R_hist), "t_star_s": t_star_s,
        "t_star_h": (t_star_s / P.H_TO_S) if t_star_s is not None else None,
        "cmax_cross": cmax_cross, "cmax_prev": cmax_prev,
        "cbar0": cbar0, "cbar_end": cbar, "cum_flux": cum_flux,
        "cons_residual": cons_res, "picard_res_max": picard_res_max,
        "n_steps": n_steps, "Cs_end": cs_end, "Cair_end": cair_end,
        "grid": grid, "argmax_r_end": int(np.argmax(C)),
        "rho_s_R2": rho_s_R2,
    }


def _assemble_moisture_alt(C_old, C_it, T_it, props, grid, one_over_R2, R_now,
                           Cair, hm, dt, interface):
    """对照用界面平均（算术/调和），仅供 sec.8.4 离散决策可证伪性验证，非主算路径。

    interface="arithmetic"：算术平均 0.5(D_L+D_R)；
    interface="harmonic"：调和平均 2 D_L D_R/(D_L+D_R)（报告禁用，此处仅量化其后果）。
    """
    M = grid["M"]
    w = grid["w_j"]
    dxi = grid["dxi"]
    xi_half = grid["xi_half"]
    a = props.d_exp
    Cc = np.maximum(C_it, P.CFLOOR)
    D_node = props.d_pre * arrhenius_factor(T_it, props.arr_T) * np.exp(-a / Cc)
    DL, DR = D_node[:-1], D_node[1:]
    if interface == "arithmetic":
        Dhat = 0.5 * (DL + DR)
    elif interface == "harmonic":
        Dhat = 2.0 * DL * DR / (DL + DR)
    else:
        raise ValueError(interface)
    coef_face = 2.0 * one_over_R2 * xi_half * Dhat / dxi
    a_sub = np.zeros(M + 1)
    b_diag = np.zeros(M + 1)
    c_sup = np.zeros(M + 1)
    d_rhs = np.zeros(M + 1)
    for j in range(M + 1):
        b = w[j] / dt
        rhs = w[j] / dt * C_old[j]
        if j >= 1:
            a_sub[j] = -coef_face[j - 1]
            b += coef_face[j - 1]
        if j <= M - 1:
            c_sup[j] = -coef_face[j]
            b += coef_face[j]
        else:
            surf = 2.0 * hm / R_now
            b += surf
            rhs += surf * Cair
        b_diag[j] = b
        d_rhs[j] = rhs
    return a_sub, b_diag, c_sup, d_rhs
# ============================================================
# 输出场映射：xi 网格解 -> 固定物理列 0.0..2.0 cm（M8 线性插值，P4 域外留空）
# ============================================================
def map_field_to_columns(field, R_now, *, shrinking=False):
    """把一时刻 xi 网格解（长 M+1，节点 xi=0..1）映射到 21 个固定物理列。

    固定域（P1--P3，R_now==R0 恒定）：M=20 时节点与列严格重合，返回原值（零插值）。
    收缩域（P4，shrinking=True）：物理列 p_cm=0..1.9 映到 xi=(p_cm*CM_TO_M)/R_now，
      线性插值；xi>1（物理半径已收缩到该列内侧）写 np.nan；末列(索引20)恒取表面 xi=1 值。
    返回长度 21 的一维数组。
    """
    field = np.asarray(field, dtype=float)
    M = field.shape[0] - 1
    xi_nodes = np.linspace(0.0, 1.0, M + 1)
    ncol = P.N_COLS
    out = np.full(ncol, np.nan)
    if not shrinking:
        # 物理列 j*DR_OUT 对应 xi=(j*DR_OUT_CM*CM_TO_M)/R0；M=20 时恰为节点
        for j in range(ncol):
            xi_t = (P.R_OUT_CM[j] * P.CM_TO_M) / R_now
            out[j] = np.interp(xi_t, xi_nodes, field)
        return out
    for j in range(ncol - 1):
        xi_t = (P.R_OUT_CM[j] * P.CM_TO_M) / R_now
        out[j] = np.interp(xi_t, xi_nodes, field) if xi_t <= 1.0 else np.nan
    out[ncol - 1] = field[-1]     # 末列=当前物理表面 xi=1
    return out
def build_output_matrix(hist, t_out, R_hist, *, shrinking=False,
                        t_star_s=None, cross_step=None):
    """由 record_full 的场历史构造输出矩阵 (n_rows x 21)。

    hist: 各时刻场列表（长 n_out+1，含 t=0）；t_out/R_hist 同步。
    终点定位（P3/P4，给 t_star_s 与 cross_step=n）：输出规则步 0..(n-1)*dt 的整行，
      再把末行时间替换为 t*、场按穿越前后两步 [n-1,n] 线性插值（frac 定位）。
    返回 (time_col 长度 n_rows, matrix n_rowsx21)。
    """
    rows = []
    times = []
    if t_star_s is None:
        for k in range(len(hist)):
            rows.append(map_field_to_columns(hist[k], R_hist[k], shrinking=shrinking))
            times.append(t_out[k])
        return np.array(times), np.vstack(rows)
    n = cross_step
    for k in range(n):                # 规则步 0..n-1（含 t=0 初值行）
        rows.append(map_field_to_columns(hist[k], R_hist[k], shrinking=shrinking))
        times.append(t_out[k])
    dt = t_out[1] - t_out[0]
    frac = (t_star_s - (n - 1) * dt) / dt
    field_star = (1.0 - frac) * np.asarray(hist[n - 1]) + frac * np.asarray(hist[n])
    R_star = (1.0 - frac) * R_hist[n - 1] + frac * R_hist[n]
    rows.append(map_field_to_columns(field_star, R_star, shrinking=shrinking))
    times.append(t_star_s)
    return np.array(times), np.vstack(rows)
# ============================================================
# Excel 导出：表头逐字对齐附件3 模板；四位小数；sheet_name 显式
# ============================================================
def _columns_header(last_surface=False):
    """构造 22 列表头：A 列时间 + 21 个径向列（0.0..2.0 cm）。
    last_surface=True 时末列语义替换为「药材表面」（result4，R7）。"""
    cols = [TIME_HEADER] + [f"{r:.1f}" for r in P.R_OUT_CM]
    if last_surface:
        cols[-1] = SURFACE_LABEL
    return cols


def _frame(times, matrix, last_surface=False):
    """时间列 + 场矩阵 -> DataFrame（四位小数），列名对齐模板。np.nan 落盘为空单元。"""
    data = {TIME_HEADER: np.round(np.asarray(times, dtype=float), P.DECIMALS)}
    hdr = _columns_header(last_surface)
    mat = np.round(np.asarray(matrix, dtype=float), P.DECIMALS)
    for j, name in enumerate(hdr[1:]):
        data[name] = mat[:, j]
    return pd.DataFrame(data, columns=hdr)


def write_two_sheet(path, times, T_mat, C_mat):
    """result1/result2：两工作表「温度」「水分浓度」（R6），行=时刻，列=径向。"""
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        _frame(times, T_mat).to_excel(xw, sheet_name="温度", index=False)
        _frame(times, C_mat).to_excel(xw, sheet_name="水分浓度", index=False)


def write_one_sheet(path, times, C_mat, *, last_surface=False):
    """result3/result4：单表 Sheet1 存水分浓度（R6/R7）；result4 末列=药材表面。"""
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        _frame(times, C_mat, last_surface=last_surface).to_excel(
            xw, sheet_name="Sheet1", index=False)
# ============================================================
# 解析退化验证（sec.8.1）：常物性圆柱 Robin 扩散 Bessel 级数
# ============================================================
def bessel_roots(Bi, n_roots=40):
    """求 mu*J1(mu)=Bi*J0(mu) 的前 n_roots 个正根（Robin 特征值，j0/j1 由 scipy）。

    在 [eps, N*pi] 上按符号变化 brentq 定位（每个 J0 零点区间恰一根）。
    """
    g = lambda m: m * j1(m) - Bi * j0(m)
    roots = []
    step = np.pi / 200.0
    prev_m = 1e-6
    prev_v = g(prev_m)
    m = prev_m + step
    while len(roots) < n_roots and m < (n_roots + 2) * np.pi:
        v = g(m)
        if np.isfinite(prev_v) and np.isfinite(v) and prev_v * v < 0.0:
            roots.append(brentq(g, prev_m, m, xtol=1e-12, rtol=1e-14))
        prev_m, prev_v = m, v
        m += step
    return np.array(roots)


def bessel_series_solution(xi, Fo, Bi, n_roots=40):
    """无量纲 theta(xi,Fo)=? 2Bi/((mu_n^2+Bi^2)J0(mu_n))*J0(mu_n xi)*e^{-mu_n^2 Fo}。

    theta=(C-C_air)/(C0-C_air)，xi=r/R，Fo=D t/R^2。返回 xi 处的解（可数组）。
    """
    mus = bessel_roots(Bi, n_roots)
    xi = np.asarray(xi, dtype=float)
    theta = np.zeros_like(xi, dtype=float)
    for mu in mus:
        coef = 2.0 * Bi / ((mu ** 2 + Bi ** 2) * j0(mu))
        theta = theta + coef * j0(mu * xi) * np.exp(-(mu ** 2) * Fo)
    return theta
def const_env(Tair, Cair, t_end):
    """构造常值环境 (t,Tair,Cair)，供解析退化/复算测试用。"""
    t = np.array([0.0, t_end])
    return t, np.array([Tair, Tair]), np.array([Cair, Cair])


def analytic_verify(D_const=5e-9, t_end=3600.0, dt=1.0, C0=2.55, Cair=0.05,
                    n_roots=60, M=P.M_GRID):
    """常物性圆柱 Robin 扩散：FVM 数值解 vs Bessel 解析级数（sec.8.1）。

    D 恒定（d_exp=0、arr_T=0，用 interface='arithmetic' 绕开 exp1(0)）。
    返回 dict：max_abs_err、rel_err_l2、Bi、Fo（内部节点，排除表面奇异层）。
    """
    props = Properties(P.rho_a2, P.cp_a2, P.k_a2, D_const, 0.0, 0.0)
    env = const_env(P.T0, Cair, t_end)
    r = solve_coupled(props, t_end, dt, env, mode="hold", R0=P.R0, C0=C0,
                      T0=P.T0, M=M, record_full=True, interface="arithmetic")
    C_num = r["C_hist"][-1]
    xi = np.linspace(0.0, 1.0, M + 1)
    Bi = P.HM_CONV * P.R0 / D_const
    Fo = D_const * t_end / (P.R0 * P.R0)
    theta = bessel_series_solution(xi, Fo, Bi, n_roots)
    C_ana = Cair + (C0 - Cair) * theta
    interior = slice(0, M)            # 排除表面节点（级数在 xi=1 收敛慢）
    err = np.abs(C_num[interior] - C_ana[interior])
    denom = np.linalg.norm(C_ana[interior])
    return {
        "max_abs_err": float(err.max()),
        "rel_err_l2": float(np.linalg.norm(err) / denom),
        "Bi": float(Bi), "Fo": float(Fo),
        "C_num_surface": float(C_num[-1]), "C_ana_surface": float(C_ana[-1]),
    }
# ============================================================
# 独立复算（M9, CK10）：solve_ivp/BDF 对半离散水分 ODE 交叉验证
# ============================================================
def _moisture_rhs(C, props, grid, one_over_R2, R_now, Cair):
    """半离散水分方程右端 dC/dt = flux_j / w_j（与 _assemble_moisture 同一通量，显式形式）。"""
    M = grid["M"]
    w = grid["w_j"]
    dxi = grid["dxi"]
    xi_half = grid["xi_half"]
    T_dummy = np.full(M + 1, P.T0)                # arr_T=0 时 D 与 T 无关
    Dhat = interface_diffusivity(C, T_dummy, props)
    coef_face = 2.0 * one_over_R2 * xi_half * Dhat / dxi   # 长 M
    flux = np.zeros(M + 1)
    for j in range(M + 1):
        if j >= 1:
            flux[j] += coef_face[j - 1] * (C[j - 1] - C[j])
        if j <= M - 1:
            flux[j] += coef_face[j] * (C[j + 1] - C[j])
        else:
            flux[j] += (2.0 * P.HM_CONV / R_now) * (Cair - C[j])
    return flux / w


def bdf_cross_check(props, t_end, env, C_theta_hist, t_hist, *, R0=P.R0,
                    C0=P.C0, M=P.M_GRID, mode="hold"):
    """对 P1 水分场用 BDF 独立复算，返回与 theta=1 场的 max|dC|（CK10，判据<1e-3）。

    C_theta_hist/t_hist 为主求解器 record_full 输出（含 t=0）。仅对 arr_T=0 解耦场适用。
    """
    grid = build_grid(M)
    one_over_R2 = 1.0 / (R0 * R0)

    def rhs(t, C):
        Cair = env_at(float(t), env, mode)[1]
        return _moisture_rhs(C, props, grid, one_over_R2, R0, Cair)

    C_init = np.full(M + 1, C0)
    sol = solve_ivp(rhs, (0.0, t_end), C_init, method="BDF",
                    t_eval=np.asarray(t_hist, dtype=float),
                    rtol=1e-9, atol=1e-11, max_step=50.0)
    C_bdf = sol.y.T                                  # (n_out, M+1)
    C_ref = np.vstack(C_theta_hist)
    return float(np.max(np.abs(C_bdf - C_ref)))
# ============================================================
# 空间收敛阶（CK8）与界面平均对照（CK7）
# ============================================================
def spatial_convergence(props, env, dt, *, grids=(20, 40, 80), R0=P.R0,
                        C0=P.C0, T0=P.T0, t_cap=None):
    """在三套网格上求 t*，Richardson 估计空间收敛阶 p=log2(|u20-u40|/|u40-u80|)。

    返回 dict：t_star_h（各网格）、order_p。endpoint_stop 省算。
    """
    ts = {}
    for M in grids:
        r = solve_coupled(props, t_cap or 400.0 * P.H_TO_S, dt, env,
                          mode="hold", R0=R0, C0=C0, T0=T0, M=M,
                          endpoint_stop=True)
        ts[M] = r["t_star_h"]
    g = list(grids)
    num = abs(ts[g[0]] - ts[g[1]])
    den = abs(ts[g[1]] - ts[g[2]])
    p = float(np.log2(num / den)) if den > 0 else float("nan")
    return {"t_star_h": ts, "order_p": p}


def interface_comparison(props, env, dt, *, R0=P.R0, C0=P.C0, T0=P.T0,
                         t_cap=None):
    """同一模型仅改界面平均方式求 t*：Kirchhoff（主算）/算术/调和（CK7、sec.8.4）。

    调和平均在 D 跨量级时被最小值锁死 -> t* 暴涨，作可证伪对照（报告禁用）。
    """
    out = {}
    for name in ("kirchhoff", "arithmetic", "harmonic"):
        r = solve_coupled(props, t_cap or 700.0 * P.H_TO_S, dt, env,
                          mode="hold", R0=R0, C0=C0, T0=T0,
                          endpoint_stop=True, interface=name)
        out[name] = r["t_star_h"]
    return out
# ============================================================
# 每 6 h 中心含水率序列（CK11/CK12）与表面通量匹配审计
# ============================================================
def center_every_6h(C_hist, t_out, t_star_s):
    """从场历史抽 t=6,12,... h（不超过 t*）的中心含水率 C(r=0)。返回 (times_h, C_center)。"""
    C_arr = np.vstack(C_hist)
    t = np.asarray(t_out, dtype=float)
    marks_h = []
    vals = []
    k = 1
    while k * 6.0 * P.H_TO_S <= (t_star_s if t_star_s else t[-1]) + 1e-9:
        tq = k * 6.0 * P.H_TO_S
        c0 = float(np.interp(tq, t, C_arr[:, 0]))
        marks_h.append(k * 6.0)
        vals.append(c0)
        k += 1
    return marks_h, vals


def surface_cv_residual(C_new, C_old, T_new, props, env, dt, tn1, *,
                        R0=P.R0, mode="hold"):
    """表面控制体离散平衡残差（P1-C2 falsifiable (a)）：在收敛解上核对

      w_M(C_M^n-C_M^{n-1})/dt = (2/R^2)xi_{M-1/2}DdC/dxi - (2 h_m/R)(C_M-C_air)

    左端为累积项、右端为「内部扩散通量?表面对流通量」。相对残差应达机器精度--
    退化为直角坐标(缺 r 权)或第一类边界(C_M=C_air 直接赋值)时该恒等必然被破坏。
    返回相对残差 |LHS-RHS|/max(|各项|)。
    """
    grid = build_grid(P.M_GRID)
    Cair = env_at(tn1, env, mode)[1]
    one_over_R2 = 1.0 / (R0 * R0)
    Dhat = interface_diffusivity(C_new, T_new, props)
    xi_half = grid["xi_half"]
    dxi = grid["dxi"]
    w_M = grid["w_j"][-1]
    accum = w_M * (C_new[-1] - C_old[-1]) / dt
    F_diff = 2.0 * one_over_R2 * xi_half[-1] * Dhat[-1] * (C_new[-2] - C_new[-1]) / dxi
    F_conv = (2.0 * P.HM_CONV / R0) * (C_new[-1] - Cair)
    denom = max(abs(accum), abs(F_diff), abs(F_conv), 1e-30)
    return abs(accum - (F_diff - F_conv)) / denom


def picard_residual_trace(props, env, dt, *, tn1=None, R0=P.R0, C0=P.C0,
                          T0=P.T0, mode="hold", n_warm=1):
    """单个时间步内 Picard 残差序列（P2-C2 falsifiable (c)：应单调下降至 <1e-11）。

    先推进 n_warm 步建立非平凡场，再在下一步记录每次内迭代的 max|d| 序列。
    返回 (residuals list, n_iter, k_field_dispersion)：k 径向相对离散度（>1e-6 证明逐点物性）。
    """
    grid = build_grid(P.M_GRID)
    C = np.full(P.M_GRID + 1, C0)
    T = np.full(P.M_GRID + 1, T0)
    for n in range(1, n_warm + 1):
        tq = n * dt
        Tair, Cair = env_at(tq, env, mode)
        one_over_R2 = 1.0 / (R0 * R0)
        C_old, T_old = C, T
        C_it, T_it = C.copy(), T.copy()
        for _ in range(P.PICARD_MAX):
            aC, bC, cC, dC = _assemble_moisture(C_old, C_it, T_it, props, grid,
                                                one_over_R2, R0, Cair, P.HM_CONV, dt)
            C_new = thomas_solve(aC, bC, cC, dC)
            aT, bT, cT, dT = _assemble_temperature(T_old, C_it, T_it, props, grid,
                                                    one_over_R2, R0, Tair, P.H_CONV, dt, 0.0)
            T_new = thomas_solve(aT, bT, cT, dT)
            res = max(np.max(np.abs(C_new - C_it)), np.max(np.abs(T_new - T_it)))
            C_it, T_it = C_new, T_new
            if res < P.PICARD_TOL:
                break
        C, T = C_it, T_it
    # 记录步：从收敛场再走一步，逐迭代存残差
    tq = (n_warm + 1) * dt
    Tair, Cair = env_at(tq, env, mode)
    one_over_R2 = 1.0 / (R0 * R0)
    C_old, T_old = C, T
    C_it, T_it = C.copy(), T.copy()
    residuals = []
    for _ in range(P.PICARD_MAX):
        aC, bC, cC, dC = _assemble_moisture(C_old, C_it, T_it, props, grid,
                                            one_over_R2, R0, Cair, P.HM_CONV, dt)
        C_new = thomas_solve(aC, bC, cC, dC)
        aT, bT, cT, dT = _assemble_temperature(T_old, C_it, T_it, props, grid,
                                                one_over_R2, R0, Tair, P.H_CONV, dt, 0.0)
        T_new = thomas_solve(aT, bT, cT, dT)
        res = max(np.max(np.abs(C_new - C_it)), np.max(np.abs(T_new - T_it)))
        residuals.append(float(res))
        C_it, T_it = C_new, T_new
        if res < P.PICARD_TOL:
            break
    kv = np.broadcast_to(props.k(C_it), C_it.shape)
    k_disp = float((kv.max() - kv.min()) / max(abs(kv.mean()), 1e-30))
    return residuals, len(residuals), k_disp


