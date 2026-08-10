# Financial Reference Evaluation Record

Status: complete on 2026-08-09.

`financial_reference_evaluation_v1` is the frozen technical record for the selected
Regime-Gated Mamba model and its Multi-Scale Patch Mamba ablation. It retains the
original benchmark configuration, audits historical baseline artifacts, and makes the
model-identity translation explicit.

## Protocol

- Eight tasks: `S` and `MS` views of cross-asset, cryptoasset, foreign exchange, and
  Treasury-yield panels.
- Six horizons: 1, 5, 20, 60, 120, and 252 retained observations.
- Five seeds: 2023, 2024, 2025, 2026, and 2027.
- Primary ranking metric: path RMSSE; secondary outputs include MAE, MSE, RMSE,
  terminal-point metrics, runtime, and peak GPU memory.
- Historical baseline recipes and data-split boundary:
  `reproducibility/financial_reference_evaluation_v1/protocol/financial_confirmatory_source.json`.
- Selected-model recipe and retrospective-evidence statement:
  `configs/financial_reference_evaluation_v1.json`.

The selection snapshots were copied into the release; the active training path remains
unchanged. The model identifier mapping is stored in
`reproducibility/financial_reference_evaluation_v1/model_identity_map.json`.

## Released artifacts

| Artifact | Contents |
| --- | --- |
| `metrics/all_model_metrics_by_seed.csv` | Canonical metrics for all models, tasks, horizons, and seeds. |
| `metrics/all_model_aggregate_metrics.csv` | Mean MAE, MSE, RMSE, path RMSSE, runtime, and memory. |
| `metrics/regime_gated_mamba_paired_task_seed_bootstrap.csv` | 10,000-replicate descriptive bootstrap contrasts. |
| `metrics/matched_cuda_microbenchmark.csv` | Matched forward-pass profile. |
| `audit/legacy_baseline_audit.csv` | Audit of imported baseline evidence. |
| `candidate_selection/` | Frozen selected-model parameter snapshots. |

All release rows retain `source_model_id`, `model_id`, and `model`. This allows an
auditor to trace prior experiment artifacts without making legacy naming part of the
public interface.

The commands needed to rebuild or audit these outputs are in
[reproducibility.md](reproducibility.md).
