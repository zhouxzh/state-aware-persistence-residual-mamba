# 文档入口

本目录按**估计对象和协议命名空间**组织，而不是按文件写入日期组织。不同命名空间的
结果、阈值、种子、图表和结论均不得合并、平均或相互调参。

## 从这里开始

| 目的 | 入口 |
| --- | --- |
| 当前待执行的确认性工作 | [OCRA-v1 研究计划](OCRA_V1_SERVER_RESEARCH_PLAN.md) |
| 当前研究的简明边界与历史 SAPR 结论 | [current/README.md](current/README.md) |
| 所有结果树与紧凑证据的对应关系 | [结果命名空间登记表](results_registry.md) |
| 历史金融发布物的保留边界 | [results_inventory.md](results_inventory.md) |
| 原始金融研究的可复算说明 | [reproducibility.md](reproducibility.md) |

`OCRA-v1` 是唯一活动协议，但尚未开始训练。它使用新的 `ocra_v1_` 系列 ID 与
独立种子，在 `results/ocra_v1_r2/` 下写入产物；在 `protocol.json`、黑名单和 seed
不相交检查通过前，不得读取 OCRA test split 或训练骨干。

## 结果的三个层级

| 层级 | 位置 | 用途 |
| --- | --- | --- |
| 原始运行产物 | `results/` | 完整指标矩阵、任务清单、检查点和预测；不纳入 Git，也不手工改写。 |
| 紧凑可复算证据 | `reproducibility/<namespace>/` | 协议锁、校验和、覆盖表、判定和论文级结果表。 |
| 派生报告 | `docs/analysis/<namespace>/`、`docs/current/` | 从冻结产物重算的分析、解释与运行记录；不能替代原始证据。 |

引用某个数值时，先从该命名空间的紧凑证据重算并校验，再引用其结果表。日志、控制器
状态和汇总文字不是数值结论的来源。

## 冻结 SAPR 证据

- `canonical_v2` 是当前 SAPR 稿件的九机制合成估计对象。它支持残差补丁候选机制的
  判定，但已明确否定学习 sigmoid 状态门的主张；详见
  [结果命名空间登记表](results_registry.md)。
- `sim_v1`--`sim_v5`、BOCPD 系列、V2 开发、V3/V3.1 真实来源确认及金融发布物均是
  独立的冻结记录。它们可审计、可保留，但不能为 `canonical_v2` 或 OCRA-v1 提供
  pooled evidence。
- V4 是训练前覆盖门失败，不能写作模型结果。历史 sigmoid state gate 是冻结负对照，
  不得作为待优化方法恢复。

历史金融文档在 [archive/financial_s_only/README.md](archive/financial_s_only/README.md)。
它们不构成当前 SAPR 或 OCRA 的正面证据。

## 冻结补充材料

下列材料仍保留原址，以便审计早期设计和已完成的独立分析；它们不是当前执行授权：

| 材料 | 作用 |
| --- | --- |
| [scientific_question.md](current/scientific_question.md) | 早期 SAPR 的冻结问题与 T0--T8 设计记录。 |
| [scientific_meaning_and_simulation_plan_20261008.md](current/scientific_meaning_and_simulation_plan_20261008.md) | 早期模拟生成器与统计细节。 |
| `analysis/sapr_mamba_v2/`、`analysis/sapr_mamba_v3/` | 各自独立的历史开发与真实来源分析。 |
| `figures/sapr_canonical_v2/` | `canonical_v2` 的派生审阅图；源矩阵仍在 `results/`。 |
