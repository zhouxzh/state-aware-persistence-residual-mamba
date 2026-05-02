#!/usr/bin/env bash
set -euo pipefail

# Run GLD model-specific sweeps and select by RMSE later.
#
# This script is separate from:
#   - run_gld_baselines.sh: one locked shared setting
#   - run_gld_source_optimized.sh: imported-model/source-style sweep
#
# Usage:
#   bash scripts/gld_baseline/run_gld_rmse_optimized.sh ALL
#   bash scripts/gld_baseline/run_gld_rmse_optimized.sh S_Mamba
#   bash scripts/gld_baseline/run_gld_rmse_optimized.sh iTransformer
#   bash scripts/gld_baseline/run_gld_rmse_optimized.sh Autoformer
#   bash scripts/gld_baseline/run_gld_rmse_optimized.sh Transformer
#   bash scripts/gld_baseline/run_gld_rmse_optimized.sh Informer
#   bash scripts/gld_baseline/run_gld_rmse_optimized.sh Reformer
#
# Optional overrides:
#   HORIZONS="120 180 360" bash ... S_Mamba
#   SEQ_LENS="64 96 128 192 256 320 384" bash ... iTransformer
#
# Selection criterion:
#   collect_gld_rmse_optimized.py picks the best run per model/horizon by RMSE.

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

SELECTED_MODEL="${1:-ALL}"
DATA_ROOT="./data/GLD/"
DATA_PATH="GLD.csv"
TARGET="close"
FEATURES="S"
LOG_ROOT="./logs/gld_rmse_optimized"
TENSORBOARD_ROOT="./tensorboard/gld_rmse_optimized"

HORIZONS=(${HORIZONS:-1 3 5 7 14 30 60 90 120 180 270 360})
SEQ_LENS=(${SEQ_LENS:-16 32 64 96 128 192 256 320 384})
MODELS=(S_Mamba iTransformer Autoformer Transformer Informer Reformer)

model_preset() {
  local model_name="$1"
  case "${model_name}" in
    S_Mamba)
      echo "S1 --factor 1 --d_model 64 --d_state 16 --d_ff 128 --batch_size 16 --learning_rate 0.0001 --use_norm 1"
      ;;
    iTransformer)
      echo "I1 --factor 1 --d_model 128 --d_ff 256 --batch_size 16 --learning_rate 0.0001 --use_norm 1"
      ;;
    Autoformer)
      echo "A1 --factor 3 --d_model 512 --d_ff 2048 --batch_size 32 --learning_rate 0.0001 --moving_avg 25"
      ;;
    Transformer)
      echo "T1 --factor 3 --d_model 512 --d_ff 2048 --batch_size 32 --learning_rate 0.0001"
      ;;
    Informer)
      echo "IF1 --factor 3 --d_model 512 --d_ff 2048 --batch_size 32 --learning_rate 0.0001"
      ;;
    Reformer)
      echo "R1 --factor 3 --d_model 512 --d_ff 2048 --batch_size 32 --learning_rate 0.0001"
      ;;
    *)
      echo "Unknown model '${model_name}'." >&2
      exit 2
      ;;
  esac
}

run_model() {
  local model_name="$1"
  local preset cfg_id extra_args
  preset="$(model_preset "${model_name}")"
  cfg_id="${preset%% *}"
  extra_args="${preset#* }"

  for pred_len in "${HORIZONS[@]}"; do
    for seq_len in "${SEQ_LENS[@]}"; do
      local label_len=$((seq_len / 2))
      local run_name="GLD_RMSEOPT_${model_name}_cfg${cfg_id}_sl${seq_len}_ll${label_len}_pl${pred_len}"
      local log_path="${LOG_ROOT}/${run_name}.log"
      mkdir -p "${LOG_ROOT}"

      echo "Running RMSE-optimized GLD: model=${model_name}, cfg=${cfg_id}, seq_len=${seq_len}, pred_len=${pred_len}"
      conda run -n mamba python -u run.py \
        --task_name long_term_forecast \
        --is_training 1 \
        --model_id "${run_name}" \
        --model "${model_name}" \
        --data custom \
        --root_path "${DATA_ROOT}" \
        --data_path "${DATA_PATH}" \
        --features "${FEATURES}" \
        --target "${TARGET}" \
        --freq d \
        --seq_len "${seq_len}" \
        --label_len "${label_len}" \
        --pred_len "${pred_len}" \
        --enc_in 1 \
        --dec_in 1 \
        --c_out 1 \
        --e_layers 2 \
        --d_layers 1 \
        --num_workers 0 \
        --train_epochs 10 \
        --patience 3 \
        --des gld_rmse_optimized \
        --tensorboard_dir "${TENSORBOARD_ROOT}" \
        --itr 1 \
        ${extra_args} 2>&1 | tee "${log_path}"
    done
  done
}

if [[ "${SELECTED_MODEL}" == "ALL" ]]; then
  for model_name in "${MODELS[@]}"; do
    run_model "${model_name}"
  done
else
  run_model "${SELECTED_MODEL}"
fi
