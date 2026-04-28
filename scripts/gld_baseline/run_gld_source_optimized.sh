#!/usr/bin/env bash
set -euo pipefail

# Run GLD comparison models with the hyperparameter style used by
# nonstationary_transformer/scripts/GLD.sh.
#
# This is intentionally separate from run_gld_baselines.sh. The baseline script
# uses one locked S_Mamba-calibrated setting, while this script performs a
# source-style model-specific sweep over seq_len.
#
# Usage:
#   bash scripts/gld_baseline/run_gld_source_optimized.sh DLinear
#   bash scripts/gld_baseline/run_gld_source_optimized.sh NLinear
#   bash scripts/gld_baseline/run_gld_source_optimized.sh PatchTST
#   bash scripts/gld_baseline/run_gld_source_optimized.sh TimesNet
#   bash scripts/gld_baseline/run_gld_source_optimized.sh Nonstationary_Transformer
#   bash scripts/gld_baseline/run_gld_source_optimized.sh Autoformer
#   bash scripts/gld_baseline/run_gld_source_optimized.sh Transformer
#   bash scripts/gld_baseline/run_gld_source_optimized.sh ALL
#
# Optional overrides:
#   HORIZONS="120 180 360" SEQ_LENS="128 192 256" bash ... TimesNet

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

SELECTED_MODEL="${1:-ALL}"
DATA_ROOT="./data/GLD/"
DATA_PATH="GLD.csv"
TARGET="close"
FEATURES="S"
LOG_ROOT="./logs/gld_source_optimized"
TENSORBOARD_ROOT="./tensorboard/gld_source_optimized"

HORIZONS=(${HORIZONS:-1 3 5 7 14 30 60 90 120 180 270 360})
SEQ_LENS=(${SEQ_LENS:-16 32 64 96 128 192 256 320 384})
MODELS=(Autoformer Transformer DLinear NLinear PatchTST TimesNet Nonstationary_Transformer)

model_args() {
  local model_name="$1"
  case "${model_name}" in
    Autoformer)
      echo "--factor 3 --batch_size 32 --learning_rate 0.0001 --d_model 512 --d_ff 2048"
      ;;
    Transformer)
      echo "--factor 3 --batch_size 32 --learning_rate 0.0001 --d_model 512 --d_ff 2048"
      ;;
    NLinear)
      echo "--factor 1 --batch_size 64 --learning_rate 0.005 --individual"
      ;;
    DLinear)
      echo "--factor 1 --batch_size 64 --learning_rate 0.0005 --individual"
      ;;
    PatchTST)
      echo "--factor 3 --batch_size 32 --learning_rate 0.0001 --d_model 512 --d_ff 2048 --patch_len 16 --stride 8"
      ;;
    TimesNet)
      echo "--factor 3 --batch_size 32 --learning_rate 0.0001 --d_model 64 --d_ff 64 --top_k 5 --num_kernels 6"
      ;;
    Nonstationary_Transformer)
      echo "--factor 3 --batch_size 32 --learning_rate 0.0001 --d_model 64 --d_ff 64 --top_k 5 --p_hidden_dims 256 256 --p_hidden_layers 2"
      ;;
    *)
      echo "Unknown model '${model_name}'." >&2
      exit 2
      ;;
  esac
}

run_model() {
  local model_name="$1"
  local extra_args
  extra_args="$(model_args "${model_name}")"

  for pred_len in "${HORIZONS[@]}"; do
    for seq_len in "${SEQ_LENS[@]}"; do
      local label_len=$((seq_len / 2))
      local run_name="GLD_OPT_${model_name}_sl${seq_len}_ll${label_len}_pl${pred_len}"
      local log_path="${LOG_ROOT}/${run_name}.log"
      mkdir -p "${LOG_ROOT}"

      echo "Running source-optimized GLD: model=${model_name}, seq_len=${seq_len}, pred_len=${pred_len}"
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
        --moving_avg 25 \
        --train_epochs 10 \
        --patience 3 \
        --num_workers 0 \
        --des gld_source_optimized \
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
