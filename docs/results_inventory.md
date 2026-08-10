# Results Inventory

Updated: 2026-08-10

The authoritative manuscript metrics are the frozen CSV files under
`reproducibility/financial_reference_evaluation_v1/metrics/`. The large local result
trees are training and audit workspaces, not the primary source for manuscript tables.

## Retained local evidence

| Path | Use |
| --- | --- |
| `reproducibility/financial_reference_evaluation_v1/metrics/` | Authoritative MAE, MSE, RMSE, path RMSSE, seed, horizon, runtime, and memory tables. |
| `reproducibility/financial_reference_evaluation_v1/candidate_selection/` | Frozen selected-model parameter snapshots. |
| `results/manuscript_evidence/selection_safe/` | Data-shift diagnostics and selection-safe HPO summaries. |
| `results/manuscript_evidence/merge_gate/` | Final merge-gate candidate comparison and promotion decision. |
| `results/manuscript_evidence/profile/` | Horizon/task inference profile used during model selection. |
| `results/manuscript_evidence/protocol_manifests/` | Development and merge-gate protocol manifests. |
| `results/financial_reference_evaluation_v1/` | Empty active output directory for a future rerun of the canonical evaluation. |

For manuscript tables and figures, start with the frozen reproducibility metrics. Use
the retained local evidence only to explain data nonstationarity, model selection, or
computational trade-offs.

## Archived local results

The following directories are recoverable under `backup/results/` and are ignored by
Git:

- `financial_confirmatory`: raw historical baseline predictions and checkpoints used
  by the audit.
- `pms_mamba_publication_v1`: raw candidate predictions, checkpoints, and TensorBoard
  outputs superseded by compact frozen metrics.
- `optuna` and `legacy_optuna_csv`: raw studies and old dataset HPO summaries.
- `nonstationary_analysis_v2`, `nonstationary_analysis_v3`, `nonstationary_analysis_v4`,
  `nonstationary_analysis_v5_development`: intermediate screens and model-development
  generations.
- `nonstationary_analysis`, `nonstationary_metric_suite`, `nsv4`, and `nsv5`: superseded
  analysis and profiling workspaces.

These archives are not evidence for a new claim unless a result is explicitly traced to
the frozen protocol and canonical model identity. Do not cite an archived smoke run,
development screen, or obsolete model label as a final result.

## Git policy

`results/`, `backup/`, checkpoints, TensorBoard logs, and raw data are ignored by Git.
The reproducible public record is the code, configuration, technical documentation,
figures, manifests, and compact metrics committed under `reproducibility/`.
