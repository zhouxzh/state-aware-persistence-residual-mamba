# Selection-Safe Nonstationary Forecasting Analysis

Generated from frozen protocol `financial_confirmatory_v1`. The four market panels are reference datasets for a broader study of nonstationary forecasting; they do not define the research domain.

## Evidence boundary

This report uses data quality metadata, train/validation nonstationarity diagnostics, and validation-only Optuna selection artifacts. It does not read protected test targets or present validation ranks as confirmatory model performance. Final paired bootstrap intervals, Holm-adjusted comparisons, regime results, and test-period claims remain unavailable until the formal prediction matrix is complete.

## Completion status

- Reference panels characterized: 4/4.
- S/MS forecasting tasks audited: 8/8.
- Validation model selections audited: 72/72.
- Formal neural task/model/seed cells: 0/360.
- Statistical-reference metric rows: 0.
- Final inferential analysis ready: False.

## Data analysis

All panels have zero missing cells and zero duplicate dates in the processed complete-case files. ADF and KPSS are reported jointly because neither test alone identifies all forms of nonstationarity. `level_consensus_nonstationary` means the level ADF test did not reject a unit root while KPSS rejected trend stationarity at 5%. `difference_consensus_stationary` means the differenced ADF rejected a unit root while KPSS did not reject stationarity at 5%.

| dataset | level_consensus_nonstationary | difference_consensus_stationary | validation_mean_shift_train_sd | validation_std_ratio | validation_difference_std_ratio | validation_correlation_shift_mean_abs |
| --- | --- | --- | --- | --- | --- | --- |
| cross_asset | True | True | 1.708 | 0.344 | 1.251 | 0.176 |
| crypto | True | False | 7.750 | 3.669 | 4.521 | 0.085 |
| fx | True | True | -1.294 | 0.430 | 0.823 | 0.177 |
| yields | True | True | -0.512 | 0.858 | 1.129 | 0.016 |

The raw magnitudes show that shift is heterogeneous rather than a single financial-data effect. `crypto` has the largest absolute train-to-validation level shift, `crypto` has the largest difference-scale ratio, and `fx` has the largest mean change in target-feature difference correlations. These are descriptive validation-era facts, not test-period findings.

## Model architecture analysis

| model | family | implemented mechanism |
| --- | --- | --- |
| DLinear | linear | moving-average decomposition with linear heads |
| NLinear | linear | last-value normalization with a linear head |
| PatchTST | transformer | channel-independent temporal patch Transformer |
| TimesNet | convolutional | multi-period 2D temporal representation |
| iTransformer | transformer | inverted variable-token Transformer |
| S_Mamba | mamba baseline | normalized inverted tokens with bidirectional Mamba |
| NS_Mamba-D | mamba proposal | additive trend/seasonal/residual Mamba branches |
| MS_Mamba-MD | mamba proposal | decomposed multi-scale Mamba with mean fusion |
| PMS_Mamba-PD | mamba proposal | decomposed multi-scale temporal-patch Mamba |

## Validation-only model analysis

Lower balanced RMSSE is better. Mean task rank is used for cross-panel description because RMSSE levels still vary by task. These rankings selected frozen configurations; they are exploratory and cannot establish superiority.

| model | mean_task_rank | median_task_rank | task_wins | task_top3 | mean_validation_balanced_rmsse |
| --- | --- | --- | --- | --- | --- |
| NLinear | 2.875 | 2.000 | 1 | 6 | 9.6737 |
| S_Mamba | 3.125 | 2.000 | 3 | 5 | 9.6861 |
| NS_Mamba-D | 3.875 | 3.500 | 0 | 4 | 9.8527 |
| MS_Mamba-MD | 4.000 | 4.000 | 0 | 2 | 9.8636 |
| PatchTST | 5.125 | 5.500 | 2 | 2 | 10.6963 |
| PMS_Mamba-PD | 5.375 | 5.500 | 0 | 1 | 9.9959 |
| iTransformer | 6.250 | 7.000 | 0 | 2 | 11.0838 |
| DLinear | 6.625 | 8.000 | 2 | 2 | 11.6124 |
| TimesNet | 7.750 | 8.000 | 0 | 0 | 12.7101 |

Task winners:

| task | model | validation_balanced_rmsse |
| --- | --- | --- |
| financial_cross_asset_ms | S_Mamba | 4.7302 |
| financial_cross_asset_s | S_Mamba | 4.7257 |
| financial_crypto_ms | S_Mamba | 23.0135 |
| financial_crypto_s | NLinear | 23.0198 |
| financial_fx_ms | PatchTST | 3.5748 |
| financial_fx_s | PatchTST | 3.6044 |
| financial_yields_ms | DLinear | 6.1420 |
| financial_yields_s | DLinear | 6.1420 |

S/MS validation comparison by model:

| model | mean_ms_minus_s | mean_ms_relative_change | ms_better_panels |
| --- | --- | --- | --- |
| MS_Mamba-MD | -0.0173 | -0.13% | 2 |
| PMS_Mamba-PD | -0.0092 | 0.03% | 1 |
| S_Mamba | -0.0001 | 0.05% | 2 |
| DLinear | -0.0000 | -0.00% | 2 |
| NLinear | -0.0000 | 0.00% | 2 |
| NS_Mamba-D | 0.0033 | -0.01% | 2 |
| PatchTST | 0.0394 | 0.48% | 3 |
| iTransformer | 0.2675 | -1.93% | 2 |
| TimesNet | 2.0384 | 6.84% | 1 |

Proposed Mamba variants relative to S-Mamba on validation tasks:

| proposal | mean_delta | mean_relative_change | better_tasks |
| --- | --- | --- | --- |
| NS_Mamba-D | 0.1667 | 1.99% | 2 |
| MS_Mamba-MD | 0.1775 | 2.01% | 3 |
| PMS_Mamba-PD | 0.3098 | 3.89% | 2 |

## HPO audit

The 72 model/task studies contain 548 complete, 316 pruned, and 2 failed/interrupted trial rows, plus 216 full-horizon validation replays. The calibration-best trial remained the full-horizon replay winner in 57/72 selections. Differences are expected because calibration used horizons [5, 60, 252] while replay used all horizons [1, 5, 20, 60, 120, 252].

No p-values are calculated from these selected validation scores. Treating task ranks or selected configurations as independent replications would understate dependence and reuse selection data for inference.

## Required final analysis

After all 360 formal neural cells and the statistical references exist, run:

```bash
conda run --no-capture-output -n mamba python scripts/financial/run_statistical_baselines.py --unlock-test
conda run --no-capture-output -n mamba python scripts/financial/analyze_financial_results.py
```

That stage will compute per-origin path and terminal metrics, last-value skill, S/MS comparisons, prespecified volatility-regime metrics, 10,000-replicate moving-block bootstrap intervals, and Holm-adjusted p-values. Until then, model conclusions must remain labeled validation-only.
