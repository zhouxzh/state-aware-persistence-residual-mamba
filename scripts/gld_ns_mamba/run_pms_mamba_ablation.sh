#!/usr/bin/env bash
set -euo pipefail

# Run patch multi-scale Mamba GLD ablations.
#
# Usage from the repository root:
#   bash scripts/gld_ns_mamba/run_pms_mamba_ablation.sh smoke
#   bash scripts/gld_ns_mamba/run_pms_mamba_ablation.sh diagnostic
#   bash scripts/gld_ns_mamba/run_pms_mamba_ablation.sh full PMS_Mamba-PD
#
# Optional overrides:
#   MS_SCALES="1 2 4" PATCH_LEN=16 STRIDE=8 bash scripts/gld_ns_mamba/run_pms_mamba_ablation.sh diagnostic

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

MODE="${1:-diagnostic}"
SELECTED_VARIANT="${2:-ALL}"

DATA_ROOT="./data/GLD/"
DATA_PATH="GLD.csv"
TARGET="close"
MODEL_NAME="PMS_Mamba"
MOVING_AVG="${MOVING_AVG:-25}"
MS_SCALES="${MS_SCALES:-1 2 4}"
PATCH_LEN="${PATCH_LEN:-16}"
STRIDE="${STRIDE:-8}"
LOG_ROOT="./logs/gld_pms_mamba"

VARIANTS=(PMS_Mamba-P PMS_Mamba-PG PMS_Mamba-PD PMS_Mamba-PDG)

scale_tag() {
  local tag
  tag="$(echo "${MS_SCALES}" | tr ' ' '-')"
  echo "s${tag}"
}

variant_flags() {
  local variant="$1"
  case "${variant}" in
    PMS_Mamba-P)
      echo "0 mean"
      ;;
    PMS_Mamba-PG)
      echo "0 gate"
      ;;
    PMS_Mamba-PD)
      echo "1 mean"
      ;;
    PMS_Mamba-PDG)
      echo "1 gate"
      ;;
    *)
      echo "Unknown PMS_Mamba variant '${variant}'." >&2
      exit 2
      ;;
  esac
}

mode_settings() {
  case "${MODE}" in
    smoke)
      echo "30 15 32 64 1 16 1 1 5"
      ;;
    diagnostic)
      echo "360 180 64 128 2 16 10 3 30 120 180 360"
      ;;
    full)
      echo "360 180 64 128 2 16 10 3 1 3 5 7 14 30 60 90 120 180 270 360"
      ;;
    *)
      echo "Unknown mode '${MODE}'. Use smoke, diagnostic, or full." >&2
      exit 2
      ;;
  esac
}

read -r SEQ_LEN LABEL_LEN D_MODEL D_FF E_LAYERS BATCH_SIZE TRAIN_EPOCHS PATIENCE HORIZONS_STRING <<< "$(mode_settings)"
read -r -a HORIZONS <<< "${HORIZONS_STRING}"
read -r -a MS_SCALE_ARGS <<< "${MS_SCALES}"

run_variant() {
  local variant="$1"
  local ms_use_decomp
  local ms_fusion
  local scales_tag
  read -r ms_use_decomp ms_fusion <<< "$(variant_flags "${variant}")"
  scales_tag="$(scale_tag)"

  for pred_len in "${HORIZONS[@]}"; do
    local run_name
    local log_path

    if [[ "${MODE}" == "smoke" ]]; then
      run_name="GLD_smoke_${variant}_pl${pred_len}_${scales_tag}_f${ms_fusion}_dc${ms_use_decomp}_ma${MOVING_AVG}_p${PATCH_LEN}_st${STRIDE}"
    else
      run_name="GLD_PMS_${variant}_pl${pred_len}_${scales_tag}_f${ms_fusion}_dc${ms_use_decomp}_ma${MOVING_AVG}_p${PATCH_LEN}_st${STRIDE}"
    fi
    log_path="${LOG_ROOT}/${MODE}/${run_name}.log"
    mkdir -p "$(dirname "${log_path}")"

    echo "Running ${MODE}: variant=${variant}, pred_len=${pred_len}, scales=${MS_SCALES}, patch_len=${PATCH_LEN}, stride=${STRIDE}, fusion=${ms_fusion}, decomp=${ms_use_decomp}"
    conda run -n mamba python -u run.py \
      --is_training 1 \
      --model_id "${run_name}" \
      --model "${MODEL_NAME}" \
      --data custom \
      --root_path "${DATA_ROOT}" \
      --data_path "${DATA_PATH}" \
      --features S \
      --target "${TARGET}" \
      --freq d \
      --seq_len "${SEQ_LEN}" \
      --label_len "${LABEL_LEN}" \
      --pred_len "${pred_len}" \
      --enc_in 1 \
      --dec_in 1 \
      --c_out 1 \
      --d_model "${D_MODEL}" \
      --d_state 16 \
      --d_ff "${D_FF}" \
      --e_layers "${E_LAYERS}" \
      --d_layers 1 \
      --moving_avg "${MOVING_AVG}" \
      --batch_size "${BATCH_SIZE}" \
      --learning_rate 0.0001 \
      --train_epochs "${TRAIN_EPOCHS}" \
      --patience "${PATIENCE}" \
      --num_workers 0 \
      --des "gld_pms_mamba_${MODE}" \
      --tensorboard_dir ./tensorboard/gld_pms_mamba \
      --ms_scales "${MS_SCALE_ARGS[@]}" \
      --ms_fusion "${ms_fusion}" \
      --ms_use_decomp "${ms_use_decomp}" \
      --patch_len "${PATCH_LEN}" \
      --stride "${STRIDE}" \
      --itr 1 2>&1 | tee "${log_path}"
  done
}

if [[ "${SELECTED_VARIANT}" == "ALL" ]]; then
  for variant in "${VARIANTS[@]}"; do
    run_variant "${variant}"
  done
else
  run_variant "${SELECTED_VARIANT}"
fi
