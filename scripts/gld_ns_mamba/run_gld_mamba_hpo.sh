#!/usr/bin/env bash
set -euo pipefail

# Hyperparameter optimization for GLD Mamba-based models.
#
# This is separate from:
#   - scripts/gld_baseline/run_gld_baselines.sh: fixed shared setting
#   - scripts/gld_baseline/run_gld_source_optimized.sh: imported-model HPO
#
# Usage from the repository root:
#   bash scripts/gld_ns_mamba/run_gld_mamba_hpo.sh diagnostic ALL
#   bash scripts/gld_ns_mamba/run_gld_mamba_hpo.sh diagnostic MS_Mamba-MD
#   bash scripts/gld_ns_mamba/run_gld_mamba_hpo.sh full MS_Mamba-MD
#
# Optional overrides:
#   HORIZONS="120 180 360" SEQ_LENS="128 192 256 320 384" bash ... diagnostic MS_Mamba-MD
#   SEARCH_SPACE=wide bash scripts/gld_ns_mamba/run_gld_mamba_hpo.sh diagnostic ALL
#   FORCE=1 bash scripts/gld_ns_mamba/run_gld_mamba_hpo.sh diagnostic S_Mamba
#
# Selection criterion:
#   collect_gld_mamba_hpo.py picks the best run per variant/horizon by RMSE.

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

MODE="${1:-diagnostic}"
SELECTED_VARIANT="${2:-ALL}"
SEARCH_SPACE="${SEARCH_SPACE:-focused}"
FORCE="${FORCE:-0}"

DATA_ROOT="./data/GLD/"
DATA_PATH="GLD.csv"
TARGET="close"
FEATURES="S"
LOG_ROOT="./logs/gld_mamba_hpo"
TENSORBOARD_ROOT="./tensorboard/gld_mamba_hpo"

case "${MODE}" in
  smoke)
    HORIZONS=(${HORIZONS:-5})
    SEQ_LENS=(${SEQ_LENS:-30})
    TRAIN_EPOCHS="${TRAIN_EPOCHS:-1}"
    PATIENCE="${PATIENCE:-1}"
    ;;
  diagnostic)
    HORIZONS=(${HORIZONS:-30 120 180 360})
    SEQ_LENS=(${SEQ_LENS:-128 192 256 320 360 384})
    TRAIN_EPOCHS="${TRAIN_EPOCHS:-10}"
    PATIENCE="${PATIENCE:-3}"
    ;;
  full)
    HORIZONS=(${HORIZONS:-1 3 5 7 14 30 60 90 120 180 270 360})
    SEQ_LENS=(${SEQ_LENS:-128 192 256 320 360 384})
    TRAIN_EPOCHS="${TRAIN_EPOCHS:-10}"
    PATIENCE="${PATIENCE:-3}"
    ;;
  *)
    echo "Unknown mode '${MODE}'. Use smoke, diagnostic, or full." >&2
    exit 2
    ;;
esac

VARIANTS=(
  S_Mamba
  NS_Mamba-D
  MS_Mamba-MD
  MS_Mamba-MDG
  MS_Mamba-MDS
  PMS_Mamba-PD
)

tag_float() {
  local value="$1"
  echo "${value//./p}"
}

scales_tag() {
  local value="$1"
  if [[ "${value}" == "na" ]]; then
    echo "na"
  else
    echo "${value// /-}"
  fi
}

model_for_variant() {
  local variant="$1"
  case "${variant}" in
    S_Mamba)
      echo "S_Mamba"
      ;;
    NS_Mamba-*)
      echo "NS_Mamba"
      ;;
    MS_Mamba-*)
      echo "MS_Mamba"
      ;;
    PMS_Mamba-*)
      echo "PMS_Mamba"
      ;;
    *)
      echo "Unknown variant '${variant}'." >&2
      exit 2
      ;;
  esac
}

# Fields:
# variant|config_id|d_model|d_ff|d_state|e_layers|batch_size|learning_rate|moving_avg|ms_scales|ms_fusion|ms_use_decomp|ms_use_linear_skip|patch_len|stride|extra_args
focused_configs() {
  cat <<'EOF'
S_Mamba|S64|64|128|16|2|16|0.0001|25|na|na|na|na|na|na|--use_norm 1
S_Mamba|S128|128|256|16|2|16|0.0001|25|na|na|na|na|na|na|--use_norm 1
NS_Mamba-D|NSD25|64|128|16|2|16|0.0001|25|na|na|na|na|na|na|--use_adaptive_norm 0 --use_decomp 1 --use_shift_gate 0 --use_norm 1
NS_Mamba-D|NSD49|64|128|16|2|16|0.0001|49|na|na|na|na|na|na|--use_adaptive_norm 0 --use_decomp 1 --use_shift_gate 0 --use_norm 1
MS_Mamba-MD|MSD25S124|64|128|16|2|16|0.0001|25|1 2 4|mean|1|0|na|na|--use_norm 1
MS_Mamba-MD|MSD49S124|64|128|16|2|16|0.0001|49|1 2 4|mean|1|0|na|na|--use_norm 1
MS_Mamba-MD|MSD25S1248|64|128|16|2|16|0.0001|25|1 2 4 8|mean|1|0|na|na|--use_norm 1
MS_Mamba-MD|MSD25S136|64|128|16|2|16|0.0001|25|1 3 6|mean|1|0|na|na|--use_norm 1
MS_Mamba-MDS|MSS25S124|64|128|16|2|16|0.0001|25|1 2 4|mean|1|1|na|na|--use_norm 1
MS_Mamba-MDG|MSG25S124|64|128|16|2|16|0.0001|25|1 2 4|gate|1|0|na|na|--use_norm 1
PMS_Mamba-PD|PMS25S124P16|64|128|16|2|16|0.0001|25|1 2 4|mean|1|0|16|8|--use_norm 1
EOF
}

wide_configs() {
  focused_configs
  cat <<'EOF'
S_Mamba|S64D32|64|128|32|2|16|0.0001|25|na|na|na|na|na|na|--use_norm 1
S_Mamba|S128D32|128|256|32|2|16|0.0001|25|na|na|na|na|na|na|--use_norm 1
NS_Mamba-D|NSD13|64|128|16|2|16|0.0001|13|na|na|na|na|na|na|--use_adaptive_norm 0 --use_decomp 1 --use_shift_gate 0 --use_norm 1
NS_Mamba-D|NSD25W|128|256|16|2|16|0.0001|25|na|na|na|na|na|na|--use_adaptive_norm 0 --use_decomp 1 --use_shift_gate 0 --use_norm 1
MS_Mamba-MD|MSD13S124|64|128|16|2|16|0.0001|13|1 2 4|mean|1|0|na|na|--use_norm 1
MS_Mamba-MD|MSD25S12|64|128|16|2|16|0.0001|25|1 2|mean|1|0|na|na|--use_norm 1
MS_Mamba-MD|MSD25S148|64|128|16|2|16|0.0001|25|1 4 8|mean|1|0|na|na|--use_norm 1
MS_Mamba-MD|MSD25W|128|256|16|2|16|0.0001|25|1 2 4|mean|1|0|na|na|--use_norm 1
MS_Mamba-MD|MSD25D32|64|128|32|2|16|0.0001|25|1 2 4|mean|1|0|na|na|--use_norm 1
MS_Mamba-MDS|MSS25S1248|64|128|16|2|16|0.0001|25|1 2 4 8|mean|1|1|na|na|--use_norm 1
MS_Mamba-MDGS|MSGS25S124|64|128|16|2|16|0.0001|25|1 2 4|gate|1|1|na|na|--use_norm 1
PMS_Mamba-PD|PMS25S124P8|64|128|16|2|16|0.0001|25|1 2 4|mean|1|0|8|4|--use_norm 1
EOF
}

config_lines() {
  case "${SEARCH_SPACE}" in
    focused)
      focused_configs
      ;;
    wide)
      wide_configs
      ;;
    *)
      echo "Unknown SEARCH_SPACE '${SEARCH_SPACE}'. Use focused or wide." >&2
      exit 2
      ;;
  esac
}

result_exists() {
  local run_name="$1"
  compgen -G "results/${run_name}_*/metrics.npy" >/dev/null
}

run_config() {
  local variant="$1"
  local cfg_id="$2"
  local d_model="$3"
  local d_ff="$4"
  local d_state="$5"
  local e_layers="$6"
  local batch_size="$7"
  local learning_rate="$8"
  local moving_avg="$9"
  local ms_scales="${10}"
  local ms_fusion="${11}"
  local ms_use_decomp="${12}"
  local ms_use_linear_skip="${13}"
  local patch_len="${14}"
  local stride="${15}"
  local extra_args="${16}"

  local model_name
  local scales_slug
  local lr_slug
  model_name="$(model_for_variant "${variant}")"
  scales_slug="$(scales_tag "${ms_scales}")"
  lr_slug="$(tag_float "${learning_rate}")"

  for pred_len in "${HORIZONS[@]}"; do
    for seq_len in "${SEQ_LENS[@]}"; do
      local label_len=$((seq_len / 2))
      local run_name
      local log_path
      run_name="GLD_MAMBAHPO_${variant}_cfg${cfg_id}_sl${seq_len}_ll${label_len}_pl${pred_len}_dm${d_model}_df${d_ff}_ds${d_state}_el${e_layers}_bs${batch_size}_lr${lr_slug}_ma${moving_avg}_sc${scales_slug}_fu${ms_fusion}_dc${ms_use_decomp}_ls${ms_use_linear_skip}_p${patch_len}_st${stride}"

      if [[ "${FORCE}" != "1" ]] && result_exists "${run_name}"; then
        echo "Skipping existing run: ${run_name}"
        continue
      fi

      log_path="${LOG_ROOT}/${MODE}/${variant}/${run_name}.log"
      mkdir -p "$(dirname "${log_path}")"

      echo "Running Mamba HPO: mode=${MODE}, variant=${variant}, cfg=${cfg_id}, seq_len=${seq_len}, pred_len=${pred_len}"
      cmd=(
        conda run -n mamba python -u run.py
        --task_name long_term_forecast
        --is_training 1
        --model_id "${run_name}"
        --model "${model_name}"
        --data custom
        --root_path "${DATA_ROOT}"
        --data_path "${DATA_PATH}"
        --features "${FEATURES}"
        --target "${TARGET}"
        --freq d
        --seq_len "${seq_len}"
        --label_len "${label_len}"
        --pred_len "${pred_len}"
        --enc_in 1
        --dec_in 1
        --c_out 1
        --d_model "${d_model}"
        --d_state "${d_state}"
        --d_ff "${d_ff}"
        --e_layers "${e_layers}"
        --d_layers 1
        --moving_avg "${moving_avg}"
        --batch_size "${batch_size}"
        --learning_rate "${learning_rate}"
        --train_epochs "${TRAIN_EPOCHS}"
        --patience "${PATIENCE}"
        --num_workers 0
        --des "gld_mamba_hpo_${MODE}"
        --tensorboard_dir "${TENSORBOARD_ROOT}"
        --itr 1
      )

      if [[ "${ms_scales}" != "na" ]]; then
        read -r -a ms_scale_args <<< "${ms_scales}"
        cmd+=(--ms_scales "${ms_scale_args[@]}")
      fi
      if [[ "${ms_fusion}" != "na" ]]; then
        cmd+=(--ms_fusion "${ms_fusion}")
      fi
      if [[ "${ms_use_decomp}" != "na" ]]; then
        cmd+=(--ms_use_decomp "${ms_use_decomp}")
      fi
      if [[ "${ms_use_linear_skip}" != "na" ]]; then
        cmd+=(--ms_use_linear_skip "${ms_use_linear_skip}")
      fi
      if [[ "${patch_len}" != "na" ]]; then
        cmd+=(--patch_len "${patch_len}")
      fi
      if [[ "${stride}" != "na" ]]; then
        cmd+=(--stride "${stride}")
      fi

      # shellcheck disable=SC2206
      extra_array=(${extra_args})
      cmd+=("${extra_array[@]}")

      "${cmd[@]}" 2>&1 | tee "${log_path}"
    done
  done
}

while IFS='|' read -r variant cfg_id d_model d_ff d_state e_layers batch_size learning_rate moving_avg ms_scales ms_fusion ms_use_decomp ms_use_linear_skip patch_len stride extra_args; do
  [[ -z "${variant}" ]] && continue
  if [[ "${SELECTED_VARIANT}" != "ALL" && "${SELECTED_VARIANT}" != "${variant}" ]]; then
    continue
  fi
  run_config \
    "${variant}" \
    "${cfg_id}" \
    "${d_model}" \
    "${d_ff}" \
    "${d_state}" \
    "${e_layers}" \
    "${batch_size}" \
    "${learning_rate}" \
    "${moving_avg}" \
    "${ms_scales}" \
    "${ms_fusion}" \
    "${ms_use_decomp}" \
    "${ms_use_linear_skip}" \
    "${patch_len}" \
    "${stride}" \
    "${extra_args}"
done < <(config_lines)
