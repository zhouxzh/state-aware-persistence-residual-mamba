#!/usr/bin/env python
import argparse
import csv
import gc
import hashlib
import json
import os
import random
import shutil
import sys
from argparse import Namespace
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from utils.optuna_support import (
    METRIC_FIELDS,
    json_dumps_stable,
    load_dataset_manifest,
    require_term_coverage,
    summarize_horizon_metrics,
    term_for_horizon,
    term_report_steps,
    validate_dataset_file,
)

try:
    import optuna
except ModuleNotFoundError:
    optuna = None

try:
    import torch
except ModuleNotFoundError:
    torch = None


DEFAULT_MANIFEST = REPO_ROOT / "configs" / "optuna_datasets.json"
DEFAULT_CALIBRATION_HORIZONS = [7, 90, 360]
DEFAULT_BASELINE_MODELS = [
    "iTransformer",
    "Transformer",
    "Informer",
    "Reformer",
    "Autoformer",
    "DLinear",
    "NLinear",
    "PatchTST",
    "TimesNet",
    "Nonstationary_Transformer",
]
DEFAULT_MAMBA_MODELS = [
    "S_Mamba",
    "NS_Mamba-D",
    "MS_Mamba-MD",
    "PMS_Mamba-PD",
]

OPTUNA_SEARCH_SPACE_VERSION = "narrow_v2"


def study_version(cli_args):
    suffix = str(getattr(cli_args, "study_suffix", "") or "").strip()
    if not suffix:
        return OPTUNA_SEARCH_SPACE_VERSION
    safe_suffix = suffix.replace(" ", "_")
    return f"{OPTUNA_SEARCH_SPACE_VERSION}_{safe_suffix}"


def parse_args():
    parser = argparse.ArgumentParser(description="Run Optuna HPO for a custom CSV forecasting dataset.")
    parser.add_argument("--dataset", required=True, help="Dataset slug defined in the manifest JSON.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Path to dataset manifest JSON.")
    parser.add_argument("--phase", choices=["baseline", "mamba"], default="baseline")
    parser.add_argument(
        "--models",
        nargs="+",
        default=["ALL"],
        help="Model names for the selected phase, or ALL.",
    )
    parser.add_argument("--trials", type=int, default=0, help="Target total trials per model study.")
    parser.add_argument("--top-k-replays", type=int, default=5, help="Number of top calibration trials to replay.")
    parser.add_argument(
        "--calibration-horizons",
        type=int,
        nargs="+",
        default=None,
        help="Calibration horizons. Default: 7 90 360",
    )
    parser.add_argument(
        "--full-horizons",
        type=int,
        nargs="+",
        default=None,
        help="Full replay horizons. Default: dataset manifest horizons",
    )
    parser.add_argument("--seed", type=int, default=2023)
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--cpu", action="store_true", help="Force CPU execution.")
    parser.add_argument("--train-epochs", type=int, default=10)
    parser.add_argument("--patience", type=int, default=3)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--tensorboard-dir", type=str, default="./tensorboard/optuna")
    parser.add_argument("--checkpoints", type=str, default="./checkpoints/")
    parser.add_argument("--startup-trials", type=int, default=4)
    parser.add_argument("--warmup-steps", type=int, default=1)
    parser.add_argument("--interval-steps", type=int, default=1)
    parser.add_argument("--no-save-final-artifacts", action="store_true")
    parser.add_argument(
        "--study-suffix",
        default="",
        help=(
            "Optional suffix appended to Optuna study names. Use this when the objective changes, "
            "for example when switching from sparse calibration horizons to full-horizon calibration."
        ),
    )
    return parser.parse_args()


def require_optuna():
    if optuna is None:
        raise SystemExit(
            "Optuna is not installed in the current environment.\n"
            "Run this script inside the mamba environment:\n"
            "  conda run -n mamba python scripts/optuna/run_dataset_optuna.py --dataset gld"
        )
    return optuna


def require_torch():
    if torch is None:
        raise SystemExit(
            "PyTorch is not installed in the current environment.\n"
            "Run this script inside the mamba environment:\n"
            "  conda run -n mamba python scripts/optuna/run_dataset_optuna.py --dataset gld"
        )
    return torch


def default_trials_for_phase(phase):
    return 20 if phase == "baseline" else 24


def phase_model_list(phase):
    return DEFAULT_BASELINE_MODELS if phase == "baseline" else DEFAULT_MAMBA_MODELS


def selected_models(phase, requested):
    defaults = phase_model_list(phase)
    if requested == ["ALL"]:
        return defaults
    invalid = [model for model in requested if model not in defaults]
    if invalid:
        raise ValueError(f"Invalid models for phase '{phase}': {invalid}")
    return requested


def set_global_seed(seed):
    require_torch()
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def model_config_hash(params):
    return hashlib.md5(json_dumps_stable(params).encode("utf-8")).hexdigest()[:10]


def model_label_to_runtime_name(model_label):
    if model_label == "NS_Mamba-D":
        return "NS_Mamba"
    if model_label == "MS_Mamba-MD":
        return "MS_Mamba"
    if model_label == "PMS_Mamba-PD":
        return "PMS_Mamba"
    return model_label


def build_base_args(cli_args, dataset_cfg, model_label, params, pred_len, stage_tag):
    require_torch()
    runtime_model = model_label_to_runtime_name(model_label)
    seq_len = int(params["seq_len"])
    label_len = seq_len // 2
    config_hash = model_config_hash(params)
    model_id = f"OPTUNA_{dataset_cfg['slug']}_{cli_args.phase}_{model_label}_pl{pred_len}_{stage_tag}_{config_hash}"
    use_gpu = torch.cuda.is_available() and not cli_args.cpu

    return Namespace(
        is_training=1,
        model_id=model_id,
        model=runtime_model,
        task_name="long_term_forecast",
        data=dataset_cfg["data"],
        root_path=dataset_cfg["root_path"],
        data_path=dataset_cfg["data_path"],
        features=dataset_cfg["features"],
        target=dataset_cfg["target"],
        freq=dataset_cfg["freq"],
        checkpoints=cli_args.checkpoints,
        seq_len=seq_len,
        label_len=label_len,
        pred_len=int(pred_len),
        enc_in=int(dataset_cfg["enc_in"]),
        dec_in=int(dataset_cfg["dec_in"]),
        c_out=int(dataset_cfg["c_out"]),
        d_model=int(params.get("d_model", 512)),
        n_heads=8,
        e_layers=int(params.get("e_layers", 2)),
        d_layers=1,
        d_ff=int(params.get("d_ff", 2048)),
        moving_avg=int(params.get("moving_avg", 25)),
        individual=bool(params.get("individual", False)),
        top_k=int(params.get("top_k", 5)),
        num_kernels=int(params.get("num_kernels", 6)),
        patch_len=int(params.get("patch_len", 16)),
        stride=int(params.get("stride", 8)),
        factor=int(params.get("factor", 1)),
        distil=True,
        dropout=0.1,
        embed="timeF",
        activation="gelu",
        output_attention=False,
        do_predict=False,
        num_workers=int(cli_args.num_workers),
        itr=1,
        train_epochs=int(cli_args.train_epochs),
        batch_size=int(params.get("batch_size", 32)),
        patience=int(cli_args.patience),
        learning_rate=float(params.get("learning_rate", 1e-4)),
        des=f"optuna_{cli_args.phase}_{stage_tag}",
        loss="MSE",
        lradj="type1",
        use_amp=False,
        tensorboard_dir=cli_args.tensorboard_dir,
        use_gpu=use_gpu,
        gpu=int(cli_args.gpu),
        use_multi_gpu=False,
        devices=str(cli_args.gpu),
        inverse=True,
        class_strategy="projection",
        use_norm=int(params.get("use_norm", 1)),
        d_state=int(params.get("d_state", 32)),
        p_hidden_dims=list(params.get("p_hidden_dims", [128, 128])),
        p_hidden_layers=int(params.get("p_hidden_layers", 2)),
        use_adaptive_norm=int(params.get("use_adaptive_norm", 1)),
        use_decomp=int(params.get("use_decomp", 0)),
        use_shift_gate=int(params.get("use_shift_gate", 0)),
        ns_adaptive_scale=float(params.get("ns_adaptive_scale", 0.1)),
        ns_recent_ratio=float(params.get("ns_recent_ratio", 0.25)),
        ms_scales=list(params.get("ms_scales", [1, 2, 4])),
        ms_fusion=str(params.get("ms_fusion", "gate")),
        ms_use_decomp=int(params.get("ms_use_decomp", 1)),
        ms_use_linear_skip=int(params.get("ms_use_linear_skip", 0)),
        channel_independence=False,
        disable_tensorboard=True,
    )


def format_setting(args, ii=0):
    return '{}_{}_{}_{}_ft{}_sl{}_ll{}_pl{}_dm{}_nh{}_el{}_dl{}_df{}_fc{}_eb{}_dt{}_{}_{}'.format(
        args.model_id,
        args.model,
        args.data,
        args.features,
        args.seq_len,
        args.label_len,
        args.pred_len,
        args.d_model,
        args.n_heads,
        args.e_layers,
        args.d_layers,
        args.d_ff,
        args.factor,
        args.embed,
        args.distil,
        args.des,
        args.class_strategy,
        ii,
    )


def close_writer(exp):
    writer = getattr(exp, "writer", None)
    if writer is not None:
        writer.close()
        exp.writer = None


def cleanup_run_artifacts(setting, tensorboard_dir):
    paths = [
        Path("./checkpoints") / setting,
        Path("./results") / setting,
        Path("./test_results") / setting,
        Path(tensorboard_dir) / setting,
    ]
    for path in paths:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)


def normalize_params(params):
    normalized = {}
    for key, value in params.items():
        if isinstance(value, tuple):
            normalized[key] = [normalize_params({str(i): item for i, item in enumerate(value)})[str(i)] for i, item in enumerate(value)]
        elif isinstance(value, list):
            normalized[key] = [int(item) if isinstance(item, (np.integer, int)) else item for item in value]
        elif isinstance(value, np.integer):
            normalized[key] = int(value)
        elif isinstance(value, np.floating):
            normalized[key] = float(value)
        else:
            normalized[key] = value
    return normalized


def suggest_patch_stride_pair(trial, param_name, valid_pairs):
    pair_tag = trial.suggest_categorical(
        param_name,
        [f"{patch_len}:{stride}" for patch_len, stride in valid_pairs],
    )
    patch_len_str, stride_str = pair_tag.split(":")
    return int(patch_len_str), int(stride_str)


def sample_params(trial, phase, model_label):
    params = {}
    if phase == "baseline":
        if model_label == "iTransformer":
            seq_len = trial.suggest_categorical("seq_len", [128, 192, 256])
            params.update(
                seq_len=int(seq_len),
                factor=1,
                d_model=trial.suggest_categorical("d_model", [128, 256]),
                d_ff=trial.suggest_categorical("d_ff", [256, 512]),
                batch_size=trial.suggest_categorical("batch_size", [16]),
                learning_rate=trial.suggest_categorical("learning_rate", [0.0001, 0.0002, 0.0003]),
                use_norm=1,
            )
        elif model_label in {"Transformer", "Informer"}:
            seq_len = trial.suggest_categorical("seq_len", [16, 32, 192])
            params.update(
                seq_len=int(seq_len),
                factor=3,
                d_model=trial.suggest_categorical("d_model", [256]),
                d_ff=trial.suggest_categorical("d_ff", [1024, 2048]),
                batch_size=trial.suggest_categorical("batch_size", [16, 32]),
                learning_rate=trial.suggest_categorical("learning_rate", [0.0001, 0.0002, 0.0003]),
            )
        elif model_label == "Reformer":
            seq_len = trial.suggest_categorical("seq_len", [192, 320])
            params.update(
                seq_len=int(seq_len),
                factor=3,
                d_model=trial.suggest_categorical("d_model", [512]),
                d_ff=trial.suggest_categorical("d_ff", [2048]),
                batch_size=trial.suggest_categorical("batch_size", [16, 32]),
                learning_rate=trial.suggest_categorical("learning_rate", [0.0001, 0.0002, 0.0003]),
            )
        elif model_label == "Autoformer":
            seq_len = trial.suggest_categorical("seq_len", [16, 32])
            params.update(
                seq_len=int(seq_len),
                factor=3,
                d_model=trial.suggest_categorical("d_model", [256]),
                d_ff=trial.suggest_categorical("d_ff", [512, 1024]),
                batch_size=trial.suggest_categorical("batch_size", [32]),
                learning_rate=trial.suggest_categorical("learning_rate", [0.0001, 0.0002, 0.0003]),
                moving_avg=trial.suggest_categorical("moving_avg", [13, 25]),
            )
        elif model_label == "DLinear":
            seq_len = trial.suggest_categorical("seq_len", [96, 192, 256])
            params.update(
                seq_len=int(seq_len),
                batch_size=trial.suggest_categorical("batch_size", [32, 64]),
                learning_rate=trial.suggest_categorical("learning_rate", [0.003, 0.005]),
                moving_avg=trial.suggest_categorical("moving_avg", [13, 25]),
                individual=True,
                factor=1,
            )
        elif model_label == "NLinear":
            seq_len = trial.suggest_categorical("seq_len", [64, 192, 320, 384])
            params.update(
                seq_len=int(seq_len),
                batch_size=trial.suggest_categorical("batch_size", [32, 64]),
                learning_rate=trial.suggest_categorical("learning_rate", [0.005, 0.01]),
                individual=True,
                factor=1,
            )
        elif model_label == "PatchTST":
            seq_len = trial.suggest_categorical("seq_len", [128, 256, 320])
            patch_len, stride = suggest_patch_stride_pair(
                trial,
                "patch_stride_pair",
                [
                    (16, 8),
                    (24, 12),
                    (32, 16),
                ],
            )
            params.update(
                seq_len=int(seq_len),
                factor=3,
                d_model=trial.suggest_categorical("d_model", [128, 256]),
                d_ff=trial.suggest_categorical("d_ff", [512, 2048]),
                patch_len=patch_len,
                stride=stride,
                batch_size=trial.suggest_categorical("batch_size", [16, 32]),
                learning_rate=trial.suggest_categorical("learning_rate", [0.0002, 0.0003, 0.0005]),
            )
        elif model_label == "TimesNet":
            seq_len = trial.suggest_categorical("seq_len", [128, 256, 320])
            params.update(
                seq_len=int(seq_len),
                factor=3,
                d_model=trial.suggest_categorical("d_model", [32, 64]),
                d_ff=trial.suggest_categorical("d_ff", [128, 256]),
                top_k=trial.suggest_categorical("top_k", [5]),
                num_kernels=trial.suggest_categorical("num_kernels", [6, 8]),
                batch_size=trial.suggest_categorical("batch_size", [16, 32]),
                learning_rate=trial.suggest_categorical("learning_rate", [0.0001, 0.0002, 0.0003]),
            )
        elif model_label == "Nonstationary_Transformer":
            seq_len = trial.suggest_categorical("seq_len", [16, 32])
            hidden_dims = [256, 256]
            params.update(
                seq_len=int(seq_len),
                factor=3,
                d_model=trial.suggest_categorical("d_model", [32, 64]),
                d_ff=trial.suggest_categorical("d_ff", [128, 256]),
                top_k=trial.suggest_categorical("top_k", [3]),
                p_hidden_dims=hidden_dims,
                p_hidden_layers=2,
                batch_size=trial.suggest_categorical("batch_size", [16]),
                learning_rate=trial.suggest_categorical("learning_rate", [0.0001, 0.0002]),
            )
        else:
            raise ValueError(f"Unsupported baseline model: {model_label}")
    else:
        seq_len = trial.suggest_categorical("seq_len", [16, 32, 64, 96, 128, 192, 256, 320, 384])
        params.update(
            seq_len=int(seq_len),
            factor=1,
            d_model=trial.suggest_categorical("d_model", [64, 128]),
            d_ff=trial.suggest_categorical("d_ff", [128, 256]),
            d_state=trial.suggest_categorical("d_state", [16, 32]),
            batch_size=16,
            learning_rate=trial.suggest_categorical("learning_rate", [0.00005, 0.0001, 0.0002, 0.0003]),
            moving_avg=trial.suggest_categorical("moving_avg", [13, 25, 49]),
            use_norm=1,
        )
        if model_label == "S_Mamba":
            pass
        elif model_label == "NS_Mamba-D":
            params.update(use_adaptive_norm=0, use_decomp=1, use_shift_gate=0)
        elif model_label == "MS_Mamba-MD":
            scale_tag = trial.suggest_categorical("ms_scales", ["1,2,4", "1,2,4,8", "1,3,6", "1,4,8"])
            params.update(
                ms_scales=[int(piece) for piece in scale_tag.split(",")],
                ms_fusion="mean",
                ms_use_decomp=1,
                ms_use_linear_skip=0,
            )
        elif model_label == "PMS_Mamba-PD":
            scale_tag = trial.suggest_categorical("ms_scales", ["1,2,4", "1,2,4,8"])
            patch_len, stride = suggest_patch_stride_pair(
                trial,
                "patch_stride_pair",
                [
                    (8, 4),
                    (8, 8),
                    (16, 4),
                    (16, 8),
                ],
            )
            params.update(
                ms_scales=[int(piece) for piece in scale_tag.split(",")],
                ms_fusion="mean",
                ms_use_decomp=1,
                patch_len=patch_len,
                stride=stride,
            )
        else:
            raise ValueError(f"Unsupported mamba model: {model_label}")

    return normalize_params(params)


def run_horizon(cli_args, dataset_cfg, model_label, params, pred_len, stage_tag, save_artifacts,
                eval_flag='val'):
    require_torch()
    from experiments.exp_long_term_forecasting import Exp_Long_Term_Forecast

    setting = None
    exp = None
    args = build_base_args(cli_args, dataset_cfg, model_label, params, pred_len, stage_tag)
    set_global_seed(cli_args.seed)
    try:
        exp = Exp_Long_Term_Forecast(args)
        setting = format_setting(args)
        exp.train(setting)
        evaluation = exp.evaluate(
            setting=setting,
            save_artifacts=save_artifacts,
            save_visuals=save_artifacts,
            write_result_log=save_artifacts,
            write_tensorboard=False,
            flag=eval_flag,
        )
        metrics = {metric: float(evaluation[metric]) for metric in METRIC_FIELDS}
        return {
            "setting": setting,
            "metrics": metrics,
        }
    finally:
        if exp is not None:
            close_writer(exp)
        if not save_artifacts and setting is not None:
            cleanup_run_artifacts(setting, args.tensorboard_dir)
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()


def evaluate_horizons(cli_args, dataset_cfg, model_label, params, horizons, stage_tag,
                      trial=None, save_artifacts=False, eval_flag='val'):
    horizon_metrics = {}
    run_settings = {}
    report_steps = {step for step, _ in term_report_steps(horizons, dataset_cfg["term_groups"])}

    for step, horizon in enumerate(horizons, start=1):
        run = run_horizon(
            cli_args=cli_args,
            dataset_cfg=dataset_cfg,
            model_label=model_label,
            params=params,
            pred_len=horizon,
            stage_tag=f"{stage_tag}_h{horizon}",
            save_artifacts=save_artifacts,
            eval_flag=eval_flag,
        )
        horizon_metrics[int(horizon)] = run["metrics"]
        run_settings[int(horizon)] = run["setting"]

        if trial is not None and step in report_steps:
            partial_summary = summarize_horizon_metrics(horizon_metrics, dataset_cfg["term_groups"])
            trial.report(partial_summary["balanced_rmsse"], step)
            if trial.should_prune():
                raise optuna.exceptions.TrialPruned(
                    f"Pruned after calibration step {step} for {model_label}"
                )

    summary = summarize_horizon_metrics(horizon_metrics, dataset_cfg["term_groups"])
    return horizon_metrics, summary, run_settings


def trial_rows_from_study(study, dataset_slug, phase, model_label):
    rows = []
    for trial in study.trials:
        summary = trial.user_attrs.get("calibration_summary", {})
        grouped = summary.get("grouped_metrics", {})
        rmsse_grouped = grouped.get("rmsse", {})
        rows.append(
            {
                "dataset": dataset_slug,
                "phase": phase,
                "model": model_label,
                "study_name": study.study_name,
                "trial_number": trial.number,
                "state": str(trial.state),
                "objective": trial.value if trial.value is not None else "",
                "short_rmsse": rmsse_grouped.get("short", ""),
                "middle_rmsse": rmsse_grouped.get("middle", ""),
                "long_rmsse": rmsse_grouped.get("long", ""),
                "balanced_rmsse": summary.get("balanced_rmsse", ""),
                "params_json": json_dumps_stable(trial.user_attrs.get("resolved_params", {})),
                "per_horizon_metrics_json": json_dumps_stable(
                    trial.user_attrs.get("calibration_horizon_metrics", {})
                ),
                "error": trial.user_attrs.get("error", ""),
            }
        )
    return rows


def replay_rows_from_candidates(dataset_slug, phase, model_label, study_name, candidate_rows):
    rows = []
    for row in candidate_rows:
        rows.append(
            {
                "dataset": dataset_slug,
                "phase": phase,
                "model": model_label,
                "study_name": study_name,
                "trial_number": row["trial_number"],
                "candidate_rank": row["candidate_rank"],
                "eval_flag": row["eval_flag"],
                "balanced_rmsse": row["summary"]["balanced_rmsse"],
                "params_json": json_dumps_stable(row["params"]),
                "per_horizon_metrics_json": json_dumps_stable(row["horizon_metrics"]),
            }
        )
    return rows


def optimize_model(optuna_mod, cli_args, dataset_cfg, model_label, trials_target, calibration_horizons, full_horizons):
    output_dir = REPO_ROOT / "results" / "optuna" / dataset_cfg["slug"]
    output_dir.mkdir(parents=True, exist_ok=True)
    storage_path = output_dir / "studies.db"
    study_name = f"{dataset_cfg['slug']}_{cli_args.phase}_{model_label}_{study_version(cli_args)}"
    storage = f"sqlite:///{storage_path}"

    sampler = optuna_mod.samplers.TPESampler(seed=cli_args.seed)
    pruner = optuna_mod.pruners.MedianPruner(
        n_startup_trials=cli_args.startup_trials,
        n_warmup_steps=cli_args.warmup_steps,
        interval_steps=cli_args.interval_steps,
    )
    study = optuna_mod.create_study(
        study_name=study_name,
        storage=storage,
        direction="minimize",
        sampler=sampler,
        pruner=pruner,
        load_if_exists=True,
    )

    def objective(trial):
        params = sample_params(trial, cli_args.phase, model_label)
        trial.set_user_attr("resolved_params", params)
        try:
            horizon_metrics, summary, _ = evaluate_horizons(
                cli_args=cli_args,
                dataset_cfg=dataset_cfg,
                model_label=model_label,
                params=params,
                horizons=calibration_horizons,
                stage_tag=f"trial{trial.number}_calibration",
                trial=trial,
                save_artifacts=False,
            )
            trial.set_user_attr("calibration_horizon_metrics", horizon_metrics)
            trial.set_user_attr("calibration_summary", summary)
            return summary["balanced_rmsse"]
        except optuna_mod.exceptions.TrialPruned:
            raise
        except Exception as exc:
            trial.set_user_attr("error", str(exc))
            raise optuna_mod.exceptions.TrialPruned(str(exc))

    completed_trials_before = len(study.trials)
    remaining_trials = max(0, trials_target - completed_trials_before)
    if remaining_trials > 0:
        study.optimize(objective, n_trials=remaining_trials, gc_after_trial=True)

    completed_trials = [
        trial for trial in study.trials
        if trial.state == optuna_mod.trial.TrialState.COMPLETE and trial.value is not None
    ]
    completed_trials.sort(key=lambda trial: trial.value)
    if not completed_trials:
        raise RuntimeError(f"No completed Optuna trials found for {model_label}")

    candidate_trials = completed_trials[: min(cli_args.top_k_replays, len(completed_trials))]
    candidate_results = []
    for candidate_rank, trial in enumerate(candidate_trials, start=1):
        params = normalize_params(trial.user_attrs.get("resolved_params", {}))
        try:
            horizon_metrics, summary, _ = evaluate_horizons(
                cli_args=cli_args,
                dataset_cfg=dataset_cfg,
                model_label=model_label,
                params=params,
                horizons=full_horizons,
                stage_tag=f"trial{trial.number}_valfullrank{candidate_rank}",
                save_artifacts=False,
                eval_flag='val',
            )
        except Exception as exc:
            print(
                f"Skipping validation replay candidate for {model_label}: "
                f"trial={trial.number}, rank={candidate_rank}, error={exc}"
            )
            continue
        candidate_results.append(
            {
                "trial_number": trial.number,
                "candidate_rank": candidate_rank,
                "eval_flag": "val",
                "params": params,
                "horizon_metrics": horizon_metrics,
                "summary": summary,
            }
        )

    if not candidate_results:
        raise RuntimeError(f"No successful validation replay candidates for {model_label}")

    best_candidate = min(candidate_results, key=lambda row: row["summary"]["balanced_rmsse"])
    final_horizon_metrics, final_summary, final_settings = evaluate_horizons(
        cli_args=cli_args,
        dataset_cfg=dataset_cfg,
        model_label=model_label,
        params=best_candidate["params"],
        horizons=full_horizons,
        stage_tag=f"trial{best_candidate['trial_number']}_bestfinal",
        save_artifacts=not cli_args.no_save_final_artifacts,
        eval_flag='test',
    )

    return {
        "study": study,
        "study_name": study_name,
        "model": model_label,
        "best_calibration_trial": completed_trials[0].number,
        "best_calibration_objective": completed_trials[0].value,
        "candidate_results": candidate_results,
        "best_candidate": best_candidate,
        "final_horizon_metrics": final_horizon_metrics,
        "final_summary": final_summary,
        "final_settings": final_settings,
    }


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def phase_best_rows(dataset_cfg, phase, model_results):
    rows = []
    for result in model_results:
        model_label = result["model"]
        summary = result["final_summary"]
        grouped = summary["grouped_metrics"]
        params_json = json_dumps_stable(result["best_candidate"]["params"])
        for horizon in summary["available_horizons"]:
            metrics = result["final_horizon_metrics"][horizon]
            rows.append(
                {
                    "dataset": dataset_cfg["slug"],
                    "target": dataset_cfg["target"],
                    "phase": phase,
                    "model": model_label,
                    "horizon": horizon,
                    "term": term_for_horizon(horizon, dataset_cfg["term_groups"]),
                    "seq_len": result["best_candidate"]["params"]["seq_len"],
                    "label_len": result["best_candidate"]["params"]["seq_len"] // 2,
                    "pred_len": horizon,
                    "mae": metrics["mae"],
                    "mse": metrics["mse"],
                    "rmse": metrics["rmse"],
                    "mape": metrics["mape"],
                    "mspe": metrics["mspe"],
                    "rmsse": metrics["rmsse"],
                    "short_avg_rmse": grouped["rmse"].get("short", ""),
                    "middle_avg_rmse": grouped["rmse"].get("middle", ""),
                    "long_avg_rmse": grouped["rmse"].get("long", ""),
                    "overall_avg_rmse": grouped["rmse"]["overall"],
                    "short_avg_mae": grouped["mae"].get("short", ""),
                    "middle_avg_mae": grouped["mae"].get("middle", ""),
                    "long_avg_mae": grouped["mae"].get("long", ""),
                    "overall_avg_mae": grouped["mae"]["overall"],
                    "short_avg_rmsse": grouped["rmsse"].get("short", ""),
                    "middle_avg_rmsse": grouped["rmsse"].get("middle", ""),
                    "long_avg_rmsse": grouped["rmsse"].get("long", ""),
                    "overall_avg_rmsse": grouped["rmsse"]["overall"],
                    "overall_balanced_rmsse": summary["balanced_rmsse"],
                    "calibration_balanced_rmsse": result["best_calibration_objective"],
                    "selection_eval_flag": result["best_candidate"]["eval_flag"],
                    "selection_balanced_rmsse": result["best_candidate"]["summary"]["balanced_rmsse"],
                    "final_eval_flag": "test",
                    "study_name": result["study_name"],
                    "trial_number": result["best_candidate"]["trial_number"],
                    "params_json": params_json,
                    "run": result["final_settings"][horizon],
                    "status": "complete",
                    "notes": "",
                }
            )
    rows.sort(key=lambda row: (row["model"], row["horizon"]))
    return rows


def best_params_payload(dataset_cfg, phase, model_results, calibration_horizons, full_horizons, search_space_version):
    return {
        "dataset": dataset_cfg["slug"],
        "phase": phase,
        "search_space_version": search_space_version,
        "objective_metric": "balanced_rmsse",
        "calibration_horizons": list(calibration_horizons),
        "full_horizons": list(full_horizons),
        "models": {
            result["model"]: {
                "study_name": result["study_name"],
                "best_calibration_trial": result["best_calibration_trial"],
                "best_calibration_objective": result["best_calibration_objective"],
                "selection_eval_flag": result["best_candidate"]["eval_flag"],
                "best_validation_replay_trial": result["best_candidate"]["trial_number"],
                "best_validation_replay_balanced_rmsse": result["best_candidate"]["summary"]["balanced_rmsse"],
                "final_eval_flag": "test",
                "final_test_balanced_rmsse": result["final_summary"]["balanced_rmsse"],
                "params": result["best_candidate"]["params"],
            }
            for result in model_results
        },
    }


def comparison_rows_from_phase_best(best_rows):
    grouped = {}
    for row in best_rows:
        model = row["model"]
        grouped.setdefault(model, []).append(row)

    rows = []
    for model, model_rows in grouped.items():
        first = model_rows[0]
        per_horizon = {}
        for row in sorted(model_rows, key=lambda item: int(item["horizon"])):
            per_horizon[int(row["horizon"])] = {
                "term": row["term"],
                "mae": float(row["mae"]),
                "mse": float(row["mse"]),
                "rmse": float(row["rmse"]),
                "mape": float(row["mape"]),
                "mspe": float(row["mspe"]),
                "rmsse": float(row["rmsse"]),
            }
        rows.append((first, per_horizon))
    return rows


def load_phase_best_rows(path):
    if not path.exists():
        return []
    with path.open() as f:
        return list(csv.DictReader(f))


def comparison_summary_rows(dataset_slug, phase_best_paths):
    rows = []
    for path in phase_best_paths:
        for row, per_horizon in comparison_rows_from_phase_best(load_phase_best_rows(path)):
            rows.append(
                {
                    "dataset": dataset_slug,
                    "target": row["target"],
                    "phase": row["phase"],
                    "model": row["model"],
                    "objective_metric": "balanced_rmsse",
                    "short_avg_rmse": row["short_avg_rmse"],
                    "middle_avg_rmse": row["middle_avg_rmse"],
                    "long_avg_rmse": row["long_avg_rmse"],
                    "overall_avg_rmse": row["overall_avg_rmse"],
                    "short_avg_mae": row["short_avg_mae"],
                    "middle_avg_mae": row["middle_avg_mae"],
                    "long_avg_mae": row["long_avg_mae"],
                    "overall_avg_mae": row["overall_avg_mae"],
                    "short_avg_rmsse": row["short_avg_rmsse"],
                    "middle_avg_rmsse": row["middle_avg_rmsse"],
                    "long_avg_rmsse": row["long_avg_rmsse"],
                    "overall_avg_rmsse": row["overall_avg_rmsse"],
                    "overall_balanced_rmsse": row["overall_balanced_rmsse"],
                    "study_name": row["study_name"],
                    "trial_number": row["trial_number"],
                    "params_json": row["params_json"],
                    "per_horizon_metrics_json": json_dumps_stable(per_horizon),
                }
            )
    rows.sort(key=lambda row: float(row["overall_balanced_rmsse"]))
    return rows


def main():
    cli_args = parse_args()
    optuna_mod = require_optuna()
    dataset_cfg = load_dataset_manifest(cli_args.manifest, cli_args.dataset, REPO_ROOT)
    validate_dataset_file(dataset_cfg)

    calibration_horizons = cli_args.calibration_horizons or DEFAULT_CALIBRATION_HORIZONS
    full_horizons = cli_args.full_horizons or dataset_cfg["horizons"]
    calibration_horizons = [int(horizon) for horizon in calibration_horizons]
    full_horizons = [int(horizon) for horizon in full_horizons]

    invalid_calibration = sorted(set(calibration_horizons) - set(dataset_cfg["horizons"]))
    invalid_full = sorted(set(full_horizons) - set(dataset_cfg["horizons"]))
    if invalid_calibration:
        raise ValueError(f"Calibration horizons are not in the manifest horizon suite: {invalid_calibration}")
    if invalid_full:
        raise ValueError(f"Full horizons are not in the manifest horizon suite: {invalid_full}")

    require_term_coverage(calibration_horizons, dataset_cfg["term_groups"], "Calibration horizons")
    require_term_coverage(full_horizons, dataset_cfg["term_groups"], "Full horizons")

    models = selected_models(cli_args.phase, cli_args.models)
    trials_target = cli_args.trials or default_trials_for_phase(cli_args.phase)

    output_dir = REPO_ROOT / "results" / "optuna" / dataset_cfg["slug"]
    output_dir.mkdir(parents=True, exist_ok=True)

    all_trial_rows = []
    all_replay_rows = []
    model_results = []

    for model_label in models:
        print(
            f"Running Optuna phase={cli_args.phase}, dataset={dataset_cfg['slug']}, "
            f"model={model_label}, study_version={study_version(cli_args)}, "
            f"target_trials={trials_target}"
        )
        result = optimize_model(
            optuna_mod=optuna_mod,
            cli_args=cli_args,
            dataset_cfg=dataset_cfg,
            model_label=model_label,
            trials_target=trials_target,
            calibration_horizons=calibration_horizons,
            full_horizons=full_horizons,
        )
        model_results.append(result)
        all_trial_rows.extend(
            trial_rows_from_study(result["study"], dataset_cfg["slug"], cli_args.phase, model_label)
        )
        all_replay_rows.extend(
            replay_rows_from_candidates(
                dataset_cfg["slug"], cli_args.phase, model_label, result["study_name"], result["candidate_results"]
            )
        )

    trials_csv = output_dir / f"{cli_args.phase}_trials.csv"
    replays_csv = output_dir / f"{cli_args.phase}_replays.csv"
    best_params_json = output_dir / f"{cli_args.phase}_best_params.json"
    phase_best_csv = REPO_ROOT / "results" / f"{dataset_cfg['slug']}_{cli_args.phase}_optuna_best.csv"
    comparison_csv = REPO_ROOT / "results" / f"{dataset_cfg['slug']}_optuna_comparison.csv"

    write_csv(
        trials_csv,
        all_trial_rows,
        [
            "dataset",
            "phase",
            "model",
            "study_name",
            "trial_number",
            "state",
            "objective",
            "short_rmsse",
            "middle_rmsse",
            "long_rmsse",
            "balanced_rmsse",
            "params_json",
            "per_horizon_metrics_json",
            "error",
        ],
    )
    write_csv(
        replays_csv,
        all_replay_rows,
        [
            "dataset",
            "phase",
            "model",
            "study_name",
            "trial_number",
            "candidate_rank",
            "eval_flag",
            "balanced_rmsse",
            "params_json",
            "per_horizon_metrics_json",
        ],
    )
    best_params_json.write_text(
        json.dumps(
            best_params_payload(
                dataset_cfg,
                cli_args.phase,
                model_results,
                calibration_horizons,
                full_horizons,
                study_version(cli_args),
            ),
            indent=2,
            sort_keys=True,
        )
    )

    phase_best = phase_best_rows(dataset_cfg, cli_args.phase, model_results)
    write_csv(
        phase_best_csv,
        phase_best,
        [
            "dataset",
            "target",
            "phase",
            "model",
            "horizon",
            "term",
            "seq_len",
            "label_len",
            "pred_len",
            "mae",
            "mse",
            "rmse",
            "mape",
            "mspe",
            "rmsse",
            "short_avg_rmse",
            "middle_avg_rmse",
            "long_avg_rmse",
            "overall_avg_rmse",
            "short_avg_mae",
            "middle_avg_mae",
            "long_avg_mae",
            "overall_avg_mae",
            "short_avg_rmsse",
            "middle_avg_rmsse",
            "long_avg_rmsse",
            "overall_avg_rmsse",
            "overall_balanced_rmsse",
            "calibration_balanced_rmsse",
            "selection_eval_flag",
            "selection_balanced_rmsse",
            "final_eval_flag",
            "study_name",
            "trial_number",
            "params_json",
            "run",
            "status",
            "notes",
        ],
    )

    comparison_rows = comparison_summary_rows(
        dataset_cfg["slug"],
        [
            REPO_ROOT / "results" / f"{dataset_cfg['slug']}_baseline_optuna_best.csv",
            REPO_ROOT / "results" / f"{dataset_cfg['slug']}_mamba_optuna_best.csv",
        ],
    )
    write_csv(
        comparison_csv,
        comparison_rows,
        [
            "dataset",
            "target",
            "phase",
            "model",
            "objective_metric",
            "short_avg_rmse",
            "middle_avg_rmse",
            "long_avg_rmse",
            "overall_avg_rmse",
            "short_avg_mae",
            "middle_avg_mae",
            "long_avg_mae",
            "overall_avg_mae",
            "short_avg_rmsse",
            "middle_avg_rmsse",
            "long_avg_rmsse",
            "overall_avg_rmsse",
            "overall_balanced_rmsse",
            "study_name",
            "trial_number",
            "params_json",
            "per_horizon_metrics_json",
        ],
    )

    print(f"wrote {trials_csv.relative_to(REPO_ROOT)}")
    print(f"wrote {replays_csv.relative_to(REPO_ROOT)}")
    print(f"wrote {best_params_json.relative_to(REPO_ROOT)}")
    print(f"wrote {phase_best_csv.relative_to(REPO_ROOT)}")
    print(f"wrote {comparison_csv.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
