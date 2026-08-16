# Financial Data Reference

## Scope

The active benchmark is target-only (`S`) daily **level** forecasting. Every task
uses one historical target series as input and predicts the same target. It does not
use exogenous variables at inference time. Forecasts are evaluated on the original
level scale, not as investment signals, returns, or economic forecasts.

The shared split boundary is fixed for both releases:

| Partition | Date interval |
| --- | --- |
| Training | Through 2020-12-31 |
| Validation | 2021-01-01 through 2022-12-31 |
| Retrospective evaluation | 2023-01-01 through 2026-06-30 |

The horizons are retained observations, not calendar days: 1, 5, 20, 60, 120, and
252. Reporting groups them as short (1, 5), middle (20, 60), and long (120, 252).
The test interval was previously viewed, so no active release may call it untouched
or prospective.

## v1: Original Target Panels

`financial_s_only_v1` retains the original panel construction and four selected
targets. The wide panels stay local because they record source construction, but the
active model input is always one target column.

| Task | Target | Full range | Rows | Train / validation / test |
| --- | --- | --- | ---: | ---: |
| `financial_cross_asset_s` | GLD | 2016-07-25 to 2026-06-30 | 2,483 | 1,112 / 502 / 869 |
| `financial_crypto_s` | BTCUSDT | 2018-05-04 to 2026-06-30 | 2,980 | 973 / 730 / 1,277 |
| `financial_fx_s` | GBPUSD | 1999-01-04 to 2026-06-30 | 6,894 | 5,521 / 499 / 874 |
| `financial_yields_s` | DGS10 | 2006-02-09 to 2026-06-30 | 5,101 | 3,728 / 500 / 873 |

The frozen paths, split counts, and SHA-256 values are in
[`training_datasets.json`](../reproducibility/financial_s_only_v1/training_datasets.json).

## v2: Independent-Target Expansion

`financial_s_only_v2` avoids complete-case intersections. It materializes one
date-plus-target CSV for each series, retaining the maximum available independent
history through the same 2026-06-30 cutoff. The 18 target files must remain separate;
they are not pooled into one synthetic panel.

| Family | Targets | Count |
| --- | --- | ---: |
| Cross-asset | GLD, SP500, VIX, WTI | 4 |
| Crypto | BTCUSDT, ETHUSDT, BNBUSDT, XRPUSDT | 4 |
| Foreign exchange | EURUSD, CADUSD, JPYUSD, CHFUSD, AUDUSD, GBPUSD | 6 |
| U.S. Treasury yields | DGS2, DGS5, DGS10, DGS30 | 4 |

| Target | Range | Rows | Train / validation / test |
| --- | --- | ---: | ---: |
| GLD | 2004-11-18 to 2026-06-30 | 5,436 | 4,058 / 503 / 875 |
| SP500 | 2016-07-25 to 2026-06-30 | 2,497 | 1,119 / 503 / 875 |
| VIX | 1990-01-02 to 2026-06-30 | 9,219 | 7,810 / 508 / 901 |
| WTI | 1986-01-02 to 2026-06-30 | 10,192 | 8,821 / 502 / 869 |
| BTCUSDT | 2017-08-17 to 2026-06-30 | 3,240 | 1,233 / 730 / 1,277 |
| ETHUSDT | 2017-08-17 to 2026-06-30 | 3,240 | 1,233 / 730 / 1,277 |
| BNBUSDT | 2017-11-06 to 2026-06-30 | 3,159 | 1,152 / 730 / 1,277 |
| XRPUSDT | 2018-05-04 to 2026-06-30 | 2,980 | 973 / 730 / 1,277 |
| EURUSD | 1999-01-04 to 2026-06-30 | 6,894 | 5,521 / 499 / 874 |
| CADUSD | 1971-01-04 to 2026-06-30 | 13,921 | 12,548 / 499 / 874 |
| JPYUSD | 1971-01-04 to 2026-06-30 | 13,909 | 12,536 / 499 / 874 |
| CHFUSD | 1971-01-04 to 2026-06-30 | 13,915 | 12,542 / 499 / 874 |
| AUDUSD | 1971-01-04 to 2026-06-30 | 13,908 | 12,535 / 499 / 874 |
| GBPUSD | 1971-01-04 to 2026-06-30 | 13,915 | 12,542 / 499 / 874 |
| DGS2 | 1976-06-01 to 2026-06-30 | 12,516 | 11,143 / 500 / 873 |
| DGS5 | 1962-01-02 to 2026-06-30 | 16,108 | 14,735 / 500 / 873 |
| DGS10 | 1962-01-02 to 2026-06-30 | 16,108 | 14,735 / 500 / 873 |
| DGS30 | 1977-02-15 to 2026-06-30 | 12,338 | 10,965 / 500 / 873 |

The authoritative target-level hash manifest is
[`financial_s_only_v2/training_datasets.json`](../reproducibility/financial_s_only_v2/training_datasets.json).

## Source and Redistribution Boundary

`configs/financial_data_sources_v1.json` defines the raw source construction:
FRED for macroeconomic, FX, and yield series; Yahoo Finance for GLD; and official
Binance archives for crypto spot bars. Local raw data, processed panels, target CSVs,
and provider download manifests are ignored by Git. Recreate them only under the
applicable provider terms.

Run `scripts/data.py prepare` to rebuild the four v1 panel files and
`scripts/data.py materialize-targets` to rebuild the v2 independent targets. Each
release setup recomputes and validates hashes before any deterministic or learned
evaluation starts.
