#!/usr/bin/env bash
set -euo pipefail

# Run GLD baseline experiments with the locked calibration setting.
# Run from the repository root:
#
#   bash scripts/gld_baseline/run_gld_baselines.sh
#   bash scripts/gld_baseline/run_gld_baselines.sh S_Mamba
#   bash scripts/gld_baseline/run_gld_baselines.sh Transformer
#   bash scripts/gld_baseline/run_gld_baselines.sh PatchTST
#
# Locked setting A:
#   seq_len=360, label_len=180, d_model=64, d_ff=128, e_layers=2

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

SETTING_ID="A"
DATA_ROOT="./data/GLD/"
DATA_PATH="GLD.csv"
TARGET="close"
HORIZONS=(1 3 5 7 14 30 60 90 120 180 270 360)
CORE_MODELS=(
  S_Mamba
  Transformer
  Informer
  Reformer
  Autoformer
  iTransformer
  Nonstationary_Transformer
  DLinear
  NLinear
  PatchTST
  TimesNet
)
SELECTED_MODEL="${1:-ALL}"
LOG_ROOT="./logs/gld_baseline"

run_model() {
  local model_name="$1"

  for pred_len in "${HORIZONS[@]}"; do
    local run_name="GLD_${SETTING_ID}_${model_name}_pl${pred_len}"
    local log_path="${LOG_ROOT}/${run_name}.log"
    mkdir -p "${LOG_ROOT}"
    echo "Running GLD baseline: setting=${SETTING_ID}, model=${model_name}, pred_len=${pred_len}"
    conda run -n mamba python -u run.py \
      --is_training 1 \
      --model_id "${run_name}" \
      --model "${model_name}" \
      --data custom \
      --root_path "${DATA_ROOT}" \
      --data_path "${DATA_PATH}" \
      --features S \
      --target "${TARGET}" \
      --freq d \
      --seq_len 360 \
      --label_len 180 \
      --pred_len "${pred_len}" \
      --enc_in 1 \
      --dec_in 1 \
      --c_out 1 \
      --d_model 64 \
      --d_state 16 \
      --d_ff 128 \
      --e_layers 2 \
      --d_layers 1 \
      --moving_avg 25 \
      --top_k 5 \
      --num_kernels 6 \
      --patch_len 16 \
      --stride 8 \
      --batch_size 16 \
      --learning_rate 0.0001 \
      --train_epochs 10 \
      --patience 3 \
      --num_workers 0 \
      --des "gld_${SETTING_ID}_baseline" \
      --tensorboard_dir ./tensorboard/gld_baseline \
      --itr 1 2>&1 | tee "${log_path}"
  done
}

if [[ "${SELECTED_MODEL}" == "ALL" ]]; then
  for model_name in "${CORE_MODELS[@]}"; do
    run_model "${model_name}"
  done
else
  run_model "${SELECTED_MODEL}"
fi
