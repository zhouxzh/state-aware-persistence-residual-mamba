# 结果命名空间登记表

更新日期：2026-10-23。

本登记表是结果的导航与保留边界，不是新的分析层，也不替代各协议自己的结果报告。
每一行均为独立估计对象。禁止跨行合并指标、bootstrap、seed、阈值、机制标签或结论。

## 活动协议

| 命名空间 | 状态 | 协议与判定位置 | 原始产物位置 |
| --- | --- | --- | --- |
| `ocra_v1.r2` | 20 个 train/validation bundle 完成；E2 无可行 DEFER 阈值而停止，未加载 test | [OCRA-v1 计划](OCRA_V1_SERVER_RESEARCH_PLAN.md) | `results/ocra_v1_r2/` |
| `ocra_v1.1.r4` | 20 个 train/validation bundle 完成；E2 无可行阈值而停止，未加载 test | [v1.1 说明](OCRA_V1_1_PROTOCOL.md) | `results/ocra_v1_1_r4/` |
| `ocra_v1.2.r1` | 当前探索性协议；E1 通过，20 个 train/validation bundle 运行中 | [v1.2 说明](OCRA_V1_2_PROTOCOL.md) | `results/ocra_v1_2_r1/` |

OCRA-v1 不是 V3/V3.1 真实来源确认，也不是 `sim_v5` 的继续。它的 generator seeds、
`series_id` 前缀和训练 seeds 必须与 `canonical_v2` 分离。

## SAPR 九机制及模拟系列

| 命名空间 | 当前判定/状态 | 紧凑可复算证据 | 原始结果树 |
| --- | --- | --- | --- |
| `canonical_v2` | 当前 SAPR 稿件估计对象；`patch_claim_pass=true`，`state_gate_claim_pass=false` | [结果](../reproducibility/sapr_canonical_v2/results.md)、[判定](../reproducibility/sapr_canonical_v2/decision.json)、[校验](../reproducibility/sapr_canonical_v2/checksums.json) | `results/sapr_mamba_canonical_v2/synthetic/` |
| `canonical_v1` | 中断的先前协议；保留，不续跑 | [中断记录](current/sapr_canonical_v1_interruption.md)、`reproducibility/sapr_canonical_v1/` | `results/sapr_mamba_canonical_v1/` |
| `sim_v1` | T2 leakage gate 未通过；`state_gate_claim_pass=false` | [结果](../reproducibility/sapr_sim_v1/results.md)、[判定](../reproducibility/sapr_sim_v1/decision.json) | `results/sapr_mamba_sim_v1/synthetic/` |
| `sim_v2` | T2 leakage gate 未通过；`state_gate_claim_pass=false` | [结果](../reproducibility/sapr_sim_v2/results.md)、[判定](../reproducibility/sapr_sim_v2/decision.json) | `results/sapr_mamba_sim_v2/synthetic/` |
| `sim_v3` | `patch_claim_pass=true`，但 `state_gate_claim_pass=false` | [结果](../reproducibility/sapr_sim_v3/results.md)、[判定](../reproducibility/sapr_sim_v3/decision.json) | `results/sapr_mamba_sim_v3/synthetic/` |
| `sim_v4` | 训练前 coverage gate 失败；不是模型结果 | [失败记录](current/sapr_sim_v4_coverage_failure.md)、`reproducibility/sapr_sim_v4/` | 无有效训练矩阵 |
| `sim_v5` | `state_gate_claim_pass=false`；不作为 OCRA 的开发或确认数据 | [结果](../reproducibility/sapr_sim_v5/results.md)、[判定](../reproducibility/sapr_sim_v5/decision.json) | `results/sapr_mamba_sim_v5/synthetic/` |

所有上表判定均直接引用各自冻结 `decision.json`，不是从训练日志摘取的结论。

## 真实来源、BOCPD 与历史发布物

| 命名空间 | 状态/边界 | 紧凑证据 | 原始结果树 |
| --- | --- | --- | --- |
| V2 开发 | 已冻结的开发记录；不与后续确认合并 | `reproducibility/sapr_mamba_v2/`、`docs/analysis/sapr_mamba_v2/` | `results/sapr_mamba_v2/` |
| V3/V3.1 | 独立真实/公共来源确认；不可替代或汇入 `canonical_v2` | `reproducibility/sapr_mamba_v3/`、`docs/analysis/sapr_mamba_v3/` | `results/sapr_mamba_v3/` |
| V4 | 不可变的预训练 coverage-gate 失败 | `docs/analysis/sapr_mamba_v4/` | `results/sapr_mamba_v4/` 中仅保留历史运行记录 |
| V5--V8 | 后续真实来源/确认工作；各自独立 | `docs/analysis/sapr_mamba_v5/`--`sapr_mamba_v8/` | `results/sapr_mamba_v5/`、`sapr_mamba_v6/`（其余仅紧凑记录） |
| BOCPD E1--E5 | 独立 BOCPD 实验系列；E2--E5 覆盖失败仍须保留 | `reproducibility/sapr_bocpd_*/`、`docs/current/sapr_bocpd_*` | 仅保留对应的历史配置、运行日志或紧凑证据 |
| 金融 S-only V1/V2 | 历史、回顾性发布物；不是当前 SAPR/OCRA 证据 | `reproducibility/financial_s_only_v1/`、`financial_s_only_v2/` | 完整历史结果树已按 [inventory](results_inventory.md) 所记边界删除 |

## 使用规则

1. 先从 `reproducibility/<namespace>/` 的协议锁、校验和和结果表确认一条结论，再读取
   `docs/analysis/` 中的解释。
2. `results/` 中的 `metrics_all.csv`、任务清单和预测数组是完整运行证据；不可手工编辑、
   删除失败任务或以局部表覆盖原文件。
3. 覆盖失败、中断、负对照和被 supersede 的产物仍保持原路径和版本标签。整理时只能新增
   索引或派生文件，不能改写其锁文件、hash 或已有报告。
4. 对 OCRA-v1，完整数组、检查点与协议产物留在 `results/ocra_v1_r2/`；未来仅复制紧凑表、
   校验和、图和 claim verdict 到版本库或论文工作区。
