# Financial Reference Data

Updated: 2026-08-09

The completed evaluation uses four daily financial panels as reference data for
nonstationary time-series forecasting. Each panel supplies a target-only (`S`) task
and a multivariate-input, single-target (`MS`) task, for eight tasks in total.

| Panel | Target | Variables available to the `MS` task | Date range | Rows |
| --- | --- | --- | --- | ---: |
| Cross-asset | GLD | SP500, WTI, VIX, GLD | 2016-07-25 to 2026-06-30 | 2,483 |
| Cryptoasset | BTCUSDT | ETHUSDT, BNBUSDT, XRPUSDT, BTCUSDT | 2018-05-04 to 2026-06-30 | 2,980 |
| Foreign exchange | GBPUSD | EURUSD, CADUSD, JPYUSD, CHFUSD, AUDUSD, GBPUSD | 1999-01-04 to 2026-06-30 | 6,894 |
| Treasury yields | DGS10 | DGS2, DGS5, DGS30, DGS10 | 2006-02-09 to 2026-06-30 | 5,101 |

`S` observes only the target history. `MS` observes all variables listed above but is
scored only on its named target. Forecasts are made in the observed level scale, not
on returns or first differences.

## Splits and horizons

| Stage | Training window | Evaluation window | Use |
| --- | --- | --- | --- |
| Development | Through 2020-12-31 | 2021 | Architecture and parameter exploration. |
| Merge gate | Through 2021-12-31 | 2022 | Frozen promotion decision for the selected model. |
| Financial reference evaluation | Through 2022-12-31 | 2023-01-01 to 2026-06-30 | Retrospective, protocol-matched comparison. |

The completed evaluation uses horizons 1, 5, 20, 60, 120, and 252 retained
observations. They are grouped as short (1, 5), medium (20, 60), and long (120, 252)
for descriptive reporting. The merge gate did not include horizon 252 because its
evaluation window was too short for the intended boundary.

| Panel | Rows through 2020 | Rows in 2021-2022 | Rows in 2023-2026 |
| --- | ---: | ---: | ---: |
| Cross-asset | 1,112 | 502 | 869 |
| Cryptoasset | 973 | 730 | 1,277 |
| Foreign exchange | 5,521 | 499 | 874 |
| Treasury yields | 3,728 | 500 | 873 |

## Nonstationarity diagnostics

The following diagnostics were calculated from the recorded panel construction. They
describe distribution change; they do not establish a component-level causal effect.

| Panel | Test mean shift in training SD | Test difference-SD ratio |
| --- | ---: | ---: |
| Cross-asset | +6.53 | 3.66 |
| Cryptoasset | +15.41 | 4.99 |
| Foreign exchange | -1.37 | 0.64 |
| Treasury yields | +1.35 | 1.06 |

## Data policy and manifests

Raw provider downloads, processed price panels, checkpoints, prediction arrays, and
TensorBoard traces are intentionally excluded from Git. Redistribution must follow
each provider's terms. A permitted local copy can be reconstructed with the commands
in [reproducibility.md](reproducibility.md).

The authoritative local inputs are:

- `data/financial/manifests/training_datasets.json`: task-level paths and hashes.
- `data/financial/manifests/quality_report.json`: quality checks from preparation.
- `data/financial/manifests/nonstationarity_diagnostics_selection_safe.csv`: diagnostics
  available before final evaluation targets were opened.
- `reproducibility/financial_reference_evaluation_v1/protocol/financial_confirmatory_source.json`:
  archived benchmark split and baseline protocol.
- `configs/financial_reference_evaluation_v1.json`: selected-model evaluation record.
