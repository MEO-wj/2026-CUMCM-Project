# 论文数据真实性核对清单（数据原料）

**模式**: PDF
**JSON 源**: all_results.json, problem_1_results.json, problem_2_results.json, problem_3_results.json, problem_4_results.json, sensitivity_results.json
**JSON 数据条目**: 167
**已生成的 TABLE 文件**: 5 个

---

## 自检步骤（请你按以下顺序执行）

**重要原则**：本工作区的实验/分析阶段已经把所有真实数据存到 `figures/*.json`，
并由 paper-figure 步骤渲染成 `figures/TABLE_*.tex|md`。
**论文数据应能追溯到这些文件或题设，并允许有明确计算依据的派生量、单位换算及舍入。未直接匹配不等于编造。**

### 第 1 步：识别论文中的「数据性数字」

打开你的论文文件，逐章扫描：

- ✅ **需要核对的**：表格里的所有单元格数字、正文里引用实验结果的数字（如 "RMSE 达到 0.023"、"准确率 94%"、"最优解 295.83"、"R² 为 0.94"）
- ⏭️ **不需要核对的**（叙述里自然出现的数字）：
    - 章节编号、列号、引用 [1][2,3]、图编号「图 3-1」
    - 年份「2024 年」、日期「3 月 5 日」
    - 公式中的常数（在 `$...$` 或 `$$...$$` 内）
    - 算法描述里的步骤数「分 5 步」
    - 文献综述里别人论文的数字

### 第 2 步：对每个「数据性数字」核对

对照下方的 JSON 数据清单和 TABLE 文件全文：

1. **能在数据清单/TABLE 文件里找到完全一致的数字** → ✅ 真实，跳过
2. **数据清单里有但论文写错了**（如 RMSE 真实是 0.023，论文写的 0.999） → 改正文，**禁止反向操作**（禁止改 JSON）
3. **数据清单里没有这个数字** → 两种可能：
   - **AI 编造**（最常见）→ 删除该说法或从清单中找正确数据补充
   - **从其他来源算出来的合理派生量**（如百分比 = 子集/总数 ×100）→ 检查派生公式是否合理

### 第 3 步：表格优先用预生成的 TABLE 文件

如果论文里手抄了表格内容，**优先改成** `\input{figures/TABLE_*.tex}` 引入（已经从 JSON 渲染好，不会出错）。

### 第 4 步：自检完成后登记独立回执

后置自检使用本轮任务指定的 `.mh/quality/data-review-ack-*.txt` 和确认值；不要将确认值写入论文。
如果本轮写作上下文仍明确要求兼容旧注释，必须在最终编译之前完成；编译之后不得为登记状态再次改源码。
没有本轮确认值时不要复制旧回执或自行编造；系统只接受与当前内容绑定的有效核对。

**判断原则**：
- 以 JSON 为准修论文，禁止反向修 JSON
- 不必把 JSON 中的每个数字都搬到论文里——只关心论文里出现的数字是否真实
- 不确定某个数字是不是数据 → 当成数据核对一遍，确认能找到来源就行

---

## 图表来源与论断对应（并入本次核对，不启动额外模型轮次）

数字出现过不等于支持当前论断。逐图核对数据所属问题、场景、参数、样本量和统计量；
跨问题引用允许，但必须解释可迁移的结论。一个概率水平的收敛曲线不能直接证明另一个临界点可靠。
下面仅列静态识别的真实文件引用，不代表已经验证数学结论；动态路径请按生成脚本补查。

| 图 | 生成脚本 | 可观察的数据来源 |
|---|---|---|
| fig_analytic_validation | figures/gen_fig_analytic_validation.py | 动态来源，需按脚本定位 |
| fig_biot_regime | figures/gen_fig_biot_regime.py | 动态来源，需按脚本定位 |
| fig_conservation | figures/gen_fig_conservation.py | 动态来源，需按脚本定位 |
| fig_convergence | figures/gen_fig_convergence.py | 动态来源，需按脚本定位 |
| fig_diffusivity_contour | figures/gen_fig_diffusivity_contour.py | 动态来源，需按脚本定位 |
| fig_diffusivity_range | figures/gen_fig_diffusivity_range.py | 动态来源，需按脚本定位 |
| fig_drying_curve | figures/gen_fig_drying_curve.py | 动态来源，需按脚本定位 |
| fig_env_driving | figures/gen_fig_env_driving.py | 动态来源，需按脚本定位 |
| fig_field_heatmap_p1 | figures/gen_fig_field_heatmap_p1.py | 动态来源，需按脚本定位 |
| fig_field_heatmap_p2 | figures/gen_fig_field_heatmap_p2.py | 动态来源，需按脚本定位 |
| fig_interface_scheme | figures/gen_fig_interface_scheme.py | 动态来源，需按脚本定位 |
| fig_orthogonal_waterfall | figures/gen_fig_orthogonal_waterfall.py | 动态来源，需按脚本定位 |
| fig_radial_profiles | figures/gen_fig_radial_profiles.py | 动态来源，需按脚本定位 |
| fig_radius_shrink | figures/gen_fig_radius_shrink.py | 动态来源，需按脚本定位 |
| fig_ridgeline_profile | figures/gen_fig_ridgeline_profile.py | 动态来源，需按脚本定位 |
| fig_sensitivity_tornado | figures/gen_fig_sensitivity_tornado.py | 动态来源，需按脚本定位 |
| fig_shrink_evidence | figures/gen_fig_shrink_evidence.py | 动态来源，需按脚本定位 |
| fig_shrink_field | figures/gen_fig_shrink_field.py | 动态来源，需按脚本定位 |
| fig_stage_rate | figures/gen_fig_stage_rate.py | 动态来源，需按脚本定位 |
| fig_surface_3d | figures/gen_fig_surface_3d.py | 动态来源，需按脚本定位 |
| fig_temp_contour_p2 | figures/gen_fig_temp_contour_p2.py | 动态来源，需按脚本定位 |
| fig_timescale_split | figures/gen_fig_timescale_split.py | 动态来源，需按脚本定位 |

## JSON 真实数据清单

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

---

## 已生成的 TABLE 文件（论文应直接嵌入这些表，不要自己手抄）

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

### `figures/TABLE_verification.tex` (2157 字节)

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
  注：守恒残差定义为 $\big|\Delta\!\int C\,\mathrm{d}V-\int\! q_s\,\mathrm{d}t\big|/\int C_0\mathrm{d}V$，已达双精度舍入量级（$\sim10^{-16}$）。
  空间收敛以 $M=20/40/80$ 三套网格算得，时间收敛以
  $\Delta t=240/120/60$ s 相对 $30$ s 参考解算得；后者为向后欧拉，
  理论一阶，观测 1.215 说明主算步长 60 s 已落在渐近区。}
\end{table}
```
