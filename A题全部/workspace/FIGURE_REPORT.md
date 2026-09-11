# 数据图与表格生成报告（paper-figure 步骤）

生成日期：2026-09-11　　题目：CUMCM 2026 A 题「药材的烘干问题」
配色 `dutch_field`　版式 `framed_journal`　语言 中文　输出 矢量 PDF

产出：22 张数据图（`figures/fig_*.pdf`）、5 张 LaTeX 表格、`figures/latex_includes.tex`。
流程/架构图（`fig_roadmap` 等）与情景示意图（`fig_scene`）由 `paper-figure-html`
与 GPTIMG 步骤产出，不属本步骤范围。

---

## 1. FIGURE_MANIFEST 对账

规划见 `MODELING_REPORT.md` §12（F01--F19，19 张数据图）。逐条对账如下，
**无一条规划判断缺图**。

| 规划 | 承担的判断 | 实际图件 | 处置 |
|---|---|---|---|
| F01 | 环境驱动的实际形态 | `fig_env_driving` | 按规划 |
| F02 | 预热段水分只动表层 | `fig_field_heatmap_p1`(b) | 合并为热力图，判断不变 |
| F03 | 温度渗透快于水分 | `fig_field_heatmap_p1`(a)、`fig_radial_profiles`(a) | 按规划 |
| F04 | 可核对的离散锚点 | `TABLE_main_results` | 转为表格（数值锚点用表比图精确） |
| F05 | P2 水分场整体演化 | `fig_field_heatmap_p2` | 按规划 |
| F06 | P2 温度场已近均匀 | `fig_temp_contour_p2` | 按规划 |
| F07 | 两个时间尺度分离 | `fig_timescale_split` | 按规划 |
| F08 | 变物性的非线性程度 | `fig_diffusivity_contour`、`fig_diffusivity_range` | 拆为两图（响应面 + 量级对比） |
| F09 | 终点判据的定位方式 | `fig_drying_curve` | 按规划 |
| F10 | 干燥速率随时间递减 | `fig_ridgeline_profile` | 改山脊图（更清楚地分离各时刻） |
| F11 | 速率递减的定量刻画 | `fig_stage_rate` | 按规划 |
| F12 | 收缩与脱水的耦合 | `fig_radius_shrink`、`fig_shrink_field` | 拆为两图（插值质量 + 场演化） |
| F13 | 动边界与留空语义 | `fig_shrink_field` | 按规划 |
| F14 | P4 比 P3 快是净差 | `fig_orthogonal_waterfall` | 按规划 |
| F15 | 离散阶落在理论预期 | `fig_convergence` | 按规划 |
| F16 | 残差在机器精度 | `fig_conservation` | 改棒棒糖图（见下方说明） |
| F17 | 界面平均是实质决策 | `fig_interface_scheme` | 按规划 |
| F18 | 不确定度来源排序 | `fig_sensitivity_tornado` | 按规划 |
| F19 | 收缩假设有独立证据 | `fig_shrink_evidence` | 按规划 |

规划外新增 3 张（均承担规划中未覆盖的独立判断）：

| 新增 | 承担的判断 |
|---|---|
| `fig_analytic_validation` | 数值解与 Bessel 级数解析解逐点一致，$R^2=0.999996$ |
| `fig_biot_regime` | 传质毕奥数跨三个量级（1.49→5226），存在真实的控制机制转换 |
| `fig_surface_3d` | 含水率时空曲面与达标阈值平面的相交关系 |

**F16 口径说明（如实标注）**：规划要求「守恒残差 $\varepsilon_{cons}(t)$ 随时间」，
现有 `figures/*_results.json` 只保存了各问的**终值**残差，未保存逐时间步序列。
`fig_conservation` 因此改为棒棒糖图，横轴对数展示 9 项校核残差的量级，
覆盖了「残差在机器精度」这一判断；「不随时程累积」这一子判断
**未由本图证明**，其证据是 Picard 终残差上界 $9.998\times10^{-12}$
与四问守恒残差同处 $10^{-16}$ 量级（时程相差 30 倍而残差量级不变）。

图型统计：16 种——双轴时序、多面板热力图、Hovmöller 图、等值线、山脊图、
变域留空热力图、三维曲面、阈值穿越（带放大插图）、阶段柱状+对数折线、
正交瀑布、双对数收敛、棒棒糖残差、断轴柱状、龙卷风、机制分区带、
散点-折线叠合。用户「图要多样化」的要求以此落实。

---

## 2. 逐图证据溯源

字段口径：**问题/情景** → **脚本** → **数据文件与字段** → **参数条件** →
**样本量** → **统计量与不确定度定义**。凡不可知者写「未知」，不以估读替代。

### 公共前置

**fig_env_driving** — 环境驱动条件
- 脚本 `figures/gen_fig_env_driving.py`；数据 `user_data/附件1.xlsx` 字段 `时间`/`温度`/`水分浓度`
- 条件：题面给定的热风工况，0--4 h（14400 s），采样步长 60 s
- 样本量 241 行（全量，未抽样）
- 统计量：原始时序，无平滑、无拟合；不确定度未知（题面未给测量误差）

**fig_radius_shrink** — 半径收缩与收缩速率
- 脚本 `gen_fig_radius_shrink.py`；数据 `user_data/附件2.xlsx` 字段 `时间`/`半径`
- 条件：0--72 h（259200 s），采样步长 1800 s
- 样本量 145 行（全量）；散点按 `[::6]` 抽稀仅为显示，曲线用全量点
- 统计量：PCHIP 单调插值曲线与其解析导数；平台判据 $|\mathrm{d}R/\mathrm{d}t|<1\%$ 峰值速率
- 不确定度：插值最大相对误差 $0.000$（`all_results.json: R_interp_relative_error_max`），
  即插值在节点处精确复现实测值，无过冲

**fig_diffusivity_range** — 三附录扩散系数量级对比
- 脚本 `gen_fig_diffusivity_range.py`；数据 `PROBLEM_FACTS.json` → `code/params.py`
- 条件：$C\in[0.15,2.55]$ 全区间；附录3/4 的 Arrhenius 项按 $T$ 取题面工况
- 样本量：解析曲线（非采样数据）
- 统计量：公式直算，无拟合。**不采用** `MODELING_REPORT.md` §5.2/§9.1
  的附录3 抄写值（该处误填了类附录4 参数），以 OCR 已核验的
  `PROBLEM_FACTS.json` 为唯一权威来源

**fig_diffusivity_contour** — $D(C,T)$ 二维响应面
- 脚本 `gen_fig_diffusivity_contour.py`；来源同上
- 条件：附录3 公式 $D=2.4\times10^{-3}e^{-0.45/C}e^{-3850/T_K}$
- 统计量：等值线为公式直算；标注 $C=0.15$ 达标线位置

### 问题1（附录2 常物性，预热段）

**fig_field_heatmap_p1** — 温度场与含水率场
- 脚本 `gen_fig_field_heatmap_p1.py`；数据 `result1.xlsx` 工作表 `温度`、`水分浓度`
- 条件：附录2 常物性，固定域 $R_0=2$ cm，$\Delta t=1$ s，$M=20$，时程 0--1800 s
- 样本量 $1801\times21$（全量，两个场各一）
- 统计量：场值本身。图内栅格按 350 DPI 光栅化（矢量化 3.7 万个网格会使 PDF 臃肿），
  全部文字仍为矢量

**fig_radial_profiles** — P1 温度剖面 + P2 含水率剖面
- 脚本 `gen_fig_radial_profiles.py`；数据 `result1.xlsx: 温度`、`result2.xlsx: 水分浓度`
- 条件：同上两问设定；取 6 个代表时刻
- 样本量：每条剖面 21 个径向节点，节点与输出列严格重合（无插值）

### 问题2（附录3 变物性，恒温段）

**fig_field_heatmap_p2** — 含水率场与边缘剖面
- 脚本 `gen_fig_field_heatmap_p2.py`；数据 `result2.xlsx` 两个工作表
- 条件：附录3 变物性，Picard 内迭代容差 $10^{-11}$，$\Delta t=1$ s，时程 0--3 h
- 样本量 $10801\times21$（全量）
- 统计量：主图为场值；上/右边缘为 3 h 剖面与中心/表面时序

**fig_temp_contour_p2** — 温度等值线
- 脚本 `gen_fig_temp_contour_p2.py`；数据 `result2.xlsx: 温度`
- 条件同上；行方向抽稀到约 300 行仅为等值线平滑，不改变数值
- 样本量：抽稀后 $\sim300\times21$；全径向温差由**全量**行计算
- 统计量：终点全径向温差 $\max_rT-\min_rT=0.12$ K（实测，非估计）

**fig_timescale_split** — 时间尺度分离
- 脚本 `gen_fig_timescale_split.py`；数据 `result2.xlsx` 两个工作表
- 样本量 10801 行（全量）
- 统计量：$\max_rT-\min_rT$（对数右轴）与 $C_{\text{中心}}-C_{\text{表面}}$；
  终点值 0.12 K 与 0.76 kg·kg$^{-1}$

### 问题3（附录3 + 附件1 环境，长时程判据）

**fig_drying_curve** — 干燥曲线与阈值穿越
- 脚本 `gen_fig_drying_curve.py`；数据 `result3.xlsx: Sheet1`、`problem_3_results.json`
- 条件：附录3 物性，附件1 环境（覆盖外按 hold 外推），$\Delta t=60$ s，$M=20$
- 样本量 3437 行（全量）
- 统计量：$C_{\max}(t)$、体积平均 $\bar C$（圆柱测度权重 $2r/R^2$）、表面 $C_s$；
  达标时刻 $t^*=57.262062$ h 为**首次穿越**（穿越次数 1，
  穿越前后 $C_{\max}=0.150013\to0.149995$，未取整）
- 不确定度：网格 $M=20/40/80$ 给 $t^*=57.262/57.232/57.224$ h，
  Richardson 观测阶 1.925；时间步 240/120/60/30 s 观测阶 1.215

**fig_ridgeline_profile** — 径向剖面堆叠演化
- 脚本 `gen_fig_ridgeline_profile.py`；数据 `result3.xlsx: Sheet1`
- 条件同上；取 12 个时刻（0/3/6/.../54 h 及 $t^*$）
- 样本量：每条脊线 21 个节点；基线偏移 0.36（显示用，已在轴标签写明）

**fig_stage_rate** — 阶段降幅
- 脚本 `gen_fig_stage_rate.py`；数据 `problem_3_results.json`
  字段 `p3_center_6h_marks_h`/`p3_center_6h_values`，初值锚点取自 `problem_1_results.json`
- 样本量 9 个 6 h 区间
- 统计量：相邻区间中心含水率之差；首段 1.533、末段 0.008（递减两个量级）

**fig_surface_3d** — 时空曲面与阈值平面
- 脚本 `gen_fig_surface_3d.py`；数据 `result3.xlsx: Sheet1`
- 样本量：为渲染性能抽稀后的规则网格；曲面几何不做平滑

**fig_biot_regime** — 传质毕奥数机制转换
- 脚本 `gen_fig_biot_regime.py`；数据 `figures/_plot_data.json: biot_trace`
- 条件：由 `prep_plot_data.py` 以 `record_full=True` 重跑 P3 得到温度场后计算
  $Bi_m=h_mR_0/D(C_s,T_s)$，$h_m=8\times10^{-7}$ m·s$^{-1}$
- 样本量：P3 全时程（3437 输出步）
- 统计量：$Bi_m$ 由 1.489 升至 5226.2（三个量级）；分区阈值
  $Bi_m<1$ 外部对流控制、$1\sim100$ 混合、$>100$ 内部扩散控制
  （通用工程判据，非本题拟合值）

### 问题4（附录4 + 动边界）

**fig_shrink_field** — 收缩域含水率场
- 脚本 `gen_fig_shrink_field.py`；数据 `result4.xlsx: Sheet1`、`附件2.xlsx`、`problem_4_results.json`
- 条件：附录4 物性，Landau 变换 $\xi=r/R(t)$ 固定域求解，$\Delta t=60$ s
- 样本量 $3055\times21$（末列为「药材表面」）
- 统计量：域外以 `np.nan` 留空（非填 0），移动边界叠 $R(t)$ 实测轨迹；
  终态 $R(t^*)=1.2000$ cm，不变量 $\rho_sR^2=0.040137$

**fig_shrink_evidence** — 收缩方式的独立检验
- 脚本 `gen_fig_shrink_evidence.py`；数据 `附件2.xlsx` + `code/params.py` 附录4 密度式
- 条件：**完全不依赖 PDE 求解**，仅用干物质守恒与 $\rho=760+90C$
- 样本量 145 行（附件2 全量）
- 统计量：$V_\infty/V_0=0.3668$；纯径向预测 $R_\infty=R_0\sqrt{V_\infty/V_0}=1.2112$ cm，
  偏差 1.10%；各向同性预测 $R_0(V_\infty/V_0)^{1/3}=1.4313$ cm，偏差 19.47%
  （相对附件2 实测终值 1.198 cm）

**fig_orthogonal_waterfall** — $2\times2$ 正交分解
- 脚本 `gen_fig_orthogonal_waterfall.py`；数据 `all_results.json`
- 统计量：57.26 h（附录3+固定域）→ 129.25 h（换附录4 物性）→ 50.90 h（再加收缩）；
  净差 $-11.11\%$ 是 $+125.7\%$ 与 $-60.6\%$ 两个反向效应的合成

### 模型检验与灵敏度

**fig_analytic_validation** — Bessel 解析对照
- 脚本 `gen_fig_analytic_validation.py`；数据 `_plot_data.json: bessel_pointwise`
- 条件：为构造可解析对照，取 $D$ 恒定 $5\times10^{-9}$ m²·s$^{-1}$、
  $t_{end}=3600$ s、$\Delta t=1$ s、$M=20$、Robin 特征值 $\mu J_1(\mu)=Bi\,J_0(\mu)$ 取 60 根；
  $Bi=h_mR_0/D=3.20$，$Fo=0.045$
- 样本量：排除表面节点后的 20 个内部节点
- 统计量：$R^2=0.9999956$，RMSE $=6.59\times10^{-4}$，$L_2$ 相对误差 $2.84\times10^{-4}$，
  最大绝对误差 $9.80\times10^{-4}$

**fig_convergence** — 收敛阶
- 脚本 `gen_fig_convergence.py`；数据 `problem_3_results.json`、`_plot_data.json`
- 样本量：空间 3 套网格（20/40/80），时间 4 个步长（240/120/60/30 s）
- 统计量：空间以 $M=80$ 为参考，观测阶 1.925（理论 2）；
  时间以 $\Delta t=30$ s 为参考，观测阶 1.215（向后欧拉理论 1）。
  主算步长 60 s 复现主结果 57.262062 h，与独立重跑逐位一致

**fig_conservation** — 残差量级总览
- 脚本 `gen_fig_conservation.py`；数据 `all_results.json`、`problem_1/2_results.json`
- 样本量 9 项校核指标
- 统计量：四问守恒残差 $3.3\times10^{-16}\sim5.6\times10^{-16}$，
  表面控制体残差 $4.1\times10^{-14}$/$3.4\times10^{-13}$，
  Picard 终残差 $9.998\times10^{-12}$，Bessel $L_2$ $2.84\times10^{-4}$，
  BDF 交叉校核 $5.77\times10^{-4}$；判定线 $10^{-8}$

**fig_interface_scheme** — 界面平均方式
- 脚本 `gen_fig_interface_scheme.py`；数据 `problem_3_results.json`、
  `result3.xlsx`、`_plot_data.json`，界面 $\hat D$ 调用 `code/utils.interface_diffusivity`
- 条件：面板 (b) 取 P3 的 12 h 真实 $(C,T)$ 节点剖面
- 统计量：$t^*$ 为 57.26 / 56.23 / 557.76 h（Kirchhoff / 算术 / 调和）。
  调和平均在 $D$ 跨三个量级时被界面最小值锁死，产生非物理结果，故主算禁用

**fig_sensitivity_tornado** — 不确定度排序
- 脚本 `gen_fig_sensitivity_tornado.py`；数据 `sensitivity_results.json`、`all_results.json`、`problem_3_results.json`
- 统计量：H7 固定域 $+153.95\%$、M3 调和 $+874.05\%$、H4 潜热 $+9.40\%$、
  M3 算术 $-1.80\%$、H3 外推 $+0.53\%/-0.26\%$。
  基准为 hold 外推口径（P3 57.262062 h、P4 50.897541 h）

---

## 3. 表格

| 文件 | 内容 | 数据来源 |
|---|---|---|
| `TABLE_main_results.tex` | 四问核心结果汇总 | `problem_1..4_results.json`、`result1-4.xlsx` |
| `TABLE_data_stats.tex` | 附件输入数据描述统计 | `附件1.xlsx`(241)、`附件2.xlsx`(145) |
| `TABLE_properties.tex` | 三套附录物性模型对照 | `PROBLEM_FACTS.json` → `code/params.py` |
| `TABLE_verification.tex` | 数值验证与守恒校核 | `all_results.json`、`_plot_data.json` |
| `TABLE_sensitivity.tex` | 假设扰动对 $t^*$ 的影响 | `sensitivity_results.json`、`all_results.json` |

描述统计的不确定度定义：标准差为样本标准差（$n-1$ 自由度）。
两附件时间列等距采样，故均值与中位数重合，非计算错误。
题面未提供测量误差，故输入数据的观测不确定度**未知**，表中不臆造误差棒。

---

## 4. 门禁结果

| 门禁 | 结果 |
|---|---|
| 脚本数 = PDF 数 | 22 = 22 |
| 规划数据图缺失 | 0（`fig_roadmap`/`fig_scene` 属其他步骤） |
| `figure_check.sh` | 0 违规 + 0 可升级；15 项 `frameon=True` 风格建议 |
| 图内文字预算 | 24 个脚本通过 |
| 原生画布尺寸 | 全部贴合长宽比档位（缩放比 0.9--1.1） |
| `figure_pdf_quality_check.py` | 通过；17 项热力图刻度对比度需视觉复核 |
| 文字越界 / 文字互压 | 0 / 22 张 |
| 文字矢量 | 22 张全部矢量（仅色标渐变与 3 张场图为 350 DPI 光栅） |
| 表格数值溯源 | 43 项全部通过，见 `figures/TABLE_DATA_CHECK_PASSED.txt` |

保留 `frameon=True` 的理由：多张图的图例位于数据密集区上方，
`plot_utils` 的保存期遮挡校验会拒绝透明图例的放置；半透明白底框是
通过该校验且不移动数据的解法。

未完成事项（如实记录）：
1. 守恒残差的**逐时间步**序列未保存于结果 JSON，故 F16 只能给终值量级，
   见 §1 的 F16 口径说明。
2. 热力图色标刻度压在彩色背景上的 17 项对比度告警，属需人眼复核项；
   本步骤未启用视觉 QC（`MH_DATA_FIG_VISION` 未设），故标为待复核而非已合格。
