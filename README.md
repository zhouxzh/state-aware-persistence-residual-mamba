# Nonstationary Mamba Time-Series Forecasting

This repository is a forecasting research workspace based on S-Mamba. The goal is to build and evaluate Mamba-based models for nonstationary time series, using `S_Mamba` as the main baseline and extending toward `NS_Mamba`.

This README is the single project document for setup, model inventory, current status, and the research plan.

## Current Status

Completed:

- Verified the `mamba` conda environment with Torch, CUDA, and `mamba_ssm`.
- Moved the GLD dataset to `data/GLD/GLD.csv`.
- Normalized the GLD target column from `Close` to `close`.
- Ran a one-epoch `S_Mamba` smoke test on GLD `close`.
- Added adaptive normalization: `layers/NonStationaryNorm.py`.
- Added decomposition utilities: `layers/SeriesDecomp.py`.
- Added shift-aware gate: `layers/NonStationaryGate.py`.
- Completed the full GLD baseline sweep with 72 / 72 finished runs.
- Collected the finished baseline table in `results/gld_baselines.csv`.
- Implemented and registered `model/NS_Mamba.py`.
- Added GLD NS_Mamba ablation scripts under `scripts/gld_ns_mamba/`.
- Completed the NS_Mamba diagnostic sweep with 16 / 48 ablation rows finished.
- Identified `NS_Mamba-D` as the strongest diagnostic variant.
- Implemented and registered `model/MS_Mamba.py` for multi-scale Mamba forecasting.
- Added GLD MS_Mamba ablation and collection scripts under `scripts/gld_ns_mamba/`.
- Verified `MS_Mamba-MDG` with a one-epoch GLD smoke run.
- Completed Mamba-family HPO with 266 finished runs and 25 RMSE-selected best rows.
- Identified optimized `MS_Mamba-MD` as the strongest current Mamba-family model.
- Added source-style GLD optimized sweep scripts for imported models.
- Completed the optimized GLD sweep for `Nonstationary_Transformer`, `TimesNet`, `PatchTST`, `DLinear`, and `NLinear`.
- Identified `PatchTST` as the strongest imported model overall under the completed optimized sweep.
- Cleaned model baselines:
  - removed Mamba from `model/Transformer.py`
  - removed Mamba from `model/Reformer.py`
  - fixed hard-coded `d_state=16` in Mamba variants
  - made `output_attention=True` safe across registered models
  - removed unused hard-coded modules from `layers/Mamba_EncDec.py`
- Added repo-local skills:
  - `.codex/skills/nonstationary-mamba`
  - `.codex/skills/latex-manuscript`
  - `.codex/skills/graphviz`
  - `.codex/skills/tikz`

Next immediate task:

```text
Run the full 12-horizon HPO evaluation for the promoted `MS_Mamba-MD` configuration.
```

## GLD Baseline Results

Completed baseline table:

```text
results/gld_baselines.csv
72 / 72 rows complete
6 models x 12 horizons
```

Generate the LaTeX include used by the manuscript with:

```bash
python scripts/manuscript/generate_gld_results_tex.py
```

This writes:

```text
manuscript/generated/gld_baseline_results.tex
```

Key findings:

- `S_Mamba` is the best MSE baseline at horizons `1, 3, 5, 7, 14, 30, 60, 90`.
- `iTransformer` is the best MSE baseline at horizons `120, 180, 270, 360`.
- `Autoformer` is a stable third-place baseline at every horizon.
- `Transformer`, `Informer`, and `Reformer` are much weaker on GLD under the locked shared setting.

Best model by horizon, measured with MSE:

| Horizon | Best model | MSE | Runner-up | MSE |
| --- | --- | ---: | --- | ---: |
| 1 | `S_Mamba` | 19.80 | `iTransformer` | 21.02 |
| 3 | `S_Mamba` | 28.06 | `iTransformer` | 29.70 |
| 5 | `S_Mamba` | 33.13 | `iTransformer` | 37.50 |
| 7 | `S_Mamba` | 41.91 | `iTransformer` | 46.88 |
| 14 | `S_Mamba` | 66.70 | `iTransformer` | 73.03 |
| 30 | `S_Mamba` | 123.61 | `iTransformer` | 131.06 |
| 60 | `S_Mamba` | 218.91 | `iTransformer` | 221.78 |
| 90 | `S_Mamba` | 278.28 | `iTransformer` | 285.44 |
| 120 | `iTransformer` | 395.81 | `S_Mamba` | 412.55 |
| 180 | `iTransformer` | 713.54 | `S_Mamba` | 723.90 |
| 270 | `iTransformer` | 1085.45 | `S_Mamba` | 1089.31 |
| 360 | `iTransformer` | 1556.41 | `S_Mamba` | 1558.31 |

Average MSE by horizon group:

| Model | Short | Middle | Long | Overall |
| --- | ---: | ---: | ---: | ---: |
| `S_Mamba` | 30.72 | 171.87 | 946.01 | 382.87 |
| `iTransformer` | 33.78 | 177.83 | 937.80 | 383.14 |
| `Autoformer` | 1304.48 | 1366.13 | 1868.77 | 1513.13 |
| `Transformer` | 4777.44 | 4484.62 | 5306.52 | 4856.20 |
| `Informer` | 6284.64 | 5841.00 | 5315.49 | 5813.71 |
| `Reformer` | 4660.86 | 5865.86 | 7056.00 | 5860.91 |

Practical interpretation:

- `S_Mamba` is the stronger reference baseline for short and middle horizons.
- `iTransformer` is the stronger reference baseline for long-horizon MSE starting at 120 days.
- The two models are nearly tied overall: average MSE differs by `0.27`, and the 360-day MSE gap is only about `0.12%`.
- The first `NS_Mamba` comparison should therefore target both `S_Mamba` and `iTransformer`, not only one of them.

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
results/gld_mamba_hpo_all.csv
results/gld_mamba_hpo_best.csv
458 completed runs
33 best rows selected by RMSE
```

The HPO search includes:

- `S_Mamba`
- `NS_Mamba-D`
- `MS_Mamba-MD`
- `MS_Mamba-MDG`
- `MS_Mamba-MDS`
- `PMS_Mamba-PD`

The direct long-horizon comparison now uses the completed full long horizons:

```text
120, 180, 270, 360 days
```

Long-horizon average by RMSE:

| Model | Track | Long Avg. RMSE | Long Avg. MAE |
| --- | --- | ---: | ---: |
| `PatchTST` | Opt | 24.50 | 17.77 |
| `MS_Mamba-MD` | Mamba-HPO | 25.43 | 18.64 |
| `NLinear` | Opt | 26.28 | 18.70 |
| `TimesNet` | Opt | 27.01 | 19.74 |

Best Mamba-HPO row by completed diagnostic horizon:

| Horizon | Best Mamba | RMSE | MAE | seq_len | Config |
| ---: | --- | ---: | ---: | ---: | --- |
| 30 | `MS_Mamba-MDG` | 9.02 | 6.61 | 256 | `MSG25S124` |
| 120 | `MS_Mamba-MD` | 16.32 | 12.77 | 320 | `MSD49S124` |
| 180 | `MS_Mamba-MD` | 21.47 | 16.20 | 360 | `MSD49S124` |
| 360 | `MS_Mamba-MD` | 35.55 | 24.95 | 360 | `MSD49S124` |

Interpretation:

- HPO confirms `MS_Mamba-MD` as the strongest current Mamba-family model.
- On the completed full long-horizon average `120/180/270/360`, optimized `MS_Mamba-MD` beats optimized `NLinear` and `TimesNet`.
- Optimized `PatchTST` remains the best long-horizon model, with a remaining `3.78%` RMSE gap versus optimized `MS_Mamba-MD`.
- The promoted Mamba configuration is `MS_Mamba-MD` with `moving_avg=49`, `ms_scales=1 2 4`, `d_model=64`, `d_ff=128`, and `d_state=16`.

Next commands:

```bash
bash scripts/gld_ns_mamba/run_gld_mamba_hpo.sh full MS_Mamba-MD
python scripts/gld_ns_mamba/collect_gld_mamba_hpo.py
python scripts/gld_ns_mamba/analyze_gld_mamba_hpo.py
```

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
- target column

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
  --models ALL \
  --trials 20 \
  --calibration-horizons 7 90 360 \
  --full-horizons 1 3 5 7 14 30 60 90 120 180 270 360
```

- `--calibration-horizons` — Subset of horizons used during the tuning loop (one per term group). These control Optuna's pruning and objective computation on the **val** set.
- `--full-horizons` — All horizons used for final replay on the **test** set after tuning is complete. The final `balanced_rmsse` averages across all these horizons.

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

The GLD baseline stage is complete and now provides the reference point for `NS_Mamba`.

GLD target:

```text
close
```

#### Baseline Goals

The completed GLD baseline stage answers:

1. `S_Mamba` is strongest from 1 to 90 days, while `iTransformer` is strongest from 120 to 360 days on MSE.
2. `S_Mamba` degrades smoothly as horizon increases and remains competitive even at 270 and 360 days.
3. The hardest GLD horizons are the long-horizon settings from 180 to 360 days.
4. `NS_Mamba` should be compared first against both `S_Mamba` and `iTransformer`.

#### Model Set

Core baseline models:

- `S_Mamba`
- `Transformer`
- `Informer`
- `Reformer`
- `Autoformer`
- `iTransformer`

#### Horizon Suite

GLD horizons must cover short, middle, and long terms from 1 day to 360 days.

| Range | Horizons |
| --- | --- |
| Short term | 1, 3, 5, 7 days |
| Middle term | 14, 30, 60, 90 days |
| Long term | 120, 180, 270, 360 days |

This balanced `4/4/4` split is the default grouping for grouped summaries and overall horizon-balanced metrics.

Use `pred_len` equal to the horizon in days.

#### Setting Calibration

Before running the full baseline table, first find one stable shared setting. The setting should be chosen around `S_Mamba` because Mamba is the main baseline and has stricter CUDA/memory constraints than the attention-only baselines.

Calibration goals:

1. Find a setting that runs stably for `S_Mamba` across short, middle, and long horizons.
2. Keep the model size moderate enough that all core baselines can run.
3. Avoid per-model tuning before the first comparison.
4. Lock the setting before running all models.

Calibration model:

```text
S_Mamba
```

Calibration horizons:

```text
1, 7, 30, 60, 90, 120, 180, 360
```

These represent short, middle, and long forecasts, including the important 30-, 60-, 120-, and 180-day horizons. If the setting works for these calibration horizons, use it for the full horizon suite.

Calibration script:

```bash
bash scripts/gld_baseline/calibrate_s_mamba.sh
```

Run only one candidate setting:

```bash
bash scripts/gld_baseline/calibrate_s_mamba.sh A
bash scripts/gld_baseline/calibrate_s_mamba.sh B
bash scripts/gld_baseline/calibrate_s_mamba.sh C
```

Candidate setting A:

```text
features=S
target=close
freq=d
seq_len=360
label_len=180
d_model=64
d_ff=128
e_layers=2
d_layers=1
batch_size=16
train_epochs=10
patience=3
itr=1
```

Candidate setting B, if candidate A is too slow or unstable:

```text
features=S
target=close
freq=d
seq_len=180
label_len=90
d_model=64
d_ff=128
e_layers=2
d_layers=1
batch_size=16
train_epochs=10
patience=3
itr=1
```

Candidate setting C, if candidate B is still too heavy:

```text
seq_len=180
label_len=90
d_model=32
d_ff=64
e_layers=1
batch_size=16
```

Locking rule:

```text
Use the strongest setting that completes S_Mamba runs for pred_len 7, 90, and 360 without memory failure or unstable loss.
```

Calibration result:

```text
Locked default setting: A
```

Setting A is selected because it is strongest on long-horizon MSE and the 360-day stress case, which matter most for nonstationary forecasting. Setting B is a useful short-horizon or efficiency alternative, but should not be mixed into the main baseline table unless the full baseline table is explicitly labeled as setting B.

Calibration summary:

| Horizon | Best MSE | Best MAE |
| --- | --- | --- |
| 1 | B | B |
| 7 | B | B |
| 30 | B | B |
| 60 | B | B |
| 90 | A | B |
| 120 | A | B |
| 180 | A | B |
| 360 | A | A |

Aggregate result:

| Setting | Avg MSE | Avg MAE | Long-horizon Avg MSE | Long-horizon Avg MAE |
| --- | ---: | ---: | ---: | ---: |
| A | 0.3769 | 0.3816 | 1.0182 | 0.7063 |
| B | 0.3864 | 0.3750 | 1.0585 | 0.7142 |
| C | 0.4597 | 0.4156 | 1.1815 | 0.7479 |

Parsed calibration results are saved locally at:

```text
results/gld_calibration_summary.csv
```

After the setting is locked, do not tune each baseline separately in the first pass. The first pass should be a controlled comparison, not a per-model leaderboard.

#### Shared Baseline Settings

Use the locked setting for every model that is suitable for comparison.

Suitable-for-comparison means:

- the model accepts the same input/output task
- the model can run with the locked `seq_len`, `label_len`, and `pred_len`
- the model returns `[B, pred_len, 1]` for `features=S`
- the model does not need architecture-specific tuning to avoid failure

If a model cannot run with the locked setting, mark it as failed or excluded in `results/gld_baselines.csv` and explain why in `notes`. Do not silently change only that model's hyperparameters.

#### Execution Order

Run in this order:

1. Calibrate the shared setting with `S_Mamba` on horizons 7, 90, and 360.
2. Lock the shared setting.
3. Run `S_Mamba` for all 12 horizons.
4. Run `Transformer`, `Informer`, `Reformer`, `Autoformer`, and `iTransformer` for all 12 horizons using the same locked setting.
5. Run optional `_M` variants for all 12 horizons using the same locked setting.
6. Repeat the most important runs with additional seeds if the first-pass results are noisy.

Recommended seeds for later confirmation:

```text
2021, 2022, 2023
```

The current `run.py` seed is fixed internally. Add a `--seed` argument later if multi-seed GLD evaluation becomes necessary.

#### Metrics

Record:

- MSE
- MAE
- training time
- best validation loss
- test loss
- parameter count
- GPU memory usage if available
- whether fallback `seq_len=180` was used

#### Result File

Save GLD baseline results to:

```text
results/gld_baselines.csv
```

Baseline runner:

```bash
bash scripts/gld_baseline/run_gld_baselines.sh
```

Run only one baseline model:

```bash
bash scripts/gld_baseline/run_gld_baselines.sh S_Mamba
bash scripts/gld_baseline/run_gld_baselines.sh Transformer
```

Collect completed metrics into the baseline CSV:

```bash
conda run -n mamba python scripts/gld_baseline/collect_gld_baselines.py
```

Current CSV status:

```text
results/gld_baselines.csv exists.
72 / 72 rows are complete.
S_Mamba wins MSE at horizons 1-90.
iTransformer wins MSE at horizons 120-360.
```

Recommended columns:

```text
dataset,target,model,horizon,term,setting_id,seq_len,label_len,pred_len,d_model,d_ff,e_layers,d_layers,batch_size,train_epochs,patience,seed,mse,mae,rmse,mape,mspe,best_val_loss,train_time_sec,param_count,gpu_memory_mb,status,notes,run
```

Use `term` values:

```text
short
middle
long
```

#### Success Criteria

The baseline stage is complete when:

- one shared setting is calibrated and locked
- the locked setting is documented as `setting_id`
- every core model has results for all 12 horizons
- `S_Mamba` has results for all 12 horizons
- `results/gld_baselines.csv` exists
- the strongest baseline per horizon is identifiable
- there is a short written summary of which horizons are hardest

Baseline stage status: complete.

NS_Mamba diagnostic stage status: complete for horizons `30, 120, 180, 360`.

`NS_Mamba-D` is now the full 12-horizon implementation target.

#### Command Template

Use this after choosing the locked shared setting. Replace values such as `seq_len`, `label_len`, `d_model`, and `d_ff` with the locked setting values.

```bash
conda run -n mamba python -u run.py \
  --is_training 1 \
  --model_id GLD_${SETTING_ID}_${MODEL}_pl${PRED_LEN} \
  --model ${MODEL} \
  --data custom \
  --root_path ./data/GLD/ \
  --data_path GLD.csv \
  --features S \
  --target close \
  --freq d \
  --seq_len 360 \
  --label_len 180 \
  --pred_len ${PRED_LEN} \
  --enc_in 1 \
  --dec_in 1 \
  --c_out 1 \
  --d_model 64 \
  --d_state 16 \
  --d_ff 128 \
  --e_layers 2 \
  --d_layers 1 \
  --batch_size 16 \
  --train_epochs 10 \
  --patience 3 \
  --num_workers 0 \
  --des gld_${SETTING_ID} \
  --itr 1
```

Do not change the locked setting per model. If a model fails, record `status=failed` and explain the reason in `notes`.

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
72 / 72 baseline rows collected in results/gld_baselines.csv.
S_Mamba and iTransformer identified as the two reference baselines.
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
