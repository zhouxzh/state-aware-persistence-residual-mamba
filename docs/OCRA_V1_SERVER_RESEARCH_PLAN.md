# OCRA-v1 研究计划：可观测性认证的持久性残差准入

**项目**：state-aware-persistence-residual-mamba
**计划版本**：`ocra_v1`
**文档状态**：协议文本已按 2026-10-20 审核修订；在 `protocol.json` 与 seed 不相交检查完成前，不得开训
**撰写日期**：2026-10-20
**修订日期**：2026-10-23
**目标服务器**：zhong3（当前 DSH 未登记该服务器，执行前必须先完成环境探测）
**证据边界**：本计划只针对 `canonical_v2` 九类变化机制的独立合成复核，不覆盖 SAPR V3/V3.1 真实来源确认，也不覆盖 `sim_v5`。
**本文档**：`state-aware-persistence-residual-mamba/docs/` 下的唯一研究计划。

---

## 1. 一页摘要

SAPR 草稿已经显示：在已见趋势折点和可见季节形态变化上，无门控 Mamba 残差可以优于持久性、线性残差和 DLinear；但在局部稳定、仅方差改变和近随机游走上，原学习标量门没有满足关闭条件，因此“状态感知门有效”的主张不成立。草稿同时写明：局部稳定段上残差仍明显优于持久性，不能写成“稳定就应退回持久性”。

后续文献检索发现，RAEGL（arXiv:2609.33340）已经覆盖了通用的“默认保留全局预测器，只在预部署证据支持时开启 contextual residual”框架。因此本项目不再研究泛化的证据门控，而研究一个更窄的问题：

> 能否仅用预测原点之前的历史，判断均值路径变化是否已经可观测，并据此选择 `OPEN`（开启 Mamba 残差）、`DEFER`（交给 DLinear）或 `CLOSED`（回退持久性）？

本计划提出 **OCRA-v1（Observability-Certified Residual Admission）**。其核心不是把 sigmoid 门训练得更好，而是把残差准入写成一个带约束的三状态决策。`CLOSED` 在此表示**不对已见均值路径变化启用非线性残差**；若局部稳定原点被关闭，将有意放弃草稿已记录的稳定段自相关增益。这是保守准入政策，不是对 SAPR 安全阈值的重述。

主终点不是混合机制上的平均 RMSE，而是在验证集匹配正例开启率后，对预先指定负原点集合假开启率的控制。开启率一律按**原点真值**计算，不按机制行名汇总。

---

## 2. 研究问题与假设

### 2.1 研究问题

在预测原点只使用历史窗口 `x_{t-L+1:t}` 时，能否构造一个因果可审计的观测状态，使非线性残差只在“结构变化已进入历史且简单规则不足”时介入，并在不可预报或仅方差改变时默认回退？

### 2.2 主假设与匹配方向

操作化采用 Neyman–Pearson 式匹配：**固定正例开启率，比较假开启率**。这与 wiki claim C1 一致；已采纳 idea 原文中“匹配假开启、比较真开启”的句子以本计划为准。

在全新的 `ocra_v1` 合成复核协议上，OCRA 三状态证书将比容量匹配、以残差增益为监督的单证据门，在匹配正例开启率时获得更低的负原点假开启率；同时在已见趋势折点和季节形态变化上，意向混合器保留无门控 Mamba 残差相对持久性、线性残差和 DLinear 的优势；在局部稳定、未见跳变、仅方差改变和近随机游走上，假开启与误路由不超过预设上限，并满足预先声明的非劣性。

### 2.3 可证伪性

以下任一情况都将使主假设失败：

1. 正例开启率匹配后，OCRA 的宏平均假开启率没有达到预先规定的下降，或配对 bootstrap 上界不小于 0；
2. 负原点上的 `OPEN` 或 `DEFER` 超过预设上限，或相对持久性超过非劣性上界；
3. 意向混合器在已见趋势折点或季节形态变化上丢失残差增益；
4. 已见水平跳变的真可见原点没有按预期进入 `DEFER`；
5. shuffled-evidence 对照没有失去选择性；
6. 证书依赖未来信息、机制标签、序列身份或测试集调参。

---

## 3. 与最近工作的区别

### 3.1 残差增益门对照，而不是复刻 RAEGL

RAEGL 默认保留已验证的全局预测器，并通过预部署证据决定是否启用 contextual residual。OCRA 不复刻作者代码，也不把对照写成 RAEGL 复现。确认性对照是 **容量匹配的残差增益门**（下文称 GainGate）：

- 证据单元是预测原点级可观测性，不是 context 级历史有效性；
- 动作是 `OPEN / DEFER / CLOSED` 三状态，GainGate 只有 open/closed；
- OCRA 的监督是生成器原点真值映射出的目标动作；GainGate 的监督是该原点上无门控残差是否同时优于持久性与 DLinear；
- 主要指标是匹配正例开启率下的负原点假开启率，不是混合平均误差。

若 E2 显示 GainGate 在 validation 上已无法与 OCRA 匹配操作点，启动第 16 节停止规则 3，不得改用机制标签去训练 GainGate 以挽救 C1。

### 3.2 Anchor-plus-residual 与路由模型

Persistence Initialization、Global Persistence/Local Residual、AME-TS、FAME 和 Regime-Gated Residual MoE 等工作已经覆盖锚点、残差专家和结构/regime 路由。本项目固定 Mamba 残差，不声称新的编码器或 MoE 架构；贡献限于可观测性状态机、预注册的阴性对照和机制选择性评估。

### 3.3 选择性预测

Bounded-Abstention 和结构感知 abstention 等工作处理是否输出预测。OCRA 不弃权，而是选择一个有明确科学含义的安全回退动作：持久性或 DLinear。

---

## 4. Claims 与 wiki 记录

这些 claim 已在 DSH wiki 中以 `pending` 状态登记。判定以本节与第 12 节为准。

| ID | Claim | wiki claim id |
|---|---|---|
| C1 | 在验证集匹配正例开启率后，OCRA 在测试集负原点上的宏平均假开启率低于容量匹配 GainGate | `a73331f9-b291-49bd-b256-3f27ee7e6e4f` |
| C2 | OCRA 在局部稳定、未见跳变、仅方差改变和近随机游走的指定原点集合上，假开启与误路由不超过上限，并相对持久性满足非劣性 | `8b40c6a4-4452-4b26-96c6-14f690ba0d2a` |
| C3 | 在已见趋势折点和可见季节形态变化上，意向混合器保留相对持久性、线性残差和 DLinear 的增益，且不显著劣于无门控 Mamba | `8c7a6320-2957-41a6-9902-faac97d54538` |
| C4 | 已见水平跳变的真可见原点被路由到 DLinear，混合器相对该冻结简单规则非劣 | `f2df54bb-4871-4b13-9a12-481457329685` |
| C5 | 选择性来自预测原点前可观测证据，而不是未来信息、机制标签、序列身份或无效阈值 | `c1669a87-44fe-414e-bba6-c260b3a01ef4` |
| C6 | 删除稳定区间特征、方向一致特征或三动作分解会显著降低选择性或正例保留 | `6d6d6475-e591-459a-b950-0d2b69a6bf4e` |
| C7 | C1 与 C3 的方向在预先枚举的确认性稳健性格子上保持；lookback 与噪声扰动只进入 E8，不确认 C7 | `9f6e54c6-3a00-4303-9e1a-c8dcda95237a` |

---

## 5. 协议锁 `ocra_v1`

### 5.1 为什么必须新建协议

原 `canonical_v2` 的测试结果已经被查看，不能在同一测试序列上反复选择 OCRA 特征或阈值。`ocra_v1` 必须：

- 复用 `canonical_v2` 的九类机制定义与生成器版本族 `sapr_sim_canonical_v2.0` 的机制语义；
- 使用未参与原 SAPR 结果的 fresh generator seeds 与新的 `series_id`；
- 使用独立的 train / calibration / test series；
- 在所有代码和阈值冻结后，只评估 test 一次。

如果无法生成新的 disjoint test seed，则所有结果只能标记为 post hoc exploratory，不能支持 C1–C7 的确认性结论。

### 5.2 从 `canonical_v2` 拷贝并冻结的常量

| 项 | 冻结值 |
|---|---|
| 序列长度 `T` | 2048 |
| 历史长度 `L` | 384 |
| 季节周期 `P` | 48 |
| 预测步长 `H` | `{12, 24, 48, 96}` |
| 测试原点间隔 | `H_max = 96` |
| 普通机制序列数 train/val/test | 200 / 50 / 100 |
| 局部稳定、稳定季节 train/val/test | 300 / 100 / 200 |
| 测试序列总数 | 1100 |
| 训练种子个数 | 5 |
| Mamba 几何 | 两层，隐维 64，状态维 16，卷积宽度 4，扩展因子 2，dropout 0.1 |
| 优化 | AdamW `3e-4`，batch 64，最多 40 epoch，早停耐心 7 |
| 训练目标 | 路径均方误差 |
| 窗宽 | `p=48`，`w_s=12`，`w_m=48`，`w_l=192` |

### 5.3 黑名单与新种子

`canonical_v2` 已用训练种子 `{20262201, 20262202, 20262203, 20262204, 20262205}`。其测试 `series_id` 共 1100 条，命名形如 `test_stable_0000` … `test_random_walk_0099`。对 `reproducibility/sapr_canonical_v2/sequence_metrics.csv` 中唯一 `series_id` 排序后以 UTF-8 换行拼接的 SHA-256 为

```text
69589e33e194f058d26f3eda5d04611d3f26ffb33d417d58bca659c07572eda0
```

`ocra_v1` 冻结：

- 训练种子：`{20261021, 20261022, 20261023, 20261024, 20261025}`
- `series_id` 前缀：`ocra_v1_`
- 生成器主种子：`20261020`
- 黑名单：上述五个 canonical 训练种子，以及该 1100 条 `series_id`

E1 必须重算黑名单哈希并与上式比对，再对 `ocra_v1` 的 `series_id` 集合做空交集检查。任一失败则停止。

### 5.4 冻结清单

在跑主实验前生成并保存：

- generator source hash；
- mechanism config hash；
- split manifest hash；
- 第 5.2 节常量；
- 黑名单哈希与不相交证明；
- code commit；
- Python / PyTorch / CUDA / GPU driver 版本；
- analysis script hash；
- `ψ_t` 特征公式哈希；
- 证书模型类与正则网格；
- action thresholds；
- claim thresholds；
- random seed manifest；
- output directory checksum policy。

建议文件：

```text
results/ocra_v1_r2/protocol/
  protocol.json
  split_manifest.parquet
  seed_manifest.json
  blacklist_check.json
  environment.json
  code_commit.txt
  file_hashes.sha256
```

### 5.5 一次性 test 规则

- Test 数据在实现、超参数选择、阈值校准和消融代码完成前不可加载。
- Calibration 只使用 validation split。
- 若 test 已运行后发现代码或阈值错误，必须新建 `ocra_v1.1` 和新的 test seed。
- 不得删除表现不利的 origin 或 seed。
- 预检只用 `H=24` 与训练种子 `20261021`，不得使用 test split。

---

## 6. 数据、原点真值与机制矩阵

### 6.1 原点真值，而不是机制行名

每个原点必须带有与 `canonical_v2` 覆盖表一致的真值标签 `true_label ∈ {stable, visible_change, unseen_change}`，与检测器状态分开保存。开启率、假开启率和动作准确率只在下表指定的原点集合上计算。序列级 RMSE 仍按 SAPR：先在该序列全部合法原点上汇总路径误差，再对五个训练种子匹配平均。混合器在每个原点使用该原点动作对应的预测，**禁止先按动作筛选原点再比 RMSE**。

### 6.2 机制、目标动作与评价集合

| 机制 | 真值标签 | 目标动作 | 评价集合 | 评价重点 |
|---|---|---|---|---|
| 局部稳定 | `stable` | `CLOSED` | N0 = 该行全部原点 | 假开启、假 `DEFER`、安全非劣性 |
| 已见水平跳变 | `visible_change` | `DEFER` | T1-vis | 正确转交 DLinear |
| 已见水平跳变 | `stable` | `CLOSED` | 诊断 | 跳变前不得开启 |
| 窗口内未见跳变 | `unseen_change` | `CLOSED` | N2 = 仅真未见原点 | 不得利用未来跳变 |
| 窗口内未见跳变 | `stable` | `CLOSED` | 诊断 | 破位前稳定段 |
| 持续线性趋势 | `visible_change` | `DEFER` | 诊断 | 不进 C1 正例；`OPEN` 作诊断 |
| 已见趋势折点 | `visible_change` | `OPEN` | S+ 的一半 | 正例开启与意向 RMSE |
| 已见趋势折点 | `stable` | `CLOSED` | 诊断 | 折点前不得计入正例开启 |
| 稳定季节 | `stable` | `CLOSED` | 诊断 | 季节朴素只作对照 |
| 季节形态变化 | `visible_change` | `OPEN` | S+ 的一半 | 正例开启与意向 RMSE |
| 季节形态变化 | `stable` | `CLOSED` | 诊断 | 变化前不得计入正例开启 |
| 仅方差改变 | 全部 | `CLOSED` | N7 = 该行全部原点 | 不以点 RMSE 为成功 |
| 近随机游走 | 全部 | `CLOSED` | N8 = 该行全部原点 | 阴性对照 |

`S+` = 已见趋势折点与季节形态变化的 `visible_change` 原点并集。持续线性趋势和稳定季节不进入 `S+`。持续趋势上 `OPEN` 率只作诊断，预设报告阈值 `≤25%`，不并入 C1–C4。

### 6.3 动作执行器（唯一）

| 动作 | 预测 |
|---|---|
| `OPEN` | 冻结的无门控 Mamba 残差 |
| `DEFER` | DLinear |
| `CLOSED` | 持久性 |

线性残差与季节朴素保留为对照，不作为动作执行器。C4 的简单规则冻结为 DLinear，不在 test 上选择“最佳”。

### 6.4 数据切分

```text
train:
  - 用于训练 Mamba 残差骨干
  - 不向证书拟合暴露机制标签或 true_label

calibration / validation:
  - 用于证书拟合、阈值、动作约束
  - 可读取 validation 的机制标签与 true_label
  - 不得用于训练残差骨干
  - GainGate 可读取该 split 上的原点级残差误差，不得读取机制名

test:
  - 一次性评估
  - 不得用于选择特征、阈值、seed 或消融
```

Validation 与 test 使用不同 `series_id`。不能把同一序列的重叠窗口拆到不同 split。

---

## 7. OCRA-v1 方法定义

### 7.1 固定残差骨干

沿用 SAPR 草稿的 Mamba 残差实现：

- 持久性基线 `b_{t,1:H} = x_t * 1_H`；
- 窗口末值中心化与总体标准差标准化；
- Temporal Mamba 编码器，输入 `[z_ℓ; φ_t]`，几何见第 5.2 节；
- 路径残差头；
- 与无门控、常数门和原 sigmoid 状态门共享参数预算与训练配置。

OCRA 不重新设计 Mamba，也不使用 OCRA 结果声称编码器架构优越。`φ_t` 仍按 SAPR 拼进 Mamba 输入。证书另算 `ψ_t`，不得把机制标签或 `series_id` 拼入任一输入。

### 7.2 历史观测证据 `ψ_t`（冻结）

`ψ_t` 只能由 `x_{t-L+1:t}` 计算。稳健尺度

```text
s(v) = max{1.4826 MAD(v), SD_0(v), 10^{-6}}
```

`ψ_t` 为九维 `φ_t` 与下列附加量的拼接，缺测或非有限值置 0：

1. `delta_mean`：最近 `w_m` 的中位数减去 `w_l` 窗口前段长度为 `w_m` 的中位数，再除以 `s(w_l)`；
2. `early_late_mean`：`w_l` 前 2/3 与后 1/3 的均值差，除以 `s(w_l)`；
3. `dir_agree`：`φ_t` 三个斜率窗同号且均非 0 时取 1，否则 0；
4. `post_jump_stability`：在最近 `w_m` 内取 `|Δx|` 最大处 `j`；`j` 之后样本的 `s` 除以 `j` 之前样本的 `s`；若任一侧少于 4 个点则取 1；
5. `season_shape_dist`：最近一个完整周期与上一完整周期各自去均值后的欧氏距离，除以 `s`；不足两个完整周期则取 0；
6. `season_phase_shift`：上述两周期圆形互相关最大滞后除以 `P`；不足则取 0；
7. `rw_proxy`：`w_l` 上水平方差除以一阶差分方差。

特征在 calibration 上计算均值与标准差，并用于其后所有 split 的标准化。公式一旦写入 `protocol.json` 不得因 test 结果增删。

### 7.3 共享证书，不随 `H` 改变

证书只读 `ψ_t`，不读 `H`、未来窗口、机制标签或 `series_id`。四个 horizon 共用一套动作。因此正例开启率与假开启率只报告一次；四跨度条款只用于 RMSE 与非劣性。

证书模型类冻结为两阶段 L2 逻辑回归：

1. 阶段 A：`OPEN` vs 非 `OPEN`；
2. 阶段 B：在目标为 `DEFER` 或 `CLOSED` 的 calibration 原点上拟合 `DEFER` vs `CLOSED`；推断时仅当阶段 A 判为非 `OPEN` 才调用。

正则网格冻结为 `C ∈ {0.01, 0.1, 1, 10}`，在 calibration 上 5 折对数损失选择，不得扩展网格。不得改用树模型、多层网络或多分类交叉熵来替换此两类器。

### 7.4 校准算法（只使用 validation）

记 `TPR` 为 `S+` 上的 `OPEN` 率。在 validation 上：

1. 按第 7.3 节拟合两阶段模型；
2. 扫描阶段 A 阈值，保留同时满足以下约束的可行集：`TPR ≥ 80%`，且 N0、N2、N7、N8 上 `OPEN ≤ 10%`；
3. 若可行集为空，放宽为：在全部负集合 `OPEN ≤ 10%` 的前提下最大化 `TPR`；若仍空，停止规则 3；
4. 在可行集中选择使 N0、N2、N7、N8 宏平均假开启最小的阈值；并列时取更高 `TPR`；
5. 再扫描阶段 B 阈值：在 T1-vis 上 `DEFER ≥ 80%` 且 `OPEN ≤ 10%`，同时 N0、N2、N8 上 `DEFER ≤ 20%`，N7 上 `CLOSED ≥ 80%`；不可行则停止规则 3。

阈值选定后写入 `action_thresholds.json`，其后不得因 test 修改。

### 7.5 GainGate 对照

容量匹配的单证据门：

- 同一标准化 `ψ_t`，同一 L2 逻辑回归族与同一 `C` 网格；
- 监督：calibration 原点上若无门控残差路径 RMSE 同时小于持久性与 DLinear，则 `y_gain = 1`，否则 0；
- 不读取机制名、`true_label` 或三状态目标；
- 输出单个 open 概率；无 `DEFER`；
- 只在 validation 的 `S+` 上把 open 率匹配到 OCRA 的 ±1 个百分点，用于操作点对齐，不用于训练；
- 匹配失败则停止规则 3。

该实现只作为可复现对照，不声称复刻 RAEGL 作者代码。

### 7.6 两种 shuffle，不得混用

- **C5 归因 shuffle**：将 test 上 `ψ_t` 在机制行内按固定置换打乱与原点的配对，保留边际分布；**不重新拟合**证书，把已冻结证书应用到打乱特征。匹配特异度应下降。
- **E1 未来字段检查**：若实现中存在未使用的未来数组，对其置换不得改变动作。这不是 C5 的归因 shuffle。

---

## 8. 模型与对照组

所有主矩阵残差模型共享第 5.2 节的输入窗口、Mamba 几何、残差头、dropout、optimizer、学习率、训练预算、早停规则和五个 matched training seeds。为遵守 20 个主骨干和 40 次 residual-training 的冻结预算，OCRA-v1.r2 只训练无门控 Mamba（M2）；原 learned sigmoid gate 与常数门均为已冻结负对照，不重新进入 OCRA test 矩阵。

对照组：

1. Persistence；
2. Linear residual；
3. DLinear（`DEFER` 执行器）；
4. Seasonal naive（稳定季节诊断）；
5. Ungated Mamba residual（`OPEN` 执行器）；
6. GainGate；
7. OCRA three-state certificate；
8. OCRA-shuffled（C5，不重训骨干）；
9. OCRA-no-stable-test（去掉 `delta_mean` 与 `early_late_mean`）；
10. OCRA-no-direction（去掉 `dir_agree` 及来自 `φ_t` 的三个斜率维）；
11. OCRA-binary（无 `DEFER`，只做 OPEN/CLOSED）。

简单规则不参与 GPU 训练。证书层在冻结残差预测上拟合。不设需要重训骨干的 capacity-reduced 消融。

---

## 9. 指标

### 9.1 主指标

- Positive admission：`S+` 上的 `OPEN` 比例，四个 horizon 只报一次；
- False-open：N0、N2、N7、N8 各自的 `OPEN` 比例；
- Macro false-open：上述四者的算术平均，C1 主终点；
- False-defer：N0、N2、N8 上的 `DEFER` 比例；N7 上报告 `CLOSED` 率；
- Matched selectivity：validation `S+` 开启率匹配后，test 宏平均假开启之差。

### 9.2 次指标

- 三状态混淆矩阵，分评价集合报告；
- T1-vis 的 `DEFER` / `OPEN` 率；
- 持续趋势诊断 `OPEN` 率；
- 序列级路径 RMSE（意向混合器）；
- Relative path RMSE：`(model - comparator) / comparator`；
- 非劣性上界；
- GainGate 与 OCRA 的 calibration 误差；
- 运行时间、峰值显存和失败率。

### 9.3 不采用的指标

- 跨九机制汇总的单一平均 RMSE；
- 只报告最佳 horizon；
- 只用显著性、不报告效应量；
- 用方差改变上的点 RMSE 改善证明均值路径可预测；
- 用测试集最佳 seed 代替五个 seed 的匹配结果；
- 只在 `OPEN` 原点上比较 RMSE。

---

## 10. 统计协议

- 推断单位：独立 test series；开启率先在指定原点集合上计算，再汇总到 series，再对五 seed 匹配平均。
- 训练 seed：五个 seed 先匹配平均，不把 seed 当作独立样本扩大 n。
- Bootstrap：10,000 次 paired percentile bootstrap。
- RMSE 差异：双侧 95% 区间。
- 非劣性：预先声明的一侧 95% 上界。
- Holm 家族预先列表：
  - 正例保留：2 机制（折点、季节形态）× 3 对照（持久性、线性残差、DLinear）× 4H = 24；
  - 泄漏闸门：N2 与 N8 上混合器相对持久性 × 4H = 8；显著有利于混合器则停止正向 claim，先做 E1；
  - 消融：4 个消融 × 2 个终点（宏平均假开启、`S+` 保留）= 8。
- 局部稳定 2%/5% 安全界只在 `H=96` 上判定，与 SAPR 相同；其余 horizon 仍报告。
- 任何覆盖门失败、缺失或中断必须保留在 manifest 和报告中。

功效：本计划是预先规定阈值的判定研究，不声称等价性试验功效充足。N2 仅使用真未见原点，有效样本量小于该行 100 条序列的全部原点。

---

## 11. 实验矩阵

### E1 — 协议、标签与泄漏审计

**支持/推翻**：C5
**输入**：split manifest、黑名单、证书特征实现、未来字段清单。
**检查**：不得出现未来窗口、机制标签、`series_id`、test 阈值；黑名单哈希一致且交集为空；证书不读 `H`；未来字段置换不改变动作。
**产物**：`e1_leakage_audit.json`、`blacklist_check.json`、`feature_lineage.md`。

### E2 — 证书拟合与动作混淆

**支持/推翻**：C1、C2、C4、C5
**输入**：train 残差骨干、validation。
**输出**：两阶段模型、thresholds、分集合混淆矩阵、calibration curve、GainGate 匹配记录、`δ*`（见第 12 节 C1）。
**规则**：不得读取 test。
**产物**：`certificate_model.*`、`action_thresholds.json`、`validation_confusion.csv`。

### E3 — 主匹配选择性比较

**支持/推翻**：C1、C2、C3
**比较**：OCRA vs GainGate、ungated、original gate、constant gate、persistence、linear、DLinear。
**主终点**：validation 匹配后的 test 宏平均假开启之差。
**产物**：`e3_main_metrics.csv`、`e3_bootstrap.csv`。
**规则**：E1 与 E2 通过后才能加载 test。

### E4 — 已见变化保留与水平跳变转交

**支持/推翻**：C3、C4
**集合**：`S+`、T1-vis；持续趋势只作诊断。
**输出**：意向 RMSE、relative RMSE、动作率。
**产物**：`e4_positive_and_defer.csv`。

### E5 — 阴性原点关闭

**支持/推翻**：C2、C5
**集合**：N0、N2、N7、N8。
**输出**：false-open、false-defer、relative RMSE、非劣性上界、泄漏闸门。
**产物**：`e5_negative_controls.csv`。

### E6 — 组件消融

**支持/推翻**：C6
**变体**：no-stable-test、no-direction、binary-action、shuffled-evidence。全部在冻结骨干上重拟合证书，不重训 Mamba。
**输出**：与 full OCRA 的匹配特异度和正例保留差。
**产物**：`e6_ablations.csv`。

### E7 — 确认性稳健性

**支持/推翻**：C7
**预先枚举的格子（9 个）**：

- 4 个 horizon：C3 意向 RMSE 相对持久性、线性残差、DLinear 的方向（不要求每个格子单独通过 Holm）；
- 5 个 leave-one-training-seed-out：C1 方向，即宏平均假开启 OCRA < GainGate。

通过标准见第 12 节。不新增训练 run。lookback 长度与噪声扰动不在此列。

### E8 — 探索性诊断

**不确认 C1–C7**
可在预算剩余时检查 lookback、预注册噪声、无标签公开/内部序列上的动作率。必须与 E1–E7 分表报告。E8 不能回写阈值，也不能把 C7 扩大到 lookback 或噪声。

---

## 12. 预先固定的通过标准

### C1

全部满足：

- validation `S+` 上 OCRA 与 GainGate 开启率差值绝对值 ≤1 个百分点；
- 配对 95% bootstrap 上界（OCRA 宏平均假开启 − GainGate）< 0；
- test 点估计下降不少于 `δ*`，其中 `δ*` 在 E2 结束后、加载 test 前写入协议：`δ* = min(0.10, 0.5 × validation GainGate 宏平均假开启)`；
- 若 validation GainGate 宏平均假开启 < 0.05，启动停止规则 3，不把 C1 标为 confirmatory。

开启率不随 horizon 重复计数。

### C2

全部满足：

- N0、N2、N7、N8 各自 `OPEN ≤ 10%`；
- N0、N2、N8 各自 `DEFER ≤ 20%`；
- N7 上 `CLOSED ≥ 80%`；
- 局部稳定 `H=96` 相对 persistence：点估计不超过 2% 变差，一侧 95% 上界不超过 5%；
- N2 与 N8 的成功标准是相对 RMSE 上界不超过 5% 变差；若泄漏家族中出现显著优于 persistence，则先做 E1，不把“不显著”本身当作成功。

方差改变只以关闭率判定。若 N0 上证书大量 `CLOSED`，相对持久性的 2%/5% 界几乎自动满足；C2 的鉴别力主要来自假开启、假 `DEFER` 以及 N2/N8 非劣性。

### C3

对趋势折点和季节形态变化的**全部合法原点**（意向混合器，含折点前稳定原点）同时满足：

- 相对 persistence、linear、DLinear 在四个 horizon 上 Holm 后显著更优；
- 相对 ungated Mamba：点估计不超过 2% 变差，一侧 95% 上界不超过 5%；
- validation `S+` 开启率 ≥80%，test 与 validation 差值绝对值 ≤5 个百分点。

### C4

全部满足：

- T1-vis：`DEFER ≥ 80%`，`OPEN ≤ 10%`；
- 相对 DLinear：点估计不超过 1% 变差，一侧 95% 上界不超过 3%；
- 四个 horizon 均成立。

### C5

全部满足：

- future-derived field = 0；
- mechanism-label / series-id 输入 = 0；
- C5 归因 shuffle 后，匹配特异度（1 − 宏平均假开启）至少下降 8 个百分点；
- 无 test-set threshold tuning 或 selective deletion。

### C6

每个消融至少满足一项：

- 匹配宏平均假开启增加 ≥5 个百分点；
- `S+` 保留下降 ≥2 个百分点；
- 导致任一 C2 安全阈值失败。

若某个 ablation 同时改善所有主要指标，则 C6 不通过。

### C7

全部满足：

- 第 11 节枚举的 9 个格子中，至少 8 个重现 C1 或 C3 的预定方向；
- 五次 leave-one-seed-out 的宏平均假开启差中位数 ≤ −0.05（OCRA 更低）；
- 任一 horizon 上 `S+` 意向混合器相对 ungated 的劣势不超过 5 个百分点；
- 不使用旧 `canonical_v2` test `series_id` 或训练种子。

---

## 13. zhong3 执行方案

### 13.1 当前状态

当前 DSH 没有登记 zhong3 服务器，因此本计划不假设 GPU 型号、驱动、CUDA、内存或磁盘空间。上传后先执行环境探测，并把结果写入 `environment.json`。20 GPU-hours 只是停止规则，不是科学约束。

建议上传：

1. 本 Markdown 计划；
2. 协议配置；
3. 独立代码仓库地址或 archive；
4. 数据生成配置；
5. seed manifest 与黑名单检查；
6. checksum 清单。

不要把可执行训练代码复制进本论文仓库。训练代码与本计划在 zhong3 上的位置是 `~/Documents/state-aware-persistence-residual-mamba/`；计划文件为该仓库的 `docs/OCRA_V1_SERVER_RESEARCH_PLAN.md`。运行产物放在该仓库忽略的 `results/ocra_v1_r2/`。`results/ocra_v1/` 保留了未训练的 E1 hash-omission 尝试，`results/ocra_v1_r1/` 保留了未触及 test 的预算校准预检。独立代码仓库的入口名在 E1 前写入 `protocol.json`；下文命令只是接口模板。

### 13.2 推荐目录

```text
~/Documents/state-aware-persistence-residual-mamba/          # 独立代码
~/Documents/state-aware-persistence-residual-mamba/docs/OCRA_V1_SERVER_RESEARCH_PLAN.md
~/Documents/state-aware-persistence-residual-mamba/results/ocra_v1_r2/
  protocol/
  environment/
  checkpoints/
  forecasts/
  metrics/
  bootstrap/
  tables/
  figures/
  reports/
  logs/
  failures/
```

论文仓库只接收：协议元数据、compact metrics、checksums、paper-used figures、claim verdicts、失败和覆盖门记录。

### 13.3 上传前检查

在本地执行并保存：

```bash
git status --short
git rev-parse HEAD
sha256sum state-aware-persistence-residual-mamba/docs/OCRA_V1_SERVER_RESEARCH_PLAN.md
```

在 zhong3 只读预检：

```bash
hostname
nvidia-smi
df -h
free -h
python --version
```

如果目标环境使用 Conda，按服务器现有规范创建独立环境；不要修改共享环境。

### 13.4 运行顺序

```text
E1 protocol/leakage/blacklist audit
  -> backbone preflight (H=24, seed 20261021, no test)
  -> 20 main backbone runs
  -> E2 certificate calibration (writes δ*)
  -> E3 main comparison (first test load)
  -> E4 positive retention/defer
  -> E5 negative controls
  -> E6 ablations
  -> E7 robustness (no new training)
  -> E8 exploratory diagnostics
```

E3 的 test 评估只能在 E1 和 E2 通过后执行。E6/E7 不得修改 E3 的协议或阈值。

### 13.4.1 运行监控与热保护

使用 `scripts/ocra_v1_monitor.py` 记录 OCRA 专用资源状态。无活跃 OCRA 进程时每 1800 秒记录一次完整快照；有活跃 OCRA 进程时每 60 秒检查 GPU 温度，完整快照仍至少每 1800 秒保存一次。温度达到 80 C 记录告警；连续三次达到 85 C 时，监控器只向匹配 `scripts/ocra_v1.py` 的进程发送 `SIGTERM`，保留事件和 manifest，且绝不停止其他项目进程或自动重启训练。

`E2` 的协议性 `stopped_by_protocol` 不属于可自动修复错误：监控器记录状态但不放宽阈值、重训、加载 test 或创建新版本。

### 13.5 指令模板

当前实现的入口为 `scripts/ocra_v1.py`；所有命令从本仓库根目录使用
`conda run --no-capture-output -n sci-agent` 执行。`seal` 只创建 test roster，不物化
test 数值数组；`evaluate-once` 在 E2 通过后写入访问锁并首次物化、读取 test 数值。

```bash
conda run --no-capture-output -n sci-agent python scripts/ocra_v1.py seal
conda run --no-capture-output -n sci-agent python scripts/ocra_v1.py preflight
conda run --no-capture-output -n sci-agent python scripts/ocra_v1.py \
  train-bundle --horizon 24 --seed 20261021 --preflight

# 通过预检后，对 4 个 horizon 和 5 个登记 seed 逐一运行 train-bundle。
conda run --no-capture-output -n sci-agent python scripts/ocra_v1.py fit-certificate
conda run --no-capture-output -n sci-agent python scripts/ocra_v1.py evaluate-once
conda run --no-capture-output -n sci-agent python scripts/ocra_v1.py analyze
```

### 13.6 计算预算

- 主矩阵：20 个共享 Mamba 训练运行（5 seeds × 4 horizons）；
- 证书、GainGate、消融、C7：不重训骨干；
- 额外 20 个训练 run 只用于同一 20 个配置的失败重试，不用于新超参或 lookback；
- 总上限：40 个 residual-training runs 或 20 GPU-hours，先到者停止；
- 主实验开始前必须先跑一次单 backbone 预检，记录显存、耗时和输出大小；
- 不做超参数搜索，除非在协议冻结前完成并记录；
- 训练失败不得用有利 seed 替换。

### 13.7 存储预算

至少预留：

- checkpoints：按单模型大小 × 40；
- forecasts：Parquet，不保存重复完整张量；
- bootstrap：只保存 seed、索引策略和聚合结果，不保存所有重采样数组；
- figure 源文件：PNG/PDF 加生成脚本和 checksum；
- 外部原始数据不进入 Git。

### 13.8 断点与恢复

每次运行目录包含：

```text
run_manifest.json
stdout.log
stderr.log
environment.json
config.resolved.yaml
status.json
metrics.json
```

恢复时必须验证 commit、config hash、seed 和 split hash 一致。任何不一致都产生新 run id，不能覆盖旧结果。

---

## 14. 证据登记与图表

实验运行后：

1. 用 `wiki_note action=add_experiment` 登记每个 run；
2. 完成后用 `set_experiment` 写 `success/failed`、metrics 和 log path；
3. 论文使用的图用 `figure_save` 存档；
4. 失败、覆盖门失败、中断和重复运行必须保留；
5. claim 只在证据满足本文件阈值后由 pending 更新为 supported/invalidated。

建议登记粒度：

- E3 每个 horizon 一个 experiment；
- E6 每个 ablation family 一个 experiment；
- E7 作为一条稳健性 experiment；
- E8 只登记为 exploratory，不与确认性结果合并。

---

## 15. 产物清单

必须产出：

- `protocol.json`
- `split_manifest.parquet`
- `seed_manifest.json`
- `blacklist_check.json`
- `environment.json`
- `code_commit.txt`
- `file_hashes.sha256`
- `action_thresholds.json`
- `e1_leakage_audit.json`
- `e2_confusion.csv`
- `e3_main_metrics.csv`
- `e4_positive_and_defer.csv`
- `e5_negative_controls.csv`
- `e6_ablations.csv`
- `e7_robustness.csv`
- `claim_verdicts.csv`
- `ocra_v1_report.md`
- `figures/*.pdf`
- `figures/*.png`
- `logs/*.log`
- `failures/*`

---

## 16. 停止规则

出现以下任一情况，停止主实验并报告：

1. 证书输入包含未来信息、机制标签或 `series_id`；
2. fresh test seed 不可获得，黑名单哈希不一致，或 split 与旧 test `series_id` 重叠；
3. validation 上无法在预设约束内校准出可行动作阈值，或 GainGate 无法在 ±1 个百分点内匹配，或 GainGate 宏平均假开启 < 0.05；
4. E3 运行前 test 已被读取；
5. backbone 训练不稳定，无法在固定预算内收敛；
6. 计算预算超过 20 GPU-hours 或 40 个 residual-training runs；
7. 运行 manifest、代码 commit 或数据 hash 不一致；
8. 结果只能通过改变阈值、删除 origin 或挑选 seed 得到。

停止不是失败隐藏：失败原因、日志、覆盖门和已消耗预算必须保留。

---

## 17. 时间安排

| 阶段 | 工作 | 预计 |
|---|---|---|
| D1 | 协议冻结、seed/split/hash/黑名单 | 0.5 天 |
| D2 | 泄漏审计、数据检查、单 run 预检 | 0.75 天 |
| D3–D4 | baseline、GainGate、OCRA 实现 | 1.5 天 |
| D5–D7 | 20 个主 backbone 运行与 E2–E5 | 2–3 天 + GPU |
| D8–D9 | E6 消融与 E7 稳健性 | 1 天，无额外训练 |
| D10 | bootstrap、Holm、claim verdict | 1 天 |
| D11–D12 | 独立复核、复现实验包 | 1.5 天 |
| D13 | E8 探索性诊断 | 仅在预算剩余时 |

实际时间以 zhong3 单 run 预检结果为准，但不得通过减少 seeds、horizons 或 test series 来压缩确认性实验。

---

## 18. 完成定义

本项目只有在以下条件全部满足时才算完成：

- `ocra_v1` 协议和代码 commit 可追溯；
- 黑名单检查通过；
- E1–E7 每个实验都有 run manifest、状态和日志；
- C1–C7 每条 claim 都有 supported / invalidated / pending 的明确结论；
- 测试集只评估一次；
- 失败和阴性结果留在证据库；
- 论文用图有源数据和 checksum；
- 独立复核者能从协议、seed、hash 和命令重建主要表格；
- 结论严格限制在 canonical 机制仿真范围。
