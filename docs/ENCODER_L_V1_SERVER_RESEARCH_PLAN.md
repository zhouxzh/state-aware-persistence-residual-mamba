# encoder_l_v1 仿真计划：持久性残差、编码器与历史信息的可识别对照

**项目**：state-aware-persistence-residual-mamba
**计划版本**：`encoder_l_v1.r6`
**文档状态**：r6 的70-cell训练已全部完成（0 failed），在完整checkpoint/source-hash审计后经用户授权执行了一次test评估，42项对比和资源表已生成。4项单元测试及ID/种子集合检查通过，但完整审计发现模型描述和采样seed策略与封存源码不一致，且E0没有执行完整内容独立性验证。因此不得将本次运行写成“协议完全符合”或“无偏差预注册确认”。详见[测试前偏差记录](../audit/ENCODER_R6_PRETEST_DEVIATIONS.md)、[结果报告](../evidence/encoder_l_v1_r6/results/encoder_results_report.md)及[历史说明更正](../audit/ENCODER_IMPLEMENTATION_CORRECTIONS_20261025.md)。不将旧轮次混入r6。
**修订日期**：2026-10-25
**目标服务器**：zhong3：`~/Documents/state-aware-persistence-residual-mamba`
**证据边界**：新的九机制合成后续运行；不改写 `canonical_v2`，不使用 OCRA 的阈值或结果，不覆盖 V3/V3.1 与 `sim_v5`。

**执行口径补充（测试前）**：下文保留拟议设计，但不再声称每个文字字段都已按原样实现。实际运行口径见[执行合同](../audit/ENCODER_R6_EXECUTED_CONTRACT.md)，比较族和结果解释见[报告规则](../audit/ENCODER_R6_REPORTING_RULES.md)。MLP实际125/125维、单一推进的采样随机流、C4额外Transformer0比较等差异均需披露；不得通过编辑旧锁文件抹除差异。新结果只能按实际执行范围报告。

---

## 1. 研究目的

`canonical_v2` 支持一个有界经验结论：在已见趋势折点和季节形态变化上，**当前无门控 Mamba 残差实现**相对持久性、短窗线性残差和 DLinear 有增益；它没有证明 Mamba 架构优于其他编码器，也没有证明历史摘要或门本身造成了增益。

本协议不把“使用 Mamba”写成结论，而把问题拆成三个可识别因素：

1. **编码器因素**：在相同持久性锚点、相同 lookback 和相同输入下，Mamba 是否优于满窗线性、MLP、Transformer？
2. **历史长度因素**：从 `L=96` 到 `L=384`、`L=768`，Mamba 的变化机制收益如何变化？收益是来自更长输入，还是来自编码器？
3. **状态摘要因素**：在相同 Mamba 结构中，把历史摘要 `φ_t` 置零，是否损失机制选择性或正例保留？这检验状态信息的增量作用，不等同于旧 sigmoid 外部门。

最终目标不是证明“任何任务上 Mamba 都更好”，而是判断在**持久性锚点 + 机制分层**的限定问题中，Mamba、lookback 和状态摘要各自贡献多少。

---

## 2. 证据边界与已有结果

| 命名空间 | 本协议处理方式 |
|---|---|
| `canonical_v2` | 已查看 test；只作为历史证据和机制定义来源，不重评、不调参、不混表 |
| OCRA `r2`、`v1.1`、`v1.2` | 独立证书协议；不复用其阈值、validation 选择或结果 |
| V3/V3.1、`sim_v5` | 不进入本协议 |
| `encoder_l_v1` | 新生成器主种子、新 `series_id`、新 run root、test 一次性评估 |

`canonical_v2` 的旧结果可继续支持 T4/T6 的限定性 RMSE 比较，但不能支持 Mamba 架构优越性。OCRA 旧失败记录保留为协议历史，不作为本协议的模型选择依据。

---

## 3. 可证伪主张

### C1：编码器增量

在 `L=384, H=24`，T4/T6 的共同真可见原点集合上，`Mamba-φ` 相对满窗 `Lin-L`、`MLP-L`、`Transformer-L` 的序列级路径 RMSE 差异预先定义为左减右；只有在配对 95% 区间上界均小于 0 且同一比较族 Holm 后通过时，才支持“该 Mamba 实现优于这些编码器”的限定性主张。

若 `Mamba-0`（相同 Mamba、`φ_t` 置零）也达到同一结果，不能把增益归因于状态摘要。

### C2：历史长度与旧信息

对 T4/T6，比较 `L=96,384,768` 在共同原点上的 Mamba 相对持久性差异。`L=384` 或 `L=768` 的额外收益只有在共同原点、同一训练预算和预先声明的趋势/季节事件位置下解释。不得预设“更长必然更好”：若过时历史使性能下降，该结果同样是协议结果。

### C3：状态摘要增量

在 `L=384,H=24`，比较 `Mamba-φ` 与参数、优化器、数据、随机种子均相同的 `Mamba-0`。T4/T6 的差异和 N2/N8 的安全差异分别报告。`Mamba-φ` 优于 `Mamba-0` 才能支持“历史摘要增加了条件化信息”；不能把它写成“门有效”。

### C4：阴性控制

在 T2 真未见跳变原点和 T8 近随机游走原点，Mamba-φ、Mamba-0、Transformer-L、MLP-L、Lin-L 相对持久性不得出现预设比较族内显著有利。若出现，停止该头的正向主张并先审计生成器、共同原点和输入血统。

### C5：效率描述

在固定 dtype、固定有效 batch、固定训练步数和固定硬件上记录参数量、训练吞吐、端到端训练时间、单批推理时间和峰值显存。C5 是描述性资源记录，不把一次 OOM 改写为架构普遍不可行，也不把一次速度优势写成统计显著性。

---

## 4. 数据生成与共同原点

### 4.1 生成器

- 复用 `sapr_sim_canonical_v2.0` 的九类机制语义，但使用本协议独立配置和独立 generator seed；
- `T=2048`，`P=48`，`H=24` 为主评估跨度；
- `L∈{96,384,768}`；
- 事件位置必须在 `protocol.json` 中按机制和 horizon 明确写出；
- 对 T2，未来跳变必须满足 `0 < change_point - origin <= H`，否则该原点不能进入 N2；旧配置的 `future_jump_offset=48` 不得直接用于唯一 `H=24` 的 N2；
- T4/T6 的“真可见”标签由生成器事件位置和固定 delay 计算，与 detector summary 分开保存；
- 所有机制的历史、验证、测试序列独立生成，不能由 `series_id` 改名得到新 split。

### 4.2 seed 与黑名单

- `canonical_v2` 训练 seed `{20262201,20262202,20262203,20262204,20262205}` 禁用；
- OCRA 全部已登记 generator/test series 与训练 seed 禁用；
- 当前 r6 使用 generator master seed `20261520`；训练 seeds `{20261521,20261522,20261523,20261524,20261525}`；series 前缀 `enc_l_v1_r6_`。旧轮次已停止且不混入 r6，但不能把所有停止理由都当作已验证缺陷：r3 源码已经包含 replacement sampling，r4 的数据集层已经对 state-off 输入置零。此前两项作废解释属于助手误判，详见更正记录；不覆盖远程原始记录。
- `series_id` 前缀统一为 `enc_l_v1_r6_`；
- E0 必须同时检查 generator seed、series roster hash、split hash 和内容 hash，不得只检查字符串前缀。

### 4.3 共同原点主 estimand

先按最大 `L=768` 生成并登记每个 split 的合法 forecast origins。所有 `L` 对同一 `(series_id, origin, horizon)` 使用嵌套历史窗口：短窗口是长窗口的后缀。主比较只使用所有 L 都合法且真值标签一致的共同原点集合。

- `S+`：T4/T6 的真 `visible_change` 共同原点；主标签要求事件点仍在最短 `L=96` 历史窗内且已超过 delay；
- `N2`：T2 中事件确实落入 `H=24` 且真 `unseen_change` 的共同原点；
- `N8`：T8 的共同原点；
- 其他原点作为预先登记的敏感性分析，不得替代主集合。

序列级 RMSE 的主推断单位仍为独立 test series；五训练 seed 先对同一 series/origin 集合匹配平均，再做 paired bootstrap。报告每个 L 的有效 series 数和 origin 数。

---

## 5. 模型与输入因子

所有头都采用同一预测分解：

```text
forecast = persistence(x_t) + residual_head(history, optional_phi)
```

不得使用 sigmoid 外部门。`φ_t` 是 canonical 方法中定义的九维历史摘要；状态关闭条件为把该向量置零，但保留相同输入槽位、参数形状和训练预算。

| 模型 | 编码器 | 状态因子 |
|---|---|---|
| M0 | 持久性 | 不适用 |
| Lin-L | 满 L 的单一线性残差头 | φ on/off 两者只在 C3 子矩阵使用 |
| MLP-L | 两层 MLP，hidden=64，固定输出头 | φ on/off 只在 C3 子矩阵使用 |
| Transformer-L | 两层 encoder，d_model=64，nhead=4，ff=128，固定位置编码方案 | φ on/off 只在 C3 子矩阵使用 |
| Mamba-0 | 现有 Temporal Mamba，φ 置零 | off |
| Mamba-φ | 相同 Temporal Mamba | on |

主矩阵的所有头必须明确使用同一 `z` 归一化、相同 residual head 输出尺度、相同目标、相同 batch 采样和相同 early-stopping 规则。参数量、可训练参数、FLOPs 估计和实际时间写入 bundle manifest。

### 5.1 不允许的公平性捷径

- 不以“d_model 相同”替代参数量报告；
- 不在看到 validation/test 后调整 MLP 层宽、Transformer 位置编码或 Mamba 宽度；
- 不给 Transformer 单独更多调参次数；
- 不因 OOM 删除该格。若协议预先规定 microbatch+gradient accumulation，所有头都可使用同一有效 batch；否则标记 `not_estimable`，不得把 OOM 当作预测优势。

---

## 6. 训练矩阵与预算

### A：编码器与状态摘要主矩阵（确认性）

固定 `H=24`、五个 training seeds。

- `L=384`：`Lin-φ`、`MLP-φ`、`Transformer-φ`、`Transformer-0`、`Mamba-φ`、`Mamba-0`，共 6×5=30 runs；
- `L∈{96,768}`：`Transformer-φ/0`、`Mamba-φ/0`，共 4×2×5=40 runs；
- A 合计 **70 neural training runs**。

`φ` 始终使用最近 96 个历史点计算的同一冻结九维 summary，与当前 L 无关；`0` 表示将同形状 summary 向量置零。Mamba/Transformer 状态因子在相同架构中成对比较。Lin/MLP 在 L=384 提供 state-on 的编码器对照，不声称其状态因果效应。

### B：其他 horizon

不属于当前确认性预算；只有新协议、剩余预算且在任何 test 读取前预注册，才能开展。不得在查看 A 的 test 结果后挑 horizon 补实验。

**有效预算上限**：70 个 registered training runs 或 30 GPU-hours，先到者停止。预检使用 A 中 `L=384,H=24` 的 Mamba-φ cell；该 cell是注册矩阵之一，不额外增加 run；预检不读 test。

---

## 7. 统计与通过标准

- 主要误差：原始尺度路径 RMSE；差值左模型减右模型；
- 10,000 次 paired percentile bootstrap；
- 五 seed 先按共同 series/origin 匹配平均；
- C1 的比较族固定为 T4/T6 ×（L=384 的 Mamba-φ 对 Lin/MLP/Transformer-φ）× 机制；Holm 统一修正；lookback 曲线为 C2 单独一族；
- C3 单独一族：T4/T6 的 Mamba-φ − Mamba-0 在 L=384；
- C4 单独一族：N2/N8 上五个头相对 M0，L=384；
- C5 不进入显著性检验。

通过状态只能为 `supported / invalidated / not_estimable / pending`。不显著不写成等价；C4 的不显著只能表示没有触发预设泄漏闸门。

### C1

L=384、H=24、S+ 主集合：Mamba-φ 相对 Lin-L、MLP-L、Transformer-L，在 T4 与 T6 的每个预设比较中点估计为负且 Holm 后 95% 上界小于零。任何一个主要比较失败，C1 为 invalidated。

### C2

在共同原点上报告 Δ(L) 的全曲线，不预设单调变好。只有当 L=384 的 Mamba-φ 相对 L=96 的增益方向在 T4/T6 都重现，且对应 Mamba-0 的增量不完全相同，才可讨论“状态摘要与历史长度的交互”。若 Transformer/MLP 在某 L 不可估计，C1/C2 对该比较为 not_estimable。

### C3

L=384、H=24、S+：Mamba-φ 相对 Mamba-0 的差异必须在 T4/T6 都达到预设区间方向，并且不允许把门值 RMSE 解释成状态门证据。

### C4

N2/N8 上任一模型相对持久性显著有利时，停止该模型的正向编码器主张，保留原点、seed 和完整日志，启动输入血统与生成器审计。

### C5

每格报告参数量、固定步数吞吐、同步 CUDA 后墙钟、峰值显存、OOM/失败。未预设资源优劣阈值；资源表的缺失值为 pending。

---

## 8. test 锁与运行顺序

```text
E0：环境、代码 commit、配置 hash、seed/series 内容黑名单、共同原点 manifest
E1：输入血统审计、state-on/off unit test、AMP 与样本采样合同审计；只读 train/validation
A：70 runs；保存所有 bundle、失败和资源数据
A 后核对全部 manifests，冻结 analysis script 与 comparison family hash
人工确认 test lock、无进程重复运行、无失败/缺失 cell
一次性加载 test，生成 sequence_rmse.csv
用冻结 analysis hash 运行 paired bootstrap、sign-flip 与 Holm，生成 paired_comparisons.csv
```

test 不能在 A 完成前读取。A test 一旦读取，任何模型修复、资源修复或分析变更都必须新建 `encoder_l_v1.1` 和新的 test roster。

远程目录：

```text
results/encoder_l_v1_r6/
  protocol/
  data/                 # roster 与必要的 compact metadata；不提交大数组
  bundles/
  metrics/
  resources/
  failures/
  monitor/
```

训练代码留在 zhong3 独立代码仓；论文仓只接收 compact CSV、manifest、hash、图和 claim verdict。

---

## 9. 论文回写规则

- 新结果全部属于 `encoder_l_v1`，不得修改或替代 `canonical_v2` 主表；
- C1/C2/C3/C4/C5 未完成时，在论文中保留 `PENDING: encoder_l_v1`，不写数字、不写“证明了 Mamba 特殊”；
- C1–C4 全通过时，新增“编码器与历史长度”结果节，并明确范围为九机制合成；
- C1 失败但 Mamba-φ/Mamba-0 显示状态增量：只能讨论状态摘要增量，不能讨论 Mamba 架构优越；
- C1/C3 都失败：保留 canonical 结果，论文结论只限当前 Mamba 实现的机制比较；
- C4 触发：停止正向编码器主张，报告负面结果和审计。

---

## 10. 完成定义

- `protocol.json`、code commit、生成器/配置/共同原点/黑名单 hash 可追溯；
- A 的每格有 manifest、训练 seed、参数量、资源记录或失败/OOM；
- test 只评估一次；
- C1–C5 均有明确 verdict，缺失为 pending；
- 新结果进入论文前通过 paper-evidence 的 claim locator、paper audit 和 PDF 构建；
- 不把 OCRA 或旧 canonical 结果与本协议混池。
