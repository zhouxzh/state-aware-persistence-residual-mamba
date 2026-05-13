#!/usr/bin/env python
"""Replay the saved GLD baseline Optuna configuration and archive artifacts.

The script reads the configuration bundle produced by
``scripts/extract_gld_baseline_optuna_bundle.py`` and re-runs the selected
baseline hyperparameters for each model/horizon pair. It stores the checkpoint,
test predictions, targets, metrics, visualizations, and run metadata under
``scripts/gld_baseline_optuna_bundle/reproduced_artifacts/`` by default.
"""

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import shutil
import sys
from argparse import Namespace
from collections import defaultdict
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from utils.optuna_support import METRIC_FIELDS, summarize_horizon_metrics, term_for_horizon


DEFAULT_BUNDLE_ROOT = REPO_ROOT / "scripts" / "gld_baseline_optuna_bundle"
DEFAULT_OUTPUT_ROOT = DEFAULT_BUNDLE_ROOT / "reproduced_artifacts"
RUNNER_PATH = REPO_ROOT / "scripts" / "optuna" / "run_dataset_optuna.py"

RUNNER_MODULE = None
SETTING_FIELDNAMES = [
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
    "study_name",
    "trial_number",
    "params_json",
    "setting",
    "checkpoint_path",
    "metrics_path",
    "pred_path",
    "true_path",
    "meta_path",
    "visuals_dir",
    "run_metadata",
    "status",
    "notes",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Reproduce GLD baseline results from the saved Optuna bundle."
    )
    parser.add_argument("--bundle-root", type=Path, default=DEFAULT_BUNDLE_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--models", nargs="+", default=None, help="Subset of model names to replay.")
    parser.add_argument("--horizons", type=int, nargs="+", default=None, help="Subset of horizons to replay.")
    parser.add_argument("--seed", type=int, default=2023)
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--train-epochs", type=int, default=10)
    parser.add_argument("--patience", type=int, default=3)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true", help="Re-run and replace existing artifacts.")
    parser.add_argument(
        "--keep-work-dirs",
        action="store_true",
        help="Keep raw checkpoints/results/test_results directories in addition to organized artifacts.",
    )
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Print the replay plan without training.")
    return parser.parse_args()


def load_json(path):
    with path.open() as f:
        return json.load(f)


def require_cuda():
    try:
        import torch
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "PyTorch is required for baseline reproduction. Run this script inside the mamba environment:\n"
            "  conda run -n mamba python scripts/reproduce_gld_baseline_from_bundle.py"
        ) from exc

    if not torch.cuda.is_available():
        raise SystemExit(
            "CUDA is required for baseline reproduction. CPU replay is disabled because these runs must "
            "match the CUDA baseline workflow."
        )


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)


def stable_json(value):
    return json.dumps(value, sort_keys=True)


def config_hash(params):
    return hashlib.md5(stable_json(params).encode("utf-8")).hexdigest()[:10]


def runtime_model_name(model_label):
    if model_label == "NS_Mamba-D":
        return "NS_Mamba"
    if model_label == "MS_Mamba-MD":
        return "MS_Mamba"
    if model_label == "PMS_Mamba-PD":
        return "PMS_Mamba"
    return model_label


def resolve_repo_path(path_text):
    path = Path(path_text)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def relative(path):
    path = Path(path)
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def make_dataset_cfg(reproduction_config):
    cfg = reproduction_config["dataset_config"]
    root_path = resolve_repo_path(cfg["root_path"])
    data_file = root_path / cfg["data_path"]
    if not data_file.exists():
        raise FileNotFoundError(f"Dataset file does not exist: {data_file}")

    return {
        "slug": reproduction_config["dataset"],
        "data": cfg.get("data", "custom"),
        "root_path": str(root_path),
        "data_path": cfg["data_path"],
        "target": cfg["target"],
        "freq": cfg["freq"],
        "features": cfg["features"],
        "horizons": [int(horizon) for horizon in cfg["horizons"]],
        "term_groups": {
            term: [int(horizon) for horizon in horizons]
            for term, horizons in cfg["term_groups"].items()
        },
        "enc_in": int(cfg.get("enc_in", 1)),
        "dec_in": int(cfg.get("dec_in", 1)),
        "c_out": int(cfg.get("c_out", 1)),
        "data_file": str(data_file),
    }


def setting_for(dataset_cfg, phase, model_label, params, horizon, stage_tag):
    seq_len = int(params["seq_len"])
    label_len = seq_len // 2
    model_id = (
        f"OPTUNA_{dataset_cfg['slug']}_{phase}_{model_label}_pl{horizon}_"
        f"{stage_tag}_{config_hash(params)}"
    )
    return "{}_{}_{}_{}_ft{}_sl{}_ll{}_pl{}_dm{}_nh{}_el{}_dl{}_df{}_fc{}_eb{}_dt{}_{}_{}".format(
        model_id,
        runtime_model_name(model_label),
        dataset_cfg["data"],
        dataset_cfg["features"],
        seq_len,
        label_len,
        int(horizon),
        int(params.get("d_model", 512)),
        8,
        int(params.get("e_layers", 2)),
        1,
        int(params.get("d_ff", 2048)),
        int(params.get("factor", 1)),
        "timeF",
        True,
        f"optuna_{phase}_{stage_tag}",
        "projection",
        0,
    )


def load_runner():
    global RUNNER_MODULE
    if RUNNER_MODULE is not None:
        return RUNNER_MODULE
    spec = importlib.util.spec_from_file_location("run_dataset_optuna", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import Optuna runner from {RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    RUNNER_MODULE = module
    return module


def selected_items(reproduction_config, best_params, args):
    config_models = list(reproduction_config["models"].keys())
    if args.models is None:
        models = config_models
    else:
        invalid_models = [model for model in args.models if model not in reproduction_config["models"]]
        if invalid_models:
            raise ValueError(f"Models are not in the bundle config: {invalid_models}")
        models = args.models

    configured_horizons = best_params.get("full_horizons") or reproduction_config["dataset_config"]["horizons"]
    configured_horizons = [int(horizon) for horizon in configured_horizons]
    if args.horizons is None:
        horizons = configured_horizons
    else:
        invalid_horizons = sorted(set(args.horizons) - set(configured_horizons))
        if invalid_horizons:
            raise ValueError(f"Horizons are not in the bundle config: {invalid_horizons}")
        horizons = [int(horizon) for horizon in args.horizons]

    return models, horizons


def artifact_dir(output_root, model, horizon):
    safe_model = model.replace("/", "_")
    return output_root / "artifacts" / safe_model / f"horizon_{int(horizon):03d}"


def artifact_paths(run_dir):
    return {
        "checkpoint_dir": run_dir / "checkpoint",
        "predictions_dir": run_dir / "predictions",
        "visuals_dir": run_dir / "visuals",
        "checkpoint": run_dir / "checkpoint" / "checkpoint.pth",
        "metrics": run_dir / "predictions" / "metrics.npy",
        "pred": run_dir / "predictions" / "pred.npy",
        "true": run_dir / "predictions" / "true.npy",
        "meta": run_dir / "predictions" / "meta.json",
        "metadata": run_dir / "run.json",
    }


def artifact_complete(run_dir):
    paths = artifact_paths(run_dir)
    return all(paths[key].exists() for key in ("checkpoint", "metrics", "pred", "true", "meta", "metadata"))


def remove_if_exists(path):
    path = Path(path)
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def transfer_dir(src, dst, keep_source):
    src = Path(src)
    dst = Path(dst)
    if not src.exists():
        raise FileNotFoundError(f"Expected run artifact directory does not exist: {src}")
    remove_if_exists(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if keep_source:
        shutil.copytree(src, dst)
    else:
        shutil.move(str(src), str(dst))


def archive_run(work_root, output_root, model, horizon, setting, keep_work_dirs):
    run_dir = artifact_dir(output_root, model, horizon)
    paths = artifact_paths(run_dir)

    transfer_dir(work_root / "checkpoints" / setting, paths["checkpoint_dir"], keep_work_dirs)
    transfer_dir(work_root / "results" / setting, paths["predictions_dir"], keep_work_dirs)

    visual_src = work_root / "test_results" / setting
    if visual_src.exists():
        transfer_dir(visual_src, paths["visuals_dir"], keep_work_dirs)
    else:
        paths["visuals_dir"].mkdir(parents=True, exist_ok=True)

    missing = [
        str(paths[key])
        for key in ("checkpoint", "metrics", "pred", "true", "meta")
        if not paths[key].exists()
    ]
    if missing:
        raise FileNotFoundError(f"Missing required archived artifacts: {missing}")

    return run_dir


def replay_cli_args(args, work_root, phase):
    return Namespace(
        phase=phase,
        checkpoints=str(work_root / "checkpoints"),
        cpu=False,
        seed=int(args.seed),
        gpu=int(args.gpu),
        train_epochs=int(args.train_epochs),
        patience=int(args.patience),
        num_workers=int(args.num_workers),
        tensorboard_dir=str(work_root / "tensorboard"),
    )


def build_command(args, model, horizon):
    command = [
        "conda",
        "run",
        "-n",
        "mamba",
        "python",
        "scripts/reproduce_gld_baseline_from_bundle.py",
        "--bundle-root",
        relative(args.bundle_root),
        "--output-root",
        relative(args.output_root),
        "--models",
        model,
        "--horizons",
        str(horizon),
        "--train-epochs",
        str(args.train_epochs),
        "--patience",
        str(args.patience),
        "--num-workers",
        str(args.num_workers),
        "--gpu",
        str(args.gpu),
    ]
    if args.overwrite:
        command.append("--overwrite")
    if args.continue_on_error:
        command.append("--continue-on-error")
    return " ".join(command)


def make_row(dataset_cfg, reproduction_config, model, horizon, params, run_info, run_dir, status, notes=""):
    paths = artifact_paths(run_dir)
    metrics = run_info.get("metrics", {})
    return {
        "dataset": dataset_cfg["slug"],
        "target": dataset_cfg["target"],
        "phase": reproduction_config["phase"],
        "model": model,
        "horizon": int(horizon),
        "term": term_for_horizon(int(horizon), dataset_cfg["term_groups"]),
        "seq_len": int(params["seq_len"]),
        "label_len": int(params["seq_len"]) // 2,
        "pred_len": int(horizon),
        "mae": metrics.get("mae", ""),
        "mse": metrics.get("mse", ""),
        "rmse": metrics.get("rmse", ""),
        "mape": metrics.get("mape", ""),
        "mspe": metrics.get("mspe", ""),
        "rmsse": metrics.get("rmsse", ""),
        "short_avg_rmse": "",
        "middle_avg_rmse": "",
        "long_avg_rmse": "",
        "overall_avg_rmse": "",
        "short_avg_mae": "",
        "middle_avg_mae": "",
        "long_avg_mae": "",
        "overall_avg_mae": "",
        "short_avg_rmsse": "",
        "middle_avg_rmsse": "",
        "long_avg_rmsse": "",
        "overall_avg_rmsse": "",
        "overall_balanced_rmsse": "",
        "study_name": reproduction_config["models"][model]["study_name"],
        "trial_number": reproduction_config["models"][model]["best_validation_replay_trial"],
        "params_json": stable_json(params),
        "setting": run_info.get("setting", ""),
        "checkpoint_path": relative(paths["checkpoint"]) if paths["checkpoint"].exists() else "",
        "metrics_path": relative(paths["metrics"]) if paths["metrics"].exists() else "",
        "pred_path": relative(paths["pred"]) if paths["pred"].exists() else "",
        "true_path": relative(paths["true"]) if paths["true"].exists() else "",
        "meta_path": relative(paths["meta"]) if paths["meta"].exists() else "",
        "visuals_dir": relative(paths["visuals_dir"]) if paths["visuals_dir"].exists() else "",
        "run_metadata": relative(paths["metadata"]) if paths["metadata"].exists() else "",
        "status": status,
        "notes": notes,
    }


def row_from_metadata(path):
    payload = load_json(path)
    return payload["summary_row"]


def enrich_summary_fields(rows, term_groups):
    rows_by_model = defaultdict(list)
    for row in rows:
        if row.get("status") == "complete":
            rows_by_model[row["model"]].append(row)

    summaries = {}
    for model, model_rows in rows_by_model.items():
        horizon_metrics = {}
        for row in model_rows:
            if all(row.get(metric) != "" for metric in METRIC_FIELDS):
                horizon_metrics[int(row["horizon"])] = {
                    metric: float(row[metric])
                    for metric in METRIC_FIELDS
                }
        if horizon_metrics:
            summaries[model] = summarize_horizon_metrics(horizon_metrics, term_groups)

    for row in rows:
        summary = summaries.get(row["model"])
        if summary is None:
            continue
        grouped = summary["grouped_metrics"]
        for metric in ("rmse", "mae", "rmsse"):
            for term in ("short", "middle", "long"):
                key = f"{term}_avg_{metric}"
                row[key] = grouped[metric].get(term, "")
            row[f"overall_avg_{metric}"] = grouped[metric]["overall"]
        row["overall_balanced_rmsse"] = summary["balanced_rmsse"]
    return rows


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def copy_configs(bundle_root, output_root):
    config_dir = bundle_root / "configs"
    out_dir = output_root / "configs"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in ("baseline_reproduction_config.json", "baseline_best_params.json"):
        src = config_dir / name
        if src.exists():
            shutil.copyfile(src, out_dir / name)


def run_one(args, dataset_cfg, reproduction_config, model, horizon, work_root, output_root):
    model_cfg = reproduction_config["models"][model]
    params = model_cfg["params"]
    stage_tag = f"trial{model_cfg['best_validation_replay_trial']}_bestfinal_h{int(horizon)}"
    setting = setting_for(dataset_cfg, reproduction_config["phase"], model, params, horizon, stage_tag)
    run_dir = artifact_dir(output_root, model, horizon)

    if artifact_complete(run_dir) and not args.overwrite:
        print(f"skip complete {model} h={horizon}: {relative(run_dir)}")
        return row_from_metadata(artifact_paths(run_dir)["metadata"])

    if args.overwrite:
        remove_if_exists(run_dir)

    for raw_dir in (
        work_root / "checkpoints" / setting,
        work_root / "results" / setting,
        work_root / "test_results" / setting,
    ):
        remove_if_exists(raw_dir)

    print(f"replay {model} h={horizon}: {setting}")
    runner = load_runner()
    cli_args = replay_cli_args(args, work_root, reproduction_config["phase"])

    old_cwd = Path.cwd()
    work_root.mkdir(parents=True, exist_ok=True)
    os.chdir(work_root)
    try:
        run_info = runner.run_horizon(
            cli_args=cli_args,
            dataset_cfg=dataset_cfg,
            model_label=model,
            params=params,
            pred_len=int(horizon),
            stage_tag=stage_tag,
            save_artifacts=True,
            eval_flag="test",
        )
    finally:
        os.chdir(old_cwd)

    archived_dir = archive_run(
        work_root=work_root,
        output_root=output_root,
        model=model,
        horizon=horizon,
        setting=run_info["setting"],
        keep_work_dirs=args.keep_work_dirs,
    )
    row = make_row(
        dataset_cfg=dataset_cfg,
        reproduction_config=reproduction_config,
        model=model,
        horizon=horizon,
        params=params,
        run_info=run_info,
        run_dir=archived_dir,
        status="complete",
    )
    row["run_metadata"] = relative(artifact_paths(archived_dir)["metadata"])
    metadata = {
        "model": model,
        "horizon": int(horizon),
        "setting": run_info["setting"],
        "stage_tag": stage_tag,
        "metrics": run_info["metrics"],
        "params": params,
        "source_study": {
            "study_name": model_cfg["study_name"],
            "trial_number": model_cfg["best_validation_replay_trial"],
            "validation_balanced_rmsse": model_cfg["best_validation_replay_balanced_rmsse"],
            "published_test_balanced_rmsse": model_cfg["final_test_balanced_rmsse"],
        },
        "artifacts": {
            "checkpoint": row["checkpoint_path"],
            "metrics": row["metrics_path"],
            "pred": row["pred_path"],
            "true": row["true_path"],
            "meta": row["meta_path"],
            "visuals_dir": row["visuals_dir"],
        },
        "replay_command": build_command(args, model, horizon),
        "summary_row": row,
    }
    write_json(artifact_paths(archived_dir)["metadata"], metadata)
    return row


def main():
    args = parse_args()
    bundle_root = args.bundle_root.resolve()
    output_root = args.output_root.resolve()
    reproduction_config = load_json(bundle_root / "configs" / "baseline_reproduction_config.json")
    best_params = load_json(bundle_root / "configs" / "baseline_best_params.json")
    dataset_cfg = make_dataset_cfg(reproduction_config)
    models, horizons = selected_items(reproduction_config, best_params, args)

    print(f"bundle: {relative(bundle_root)}")
    print(f"output: {relative(output_root)}")
    print(f"models: {' '.join(models)}")
    print(f"horizons: {' '.join(str(horizon) for horizon in horizons)}")

    if args.dry_run:
        for model in models:
            params = reproduction_config["models"][model]["params"]
            trial = reproduction_config["models"][model]["best_validation_replay_trial"]
            for horizon in horizons:
                stage_tag = f"trial{trial}_bestfinal_h{int(horizon)}"
                setting = setting_for(dataset_cfg, reproduction_config["phase"], model, params, horizon, stage_tag)
                print(f"dry-run {model} h={horizon}: {setting}")
        return

    require_cuda()
    copy_configs(bundle_root, output_root)
    work_root = output_root / "_work"
    rows = []
    failures = []

    for model in models:
        for horizon in horizons:
            try:
                rows.append(
                    run_one(
                        args=args,
                        dataset_cfg=dataset_cfg,
                        reproduction_config=reproduction_config,
                        model=model,
                        horizon=horizon,
                        work_root=work_root,
                        output_root=output_root,
                    )
                )
            except Exception as exc:
                message = f"{model} h={horizon}: {exc}"
                failures.append(message)
                print(f"failed {message}")
                if not args.continue_on_error:
                    raise
                params = reproduction_config["models"][model]["params"]
                rows.append(
                    make_row(
                        dataset_cfg=dataset_cfg,
                        reproduction_config=reproduction_config,
                        model=model,
                        horizon=horizon,
                        params=params,
                        run_info={},
                        run_dir=artifact_dir(output_root, model, horizon),
                        status="failed",
                        notes=str(exc),
                    )
                )

    rows = enrich_summary_fields(rows, dataset_cfg["term_groups"])
    rows.sort(key=lambda row: (row["model"], int(row["horizon"])))

    summary_dir = output_root / "summary"
    summary_csv = summary_dir / "reproduced_baseline_best.csv"
    write_csv(summary_csv, rows, SETTING_FIELDNAMES)

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "bundle_root": relative(bundle_root),
        "output_root": relative(output_root),
        "dataset": dataset_cfg["slug"],
        "phase": reproduction_config["phase"],
        "models": models,
        "horizons": horizons,
        "train_epochs": args.train_epochs,
        "patience": args.patience,
        "seed": args.seed,
        "requires_cuda": True,
        "rows": len(rows),
        "failures": failures,
        "summary_csv": relative(summary_csv),
        "artifacts_root": relative(output_root / "artifacts"),
        "configs": [
            relative(output_root / "configs" / "baseline_reproduction_config.json"),
            relative(output_root / "configs" / "baseline_best_params.json"),
        ],
    }
    write_json(summary_dir / "reproduction_manifest.json", manifest)

    print(f"wrote {relative(summary_csv)}")
    print(f"wrote {relative(summary_dir / 'reproduction_manifest.json')}")
    print(f"wrote {relative(output_root / 'artifacts')}")


if __name__ == "__main__":
    main()
