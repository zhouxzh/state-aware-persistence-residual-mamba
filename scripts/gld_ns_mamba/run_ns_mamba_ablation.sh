#!/usr/bin/env bash
set -euo pipefail

# Run NS_Mamba GLD ablations.
#
# Usage from the repository root:
#   bash scripts/gld_ns_mamba/run_ns_mamba_ablation.sh smoke
#   bash scripts/gld_ns_mamba/run_ns_mamba_ablation.sh diagnostic
#   bash scripts/gld_ns_mamba/run_ns_mamba_ablation.sh full
#   bash scripts/gld_ns_mamba/run_ns_mamba_ablation.sh diagnostic NS_Mamba-ADG
#
# Optional tuning overrides:
#   MOVING_AVG=13 bash scripts/gld_ns_mamba/run_ns_mamba_ablation.sh diagnostic NS_Mamba-AD
#   NS_ADAPTIVE_SCALE=0.05 bash scripts/gld_ns_mamba/run_ns_mamba_ablation.sh diagnostic NS_Mamba-ADG

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

MODE="${1:-diagnostic}"
SELECTED_VARIANT="${2:-ALL}"

DATA_ROOT="./data/GLD/"
DATA_PATH="GLD.csv"
TARGET="close"
MODEL_NAME="NS_Mamba"
SETTING_ID="A"
MOVING_AVG="${MOVING_AVG:-25}"
NS_ADAPTIVE_SCALE="${NS_ADAPTIVE_SCALE:-0.1}"
NS_RECENT_RATIO="${NS_RECENT_RATIO:-0.25}"
LOG_ROOT="./logs/gld_ns_mamba"

VARIANTS=(NS_Mamba-A NS_Mamba-D NS_Mamba-AD NS_Mamba-ADG)

tag_float() {
  local value="$1"
  echo "${value//./p}"
}

variant_flags() {
  local variant="$1"
  case "${variant}" in
    NS_Mamba-A)
      echo "1 0 0"
      ;;
    NS_Mamba-D)
      echo "0 1 0"
      ;;
    NS_Mamba-AD)
      echo "1 1 0"
      ;;
    NS_Mamba-ADG)
      echo "1 1 1"
      ;;
    *)
      echo "Unknown NS_Mamba variant '${variant}'." >&2
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

run_variant() {
  local variant="$1"
  read -r use_adaptive_norm use_decomp use_shift_gate <<< "$(variant_flags "${variant}")"

  for pred_len in "${HORIZONS[@]}"; do
    local scale_tag
    local ratio_tag
    local run_name
    local log_path
    scale_tag="$(tag_float "${NS_ADAPTIVE_SCALE}")"
    ratio_tag="$(tag_float "${NS_RECENT_RATIO}")"

    if [[ "${MODE}" == "smoke" ]]; then
      run_name="GLD_smoke_${variant}_pl${pred_len}_ma${MOVING_AVG}_as${scale_tag}_rr${ratio_tag}"
    else
      run_name="GLD_${SETTING_ID}_${variant}_pl${pred_len}_ma${MOVING_AVG}_as${scale_tag}_rr${ratio_tag}"
    fi
    log_path="${LOG_ROOT}/${MODE}/${run_name}.log"
    mkdir -p "$(dirname "${log_path}")"

    echo "Running ${MODE}: variant=${variant}, pred_len=${pred_len}, moving_avg=${MOVING_AVG}, adaptive_scale=${NS_ADAPTIVE_SCALE}"
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
      --des "gld_ns_mamba_${MODE}" \
      --tensorboard_dir ./tensorboard/gld_ns_mamba \
      --use_adaptive_norm "${use_adaptive_norm}" \
      --use_decomp "${use_decomp}" \
      --use_shift_gate "${use_shift_gate}" \
      --ns_adaptive_scale "${NS_ADAPTIVE_SCALE}" \
      --ns_recent_ratio "${NS_RECENT_RATIO}" \
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
