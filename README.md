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
- Cleaned model baselines:
  - removed Mamba from `model/Transformer.py`
  - removed Mamba from `model/Reformer.py`
  - fixed hard-coded `d_state=16` in Mamba variants
  - made `output_attention=True` safe across registered models
  - removed unused hard-coded modules from `layers/Mamba_EncDec.py`
- Added repo-local skills:
  - `.codex/skills/nonstationary-mamba`
  - `.codex/skills/latex-manuscript`

Next immediate task:

```text
Calculate baseline results on GLD close before implementing NS_Mamba.
Evaluate short-, middle-, and long-horizon forecasts from 1 day to 360 days.
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

## Models

All model files live in `model/`. Each model exposes a `Model` class and is registered in `experiments/exp_basic.py`.

### Clean Baselines

These are non-Mamba baseline models after cleanup.

| Model name | File | Main idea | Notes |
| --- | --- | --- | --- |
| `Autoformer` | `model/Autoformer.py` | AutoCorrelation with decomposition | Encoder-decoder baseline |
| `Flashformer` | `model/Flashformer.py` | Flash attention encoder, Transformer decoder | Clean attention baseline |
| `Flowformer` | `model/Flowformer.py` | Flow attention encoder, Transformer decoder | Clean attention baseline |
| `Informer` | `model/Informer.py` | ProbSparse attention | Clean attention baseline |
| `Reformer` | `model/Reformer.py` | Reformer LSH attention | Mamba removed from this baseline |
| `Transformer` | `model/Transformer.py` | Full attention Transformer | Mamba removed from this baseline |

### Mamba Encoder Variants

These models use Mamba inside or after the encoder while keeping the original decoder style.

| Model name | File | Main idea | Notes |
| --- | --- | --- | --- |
| `Autoformer_M` | `model/Autoformer_M.py` | Autoformer decoder with Mamba encoder layers | Uses `configs.d_state` |
| `Flashformer_M` | `model/Flashformer_M.py` | Flashformer-style decoder with Mamba encoder layers | Uses `configs.d_state` |
| `Flowformer_M` | `model/Flowformer_M.py` | Flowformer-style decoder with Mamba encoder layers | Uses `configs.d_state` |
| `Informer_M` | `model/Informer_M.py` | Informer encoder followed by residual Mamba | Uses `configs.d_state` |
| `Reformer_M` | `model/Reformer_M.py` | Reformer encoder with residual Mamba before attention | Uses `configs.d_state` |
| `Transformer_M` | `model/Transformer_M.py` | Transformer encoder followed by residual Mamba | Uses `configs.d_state` |

### Inverted Variable-Token Models

These models use `DataEmbedding_inverted`, treating variables and time features as tokens.

| Model name | File | Main idea | Notes |
| --- | --- | --- | --- |
| `iTransformer` | `model/iTransformer.py` | Inverted full-attention Transformer | Supports `--use_norm` |
| `iInformer` | `model/iInformer.py` | Inverted ProbSparse attention | Always applies mean/std normalization |
| `iReformer` | `model/iReformer.py` | Inverted Reformer attention | Always applies mean/std normalization |
| `iFlowformer` | `model/iFlowformer.py` | Inverted Flow attention | Always applies mean/std normalization |
| `iFlashformer` | `model/iFlashformer.py` | Inverted Flash attention | Always applies mean/std normalization |

### Main Mamba Baseline

| Model name | File | Main idea | Notes |
| --- | --- | --- | --- |
| `S_Mamba` | `model/S_Mamba.py` | Inverted embedding plus bidirectional Mamba encoder | Main baseline for this project |

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

Status: next.

Create:

```text
model/NS_Mamba.py
```

Register in:

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

First version:

```text
S_Mamba structure + AdaptiveRevIN
```

### Step 4: Add Decomposition

Status: pending.

Add decomposition to `NS_Mamba` after the adaptive-normalization version works.

Suggested flags:

```text
--use_decomp 1
--moving_avg 25
```

### Step 5: Add Shift Gate

Status: pending.

Add shift-aware hidden gating or branch fusion after decomposition is stable.

Suggested flag:

```text
--use_shift_gate 1
```

## Experiment Plan

### GLD Baseline Plan

First calculate baseline results on GLD because it is the local target dataset for this project. Do this before implementing `NS_Mamba`; otherwise there is no reliable reference point for whether the new nonstationary idea helps.

GLD target:

```text
close
```

#### Baseline Goals

The GLD baseline stage should answer:

1. Which existing model is strongest on GLD?
2. How does `S_Mamba` behave as horizon increases from 1 day to 360 days?
3. Which horizons show the largest nonstationary forecasting difficulty?
4. Which baseline should `NS_Mamba` be compared against first?

#### Model Set

Core baseline models:

- `S_Mamba`
- `Transformer`
- `Informer`
- `Reformer`
- `Autoformer`
- `iTransformer`

Optional Mamba-encoder comparisons:

- `Transformer_M`
- `Informer_M`
- `Reformer_M`

Run the core models first. Add optional `_M` variants only after the core baseline table is complete.

#### Horizon Suite

GLD horizons must cover short, middle, and long terms from 1 day to 360 days.

| Range | Horizons |
| --- | --- |
| Short term | 1, 3, 5, 7 days |
| Middle term | 14, 30, 60, 90, 120 days |
| Long term | 180, 270, 360 days |

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

Recommended columns:

```text
dataset,target,model,horizon,term,setting_id,seq_len,label_len,pred_len,d_model,d_ff,e_layers,d_layers,batch_size,train_epochs,patience,seed,mse,mae,best_val_loss,train_time_sec,param_count,gpu_memory_mb,status,notes
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

Only after this should `NS_Mamba-A` be implemented and compared.

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

Most important comparison:

```text
S_Mamba vs NS_Mamba-ADG
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

Status: in progress.

Done:

```text
GLD dataset moved and validated.
S_Mamba smoke test completed on GLD close.
AdaptiveRevIN layer implemented.
SeriesDecomp layer implemented.
NonStationaryGate layer implemented.
Baseline model cleanup completed.
```

Remaining:

```text
Run full GLD baseline evaluation before implementing NS_Mamba.
Evaluate horizons: 1, 3, 5, 7, 14, 30, 60, 90, 120, 180, 270, 360 days.
Save results to results/gld_baselines.csv.
```

### Milestone 2

Implement the first `NS_Mamba` version:

```text
S_Mamba structure + AdaptiveRevIN
```

Run the same GLD horizon suite:

```text
1, 3, 5, 7, 14, 30, 60, 90, 120, 180, 270, 360 days
```

Compare:

```text
S_Mamba vs NS_Mamba-A
```

Save results to:

```text
results/gld_ns_mamba_a.csv
```

### Milestone 3

Run the first real comparison:

```text
S_Mamba vs NS_Mamba-A
```

Datasets:

- Exchange
- Weather

Prediction lengths:

- Exchange and Weather: 96, 192, 336, 720

### Milestone 4

Add decomposition:

```text
AdaptiveRevIN + trend/seasonal decomposition + Mamba
```

Run on:

- Exchange
- Weather
- ETTm1
- ETTm2

### Milestone 5

Add shift-aware fusion gate and run the full ablation:

```text
S_Mamba
NS_Mamba-A
NS_Mamba-D
NS_Mamba-AD
NS_Mamba-ADG
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
