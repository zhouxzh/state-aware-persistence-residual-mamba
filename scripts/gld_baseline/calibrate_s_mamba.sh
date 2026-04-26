#!/usr/bin/env bash
set -euo pipefail

# Calibrate one shared GLD baseline setting around S_Mamba before running all
# comparable baseline models. Run from the repository root:
#
#   bash scripts/gld_baseline/calibrate_s_mamba.sh
#   bash scripts/gld_baseline/calibrate_s_mamba.sh A
#
# Settings:
#   A: seq_len=360, label_len=180, d_model=64, d_ff=128, e_layers=2
#   B: seq_len=180, label_len=90,  d_model=64, d_ff=128, e_layers=2
#   C: seq_len=180, label_len=90,  d_model=32, d_ff=64,  e_layers=1

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

MODEL_NAME="S_Mamba"
DATA_ROOT="./data/GLD/"
DATA_PATH="GLD.csv"
TARGET="close"
HORIZONS=(1 7 30 60 90 120 180 360)
SELECTED_SETTING="${1:-ALL}"

run_setting() {
  local setting_id="$1"
  local seq_len="$2"
  local label_len="$3"
  local d_model="$4"
  local d_ff="$5"
  local e_layers="$6"
  local batch_size="$7"

  for pred_len in "${HORIZONS[@]}"; do
    echo "Running GLD calibration: setting=${setting_id}, model=${MODEL_NAME}, pred_len=${pred_len}"
    conda run -n mamba python -u run.py \
      --is_training 1 \
      --model_id "GLD_calib_${setting_id}_${MODEL_NAME}_pl${pred_len}" \
      --model "${MODEL_NAME}" \
      --data custom \
      --root_path "${DATA_ROOT}" \
      --data_path "${DATA_PATH}" \
      --features S \
      --target "${TARGET}" \
      --freq d \
      --seq_len "${seq_len}" \
      --label_len "${label_len}" \
      --pred_len "${pred_len}" \
      --enc_in 1 \
      --dec_in 1 \
      --c_out 1 \
      --d_model "${d_model}" \
      --d_state 16 \
      --d_ff "${d_ff}" \
      --e_layers "${e_layers}" \
      --d_layers 1 \
      --batch_size "${batch_size}" \
      --learning_rate 0.0001 \
      --train_epochs 10 \
      --patience 3 \
      --num_workers 0 \
      --des "gld_calib_${setting_id}" \
      --itr 1
  done
}

case "${SELECTED_SETTING}" in
  A)
    run_setting A 360 180 64 128 2 16
    ;;
  B)
    run_setting B 180 90 64 128 2 16
    ;;
  C)
    run_setting C 180 90 32 64 1 16
    ;;
  ALL)
    run_setting A 360 180 64 128 2 16
    run_setting B 180 90 64 128 2 16
    run_setting C 180 90 32 64 1 16
    ;;
  *)
    echo "Unknown setting '${SELECTED_SETTING}'. Use A, B, C, or no argument for ALL." >&2
    exit 2
    ;;
esac
