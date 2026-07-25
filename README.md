# Nonstationary Mamba Time-Series Forecasting

This repository is a forecasting research workspace based on S-Mamba. The goal is to build and evaluate Mamba-based models for nonstationary time series, using `S_Mamba` as the main baseline and extending toward `NS_Mamba`.

This README is the single project document for setup, model inventory, current status, and the research plan.

## Current Status

Completed:

- Replaced the old 1990–2010 exchange-rate dataset with FRED daily data (1971–2026).
- Completed the full-horizon Exchange Optuna sweep (baseline + Mamba, UK Pound/USD).
- Completed the full-horizon Weather Optuna sweep (baseline + Mamba, Jena OT).
- All three benchmark datasets (GLD, Exchange, Weather) have finished S-mode evaluation.
- Consolidated benchmark results in `## Benchmark Results` below.
Next immediate task:

```text
Update the manuscript tables and figures with the three completed benchmark datasets (GLD, Exchange, Weather).
```

## GLD Baseline Results

Completed baseline table:

```text
results/gld_baseline_optuna_best.csv
120 / 120 rows complete
10 models x 12 horizons
```

Reproducibility hyperparameters:

```text
results/optuna/gld/baseline_best_params.json
```

Generate the LaTeX include used by the manuscript with:

```bash
python manuscript/scripts/generate_gld_baseline_results.py
```

Extract the plot-ready reproduction bundle with:

```bash
python scripts/extract_gld_baseline_optuna_bundle.py
```

Replay the saved baseline hyperparameters and archive checkpoints plus test
predictions with CUDA:

```bash
conda run -n mamba python scripts/reproduce_gld_baseline_from_bundle.py
```

Replay the best Mamba model with CUDA:

```bash
conda run -n mamba python scripts/reproduce_gld_mamba_from_bundle.py
```

Mamba bundle files live under:

```text
scripts/gld_mamba_optuna_bundle/
```

This writes:

```text
manuscript/sections/results_baselines.tex
scripts/gld_baseline_optuna_bundle/
scripts/gld_baseline_optuna_bundle/reproduced_artifacts/
scripts/gld_mamba_optuna_bundle/
scripts/gld_mamba_optuna_bundle/reproduced_artifacts/
```

Key findings:

- `TimesNet` is the best Optuna-tuned baseline overall.
- `iTransformer` is a near-tie runner-up, only `0.02` RMSSE behind.
- `PatchTST` is third overall and strongest at `14, 30, 90` days.
- `NLinear` is strongest at `1, 3, 7` days.
- `Nonstationary_Transformer` is strongest at `5` days.
- `TimesNet` is strongest at `60, 120, 180` days.
- `iTransformer` is strongest at `270, 360` days.
- `Transformer`, `Informer`, and `Reformer` remain far weaker on GLD under the full-horizon Optuna objective.

Best model by horizon, measured with test RMSSE:

| Horizon | Best model | RMSSE | RMSE | MAE | Runner-up | RMSSE |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| 1 | `NLinear` | 3.14 | 3.94 | 2.24 | `Nonstationary_Transformer` | 3.25 |
| 3 | `NLinear` | 4.43 | 5.55 | 3.13 | `PatchTST` | 4.52 |
| 5 | `Nonstationary_Transformer` | 5.38 | 6.75 | 4.00 | `NLinear` | 5.39 |
| 7 | `NLinear` | 6.07 | 7.61 | 4.36 | `Nonstationary_Transformer` | 6.27 |
| 14 | `PatchTST` | 7.99 | 10.02 | 6.04 | `NLinear` | 8.08 |
| 30 | `PatchTST` | 10.61 | 13.31 | 8.51 | `Nonstationary_Transformer` | 10.81 |
| 60 | `TimesNet` | 14.00 | 17.56 | 12.10 | `PatchTST` | 14.43 |
| 90 | `PatchTST` | 16.72 | 20.97 | 14.03 | `iTransformer` | 18.33 |
| 120 | `TimesNet` | 20.37 | 25.55 | 17.46 | `iTransformer` | 21.27 |
| 180 | `TimesNet` | 24.22 | 30.37 | 20.88 | `iTransformer` | 24.29 |
| 270 | `iTransformer` | 30.12 | 37.77 | 24.32 | `PatchTST` | 30.54 |
| 360 | `iTransformer` | 37.15 | 46.58 | 31.46 | `TimesNet` | 38.05 |

Average test RMSSE by horizon group:

| Model | Short | Middle | Long | Overall | Overall RMSE |
| --- | ---: | ---: | ---: | ---: | ---: |
| `TimesNet` | 5.27 | 12.94 | 28.78 | 15.66 | 19.64 |
| `iTransformer` | 5.45 | 13.39 | 28.21 | 15.68 | 19.67 |
| `PatchTST` | 5.13 | 12.44 | 30.41 | 15.99 | 20.05 |
| `NLinear` | 4.76 | 13.22 | 31.46 | 16.48 | 20.66 |
| `Autoformer` | 5.45 | 14.53 | 32.37 | 17.45 | 21.88 |
| `DLinear` | 5.01 | 15.05 | 36.30 | 18.78 | 23.55 |
| `Nonstationary_Transformer` | 4.94 | 16.28 | 38.68 | 19.96 | 25.03 |
| `Transformer` | 69.21 | 73.46 | 74.58 | 72.42 | 90.81 |
| `Reformer` | 67.74 | 76.00 | 78.29 | 74.01 | 92.80 |
| `Informer` | 70.95 | 79.65 | 75.44 | 75.35 | 94.48 |

Selected reproducibility settings:

| Model | Trial | Test RMSSE | Val RMSSE | Key hyperparameters |
| --- | ---: | ---: | ---: | --- |
| `TimesNet` | 3 | 15.66 | 6.47 | `seq_len=256, batch_size=32, learning_rate=0.0003, d_model=32, d_ff=128, factor=3, top_k=5, num_kernels=6` |
| `iTransformer` | 1 | 15.68 | 6.48 | `seq_len=192, batch_size=16, learning_rate=0.0002, d_model=256, d_ff=512, factor=1, use_norm=1` |
| `PatchTST` | 0 | 15.99 | 6.50 | `seq_len=256, batch_size=32, learning_rate=0.0002, d_model=256, d_ff=2048, factor=3, patch_len=32, stride=16` |
| `NLinear` | 1 | 16.48 | 6.58 | `seq_len=192, batch_size=32, learning_rate=0.005, factor=1, individual=true` |
| `Autoformer` | 2 | 17.45 | 6.95 | `seq_len=16, batch_size=32, learning_rate=0.0002, d_model=256, d_ff=512, factor=3, moving_avg=25` |
| `DLinear` | 8 | 18.78 | 6.81 | `seq_len=256, batch_size=32, learning_rate=0.005, factor=1, moving_avg=25, individual=true` |
| `Nonstationary_Transformer` | 8 | 19.96 | 6.88 | `seq_len=16, batch_size=16, learning_rate=0.0002, d_model=64, d_ff=128, factor=3, top_k=3, p_hidden_layers=2, p_hidden_dims=[256,256]` |
| `Transformer` | 4 | 72.42 | 4.93 | `seq_len=192, batch_size=16, learning_rate=0.0001, d_model=256, d_ff=1024, factor=3` |
| `Reformer` | 14 | 74.01 | 11.29 | `seq_len=192, batch_size=16, learning_rate=0.0003, d_model=512, d_ff=2048, factor=3` |
| `Informer` | 6 | 75.35 | 6.82 | `seq_len=16, batch_size=32, learning_rate=0.0002, d_model=256, d_ff=1024, factor=3` |

Practical interpretation:

- `TimesNet` is the strongest overall baseline under the full-horizon Optuna objective.
- `iTransformer` is effectively tied with `TimesNet`.
- `PatchTST` is the strongest middle-horizon baseline on average and a top long-horizon contender.
- `NLinear` is the strongest short-horizon baseline on average.
- The plain attention baselines remain far weaker on GLD even after tuning.

## GLD Mamba Optuna Comparison

Current Mamba tables:

```text
results/gld_mamba_optuna_best.csv
48 / 48 rows complete
4 models x 12 horizons
```

Reproducibility and comparison artifacts:

```text
results/optuna/gld/mamba_best_params.json
results/gld_optuna_comparison.csv
```

Compared with the tuned baseline family:

| Family | Best model | Balanced RMSSE | vs best baseline |
| --- | --- | ---: | ---: |
| Baseline | `TimesNet` | 15.66 | - |
| Mamba | `PMS_Mamba-PD` | 14.74 | 5.89% better |

Mamba family summary:

| Model | Short | Middle | Long | Overall | Overall RMSE |
| --- | ---: | ---: | ---: | ---: | ---: |
| `PMS_Mamba-PD` | 5.30 | 11.67 | 27.25 | 14.74 | 18.48 |
| `NS_Mamba-D` | 4.99 | 12.10 | 28.63 | 15.24 | 19.11 |
| `MS_Mamba-MD` | 5.06 | 12.70 | 30.16 | 15.98 | 20.03 |
| `S_Mamba` | 4.78 | 13.67 | 31.91 | 16.79 | 21.05 |

Family winners by horizon:

- Baseline wins `1, 3, 360`.
- Mamba wins `5, 7, 14, 30, 60, 90, 120, 180, 270`.
- The best Mamba model beats the best baseline overall, but the baseline family still edges Mamba at the shortest horizons and at 360 days.

## NS_Mamba Diagnostic Results

Current ablation table:

```text
results/gld_ns_mamba_ablation.csv
16 / 48 rows complete
4 NS_Mamba variants x 4 diagnostic horizons
```

Completed diagnostic horizons:

```text
30, 120, 180, 360 days
```

Diagnostic variants:

| Variant | Adaptive Norm | Decomposition | Shift Gate |
| --- | ---: | ---: | ---: |
| `NS_Mamba-A` | yes | no | no |
| `NS_Mamba-D` | no | yes | no |
| `NS_Mamba-AD` | yes | yes | no |
| `NS_Mamba-ADG` | yes | yes | yes |

Long-horizon diagnostic MSE average over `120, 180, 360`:

| Model | Long Avg. MSE | Long Avg. MAE |
| --- | ---: | ---: |
| `NS_Mamba-D` | 781.30 | 19.54 |
| `iTransformer` | 888.59 | 20.68 |
| `S_Mamba` | 898.25 | 20.84 |
| `NS_Mamba-AD` | 990.99 | 22.34 |
| `NS_Mamba-A` | 1061.22 | 22.97 |
| `NS_Mamba-ADG` | 1080.01 | 23.16 |

`NS_Mamba-D` improves diagnostic long-horizon MSE by:

```text
13.02% vs S_Mamba
12.07% vs iTransformer
```

It also improves diagnostic long-horizon MAE by:

```text
6.22% vs S_Mamba
5.50% vs iTransformer
```

Horizon-level MSE comparison against the best baseline at each diagnostic horizon:

| Horizon | Best baseline MSE | `NS_Mamba-D` MSE | Improvement |
| ---: | ---: | ---: | ---: |
| 30 | 123.61 | 93.31 | 24.51% |
| 120 | 395.81 | 333.03 | 15.86% |
| 180 | 713.54 | 586.47 | 17.81% |
| 360 | 1556.41 | 1424.41 | 8.48% |

Interpretation:

- The decomposition-only variant is the strongest current architecture.
- Adaptive normalization does not help in the first diagnostic sweep.
- Shift-aware fusion also does not help in the first diagnostic sweep.
- Promote `NS_Mamba-D` to the full 12-horizon GLD run before changing the architecture again.

Next commands:

```bash
bash scripts/gld_ns_mamba/run_ns_mamba_ablation.sh full NS_Mamba-D
python scripts/gld_ns_mamba/collect_ns_mamba_results.py
python scripts/gld_ns_mamba/analyze_ns_mamba_results.py
```

## Source-Optimized Imported Model Results

Current optimized sweep status:

```text
results/gld_source_optimized_all.csv
results/gld_source_optimized_best.csv
540 / 756 rows complete
```

This sweep uses the model-specific GLD hyperparameter style from:

```text
nonstationary_transformer/scripts/GLD.sh
```

So it should be interpreted separately from the locked shared-setting baseline table.

Completed models:

| Model | Completed optimized rows | Coverage |
| --- | ---: | --- |
| `PatchTST` | 108 | complete through 360 days |
| `DLinear` | 108 | complete through 360 days |
| `NLinear` | 108 | complete through 360 days |
| `TimesNet` | 108 | complete through 360 days |
| `Nonstationary_Transformer` | 108 | complete through 360 days |
| `Autoformer` | 0 | source-style sweep pending |
| `Transformer` | 0 | source-style sweep pending |

Best optimized imported model by horizon:

| Horizon | Winner | Best seq_len | MSE | MAE |
| ---: | --- | ---: | ---: | ---: |
| 1 | `NLinear` | 320 | 6.57 | 1.70 |
| 3 | `NLinear` | 320 | 12.43 | 2.36 |
| 5 | `NLinear` | 384 | 17.66 | 2.85 |
| 7 | `NLinear` | 192 | 23.35 | 3.30 |
| 14 | `NLinear` | 192 | 42.82 | 4.55 |
| 30 | `TimesNet` | 256 | 88.29 | 6.89 |
| 60 | `PatchTST` | 320 | 177.96 | 9.76 |
| 90 | `TimesNet` | 320 | 176.51 | 10.23 |
| 120 | `PatchTST` | 256 | 234.57 | 11.61 |
| 180 | `PatchTST` | 320 | 450.61 | 15.86 |
| 270 | `PatchTST` | 128 | 791.40 | 20.23 |
| 360 | `PatchTST` | 128 | 1110.96 | 23.36 |

Average MSE across the full 12-horizon imported sweep:

| Model | Short | Middle | Long | Overall |
| --- | ---: | ---: | ---: | ---: |
| `PatchTST` | 15.45 | 131.21 | 646.89 | 264.51 |
| `NLinear` | 15.00 | 145.47 | 729.23 | 296.57 |
| `TimesNet` | 15.99 | 123.92 | 785.02 | 308.31 |
| `Nonstationary_Transformer` | 18.40 | 175.74 | 948.77 | 380.97 |
| `DLinear` | 39.67 | 287.47 | 1668.13 | 665.09 |

Interpretation:

- `NLinear` is the best imported model on the short horizons `1, 3, 5, 7`.
- `TimesNet` is the strongest imported model by average middle-horizon MSE on `14, 30, 60, 90`.
- `PatchTST` is the best imported model overall and the best long-horizon imported model at `120, 180, 270, 360`.
- `TimesNet` is strongest at `30` and `90` days.
- `Nonstationary_Transformer` and `DLinear` are not competitive with the best imported model once the full optimized sweep is complete.

Best lookback patterns:

- `NLinear` prefers very large windows: `192` to `384`.
- `PatchTST` prefers `16` on short horizons, `256` to `320` from `30` to `180`, and `128` at `270` and `360`.
- `TimesNet` prefers `16` on short horizons and much larger windows at middle and long horizons.
- `Nonstationary_Transformer` still prefers mostly `16`, which appears too short for strong long-horizon GLD performance.

Compared with the best locked-setting baseline per horizon:

- optimized `NLinear` is much stronger at short horizons
- optimized `TimesNet` is strongest on the middle block overall, with `PatchTST` close behind
- optimized `PatchTST` is much stronger at long horizons
- optimized `TimesNet` is also consistently stronger than the locked-setting baseline
- optimized `DLinear` is weaker than the best locked-setting baseline at every horizon

Representative improvements:

- `NLinear` at `1d`: `6.57` vs `19.80` (`+66.83%` MSE improvement)
- `PatchTST` at `120d`: `234.57` vs `395.81` (`+40.73%`)
- `PatchTST` at `360d`: `1110.96` vs `1556.41` (`+28.62%`)
- `TimesNet` at `90d`: `176.51` vs `278.28` (`+36.57%`)

Current conclusion:

- the locked shared-setting baseline is still useful for controlled comparison
- GLD is highly sensitive to model-specific tuning
- among the completed imported models, `PatchTST` is strongest overall
- `NLinear` is the strongest short-horizon imported baseline
- `TimesNet` is the strongest middle-horizon imported baseline by average MSE
- `PatchTST` is the strongest long-horizon imported baseline

## NS_Mamba vs All Completed Models

This section is the pre-HPO direct cross-model comparison for `NS_Mamba`. It uses the only horizons where the original `NS_Mamba` diagnostic variants have completed results:

```text
30, 120, 180, 360 days
```

This comparison includes:

- shared locked-setting baselines
- all four `NS_Mamba` diagnostic variants
- tuned imported baselines from the completed source-optimized sweep

Long-horizon average over `120, 180, 360` by RMSE:

| Model | Track | Long Avg. RMSE | Long Avg. MAE |
| --- | --- | ---: | ---: |
| `PatchTST` | Opt | 23.29 | 16.94 |
| `NLinear` | Opt | 25.31 | 18.08 |
| `TimesNet` | Opt | 25.92 | 18.90 |
| `NS_Mamba-D` | NS-Diag | 26.74 | 19.54 |
| `iTransformer` | Shared | 28.69 | 20.68 |
| `S_Mamba` | Shared | 28.90 | 20.84 |
| `Nonstationary_Transformer` | Opt | 29.00 | 19.99 |
| `NS_Mamba-AD` | NS-Diag | 30.13 | 22.34 |
| `NS_Mamba-ADG` | NS-Diag | 31.10 | 23.16 |
| `NS_Mamba-A` | NS-Diag | 31.16 | 22.97 |
| `DLinear` | Opt | 37.97 | 27.13 |
| `Autoformer` | Shared | 42.79 | 29.01 |
| `Transformer` | Shared | 72.14 | 59.64 |
| `Informer` | Shared | 73.11 | 56.60 |
| `Reformer` | Shared | 83.51 | 67.99 |

`NS_Mamba-D` rank by RMSE among all completed models:

- `30d`: 5th
- `120d`: 4th
- `180d`: 3rd
- `360d`: 4th
- long-horizon average `120/180/360`: 4th overall

Interpretation:

- `NS_Mamba-D` is the strongest original `NS_Mamba` diagnostic variant.
- `NS_Mamba-D` beats every shared locked-setting baseline and every other `NS_Mamba` diagnostic variant.
- `NS_Mamba-D` does not yet beat the tuned imported leaders `PatchTST`, `NLinear`, and `TimesNet`.
- After Mamba-family HPO, the stronger Mamba result is optimized `MS_Mamba-MD`, summarized in the next section.

## Mamba HPO Results

Current HPO tables:

```text
results/gld_mamba_optuna_best.csv
results/optuna/gld/mamba_best_params.json
48 / 48 rows complete
4 models x 12 horizons
```

The HPO search includes:

- `S_Mamba`
- `NS_Mamba-D`
- `MS_Mamba-MD`
- `PMS_Mamba-PD`

Best Mamba model:

- `PMS_Mamba-PD`

Comparison with the tuned baseline family:

| Family | Best model | Balanced RMSSE |
| --- | --- | ---: |
| Baseline | `TimesNet` | 15.66 |
| Mamba | `PMS_Mamba-PD` | 14.74 |

Interpretation:

- `PMS_Mamba-PD` is the strongest current Mamba-family model.
- It beats the tuned baseline winner `TimesNet` on overall balanced RMSSE.
- `NS_Mamba-D` remains the strongest diagnostic Mamba variant outside the final promoted PMS configuration.
- Short-horizon performance still favors the baseline family at `1`, `3`, and `360` days, while Mamba dominates most of the remaining horizons.

Next commands:

```bash
python scripts/gld_ns_mamba/collect_gld_mamba_hpo.py
python scripts/gld_ns_mamba/analyze_gld_mamba_hpo.py
```

## Benchmark Results

All benchmark datasets are evaluated in **S mode** (single-variate) under identical
Optuna HPO settings: 20 baseline trials per model, 24 Mamba trials per model,
`calibration-horizons` focused on one representative horizon per term group,
full-horizon replay for the top-5 candidates, and the best candidate evaluated
on unseen test data. The objective is `balanced_rmsse` across short, middle, and
long horizon groups.

### Summary

| Dataset | Nonstationarity | Best Baseline | Best Mamba | Mamba vs Baseline |
| --- | --- | --- | --- | ---: |
| GLD | Trend + volatility shift | TimesNet (15.66) | PMS_Mamba-PD (14.74) | **+5.89%** |
| Exchange | Mean shift (1.44) | PatchTST (6.37) | S_Mamba (6.29) | **+1.24%** |
| Weather | Variance shift (1.37) | NLinear (0.132) | PMS_Mamba-PD (0.137) | −3.70% |

### Exchange (UK Pound/USD, 1971–2026)

Daily UK Pound/USD exchange rate sourced from FRED. 13,885 rows.
Trend-drift nonstationarity: ADF cannot reject unit root, mean_shift=1.44.

| Model | Phase | Short | Middle | Long | Balanced RMSSE |
| --- | --- | ---: | ---: | ---: | ---: |
| **S_Mamba** | mamba | 1.94 | 5.38 | 11.55 | **6.29** |
| NS_Mamba-D | mamba | 1.93 | 5.39 | 11.59 | 6.30 |
| PMS_Mamba-PD | mamba | 1.93 | 5.38 | 11.61 | 6.31 |
| MS_Mamba-MD | mamba | 1.96 | 5.45 | 11.62 | 6.35 |
| PatchTST | baseline | 1.96 | 5.48 | 11.67 | 6.37 |
| NLinear | baseline | **1.91** | 5.54 | 11.81 | 6.42 |
| iTransformer | baseline | 2.13 | 5.70 | 11.86 | 6.56 |
| Nonstationary_Transformer | baseline | 1.93 | 5.55 | 12.30 | 6.59 |
| TimesNet | baseline | 2.20 | 5.73 | 11.90 | 6.61 |
| Autoformer | baseline | 2.39 | 5.70 | 11.78 | 6.62 |
| DLinear | baseline | 1.92 | 5.57 | 14.46 | 7.32 |
| Informer | baseline | 2.40 | 7.03 | 15.11 | 8.18 |
| Transformer | baseline | 2.43 | 6.42 | 15.70 | 8.19 |
| Reformer | baseline | 3.28 | 13.71 | 23.37 | 13.45 |

Key findings:

- Mamba models occupy the top 4 spots, with S_Mamba as the overall winner.
- Mamba's advantage grows with horizon length: long-horizon RMSSE 11.55 vs best baseline 11.67.
- Traditional Transformer-family models (Transformer, Informer, Reformer) fail badly on this strongly nonstationary series.

### Weather (Jena, 2020–2021)

10-minute meteorological data from the Max Planck Institute Jena weather station.
52,696 rows, predicting outdoor temperature (OT). Variance-shift nonstationarity:
std_shift=1.37, the highest among all evaluated datasets.

| Model | Phase | Short | Middle | Long | Balanced RMSSE |
| --- | --- | ---: | ---: | ---: | ---: |
| **NLinear** | baseline | 0.112 | 0.128 | 0.155 | **0.132** |
| PMS_Mamba-PD | mamba | 0.121 | 0.133 | 0.156 | 0.137 |
| PatchTST | baseline | 0.122 | 0.135 | 0.155 | 0.137 |
| iTransformer | baseline | 0.125 | 0.135 | 0.158 | 0.139 |
| TimesNet | baseline | 0.124 | 0.135 | 0.165 | 0.141 |
| MS_Mamba-MD | mamba | 0.127 | 0.137 | 0.160 | 0.141 |
| NS_Mamba-D | mamba | 0.127 | 0.138 | 0.162 | 0.142 |
| S_Mamba | mamba | 0.128 | 0.138 | 0.166 | 0.144 |
| Nonstationary_Transformer | baseline | 0.129 | 0.148 | 0.167 | 0.148 |
| Informer | baseline | 0.181 | 0.207 | 0.181 | 0.190 |
| Transformer | baseline | 0.222 | 0.225 | 0.182 | 0.210 |
| Autoformer | baseline | 0.230 | 0.187 | 0.217 | 0.211 |
| DLinear | baseline | 0.202 | 0.269 | 0.284 | 0.252 |
| Reformer | baseline | 2.149 | 0.234 | 0.293 | 0.892 |

Key findings:

- NLinear's `x - last_value` normalization is particularly effective against variance-shift nonstationarity.
- PMS_Mamba-PD is a close runner-up, only 3.7% behind NLinear in balanced RMSSE.
- Mamba models are tightly clustered (0.137–0.144), showing consistent behavior.
- DLinear performs poorly (0.252) despite sharing a similar architecture with NLinear, showing that the last-value subtraction is critical for variance-drift scenarios.

## Environment

Tested local environment:

```text
conda env: mamba
Python: 3.9.23
torch: 2.6.0+cu126
mamba_ssm: 2.2.4
CUDA: available
```

Recommended setup:

```bash
conda create -n mamba python=3.9 -y
conda activate mamba
pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu126
pip install -r requirements.txt
```

If using a different CUDA version, install the matching PyTorch wheel first, then install the remaining requirements.

Run commands from outside the activated environment with:

```bash
conda run -n mamba python -u run.py ...
```

Important: models using `mamba_ssm.Mamba` require CUDA in the current tested environment.

## Data

Benchmark datasets can be downloaded from the original S-Mamba release:

```text
https://github.com/wzhwzhwzh0921/S-D-Mamba/releases/download/datasets/S-Mamba_datasets.zip
```

Custom CSV datasets use:

```text
--data custom
```

The CSV must contain:

- `date`
- target column (single in `S` mode, one of the feature columns in `M` mode)
- feature columns (for `M` / `MS` mode)

### Exchange Rate Dataset

The exchange rate data is sourced from the **US Federal Reserve (FRED)**:

```text
Foreign exchange rates from US Federal Reserve in daily, monthly and yearly basis.
https://fred.stlouisfed.org
```

Local files:

```text
data/Exchange/daily.csv          # raw FRED long-format data (22 countries, 1971–2026)
data/Exchange/exchange_rate.csv  # processed wide-format data for the pipeline
```

The processed dataset contains **11 USD/currency exchange rates** at daily frequency:

```text
Australia, Canada, Denmark, Japan, Malaysia, New Zealand, Norway,
Sweden, Switzerland, United Kingdom, OT (India)
```

- Date range: 1973-01-02 to 2026-05-15 (53 years, 13,924 rows)
- All 11 channels are **multivariate** (`features: "M"`)
- Missing values (weekends/holidays) are forward-filled

This dataset replaces the old 1990–2010 anonymous 7-country exchange rate file.
Compared with the old dataset, the FRED dataset spans more than twice the time range,
covers additional economic regimes (1970s oil crisis, Plaza Accord, Asian Financial
Crisis, 2008 GFC, Euro crisis, COVID-19, post-COVID rate hikes), and the source is
independently citable.

### Multivariate Mode and Weight Sharing

All models in this project now operate under **multivariate** (`features: "M"`) mode
for the exchange rate dataset. In this mode, all channels are predicted simultaneously
and all evaluation metrics (MSE, MAE, RMSSE) are averaged across channels.

For fair comparison, all models use **shared weights across channels**:

| Architecture | Weight sharing | Models |
| --- | --- | --- |
| Inverted (variate-as-token) | Identical weights (0 extra params) | iTransformer, S_Mamba, NS_Mamba, MS_Mamba, PMS_Mamba |
| Channel-shared | Identical weights (0 extra params) | PatchTST, DLinear (`individual=False`), NLinear (`individual=False`) |
| Traditional (input embedding) | <1% extra params (input projection only) | Transformer, Informer, Reformer, Autoformer, TimesNet, Nonstationary_Transformer |

This ensures no model gains an unfair parameter advantage when scaling from single-variate
to multivariate forecasting.

Local GLD dataset:

```text
data/GLD/GLD.csv
```

GLD target:

```text
close
```

Use GLD for quick debugging and smoke tests. It should not replace standard benchmark evaluation.

## Hyperparameter Optimization (Optuna)

The HPO pipeline is defined in `scripts/optuna/run_dataset_optuna.py`.

### Data Split Usage

The dataset is split into three disjoint periods: **train**, **val**, and **test**.

| Phase | Data Split | Purpose |
|-------|-----------|---------|
| HPO calibration (tuning) | **val** | Optuna uses validation-set metrics (`balanced_rmsse`) to rank and prune hyperparameter trials |
| Selection replay | **val** | The top-K calibrated configurations are re-evaluated on the full validation horizon set and the best one is selected |
| Final report | **test** | The selected configuration is evaluated once on unseen test data for the published result |

This means:
- The **test set is never seen during hyperparameter search** — it remains a clean final benchmark.
- The **val set guides parameter selection** (via MedianPruner + TPE sampler and the full-horizon replay).
- All metrics reported in Optuna result files (`baseline_trials.csv`, `baseline_best_params.json`) are:
  - **val-set metrics** for calibration trials
  - **val-set metrics** for selection replay rows
  - **test-set metrics** for final published rows

### Usage

```bash
conda run -n mamba python scripts/optuna/run_dataset_optuna.py \
  --dataset gld \
  --phase baseline \
  --models iTransformer Transformer Informer Reformer Autoformer DLinear NLinear PatchTST TimesNet Nonstationary_Transformer \
  --trials 20 \
  --study-suffix fullcal_v1 \
  --calibration-horizons 1 3 5 7 14 30 60 90 120 180 270 360 \
  --full-horizons 1 3 5 7 14 30 60 90 120 180 270 360
```

- `--calibration-horizons` — Horizons used during the tuning loop on the **val** set. The main GLD rerun uses the full 12-horizon suite so the calibration objective matches the final horizon-balanced comparison.
- `--full-horizons` — Horizons used for full validation replay and final **test** evaluation. The final `balanced_rmsse` averages across all these horizons.
- `--study-suffix` — Suffix appended to the Optuna study name. Use a new suffix whenever the objective changes. For example, `fullcal_v1` keeps full-horizon calibration studies separate from earlier `7 90 360` calibration studies inside `results/optuna/gld/studies.db`.
- `--trials` — Target total trials per model study, not additional trials. To continue a `fullcal_v1` study from 20 to 40 trials, rerun with `--trials 40`.

Fast pilot calibration can still use one horizon per term group:

```bash
conda run -n mamba python scripts/optuna/run_dataset_optuna.py \
  --dataset gld \
  --phase baseline \
  --models iTransformer Transformer Informer Reformer Autoformer DLinear NLinear PatchTST TimesNet Nonstationary_Transformer \
  --trials 20 \
  --study-suffix sparsecal_v1 \
  --calibration-horizons 7 90 360 \
  --full-horizons 1 3 5 7 14 30 60 90 120 180 270 360
```

Do not reuse the same study suffix across sparse and full-horizon calibration, because those objectives are not comparable.

## Models

All model files live in `model/`. Each model exposes a `Model` class and is registered in `experiments/exp_basic.py`.

### Clean Baselines

These are non-Mamba baseline models after cleanup.

| Model name | File | Main idea | Notes |
| --- | --- | --- | --- |
| `Autoformer` | `model/Autoformer.py` | AutoCorrelation with decomposition | Encoder-decoder baseline |
| `Informer` | `model/Informer.py` | ProbSparse attention | Clean attention baseline |
| `Reformer` | `model/Reformer.py` | Reformer LSH attention | Mamba removed from this baseline |
| `Transformer` | `model/Transformer.py` | Full attention Transformer | Mamba removed from this baseline |

### Inverted Variable-Token Models

This active inverted baseline uses `DataEmbedding_inverted`, treating variables and time features as tokens.

| Model name | File | Main idea | Notes |
| --- | --- | --- | --- |
| `iTransformer` | `model/iTransformer.py` | Inverted full-attention Transformer | Supports `--use_norm` |

### Main Mamba Baseline

| Model name | File | Main idea | Notes |
| --- | --- | --- | --- |
| `S_Mamba` | `model/S_Mamba.py` | Inverted embedding plus bidirectional Mamba encoder | Main baseline for this project |
| `NS_Mamba` | `model/NS_Mamba.py` | Nonstationarity-aware Mamba ablations | Best diagnostic variant so far is `NS_Mamba-D` |
| `MS_Mamba` | `model/MS_Mamba.py` | Multi-scale Mamba branches over downsampled windows | Designed to target the PatchTST/TimesNet long-horizon gap |

`S_Mamba` path:

```text
Input [B, L, N]
  -> optional mean/std normalization
  -> DataEmbedding_inverted
  -> bidirectional Mamba encoder
  -> projection to pred_len
  -> optional de-normalization
  -> forecast [B, pred_len, N]
```

`MS_Mamba` path:

```text
Input [B, L, N]
  -> optional mean/std normalization
  -> optional trend/seasonal/residual component tokens
  -> temporal downsampling at scales such as 1, 2, 4
  -> independent bidirectional Mamba encoder per scale
  -> scale-level forecast fusion by gate, learned weights, or mean
  -> optional de-normalization
  -> forecast [B, pred_len, N]
```

Useful GLD commands:

```bash
bash scripts/gld_ns_mamba/run_ms_mamba_ablation.sh smoke MS_Mamba-MDG
bash scripts/gld_ns_mamba/run_ms_mamba_ablation.sh diagnostic
python scripts/gld_ns_mamba/collect_ms_mamba_results.py
```

Mamba hyperparameter optimization by RMSE:

```bash
bash scripts/gld_ns_mamba/run_gld_mamba_hpo.sh smoke S_Mamba
bash scripts/gld_ns_mamba/run_gld_mamba_hpo.sh diagnostic MS_Mamba-MD
bash scripts/gld_ns_mamba/run_gld_mamba_hpo.sh diagnostic ALL
python scripts/gld_ns_mamba/collect_gld_mamba_hpo.py
python scripts/gld_ns_mamba/analyze_gld_mamba_hpo.py
```

The HPO runner supports:

```text
SEARCH_SPACE=focused  # default
SEARCH_SPACE=wide
HORIZONS="120 180 270 360"
SEQ_LENS="128 192 256 320 384"
FORCE=1
```

It writes:

```text
results/gld_mamba_hpo_all.csv
results/gld_mamba_hpo_best.csv
```

## Model Behavior

- Every registered model returns forecasts shaped `[B, pred_len, N]` when `--output_attention` is false.
- When `--output_attention` is true, models return `(forecast, attention_info)`.
- Some inverted models return `None` for attention info because attention output is not exposed.
- `Transformer.py` and `Reformer.py` are clean non-Mamba baselines.
- Mamba-related models should be run on GPU.

## Nonstationary Mamba Plan

### Research Goal

Build a new Mamba-based forecasting model for nonstationary multivariate time series.

The target problem is long-term forecasting under changes in:

- mean
- variance
- trend
- seasonality
- volatility
- temporal regime

The new model should keep `S_Mamba` as the baseline and create a separate model:

```text
model/NS_Mamba.py
```

### Main Idea

Propose a nonstationarity-aware Mamba model combining:

1. Adaptive normalization
2. Trend-seasonal-residual decomposition
3. Mamba-based temporal modeling
4. Distribution-shift-aware gating or fusion

Working model name:

```text
NS_Mamba
```

Core claim:

```text
A Mamba forecasting model can better handle nonstationary time series when distribution shift is explicitly estimated and used to guide normalization, decomposition, and feature fusion.
```

### Target Architecture

```text
Input sequence
  -> Adaptive nonstationary normalization
  -> Optional trend/seasonal/residual decomposition
  -> Inverted embedding
  -> Bidirectional Mamba encoder
  -> Optional distribution-shift-aware fusion gate
  -> Projection to prediction length
  -> De-normalization
  -> Forecast
```

### Variant A: Adaptive Normalization

Implemented layer:

```text
layers/NonStationaryNorm.py
```

Design:

```text
x_norm = (x - mean) / std
stats = statistics(x)
gamma, beta = MLP(stats)
x_adapted = gamma * x_norm + beta
```

Useful statistics:

- mean
- standard deviation
- first value
- last value
- recent mean
- recent standard deviation
- slope
- min / max
- recent volatility

First `NS_Mamba` integration should use `AdaptiveRevIN` without extra CLI flags. Add flags only after the first smoke test works.

### Variant B: Decomposition

Implemented layer:

```text
layers/SeriesDecomp.py
```

Design:

```text
x = trend + seasonal + residual
trend = moving_average(x)
seasonal = x - trend
residual = optional high-frequency component
```

Possible branch structure:

```text
trend -> Mamba branch
seasonal -> Mamba branch
residual -> Mamba branch
```

Final forecast:

```text
y_hat = y_trend + y_seasonal + y_residual
```

Start with simple moving average decomposition and compare window sizes:

- 13
- 25
- 49

### Variant C: Shift-Aware Gate

Implemented layer:

```text
layers/NonStationaryGate.py
```

Shift features:

```text
shift_mean = mean(recent window) - mean(full window)
shift_std = std(recent window) - std(full window)
shift_slope = last value - first value
shift_volatility = std(diff(x))
```

Hidden gating:

```text
h = gate * h_mamba + (1 - gate) * h_skip
```

Branch fusion:

```text
h = gate_trend * h_trend + gate_seasonal * h_seasonal + gate_residual * h_residual
```

## Implementation Roadmap

### Step 1: Environment and Data

Status: done.

- `mamba` conda environment works.
- CUDA is available.
- GLD custom dataset works with `S_Mamba`.

### Step 2: Baseline Cleanup

Status: done.

- Removed Mamba from `Transformer.py`.
- Removed Mamba from `Reformer.py`.
- Replaced hard-coded `d_state=16` with `configs.d_state` in Mamba variants.
- Made `output_attention=True` safe across registered models.
- Removed unused hard-coded `d_model=11` modules from `layers/Mamba_EncDec.py`.

Verification:

```text
All registered models passed CUDA forward checks with output_attention=False and output_attention=True.
```

### Step 3: Add `NS_Mamba`

Status: done.

Created:

```text
model/NS_Mamba.py
```

Registered in:

```text
experiments/exp_basic.py
```

The model must expose:

```python
class Model(nn.Module):
    def __init__(self, configs):
        ...

    def forward(self, x_enc, x_mark_enc, x_dec, x_mark_dec, mask=None):
        ...
```

Expected output:

```text
[B, pred_len, N]
```

Available CLI flags:

```text
--use_adaptive_norm
--use_decomp
--use_shift_gate
--ns_adaptive_scale
--ns_recent_ratio
```

### Step 4: Add Decomposition

Status: done.

Decomposition is implemented in `NS_Mamba-D`, `NS_Mamba-AD`, and `NS_Mamba-ADG`.

Best diagnostic variant:

```text
NS_Mamba-D
```

### Step 5: Add Shift Gate

Status: diagnostic complete.

Shift-aware branch fusion is implemented in `NS_Mamba-ADG`, but it did not improve the first GLD diagnostic sweep.

Next action:

```text
Run the full 12-horizon GLD sweep for NS_Mamba-D before redesigning the gate.
```

## Experiment Plan

### GLD Baseline Plan

The publication baseline is the Optuna-tuned comparison summarized in `## GLD Baseline Results`.

To regenerate the manuscript section and the machine-readable tables, run:

```bash
python manuscript/scripts/generate_gld_baseline_results.py
```

This writes:

```text
manuscript/sections/results_baselines.tex
manuscript/data/gld_baseline_optuna_best.csv
manuscript/data/gld_baseline_optuna_hyperparameters.csv
```

Source artifacts:

```text
results/gld_baseline_optuna_best.csv
results/optuna/gld/baseline_best_params.json
```

Current baseline summary:

1. `TimesNet` is strongest overall by balanced test RMSSE.
2. `iTransformer` is the near-tied runner-up.
3. `PatchTST` is strongest at several middle and long horizons.
4. `NLinear` is strongest on average at short horizons.

### Benchmark Baseline Plan

After GLD baselines are recorded, reproduce benchmark `S_Mamba` results on:

- ETTm1
- ETTm2
- ETTh1
- ETTh2
- Exchange
- Weather
- ECL
- Traffic

Benchmark prediction lengths:

- 96
- 192
- 336
- 720

Benchmark metrics:

- MSE
- MAE
- training time
- GPU memory usage
- parameter count

### Ablation Study

| Model | Adaptive Norm | Decomposition | Shift Gate |
| --- | --- | --- | --- |
| `S_Mamba` | No | No | No |
| `NS_Mamba-A` | Yes | No | No |
| `NS_Mamba-D` | No | Yes | No |
| `NS_Mamba-AD` | Yes | Yes | No |
| `NS_Mamba-ADG` | Yes | Yes | Yes |

Most important comparison after the diagnostic sweep:

```text
S_Mamba vs iTransformer vs NS_Mamba-D
```

### Dataset Priority

Prioritize:

1. GLD baseline results
2. GLD `NS_Mamba` ablations
3. Exchange
4. Weather
5. ETTm1 / ETTm2
6. Traffic
7. ECL

GLD is the main local dataset and should be evaluated before new architecture claims.

Exchange is important because it often has strong distribution shift.

Weather is useful because it contains seasonal patterns and changing local dynamics.

Traffic and ECL are useful for large multivariate forecasting.

## Milestones

### Milestone 1

Status: complete.

Done:

```text
GLD dataset moved and validated.
S_Mamba smoke test completed on GLD close.
AdaptiveRevIN layer implemented.
SeriesDecomp layer implemented.
NonStationaryGate layer implemented.
Baseline model cleanup completed.
Full GLD baseline evaluation completed.
120 / 120 baseline rows collected in results/gld_baseline_optuna_best.csv.
Reproducibility hyperparameters collected in results/optuna/gld/baseline_best_params.json.
TimesNet, iTransformer, and PatchTST identified as the top three Optuna-tuned baselines.
NS_Mamba implemented and registered.
Diagnostic NS_Mamba ablation completed for horizons 30, 120, 180, and 360.
NS_Mamba-D identified as the strongest diagnostic variant.
```

### Milestone 2

Status: complete.

Implemented the `NS_Mamba` ablation family:

```text
NS_Mamba-A
NS_Mamba-D
NS_Mamba-AD
NS_Mamba-ADG
```

Diagnostic horizons:

```text
30, 120, 180, 360 days
```

Best diagnostic result:

```text
NS_Mamba-D
```

Save results to:

```text
results/gld_ns_mamba_ablation.csv
```

### Milestone 3

Status: next.

Run the promoted full GLD comparison:

```text
S_Mamba vs iTransformer vs NS_Mamba-D
```

Horizons:

```text
1, 3, 5, 7, 14, 30, 60, 90, 120, 180, 270, 360 days
```

Success target:

```text
Reduce long-horizon average MSE versus both S_Mamba and iTransformer.
```

### Milestone 4

Run the first external-dataset comparison:

```text
S_Mamba vs iTransformer vs NS_Mamba-D
```

Run on:

- Exchange
- Weather

Prediction lengths:

- 96
- 192
- 336
- 720

### Milestone 5

Revisit the failed diagnostic additions only if decomposition alone is confirmed on the full GLD sweep:

```text
AdaptiveRevIN tuning
Shift-aware fusion redesign
Moving-average window tuning
```

## GLD Smoke Test

Use this to verify the environment and dataset path:

```bash
conda run -n mamba python -u run.py \
  --is_training 1 \
  --model_id GLD_smoke \
  --model S_Mamba \
  --data custom \
  --root_path ./data/GLD/ \
  --data_path GLD.csv \
  --features S \
  --target close \
  --freq d \
  --seq_len 30 \
  --label_len 15 \
  --pred_len 5 \
  --enc_in 1 \
  --dec_in 1 \
  --c_out 1 \
  --d_model 32 \
  --d_state 16 \
  --d_ff 64 \
  --e_layers 1 \
  --batch_size 16 \
  --train_epochs 1 \
  --patience 1 \
  --num_workers 0 \
  --des smoke \
  --itr 1
```

Latest smoke-test result:

```text
MSE: 0.0375749
MAE: 0.1362793
```

This is an environment check, not a final benchmark.

## Common Training Commands

Run existing `S_Mamba` benchmark scripts:

```bash
bash ./scripts/multivariate_forecasting/ECL/S_Mamba.sh
bash ./scripts/multivariate_forecasting/Exchange/S_Mamba.sh
bash ./scripts/multivariate_forecasting/Traffic/S_Mamba.sh
bash ./scripts/multivariate_forecasting/Weather/S_Mamba.sh
bash ./scripts/multivariate_forecasting/SolarEnergy/S_Mamba.sh
bash ./scripts/multivariate_forecasting/ETT/S_Mamba_ETTm1.sh
bash ./scripts/multivariate_forecasting/ETT/S_Mamba_ETTm2.sh
bash ./scripts/multivariate_forecasting/ETT/S_Mamba_ETTh1.sh
bash ./scripts/multivariate_forecasting/ETT/S_Mamba_ETTh2.sh
```

PEMS scripts:

```bash
bash ./scripts/multivariate_forecasting/PEMS/S_Mamba_03.sh
bash ./scripts/multivariate_forecasting/PEMS/S_Mamba_04.sh
bash ./scripts/multivariate_forecasting/PEMS/S_Mamba_07.sh
bash ./scripts/multivariate_forecasting/PEMS/S_Mamba_08.sh
```

## Final Deliverables

Expected final files:

```text
model/NS_Mamba.py
scripts/nonstationary_forecasting/Exchange/NS_Mamba.sh
scripts/nonstationary_forecasting/Weather/NS_Mamba.sh
scripts/nonstationary_forecasting/ETT/NS_Mamba_ETTm1.sh
scripts/nonstationary_forecasting/ETT/NS_Mamba_ETTm2.sh
```

Expected final results:

```text
results/nonstationary_mamba_ablation.csv
results/nonstationary_mamba_main_results.csv
```

## Repo-Local Skills

Local Codex skills:

```text
.codex/skills/nonstationary-mamba
.codex/skills/latex-manuscript
```

Use `nonstationary-mamba` for coding, datasets, model integration, and experiment commands.

Keep `latex-manuscript` for later paper-writing work.

## Citation

Original S-Mamba paper:

```bibtex
@article{wang2024mamba,
  title={Is mamba effective for time series forecasting?},
  author={Wang, Zihan and Kong, Fanheng and Feng, Shi and Wang, Ming and Yang, Xiaocui and Zhao, Han and Wang, Daling and Zhang, Yifei},
  journal={Neurocomputing},
  pages={129178},
  year={2024},
  publisher={Elsevier}
}
```
