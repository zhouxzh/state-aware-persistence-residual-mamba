# Technical Evidence Registry

This registry links each reader-facing technical statement to a versioned local
artifact. It prevents completed metrics from being separated from their protocol and
provenance.

| ID | Statement supported | Primary artifact |
| --- | --- | --- |
| E01 | Selected-model settings, data boundary, and retrospective status. | `configs/financial_reference_evaluation_v1.json` |
| E02 | Regime-Gated Mamba implementation. | `model/RegimeGatedMamba.py` |
| E03 | Data-task definitions and hashes. | `data/financial/manifests/training_datasets.json` |
| E04 | Selected-model parameter snapshots. | `reproducibility/financial_reference_evaluation_v1/candidate_selection/` |
| E05 | Imported baseline artifact audit. | `reproducibility/financial_reference_evaluation_v1/audit/legacy_baseline_audit.csv` |
| E06 | Model, task, horizon, and seed metrics. | `reproducibility/financial_reference_evaluation_v1/metrics/all_model_metrics_by_seed.csv` |
| E07 | Aggregated MAE, MSE, RMSE, RMSSE, runtime, and memory outputs. | `reproducibility/financial_reference_evaluation_v1/metrics/all_model_aggregate_metrics.csv` |
| E08 | Descriptive uncertainty contrasts. | `reproducibility/financial_reference_evaluation_v1/metrics/regime_gated_mamba_paired_task_seed_bootstrap.csv` |
| E09 | Matched inference profile. | `reproducibility/financial_reference_evaluation_v1/metrics/matched_cuda_microbenchmark.csv` |
| E10 | Architecture figure source. | `docs/figures/regime_gated_mamba_architecture.dot` |

Model translation is controlled by
`reproducibility/financial_reference_evaluation_v1/model_identity_map.json`. Historical
labels appear only in `source_model_id` fields, the mapping, and archived manifests.

The evidence does not support claims about investment performance, economic causality,
universal long-horizon superiority, or generalization beyond the recorded reference
tasks.
