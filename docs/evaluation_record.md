# Current Evaluation Record

Updated: 2026-08-12

## What Is Complete

The deterministic reference matrix has been generated using the exact release-local
data manifests, rolling test origins, and training-window RMSSE denominators. It is
the only complete accuracy evidence in the current active releases.

| Release | Tasks | Deterministic models | Horizons | Completed rows | Planned learned rows |
| --- | ---: | ---: | ---: | ---: | ---: |
| `financial_s_only_v1` | 4 | 3 | 6 | 72 / 72 | 1,320 |
| `financial_s_only_v2` | 18 | 3 | 6 | 324 / 324 | 5,940 |

The references are Last-value, Random-walk-with-drift, and ARIMA. ARIMA order is
selected from a prespecified 31-member low-order grid using training data only,
refit once through the validation endpoint, and then updated sequentially through
the test interval without re-estimating coefficients.

The compact metric tables are tracked here:

- [v1 deterministic metrics](../reproducibility/financial_s_only_v1/metrics/deterministic_metrics.csv)
- [v2 deterministic metrics](../reproducibility/financial_s_only_v2/metrics/deterministic_metrics.csv)

Forecast arrays, exact origin dates, and ARIMA metadata remain in ignored local
`results/financial_s_only_retrospective_v*/deterministic/` trees. The CSV rows carry
their local bundle path and SHA-256 so a regenerating user can cross-check them.

## Learned-Matrix Status

The `financial_s_only_v1` learned campaign is in progress. Its live,
restart-safe completion state is recorded in the ignored local
`results/financial_s_only_retrospective_v1/campaign_summary.json`; every completed
task-model-seed bundle retains all six horizon checkpoints, forecasts, truth arrays,
origin dates, forecast dates, metadata, and SHA-256 records. The v2 learned campaign
has not started.

Partial learned output is operational evidence only. It must not be used for a model
ranking, a table, a figure, or a manuscript claim because the pre-specified five-seed
matrix is incomplete. In particular, there is not yet a valid active comparison of
Regime-Gated Mamba with PatchTST, TimesNet, linear models, other Mamba models, or the
deterministic references.

The release status files correctly report `incomplete`:

- [v1 status](../reproducibility/financial_s_only_v1/release_status.json)
- [v2 status](../reproducibility/financial_s_only_v2/release_status.json)

The expected learned rows are calculated as
`tasks x 11 learned models x 5 seeds x 6 horizons`: 1,320 rows for v1 and 5,940 for
v2. A result report may be built only after all expected checkpoints, forecasts,
metadata, and origin arrays validate.

## Metrics

For truth `y`, prediction `y_hat`, and the training-window scale
`s = mean((y_t - y_(t-1))^2)`, the active report writes:

| Metric | Definition | Primary use |
| --- | --- | --- |
| MAE | `mean(abs(y - y_hat))` | Level-scale absolute error |
| MSE | `mean((y - y_hat)^2)` | Squared level error |
| RMSE | `sqrt(MSE)` | Level-scale comparison |
| RMSSE | `sqrt(MSE / s)` | Scale-normalized comparison |

Each metric is reported twice:

- **Path**: all leads in every rolling forecast origin. `path_rmsse` is the primary
  ranking metric.
- **Terminal**: only the final lead at each horizon. It is secondary and must not
  replace the path metric in the main ranking.

When learned results are available, they will be summarized by task, horizon, model,
and five-seed mean and standard deviation. Short, middle, and long horizons must be
shown separately rather than collapsed into one unqualified average.

## Planned Analysis After Training

The report builder will write per-seed and aggregate MAE, RMSE, and RMSSE tables,
cell ranks, Regime-Gated Mamba contrasts against the three deterministic references
and its ungated ablation, and a nested task/seed moving-origin block bootstrap. The
bootstrap uses 10,000 replicates, block length equal to the horizon, and Holm
adjustment across the complete contrast family. It is descriptive: four v1 panels or
eighteen related financial targets do not justify a claim of broad statistical
generalization on their own.

The 2023--2026 period has already been seen. Any completed report must be described
as retrospective, protocol-matched evidence; it cannot establish prospective
forecasting performance, trading value, or economic causality.
