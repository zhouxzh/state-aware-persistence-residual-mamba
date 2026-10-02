# 文档索引

更新日期：2026-10-02。当前研究设计、历史冻结证据和投稿审查材料必须分开使用。既有
历史文件保留原始路径，以避免破坏冻结发布物、图表清单和审计链接。

## 当前入口

| 文档 | 用途 |
| --- | --- |
| [current/README.md](current/README.md) | 状态感知持久性残差 Mamba 的当前研究边界、四模型比较和训练前冻结要求。 |
| [current/ace2_cleanup_20261002.md](current/ace2_cleanup_20261002.md) | 2026-10-02 历史原始结果与检查点清理记录。 |
| [reproducibility.md](reproducibility.md) | 历史金融发布物的复核边界；不是新模型的训练授权。 |

## 历史金融证据

金融 V1/V2/Supplement 是已完成的 Regime-Gated Mamba S-only 研究。它们只能用于审计该
历史研究，不能填充新状态感知持久性残差 Mamba 的结果。

| 索引 | 用途 |
| --- | --- |
| [archive/financial_s_only/README.md](archive/financial_s_only/README.md) | 历史记录、分析表、图表和冻结发布物的统一入口。 |
| [results_inventory.md](results_inventory.md) | 保留内容、已删除原始输出和恢复边界。 |
| [evidence_registry.md](evidence_registry.md) | 历史金融陈述到冻结工件的映射。 |
| [v2_evaluation_record.md](v2_evaluation_record.md) | V2 历史结果解释，非当前研究结果。 |

## 投稿审查归档

此前围绕金融回顾性论文的审查仍有审计价值，但不适用于新的方法设计：

- [Journal of Forecasting 投稿审查](archive/financial_s_only/reviews/journal_of_forecasting_submission_audit_20260914.md)
- [金融论文缺口计划](archive/financial_s_only/reviews/manuscript_publication_gap_plan_20260914.md)

---

# Historical Financial Documentation

This directory is the technical record for the historical target-only financial
forecasting releases. It contains no manuscript source and does not treat
historical mixed S/MS outputs as current evidence.

| Document | Purpose |
| --- | --- |
| [data_reference.md](data_reference.md) | Historical v1 and v2 targets, dates, data hashes, and redistribution boundary. |
| [model_reference.md](model_reference.md) | Implemented Regime-Gated Mamba architecture, ablation, limitations, and observed v1/v2 positions. |
| [evaluation_record.md](evaluation_record.md) | Verified v1 metrics, ranks, uncertainty analysis, and claim boundaries. |
| [v2_evaluation_record.md](v2_evaluation_record.md) | Verified v2 metrics, ranks, gate ablation, runtime, and claim boundaries. |
| [analysis/financial_s_only_v2/README.md](analysis/financial_s_only_v2/README.md) | Reproducible V2-derived tables, normalized comparisons, seed stability, and provenance. |
| [computational_profile.md](computational_profile.md) | Fixed-workload CUDA profiles and observed campaign runtime. |
| [reproducibility.md](reproducibility.md) | Historical rebuild, train, replay, report, and verification commands. |
| [evidence_registry.md](evidence_registry.md) | Claim-to-artifact map for technical writing. |
| [results_inventory.md](results_inventory.md) | What was preserved and what historical output was deleted. |
| [repository_structure.md](repository_structure.md) | Directory ownership and supported commands. |
| [final_evaluation_record.md](final_evaluation_record.md) | Historical acceptance state and evidence boundary. |
| [audit_response_and_computation_plan.md](audit_response_and_computation_plan.md) | Corrected audit response, V2 repair record, and V2 supplemental gate-ablation record. |
| [v2_long_horizon_consistency_check_20260821.md](v2_long_horizon_consistency_check_20260821.md) | Audit record for the non-independent V2 long-horizon supplement and replay check. |

The material below is historical. Use `financial_s_only_v1` for the original four target-only panels and
`financial_s_only_v2` for the independent-target expansion. They must be analyzed
and reported separately. Both are retrospective because their 2023--2026 targets
have already been viewed.

The local-only `financial_s_only_v2_supplement` run was a two-model, long-horizon
V2 gate-ablation supplement. Its original ignored artifacts were deleted on
2026-10-02 after release verification; they did not replace either tracked release.

The historical analysis was V2-primary. Raw MAE/RMSE remain target-specific; pooled
comparisons use path RMSSE ranks or explicitly named baseline ratios.
