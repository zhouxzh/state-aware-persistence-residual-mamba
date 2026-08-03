#!/usr/bin/env python
"""Run the validation-only PMS-Mamba V2 screening design.

The screen reuses the frozen V1 PMS hyperparameters for each task and varies only
the four prespecified factors. It evaluates validation origins only and is safe to
resume after interruption because each completed task/config/seed/horizon is written
to a CSV row immediately.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import sys
import time
from argparse import Namespace
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "data" / "financial" / "manifests" / "training_datasets.json"
DEFAULT_OUTPUT = REPO_ROOT / "results" / "nonstationary_analysis_v2" / "screen"
DEFAULT_PROTOCOL = REPO_ROOT / "configs" / "financial_benchmark.json"
SEEDS = (2023, 2024, 2025)
HORIZONS = (1, 5, 20, 60, 120, 252)
TASKS = (
    "financial_cross_asset_ms",
    "financial_cross_asset_s",
    "financial_crypto_ms",
    "financial_crypto_s",
    "financial_fx_ms",
    "financial_fx_s",
    "financial_yields_ms",
    "financial_yields_s",
)

RESULT_FIELDS = (
    "config_id", "task", "seed", "horizon", "residual_target", "loss",
    "ms_fusion", "horizon_weighting", "mae", "mse", "rmse", "mape",
    "mspe", "rmsse", "runtime_seconds", "status", "error",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--train-epochs", type=int, default=10)
    parser.add_argument("--patience", type=int, default=3)
    parser.add_argument("--max-runs", type=int, default=0,
                        help="Optional smoke limit; 0 runs the complete design.")
    parser.add_argument("--config-ids", nargs="+", default=None)
    parser.add_argument("--tasks", nargs="+", default=None)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_design(seed: int = 20260725) -> list[dict]:
    """Resolution-IV 2^(4-1) design with D=ABC and seeded run order."""
    rows = []
    for a, b, c in itertools.product((-1, 1), repeat=3):
        d = a * b * c
        rows.append({"a": a, "b": b, "c": c, "d": d})
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(rows))
    design = []
    for run_index in order:
        row = rows[int(run_index)]
        config_id = f"PMSV2_F{len(design) + 1:02d}"
        design.append({
            "config_id": config_id,
            "design_row": len(design) + 1,
            "generator": "D=ABC",
            "factor_a_code": row["a"],
            "factor_b_code": row["b"],
            "factor_c_code": row["c"],
            "factor_d_code": row["d"],
            "residual_target": int(row["a"] == 1),
            "loss": "SCALE_MSE" if row["b"] == 1 else "MSE",
            "ms_fusion": "gate" if row["c"] == 1 else "mean",
            "horizon_weighting": "long" if row["d"] == 1 else "balanced",
        })
    return design


def load_manifest(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    missing = sorted(set(TASKS) - set(payload))
    if missing:
        raise ValueError(f"Manifest is missing tasks: {missing}")
    return payload


def load_pms_params(task: str) -> dict:
    path = REPO_ROOT / "results" / "optuna" / task / "mamba_best_params.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    params = payload["models"]["PMS_Mamba-PD"]["params"]
    return json.loads(json.dumps(params))


def short_task_id(task: str) -> str:
    value = task.removeprefix("financial_")
    return value.replace("_", "")


def write_csv(path: Path, rows: list[dict], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(fields), extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def append_result(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.is_file()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(RESULT_FIELDS), extrasaction="ignore", lineterminator="\n"
        )
        if not exists:
            writer.writeheader()
        writer.writerow(row)
        handle.flush()


def completed_keys(path: Path) -> set[tuple[str, str, int, int]]:
    if not path.is_file():
        return set()
    with path.open(newline="", encoding="utf-8") as handle:
        return {
            (row["config_id"], row["task"], int(row["seed"]), int(row["horizon"]))
            for row in csv.DictReader(handle)
            if row.get("status") == "complete"
        }


def summarize(results_path: Path, output_root: Path) -> None:
    import pandas as pd

    if not results_path.is_file():
        return
    frame = pd.read_csv(results_path)
    complete = frame[frame["status"] == "complete"].copy()
    if complete.empty:
        return
    for field in ("horizon", "seed", "rmsse", "rmse", "mae", "mse"):
        complete[field] = pd.to_numeric(complete[field], errors="raise")
    term_map = {1: "short", 5: "short", 20: "middle", 60: "middle", 120: "long", 252: "long"}
    complete["term"] = complete["horizon"].map(term_map)
    by_run = (
        complete.groupby(["config_id", "task", "seed", "residual_target", "loss", "ms_fusion", "horizon_weighting", "term"])
        .agg(rmsse=("rmsse", "mean"), rmse=("rmse", "mean"), mae=("mae", "mean"), mse=("mse", "mean"), horizon_count=("horizon", "size"))
        .reset_index()
    )
    term_pivot = by_run.pivot_table(
        index=["config_id", "task", "seed", "residual_target", "loss", "ms_fusion", "horizon_weighting"],
        columns="term", values="rmsse", aggfunc="mean",
    ).reset_index()
    for term in ("short", "middle", "long"):
        if term not in term_pivot:
            term_pivot[term] = np.nan
    term_pivot["balanced_rmsse"] = term_pivot[["short", "middle", "long"]].mean(axis=1)
    term_pivot.to_csv(output_root / "screen_run_summary.csv", index=False)
    config_summary = (
        term_pivot.groupby(["config_id", "residual_target", "loss", "ms_fusion", "horizon_weighting"])
        .agg(
            completed_runs=("balanced_rmsse", "size"),
            mean_balanced_rmsse=("balanced_rmsse", "mean"),
            sd_balanced_rmsse=("balanced_rmsse", "std"),
            mean_short_rmsse=("short", "mean"),
            mean_middle_rmsse=("middle", "mean"),
            mean_long_rmsse=("long", "mean"),
        )
        .reset_index()
        .sort_values(["mean_balanced_rmsse", "config_id"])
    )
    config_summary.to_csv(output_root / "screen_config_summary.csv", index=False)


def main() -> None:
    args = parse_args()
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    design = build_design()
    all_config_ids = {row["config_id"] for row in design}
    requested_config_ids = set(args.config_ids or all_config_ids)
    unknown_configs = sorted(requested_config_ids - all_config_ids)
    if unknown_configs:
        raise ValueError(f"Unknown config IDs: {unknown_configs}")
    design = [row for row in design if row["config_id"] in requested_config_ids]
    tasks = args.tasks or list(TASKS)
    unknown_tasks = sorted(set(tasks) - set(TASKS))
    if unknown_tasks:
        raise ValueError(f"Unknown tasks: {unknown_tasks}")
    manifest = load_manifest(args.manifest)
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    design_path = output_root / "screen_design.csv"
    write_csv(design_path, design, tuple(design[0].keys()))
    results_path = output_root / "screen_results.csv"
    manifest_path = output_root / "screen_manifest.json"
    if not manifest_path.is_file():
        payload = {
            "stage": "validation_only",
            "protocol_version": protocol["protocol_version"],
            "protocol_sha256": sha256_path(args.protocol),
            "data_manifest": str(args.manifest.relative_to(REPO_ROOT)),
            "data_manifest_sha256": sha256_path(args.manifest),
            "design_seed": 20260725,
            "design_generator": "D=ABC",
            "factors": ["residual_target", "loss", "ms_fusion", "horizon_weighting"],
            "tasks": tasks,
            "seeds": [int(seed) for seed in args.seeds],
            "horizons": list(HORIZONS),
            "test_targets_read": False,
            "train_epochs": int(args.train_epochs),
            "patience": int(args.patience),
        }
        manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    sys.path.insert(0, str(REPO_ROOT / "scripts" / "optuna"))
    import run_dataset_optuna as runner

    cli = Namespace(
        phase="v2screen",
        seed=0,
        cpu=False,
        require_cuda=True,
        gpu=int(args.gpu),
        checkpoints=str(output_root / "checkpoints"),
        results_root=str(output_root / "runs"),
        tensorboard_dir=str(output_root / "tensorboard"),
        train_epochs=int(args.train_epochs),
        patience=int(args.patience),
        num_workers=int(args.num_workers),
        discard_final_checkpoints=True,
    )
    completed = completed_keys(results_path)
    run_count = 0
    total_runs = len(design) * len(tasks) * len(args.seeds) * len(HORIZONS)
    for config in design:
        for task in tasks:
            dataset_cfg = runner.load_dataset_manifest(args.manifest, task, REPO_ROOT)
            base_params = load_pms_params(task)
            params = dict(base_params)
            params.update({
                "residual_target": config["residual_target"],
                "loss": config["loss"],
                "ms_fusion": config["ms_fusion"],
                "horizon_weighting": config["horizon_weighting"],
            })
            for seed in args.seeds:
                cli.seed = int(seed)
                for horizon in HORIZONS:
                    key = (config["config_id"], task, int(seed), int(horizon))
                    if key in completed:
                        continue
                    if args.max_runs and run_count >= args.max_runs:
                        summarize(results_path, output_root)
                        return
                    run_count += 1
                    started = time.perf_counter()
                    row = {
                        "config_id": config["config_id"], "task": task, "seed": int(seed),
                        "horizon": int(horizon), "residual_target": config["residual_target"],
                        "loss": config["loss"], "ms_fusion": config["ms_fusion"],
                        "horizon_weighting": config["horizon_weighting"], "status": "failed", "error": "",
                    }
                    print(f"[{run_count}/{total_runs}] {config['config_id']} {task} seed={seed} h={horizon}", flush=True)
                    if args.dry_run:
                        row.update(status="dry_run", runtime_seconds=0.0)
                    else:
                        try:
                            run = runner.run_horizon(
                                cli_args=cli,
                                dataset_cfg=dataset_cfg,
                                model_label="PMS_Mamba-PD",
                                params=params,
                                pred_len=horizon,
                                stage_tag=f"{config['config_id'].lower()}_{short_task_id(task)}_{seed % 100}_{horizon}",
                                save_artifacts=False,
                                eval_flag="val",
                            )
                            row.update(run["metrics"], status="complete")
                        except Exception as exc:
                            row["error"] = f"{type(exc).__name__}: {exc}"
                            print(f"FAILED {row['error']}", flush=True)
                        row["runtime_seconds"] = time.perf_counter() - started
                    append_result(results_path, row)
                    if row["status"] == "complete":
                        completed.add(key)
    summarize(results_path, output_root)
    print(f"Validation screen complete: {results_path}")


if __name__ == "__main__":
    main()
