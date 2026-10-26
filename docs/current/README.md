# 当前研究入口：OCRA-v1

更新日期：2026-10-23。

当前待执行的工作是 **OCRA-v1.2.r1（Observability-Certified Residual Admission）**：对
`canonical_v2` 九机制生成器进行全新、种子不相交的合成复核。它将最近 96 点内仍可见的
水平跳变先转交 DLinear，再判断是否开启 Mamba；完整说明见
[../OCRA_V1_2_PROTOCOL.md](../OCRA_V1_2_PROTOCOL.md)。旧 `ocra_v1.r2` 与 `ocra_v1.1.r4`
均保留为 validation 阶段停止的探索记录，不得改写或合并。

## 当前状态

- OCRA-v1.2.r1 已通过 E1，正在 `results/ocra_v1_2_r1/` 运行 20 个 train/validation
  bundle；原始产物不进入 Git。
- 每个活动版本都有独立温度/资源监控：每分钟识别本版本进程，30 分钟保存完整快照；80 C
  告警，连续三次 85 C 才终止该版本进程。
- E2 只使用 validation。E2 成功后监督器才允许一次性生成 test 数组并执行 E3--E7；若 E2
  失败，保留失败记录并停止，不调阈值或读取 test。

## 历史证据边界

`canonical_v2` 是 SAPR 稿件的冻结九机制模拟估计对象。其判定是：补丁候选机制成立，
但学习 sigmoid state gate 的开启/关闭主张不成立。完整的可审计结果在
[../../reproducibility/sapr_canonical_v2/results.md](../../reproducibility/sapr_canonical_v2/results.md)，
对应判定在
[../../reproducibility/sapr_canonical_v2/decision.json](../../reproducibility/sapr_canonical_v2/decision.json)。

V2 开发、V3/V3.1 真实/公共来源确认、`sim_v1`--`sim_v5`、BOCPD、V4 覆盖失败及金融
发布物都保持原协议标签，不能与 `canonical_v2` 或 OCRA-v1 汇总。逐项位置和状态见
[../results_registry.md](../results_registry.md)。

早期 SAPR 问题陈述和模拟细节保留在
[scientific_question.md](scientific_question.md) 与
[scientific_meaning_and_simulation_plan_20261008.md](scientific_meaning_and_simulation_plan_20261008.md)，
仅供历史审计；它们不覆盖 OCRA-v1 计划。

本页只提供导航，不改变任何冻结报告、协议锁、覆盖文件或结果数组。
