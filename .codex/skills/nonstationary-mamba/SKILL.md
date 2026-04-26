---
name: nonstationary-mamba
description: "Use this skill when working in this repo on Mamba-based time-series forecasting for nonstationary data: preparing custom datasets such as GLD, running S_Mamba baselines, implementing or integrating NS_Mamba modules, registering models, creating experiment scripts, and validating runs in the `mamba` conda environment."
---

# Nonstationary Mamba

## Overview

Use this skill for development work in this forecasting repository. The project goal is to build and evaluate nonstationarity-aware Mamba models for long-term time-series forecasting.

Primary baseline:

- `model/S_Mamba.py`
- `layers/Mamba_EncDec.py`

New nonstationary components:

- `layers/NonStationaryNorm.py`
- `layers/SeriesDecomp.py`
- `layers/NonStationaryGate.py`

Main roadmap and project status:

- `README.md`

## Workflow

1. Inspect local code before changing architecture.
   Check `run.py`, `experiments/exp_basic.py`, `experiments/exp_long_term_forecasting.py`, `data_provider/data_loader.py`, and the target model/layer files.

2. Keep `S_Mamba` as the baseline.
   Add new ideas in separate files such as `model/NS_Mamba.py`. Avoid breaking existing scripts unless the user explicitly asks for a baseline refactor.

3. Register new models through `experiments/exp_basic.py`.
   New model modules must define:

   ```python
   class Model(nn.Module):
       def __init__(self, configs):
           ...

       def forward(self, x_enc, x_mark_enc, x_dec, x_mark_dec, mask=None):
           ...
   ```

   Add the module to the import list and `self.model_dict`, for example:

   ```python
   from model import ..., S_Mamba, NS_Mamba
   ...
   'NS_Mamba': NS_Mamba,
   ```

4. Use the existing custom dataset loader for CSV files.
   Custom CSVs should have a `date` column and target column. For GLD:

   - path: `data/GLD/GLD.csv`
   - target: `close`
   - data type: `--data custom`
   - single-target forecasting: `--features S --target close`
   - daily frequency: `--freq d`

5. Validate with the `mamba` conda environment.
   Prefer:

   ```bash
   conda run -n mamba python -u run.py ...
   ```

   For smoke tests, use small values such as `--seq_len 30 --label_len 15 --pred_len 5 --d_model 32 --d_ff 64 --e_layers 1 --train_epochs 1 --num_workers 0`.

6. Report exact metrics and command.
   Include MSE, MAE, dataset path, target column, model name, horizon, and whether the run was only a smoke test.

## Implementation Guidelines

- Preserve tensor conventions: time-series inputs are usually `[B, L, N]`; inverted embeddings produce variable tokens.
- Forecast outputs should be shaped `[B, pred_len, N]`.
- `PEMS` and `Solar` may pass time marks as `None`; custom datasets usually pass time features.
- Keep normalization reversible: cache encoder-window statistics and denormalize forecasts.
- Prefer compact modules in `layers/` over placing all logic inside the model file.
- Do not remove existing user data, checkpoints, results, or untracked experiment outputs unless explicitly asked.

## Nonstationary Model Pattern

Recommended first `NS_Mamba` design:

```text
Input [B, L, N]
  -> AdaptiveRevIN
  -> optional SeriesDecomp
  -> DataEmbedding_inverted
  -> bidirectional Mamba Encoder
  -> optional NonStationaryGate
  -> Linear projection to pred_len
  -> denormalization
  -> Forecast [B, pred_len, N]
```

Use ablations:

- `S_Mamba`
- `NS_Mamba-A`: adaptive normalization only
- `NS_Mamba-D`: decomposition only
- `NS_Mamba-AD`: adaptive normalization plus decomposition
- `NS_Mamba-ADG`: adaptive normalization, decomposition, and shift gate

## GLD Smoke Test

Known working command shape:

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

This command is for environment and data validation, not final research comparison.
