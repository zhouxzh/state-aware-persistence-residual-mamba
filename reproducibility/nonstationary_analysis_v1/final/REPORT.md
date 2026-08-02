# Final Nonstationary Forecasting Analysis

## Evidence boundary

This is the final test-period analysis for the current financial reference panels. The
research scope is forecasting under nonstationarity; these panels do not define the
future dataset boundary. The frozen internal protocol ID remains
`financial_confirmatory_v1` to preserve its hash.

The protected 2023-01-01 through 2026-06-30 targets were opened only after validation
selection was frozen. All 360 task/model/seed cells are complete. They contain 2,160
horizon-specific learned-model training/evaluation records across horizons 1, 5, 20,
60, 120, and 252. Statistical references add 168 deterministic records.

## Primary result

No Mamba model has the lowest mean path RMSSE in any of the 48 dataset-horizon cells.
Naive or statistical references win 38/48 cells and non-Mamba learned
models win 10/48. This does not support a claim that the proposed
Mamba variants dominate the comparison set on these reference datasets.

| model | wins |
| --- | --- |
| Last-value | 17 |
| ARIMA | 16 |
| NLinear | 4 |
| Random-walk-drift | 4 |
| PatchTST | 4 |
| DLinear | 2 |
| VAR-difference | 1 |

The pooled RMSSE means in `model_summary.csv` are descriptive only. They mix datasets
and horizons and must not replace the paired cell-level comparisons above.

## Prespecified proposal contrasts

Loss differences are proposal minus comparator, so negative values favor the proposal.
Intervals use 10,000 moving-block bootstrap replicates. Holm adjustment is applied
within each dataset/proposal/comparator family across the six horizons.

| proposal | comparator | favorable | unfavorable | not significant |
| --- | --- | --- | --- | --- |
| MS_Mamba-MD | S_Mamba | 5 | 16 | 27 |
| MS_Mamba-MD | validation-selected non-Mamba | 13 | 13 | 22 |
| NS_Mamba-D | S_Mamba | 11 | 10 | 27 |
| NS_Mamba-D | validation-selected non-Mamba | 17 | 7 | 24 |
| PMS_Mamba-PD | S_Mamba | 9 | 13 | 26 |
| PMS_Mamba-PD | validation-selected non-Mamba | 15 | 6 | 27 |

The proposal results are mixed: some improvements over S-Mamba or the
validation-selected learned baseline are statistically supported, while other cells
significantly favor the comparator. These contrasts do not overturn the all-model
winner result because naive and statistical references are also in the benchmark.

## Stability and compute

Five final seeds were used for every learned model. Median and maximum coefficients of
variation below summarize path RMSSE across seeds for each dataset/model/horizon cell.

| model | median_seed_cv | maximum_seed_cv |
| --- | --- | --- |
| S_Mamba | 0.0044 | 0.0391 |
| NS_Mamba-D | 0.0055 | 0.0922 |
| PMS_Mamba-PD | 0.0076 | 0.0758 |
| MS_Mamba-MD | 0.0081 | 0.0646 |
| NLinear | 0.0112 | 0.0607 |
| iTransformer | 0.0238 | 0.0768 |
| PatchTST | 0.0448 | 0.2716 |
| DLinear | 0.0542 | 0.1878 |
| TimesNet | 0.0637 | 0.2469 |

The 2,160 horizon-specific runs sum to 11.43 recorded GPU-hours.
This is summed model runtime, not wall-clock duration. `runtime_summary.csv` reports
model-level runtime and peak-memory distributions.

## Regime and input-mode limits

The prespecified volatility-regime table has 1800
rows. 325 rows, representing 26 distinct
dataset/horizon/regime cells, have zero eligible origins and are explicitly reported as
not estimable. They are not imputed and are excluded from regime-specific claims.

| model | pairs | MS lower RMSSE | mean MS-S RMSSE |
| --- | --- | --- | --- |
| MS_Mamba-MD | 24 | 2 | 0.3014 |
| NS_Mamba-D | 24 | 9 | 0.1437 |
| PMS_Mamba-PD | 24 | 14 | -0.0725 |
| S_Mamba | 24 | 6 | 0.2720 |

The S/MS comparison is descriptive. Multivariate input does not consistently improve
the Mamba variants, so the current evidence does not justify a general claim that
adding covariates improves nonstationary forecasting.

## Reproducibility map

- `analysis_manifest.json`: frozen protocol hash and expected analysis counts.
- `final_runs.json`: all 360 completed task/model/seed cells and their settings.
- `aggregate_metrics.csv`: task/model/horizon metrics and five-seed dispersion.
- `task_horizon_winners.csv`: the 48 primary path-RMSSE comparisons.
- `bootstrap_contrasts.csv`: paired proposal contrasts and Holm-adjusted p-values.
- `neural_metrics_by_seed.csv`: 2,160 learned-model records.
- `statistical_metrics.csv`: 168 deterministic baseline records.
- `regime_metrics.csv`: prespecified regime estimates and explicit not-estimable rows.
- `arima_convergence_audit.csv`: candidate and final-fit convergence evidence.
- `runtime_environment.json`: GPU and numerical runtime metadata.
- `SHA256SUMS`: integrity hashes for every payload in this directory.

Raw per-origin predictions are retained under `results/financial_confirmatory/` and are
not duplicated into Git because the runtime directory is approximately 1.2 GB. The
Git snapshot preserves final metrics, parameters, hashes, completion records, and
analysis provenance; exact bootstrap regeneration still requires the local per-origin
prediction arrays.
