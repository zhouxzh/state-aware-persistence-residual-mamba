# Technical Documentation

This directory is the technical record for the active target-only financial
forecasting releases. It contains no manuscript source and does not treat
historical mixed S/MS outputs as current evidence.

| Document | Purpose |
| --- | --- |
| [data_reference.md](data_reference.md) | Active v1 and v2 targets, dates, data hashes, and redistribution boundary. |
| [model_reference.md](model_reference.md) | Implemented Regime-Gated Mamba architecture, ablation, limitations, and observed v1/v2 positions. |
| [evaluation_record.md](evaluation_record.md) | Verified v1 metrics, ranks, uncertainty analysis, and claim boundaries. |
| [v2_evaluation_record.md](v2_evaluation_record.md) | Verified v2 metrics, ranks, gate ablation, runtime, and claim boundaries. |
| [analysis/financial_s_only_v2/README.md](analysis/financial_s_only_v2/README.md) | Reproducible V2-derived tables, normalized comparisons, seed stability, and provenance. |
| [computational_profile.md](computational_profile.md) | Fixed-workload CUDA profiles and observed campaign runtime. |
| [reproducibility.md](reproducibility.md) | Rebuild, train, replay, replay validation, report, figure, and verification commands. |
| [evidence_registry.md](evidence_registry.md) | Claim-to-artifact map for technical writing. |
| [results_inventory.md](results_inventory.md) | What is active, local-only, and recoverably archived. |
| [repository_structure.md](repository_structure.md) | Directory ownership and supported commands. |
| [final_evaluation_record.md](final_evaluation_record.md) | Current acceptance state and remaining evidence boundary. |
| [audit_response_and_computation_plan.md](audit_response_and_computation_plan.md) | Corrected audit response, V2 repair record, and V2 supplemental gate-ablation record. |
| [v2_long_horizon_consistency_check_20260821.md](v2_long_horizon_consistency_check_20260821.md) | Audit record for the non-independent V2 long-horizon supplement and replay check. |

Use `financial_s_only_v1` for the original four target-only panels and
`financial_s_only_v2` for the independent-target expansion. They must be analyzed
and reported separately. Both are retrospective because their 2023--2026 targets
have already been viewed.

The local-only `financial_s_only_v2_supplement` run is a two-model, long-horizon
V2 gate-ablation supplement. Its ignored artifacts are diagnostic and do not
replace either tracked release.

The current analysis is V2-primary. Raw MAE/RMSE remain target-specific; pooled
comparisons use path RMSSE ranks or explicitly named baseline ratios.
