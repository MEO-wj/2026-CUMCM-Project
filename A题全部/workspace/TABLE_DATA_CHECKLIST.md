# TABLE 数据真实性核对清单（paper-figure 步骤）

**JSON 源**: all_results.json, problem_1_results.json, problem_2_results.json, problem_3_results.json, problem_4_results.json, sensitivity_results.json
**JSON 数据条目**: 167
**TABLE 文件**: 5 个

---

## 核心规则

**表格数字须能由结果数据复算；允许单位换算、舍入、差值、比值与统计区间，保留推导依据。**

paper-figure 步骤的设计是从 JSON 数据**渲染**出 TABLE 文件
（用 `_utils/stats_utils.py` 的 `regression_table()` / `descriptive_table()` 等函数，
或者读 JSON 后用 Python 脚本生成）。

**TABLE 中出现 JSON 没有的数字 = 编造**，必须用真实 JSON 数据重新生成对应表格。

---

## 自检步骤

1. **逐个打开 figures/TABLE_*.tex|md**，识别每个表格里的数字单元格
2. **对每个数字**，对照下方 JSON 数据清单：
   - ✅ 能精确匹配（含合理的精度截断如 `0.94` ↔ `0.93724`）→ 真实
   - 未直接匹配 JSON：先查推导、单位和舍入；仍无依据则标记待确认，不能直接认定编造或删除整张表，
     用真实 JSON 数据重新生成（推荐：`python3 -c "from _utils.stats_utils import descriptive_table; ..."`）
3. **跳过非数据型数字**：列号 `(1)(2)(3)`、列宽 `width=10cm`、LaTeX 字号 `\zihao{5}` 等格式标记中的数字
4. **修完所有 TABLE 后**，写自证标记：

   ```bash
   touch figures/TABLE_DATA_CHECK_PASSED.txt
   ```

   下一轮检查看到此标记会跳过自检循环。

**禁止**：禁止改 JSON 让数字"对得上"、禁止编造解释、禁止保留疑似编造的 TABLE。

**特别提示**：如果 JSON 中确实没有支撑某张表所需的数据（比如表格规划里有「数据集统计特征」但 JSON 只存了模型对比结果），说明 paper-analysis 步骤遗漏了该数据。应该：(a) 删除这张表 + 改写论文规划中关于这张表的引用；或 (b) 临时跑一段 Python 从原始数据重算并补到 JSON，再生成 TABLE。**不能**直接保留编造的数字。

---

## TABLE 文件全文

### `figures/TABLE_data_stats.tex` (1346 字节)

```latex
% 表：附件输入数据描述性统计
% 数据来源：user_data/附件1.xlsx（241 行）、user_data/附件2.xlsx（145 行）
\begin{table}[H]
  \centering
  \caption{附件输入数据描述性统计}
  \label{tab:data_stats}
  \small
  \begin{tabular}{llrrrrrr}
    \toprule
    来源 & 变量（单位） & 样本数 & 最小值 & 最大值 & 均值 & 中位数 & 标准差 \\
    \midrule
    附件1 & 时间（s）                          & 241 & 0      & 14400  & 7200   & 7200   & 4182.894 \\
    附件1 & 热风温度（$^\circ$C）              & 241 & 28.000 & 50.246 & 47.245 & 49.757 & 5.115 \\
    附件1 & 空气水分浓度（kg$\cdot$kg$^{-1}$）  & 241 & 0.0196 & 0.0503 & 0.0448 & 0.0491 & 0.0081 \\
    \midrule
    附件2 & 时间（s）                          & 145 & 0      & 259200 & 129600 & 129600 & 75603.571 \\
    附件2 & 药材半径（cm）                     & 145 & 1.198  & 2.000  & 1.246  & 1.200  & 0.127 \\
    \bottomrule
  \end{tabular}

  \vspace{2pt}
  \parbox{0.92\linewidth}{\footnotesize
  注：标准差为样本标准差（$n-1$ 自由度）。两附件时间列均为等距采样
  （附件1 步长 60 s，附件2 步长 1800 s），故均值与中位数重合。
  半径均值 1.246 cm 高于中位数 1.200 cm，反映收缩集中在早期、随后进入平台。}
\end{table}
```

### `figures/TABLE_main_results.tex` (1150 字节)

```latex
% 表：四问核心结果汇总
% 数据来源：figures/all_results.json, problem_1..4_results.json, result1-4.xlsx
\begin{table}[H]
  \centering
  \caption{四问核心求解结果汇总}
  \label{tab:main_results}
  \small
  \begin{tabular}{clcrrrl}
    \toprule
    问题 & 物性/工况 & 时程 & 输出行数 & $C$ 中心终值 & $C$ 表面终值 & 达标时刻 $t^*$ \\
    \midrule
    1 & 附录2 常物性       & $0\sim1800$ s   & 1801  & 2.5500 & 1.5125 & 预热段，不反演 \\
    2 & 附录3 变物性       & $0\sim3$ h      & 10801 & 1.7662 & 1.0078 & 未达标 \\
    3 & 附录3 + 附件1 环境 & $0\sim57.26$ h  & 3437  & 0.1500 & 0.0525 & 57.262 h \\
    4 & 附录4 + 动边界     & $0\sim50.90$ h  & 3055  & 0.1500 & 0.0525 & 50.898 h \\
    \bottomrule
  \end{tabular}

  \vspace{2pt}
  \parbox{0.92\linewidth}{\footnotesize
  注：含水率为干基，单位 kg$\cdot$kg$^{-1}$；达标判据为全域最大含水率
  $\max_r C\le 0.15$。问题 1、2 时程由题面给定，终点含水率仍高于阈值，
  故不存在 $t^*$。问题 4 表面指动边界 $r=R(t)$ 处，$t^*$ 时刻 $R=1.2$ cm。}
\end{table}
```

### `figures/TABLE_properties.tex` (1795 字节)

```latex
% 表：三套附录物性模型与关键参数
% 数据来源：PROBLEM_FACTS.json → code/params.py（OCR SHA256 核验）
\begin{table}[H]
  \centering
  \caption{三套附录物性模型对照}
  \label{tab:properties}
  \small
  \begin{tabular}{llll}
    \toprule
    物性量 & 附录2（问题1） & 附录3（问题2、3） & 附录4（问题4） \\
    \midrule
    密度 $\rho$ / (kg$\cdot$m$^{-3}$)
      & $820$
      & $650+128\,C$
      & $760+90\,C$ \\
    比热 $c_p$ / (J$\cdot$kg$^{-1}$K$^{-1}$)
      & $2600$
      & $1450+2736\dfrac{C}{C+1}$
      & $1850+2150\dfrac{C}{C+1}$ \\
    导热 $k$ / (W$\cdot$m$^{-1}$K$^{-1}$)
      & $0.36$
      & $0.21+0.38\dfrac{C}{C+1}$
      & $0.12+0.20\dfrac{C}{C+1}$ \\
    扩散系数 $D$ / (m$^2\cdot$s$^{-1}$)
      & $7{\times}10^{-9}e^{-0.89/C}$
      & $2.4{\times}10^{-3}e^{-0.45/C}e^{-3850/T_K}$
      & $4.2{\times}10^{-4}e^{-0.30/C}e^{-3850/T_K}$ \\
    \midrule
    $D$ 初始值（$C_0$，$28^\circ$C）
      & $4.938{\times}10^{-9}$
      & $5.642{\times}10^{-9}$
      & 随工况 \\
    $D$ 终点值（$C_{\rm th}$，$50^\circ$C）
      & ---
      & $8.001{\times}10^{-10}$
      & 随工况 \\
    温度依赖性
      & 无
      & Arrhenius
      & Arrhenius \\
    边界域
      & 固定 $R_0$
      & 固定 $R_0$
      & 动边界 $R(t)$ \\
    \bottomrule
  \end{tabular}

  \vspace{2pt}
  \parbox{0.94\linewidth}{\footnotesize
  注：$C$ 为干基含水率（kg$\cdot$kg$^{-1}$），$T_K$ 为开尔文温度。
  共用参数：$R_0=2$ cm，$L=25$ cm，$T_0=28^\circ$C，$C_0=2.55$，达标阈值
  $C_{\rm th}=0.15$，对流换热 $h=25$ W$\cdot$m$^{-2}$K$^{-1}$，
  对流传质 $h_m=8{\times}10^{-7}$ m$\cdot$s$^{-1}$。
  $D$ 锚点值由上式复算，与题面校核点一致。}
\end{table}
```

### `figures/TABLE_sensitivity.tex` (1585 字节)

```latex
% 表：假设扰动灵敏度分析
% 数据来源：figures/sensitivity_results.json, all_results.json, problem_3_results.json
\begin{table}[H]
  \centering
  \caption{关键假设扰动对达标时刻的影响}
  \label{tab:sensitivity}
  \small
  \begin{tabular}{llrrr}
    \toprule
    编号 & 扰动情景 & 基准 $t^*$ / h & 扰动 $t^*$ / h & 相对变化 \\
    \midrule
    H3 & 问题3 环境保持$\to$区间均值   & 57.262 & 57.567  & $+0.53\%$ \\
    H3 & 问题3 环境保持$\to$线性外推   & 57.262 & 57.115  & $-0.26\%$ \\
    H3 & 问题4 环境保持$\to$区间均值   & 50.898 & 51.166  & $+0.53\%$ \\
    H3 & 问题4 环境保持$\to$线性外推   & 50.898 & 50.782  & $-0.23\%$ \\
    H4 & 计入蒸发潜热 $L=2.4$ MJ$\cdot$kg$^{-1}$ & 57.262 & 62.646 & $+9.40\%$ \\
    H7 & 问题4 退化为固定域（忽略收缩） & 50.898 & 129.253 & $+153.95\%$ \\
    M3 & 界面平均 Kirchhoff$\to$算术    & 57.262 & 56.230  & $-1.80\%$ \\
    M3 & 界面平均 Kirchhoff$\to$调和    & 57.262 & 557.761 & $+874.05\%$ \\
    \bottomrule
  \end{tabular}

  \vspace{2pt}
  \parbox{0.94\linewidth}{\footnotesize
  注：环境外推假设（H3）影响不足 $0.6\%$，结论稳健。
  潜热（H4）单向延长干燥期，题面未给 $L$，故基准不含潜热汇并作为下界报告。
  忽略收缩（H7）使 $t^*$ 虚高 1.5 倍，证实动边界为问题4 的必要机制。
  调和平均在 $D$ 跨三个量级时被最小值锁死，产生 557.761 h 的非物理结果，
  故界面扩散系数采用 Kirchhoff 积分平均。}
\end{table}
```

### `figures/TABLE_verification.tex` (2160 字节)

```latex
% 表：数值验证与守恒校核指标
% 数据来源：figures/all_results.json, problem_1..4_results.json, figures/_plot_data.json
\begin{table}[H]
  \centering
  \caption{数值验证与守恒校核指标}
  \label{tab:verification}
  \small
  \begin{tabular}{llll}
    \toprule
    检验类别 & 指标 & 实测值 & 判定 \\
    \midrule
    质量守恒 & 问题1 全域残差              & $5.61{\times}10^{-16}$ & 通过 \\
    质量守恒 & 问题2 全域残差              & $4.80{\times}10^{-16}$ & 通过 \\
    质量守恒 & 问题3 全域残差              & $4.38{\times}10^{-16}$ & 通过 \\
    质量守恒 & 问题4 全域残差              & $3.26{\times}10^{-16}$ & 通过 \\
    控制体守恒 & 问题1 表面控制体残差       & $4.10{\times}10^{-14}$ & 通过 \\
    控制体守恒 & 问题2 表面控制体残差       & $3.37{\times}10^{-13}$ & 通过 \\
    \midrule
    解析对照 & Bessel 级数解 $L_2$ 相对误差 & $2.84{\times}10^{-4}$  & 通过 \\
    解析对照 & Bessel 级数解最大绝对误差    & $9.80{\times}10^{-4}$  & 通过 \\
    独立算法 & BDF 交叉校核最大偏差         & $5.77{\times}10^{-4}$  & 通过 \\
    \midrule
    非线性迭代 & Picard 终残差上界          & $9.998{\times}10^{-12}$ & 通过 \\
    空间收敛 & Richardson 观测阶 $p$        & 1.925                  & 近二阶 \\
    时间收敛 & 观测阶 $p$（$\Delta t$ 加密） & 1.215                  & 超一阶 \\
    离散测度 & $\sum_j w_j - \pi R_0^2$ 误差 & 0.000                 & 精确 \\
    插值一致性 & $R(t)$ PCHIP 最大相对误差   & 0.000                  & 精确 \\
    \bottomrule
  \end{tabular}

  \vspace{2pt}
  \parbox{0.94\linewidth}{\footnotesize
  注：守恒残差定义为 $\big|\Delta\!\int C\,\mathrm{d}V-\int\! q_s\,\mathrm{d}t\big|
  /\int C_0\mathrm{d}V$，已达双精度舍入量级（$\sim10^{-16}$）。
  空间收敛以 $M=20/40/80$ 三套网格算得，时间收敛以
  $\Delta t=240/120/60$ s 相对 $30$ s 参考解算得；后者为向后欧拉，
  理论一阶，观测 1.215 说明主算步长 60 s 已落在渐近区。}
\end{table}
```

---

## JSON 真实数据完整清单

### `all_results.json`（56 条）

| 数据路径 | 数值 |
|---|---|
| `C_max_at_t_star` | 0.149995 |
| `conservation_residual_p1` | 5.611e-16 |
| `conservation_residual_p2` | 4.798e-16 |
| `conservation_residual_p3` | 4.381e-16 |
| `conservation_residual_p4` | 3.259e-16 |
| `bdf_cross_check_max_abs_diff` | 0.0005768 |
| `picard_final_residual_max` | 9.998e-12 |
| `discrete_measure_sum_error` | 0 |
| `C_surface_minus_C_air_at_t_star_p3` | 0.002637 |
| `spatial_convergence_order_p` | 1.925 |
| `R_interp_relative_error_max` | 0 |
| `t_star_p4_hours` | 50.8975 |
| `t_star_p4_hours_pchip_vs_denser_output` | 50.8778 |
| `Cbar_change_p3` | 2.42678 |
| `cumulative_surface_flux_p3` | 2.42678 |
| `t_star_p1_note` | `预热平衡阶段,不反演终点` |
| `t_star_p3_hours` | 57.2621 |
| `t_star_fixed_domain_p4_hours` | 129.253 |
| `t_star_shrinking_p4_hours` | 50.8975 |
| `t_star_latent_p3_hours` | 62.6458 |
| `t_star_no_latent_p3_hours` | 57.2621 |
| `R_tstar_cm_p4` | 1.2 |
| `sensitivity.p3_hold_h` | 57.2621 |
| `sensitivity.p3_mean_h` | 57.567 |
| `sensitivity.p3_linear_h` | 57.1152 |
| `sensitivity.p3_mean_rel_pct` | 0.5325 |
| `sensitivity.p3_linear_rel_pct` | -0.2564 |
| `sensitivity.p4_hold_h` | 50.8975 |
| `sensitivity.p4_mean_h` | 51.1656 |
| `sensitivity.p4_linear_h` | 50.7815 |
| `sensitivity.p4_mean_rel_pct` | 0.5267 |
| `sensitivity.p4_linear_rel_pct` | -0.2279 |
| `sensitivity.p3_latent_h` | 62.6458 |
| `sensitivity.p3_latent_rel_pct` | 9.4019 |
| `logic_probes.bounds[0].quantity` | `t_star_fixed_domain_hours` |
| `logic_probes.bounds[0].claim` | `upper` |
| `logic_probes.bounds[0].probe_delta_sign` | -1 |
| `logic_probes.bounds[1].quantity` | `t_star_no_latent_heat_hours` |
| `logic_probes.bounds[1].claim` | `lower` |
| `logic_probes.bounds[1].probe_delta_sign` | 1 |
| `logic_probes.monotonic[0].more` | `T_air_hot_air_temperature` |
| `logic_probes.monotonic[0].then` | `t_star_drying_time_hours` |
| `logic_probes.monotonic[0].observed_sign` | -1 |
| `logic_probes.monotonic[0].expect_sign` | -1 |
| `logic_probes.monotonic[1].more` | `h_m_mass_transfer_coefficient` |
| `logic_probes.monotonic[1].then` | `t_star_drying_time_hours` |
| `logic_probes.monotonic[1].observed_sign` | -1 |
| `logic_probes.monotonic[1].expect_sign` | -1 |
| `logic_probes.monotonic[2].more` | `R0_initial_radius` |
| `logic_probes.monotonic[2].then` | `t_star_drying_time_hours` |
| `logic_probes.monotonic[2].observed_sign` | 1 |
| `logic_probes.monotonic[2].expect_sign` | 1 |
| `logic_probes.monotonic[3].more` | `C0_initial_moisture` |
| `logic_probes.monotonic[3].then` | `t_star_drying_time_hours` |
| `logic_probes.monotonic[3].observed_sign` | 1 |
| `logic_probes.monotonic[3].expect_sign` | 1 |

### `problem_1_results.json`（21 条）

| 数据路径 | 数值 |
|---|---|
| `problem` | 1 |
| `p1_T_1800_5pt[0]` | 33.5764 |
| `p1_T_1800_5pt[1]` | 33.773 |
| `p1_T_1800_5pt[2]` | 34.3651 |
| `p1_T_1800_5pt[3]` | 35.3629 |
| `p1_T_1800_5pt[4]` | 36.786 |
| `p1_C_1800_5pt[0]` | 2.55 |
| `p1_C_1800_5pt[1]` | 2.5496 |
| `p1_C_1800_5pt[2]` | 2.5376 |
| `p1_C_1800_5pt[3]` | 2.3763 |
| `p1_C_1800_5pt[4]` | 1.5125 |
| `p1_conservation_residual` | 5.611e-16 |
| `p1_picard_residual_max` | 9.94e-12 |
| `p1_surface_cv_residual` | 4.102e-14 |
| `p1_dD_dT_rel_perturb` | 0 |
| `p1_D_at_C0` | 4.938e-09 |
| `p1_bessel_rel_err_l2` | 0.0002837 |
| `p1_bessel_max_abs_err` | 0.0009803 |
| `p1_bdf_cross_check_max_abs_diff` | 0.0005768 |
| `p1_n_rows` | 1801 |
| `p1_discrete_measure_sum_error` | 0 |

### `problem_2_results.json`（23 条）

| 数据路径 | 数值 |
|---|---|
| `problem` | 2 |
| `p2_T_3h_5pt[0]` | 49.8495 |
| `p2_T_3h_5pt[1]` | 49.8554 |
| `p2_T_3h_5pt[2]` | 49.8746 |
| `p2_T_3h_5pt[3]` | 49.9101 |
| `p2_T_3h_5pt[4]` | 49.9664 |
| `p2_C_3h_5pt[0]` | 1.7662 |
| `p2_C_3h_5pt[1]` | 1.7165 |
| `p2_C_3h_5pt[2]` | 1.5701 |
| `p2_C_3h_5pt[3]` | 1.3331 |
| `p2_C_3h_5pt[4]` | 1.0078 |
| `p2_conservation_residual` | 4.798e-16 |
| `p2_picard_residual_max` | 9.997e-12 |
| `p2_picard_trace[0]` | 0.002137 |
| `p2_picard_trace[1]` | 9.532e-07 |
| `p2_picard_trace[2]` | 3.173e-11 |
| `p2_picard_trace[3]` | 1.066e-14 |
| `p2_picard_n_iter` | 4 |
| `p2_picard_monotone` | True |
| `p2_k_radial_dispersion` | 0.118816 |
| `p2_surface_cv_residual` | 3.368e-13 |
| `p2_n_rows` | 10801 |
| `p2_discrete_measure_sum_error` | 0 |

### `problem_3_results.json`（30 条）

| 数据路径 | 数值 |
|---|---|
| `problem` | 3 |
| `p3_t_star_h` | 57.2621 |
| `p3_cmax_cross` | 0.149995 |
| `p3_cmax_prev` | 0.150013 |
| `p3_argmax_r_end` | 0 |
| `p3_cmax_monotone` | True |
| `p3_C_surface_minus_C_air` | 0.002637 |
| `p3_Cs_end` | 0.0524968 |
| `p3_Cair_end` | 0.04986 |
| `p3_conservation_residual` | 4.381e-16 |
| `p3_picard_residual_max` | 9.986e-12 |
| `p3_center_6h_marks_h[0]` | 6 |
| `p3_center_6h_marks_h[1]` | 12 |
| `p3_center_6h_marks_h[2]` | 18 |
| `p3_center_6h_marks_h[8]` | 54 |
| `p3_center_6h_marks_h[...]` | `<5 项省略>` |
| `p3_center_6h_values[0]` | 1.01716 |
| `p3_center_6h_values[1]` | 0.455768 |
| `p3_center_6h_values[2]` | 0.298448 |
| `p3_center_6h_values[8]` | 0.153637 |
| `p3_center_6h_values[...]` | `<5 项省略>` |
| `p3_spatial_order_p` | 1.925 |
| `p3_spatial_t_star_h.20` | 57.2621 |
| `p3_spatial_t_star_h.40` | 57.2322 |
| `p3_spatial_t_star_h.80` | 57.2244 |
| `p3_interface_t_star_h.kirchhoff` | 57.2621 |
| `p3_interface_t_star_h.arithmetic` | 56.2297 |
| `p3_interface_t_star_h.harmonic` | 557.761 |
| `p3_n_rows` | 3437 |
| `p3_discrete_measure_sum_error` | 0 |

### `problem_4_results.json`（24 条）

| 数据路径 | 数值 |
|---|---|
| `problem` | 4 |
| `p4_t_star_h` | 50.8975 |
| `p4_t_star_dense_h` | 50.8778 |
| `p4_cmax_cross` | 0.149995 |
| `p4_cmax_prev` | 0.150026 |
| `p4_argmax_r_end` | 0 |
| `p4_R_tstar_cm` | 1.2 |
| `p4_R_interp_rel_error_max` | 0 |
| `p4_R_max_positive_diff` | 0 |
| `p4_rho_s_R2_invariant` | 0.0401375 |
| `p4_conservation_residual` | 3.259e-16 |
| `p4_picard_residual_max` | 9.998e-12 |
| `p4_center_6h_marks_h[0]` | 6 |
| `p4_center_6h_marks_h[1]` | 12 |
| `p4_center_6h_marks_h[2]` | 18 |
| `p4_center_6h_marks_h[7]` | 48 |
| `p4_center_6h_marks_h[...]` | `<4 项省略>` |
| `p4_center_6h_values[0]` | 1.7156 |
| `p4_center_6h_values[1]` | 0.735007 |
| `p4_center_6h_values[2]` | 0.407275 |
| `p4_center_6h_values[7]` | 0.155765 |
| `p4_center_6h_values[...]` | `<4 项省略>` |
| `p4_n_rows` | 3055 |
| `p4_discrete_measure_sum_error` | 0 |

### `sensitivity_results.json`（13 条）

| 数据路径 | 数值 |
|---|---|
| `module` | `sensitivity` |
| `p3_hold_h` | 57.2621 |
| `p3_mean_h` | 57.567 |
| `p3_linear_h` | 57.1152 |
| `p3_mean_rel_pct` | 0.5325 |
| `p3_linear_rel_pct` | -0.2564 |
| `p4_hold_h` | 50.8975 |
| `p4_mean_h` | 51.1656 |
| `p4_linear_h` | 50.7815 |
| `p4_mean_rel_pct` | 0.5267 |
| `p4_linear_rel_pct` | -0.2279 |
| `p3_latent_h` | 62.6458 |
| `p3_latent_rel_pct` | 9.4019 |
