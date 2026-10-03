# SAPR-Mamba V2 执行状态

**记录日期：** 2026-10-03
**协议：** `configs/sapr_mamba_v2/protocol.lock.json`
**状态：** V2 合成与真实面板矩阵、独立指标重算、前向回放和紧凑发布物均已完成并校验。

这是执行状态记录，不修改 `sapr_mamba_v2.0` 的冻结协议。V1 及更早版本仍是
开发与审计记录，不能与 V2 汇总或论文结论混合。

## 完成证据

| 放行项 | 冻结证据 |
| --- | --- |
| 合成任务矩阵 | `docs/analysis/sapr_mamba_v2/synthetic_completion_matrix.csv`；25 个任务完成。 |
| 真实任务矩阵 | `docs/analysis/sapr_mamba_v2/real_completion_matrix.csv`；180 个任务完成，任务产物哈希和合并指标矩阵已核验。 |
| 预测指标独立重算 | `docs/analysis/sapr_mamba_v2/confirmation_verification_manifest.json`；25 个合成任务和 180 个真实任务通过。 |
| 抽样前向/统计回放 | `docs/analysis/sapr_mamba_v2/forward_replay_matrix.csv`；覆盖五个合成模型及全部真实面板/模型的 65 个冻结任务。 |
| 真实数据主比较与门控审计 | `docs/analysis/sapr_mamba_v2/real_primary_comparisons.csv`、`real_gate_audit.csv`、`real_stable_state_coverage.csv`。 |
| 统计基线失败保留 | `docs/analysis/sapr_mamba_v2/real_statistical_audit.csv`；所有拟合警告/失败按 V2 规则保留。 |
| 紧凑 release | `reproducibility/sapr_mamba_v2/release_manifest.json`、`SHA256SUMS.json`；全树 checksum 已验证。 |

## 解释边界

- 真实数据的 ETT 四个文件作为一个来源簇处理，不作为四个独立领域。
- 多数真实面板缺少或仅有极少 `stable` 状态序列单元；稳定安全性证据在
  `real_stable_state_coverage.csv` 中标记为受限或不可估计，不能表述为完整安全性结论。
- 真实比较按来源分层报告；不得从少量来源簇得出普适或跨领域结论。
- 门值关联仅为描述性审计，不能作为门控导致精度变化的因果证据。

所有数值性陈述应从 `reproducibility/sapr_mamba_v2/claim_evidence_map.csv` 指向的
冻结产物复算，不得从训练日志摘取数字。
