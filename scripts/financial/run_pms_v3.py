#!/usr/bin/env python
"""Run the frozen, resumable PMS-Mamba V3 optimization protocol."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
import time
from argparse import Namespace
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.financial.common import atomic_write_json


DEFAULT_PROTOCOL = REPO_ROOT / "configs" / "pms_mamba_v3.json"
BASE_MANIFEST = REPO_ROOT / "data" / "financial" / "manifests" / "training_datasets.json"
RESULTS_ROOT = REPO_ROOT / "results" / "nonstationary_analysis_v3"
OPTUNA_ROOT = RESULTS_ROOT / "optuna"
HPO_RUNS_ROOT = RESULTS_ROOT / "hpo_runs"
SCREEN_ROOT = RESULTS_ROOT / "screen"
GATE_ROOT = RESULTS_ROOT / "gate"
PROFILE_ROOT = RESULTS_ROOT / "profile"
EXTERNAL_ROOT = RESULTS_ROOT / "external"
EXTERNAL_PROTOCOL = (
    REPO_ROOT
    / "reproducibility"
    / "nonstationary_analysis_v3"
    / "protocol"
    / "external_tasks.json"
)

RESULT_FIELDS = (
    "config_id", "task", "model", "seed", "horizon", "forecast_head",
    "pms_branch_mode", "parent_config", "mae", "mse", "rmse", "mape",
    "mspe", "rmsse", "runtime_seconds", "peak_gpu_memory_mb", "params_json",
    "evaluation_split", "status", "error",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage",
        choices=["preflight", "hpo", "screen", "gate", "profile", "external", "all"],
        required=True,
    )
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--base-manifest", type=Path, default=BASE_MANIFEST)
    parser.add_argument("--tasks", nargs="+", default=["ALL"])
    parser.add_argument("--config-ids", nargs="+", default=None)
    parser.add_argument("--seeds", nargs="+", type=int, default=None)
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--max-runs", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--unlock-gate", action="store_true")
    parser.add_argument("--unlock-external", action="store_true")
    return parser.parse_args()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_protocol(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("protocol_version") != "pms_mamba_v3_20260804a":
        raise ValueError(f"Unexpected V3 protocol version in {path}")
    return payload


def selected_tasks(protocol: dict, requested: list[str]) -> list[str]:
    available = list(protocol["tasks"])
    if requested == ["ALL"]:
        return available
    invalid = sorted(set(requested) - set(available))
    if invalid:
        raise ValueError(f"Unknown V3 tasks: {invalid}")
    return requested


def require_cuda() -> None:
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for V3 model optimization")


def stage_manifest(protocol: dict, protocol_path: Path, base_manifest: Path, stage: str) -> Path:
    if stage not in {"development", "merge_gate"}:
        raise ValueError(f"Unknown manifest stage: {stage}")
    base = json.loads(base_manifest.read_text(encoding="utf-8"))
    split_key = "development_splits" if stage == "development" else "merge_gate_splits"
    protocol_hash = sha256_path(protocol_path)
    for task, config in base.items():
        config["split_dates"] = dict(protocol[split_key])
        config["protocol_version"] = protocol["protocol_version"]
        config["protocol_sha256"] = protocol_hash
        config["selection_stage"] = stage
    output = RESULTS_ROOT / "manifests" / f"financial_{stage}.json"
    atomic_write_json(output, base)
    return output


def append_result(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.is_file()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(RESULT_FIELDS),
            extrasaction="ignore",
            lineterminator="\n",
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


def summarize_results(results_path: Path, output_root: Path, term_groups: dict) -> None:
    import pandas as pd

    if not results_path.is_file():
        return
    frame = pd.read_csv(results_path)
    complete = frame[frame["status"] == "complete"].copy()
    if complete.empty:
        return
    horizon_to_term = {
        int(horizon): term
        for term, horizons in term_groups.items()
        for horizon in horizons
    }
    complete["term"] = complete["horizon"].astype(int).map(horizon_to_term)
    grouping = ["config_id", "task", "model", "seed"]
    by_term = (
        complete.groupby(grouping + ["term"], as_index=False)
        .agg(
            rmsse=("rmsse", "mean"),
            rmse=("rmse", "mean"),
            mae=("mae", "mean"),
            runtime_seconds=("runtime_seconds", "sum"),
        )
    )
    pivot = by_term.pivot_table(
        index=grouping,
        columns="term",
        values="rmsse",
        aggfunc="mean",
    ).reset_index()
    for term in ("short", "middle", "long"):
        if term not in pivot:
            pivot[term] = np.nan
    pivot["balanced_rmsse"] = pivot[["short", "middle", "long"]].mean(axis=1)
    runtimes = complete.groupby(grouping, as_index=False).agg(
        runtime_seconds=("runtime_seconds", "sum")
    )
    pivot = pivot.merge(runtimes, on=grouping, how="left")
    pivot.to_csv(output_root / "run_summary.csv", index=False)
    summary = (
        pivot.groupby(["config_id", "model"], as_index=False)
        .agg(
            completed_task_seed_runs=("balanced_rmsse", "size"),
            mean_balanced_rmsse=("balanced_rmsse", "mean"),
            mean_short_rmsse=("short", "mean"),
            mean_middle_rmsse=("middle", "mean"),
            mean_long_rmsse=("long", "mean"),
            median_runtime_seconds=("runtime_seconds", "median"),
        )
        .sort_values(["mean_balanced_rmsse", "config_id"])
    )
    summary.to_csv(output_root / "config_summary.csv", index=False)


def hpo_selection_path(task: str) -> Path:
    return OPTUNA_ROOT / task / "mamba_best_params.json"


def load_hpo_params(task: str, model: str) -> dict:
    path = hpo_selection_path(task)
    if not path.is_file():
        raise RuntimeError(f"Missing V3 HPO selection: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("search_space_version", "").split("_")[0:2] != ["pms", "v3"]:
        raise RuntimeError(f"Selection is not from the V3 search space: {path}")
    return json.loads(json.dumps(payload["models"][model]["params"]))


def run_hpo(args: argparse.Namespace, protocol: dict, tasks: list[str], manifest_path: Path) -> None:
    hpo = protocol["hpo"]
    for task in tasks:
        command = [
            sys.executable,
            "scripts/optuna/run_dataset_optuna.py",
            "--dataset", task,
            "--manifest", str(manifest_path),
            "--phase", "mamba",
            "--models", *hpo["models"],
            "--trials", str(hpo["trials_per_model_task"]),
            "--top-k-replays", str(hpo["top_k_validation_replays"]),
            "--calibration-horizons", *map(str, hpo["calibration_horizons"]),
            "--full-horizons", *map(str, protocol["selection_horizons"]),
            "--seed", str(hpo["seed"]),
            "--gpu", str(args.gpu),
            "--require-cuda",
            "--train-epochs", str(hpo["train_epochs"]),
            "--patience", str(hpo["patience"]),
            "--num-workers", str(args.num_workers),
            "--study-suffix", protocol["protocol_version"],
            "--search-space-version", hpo["search_space_version"],
            "--optuna-root", str(OPTUNA_ROOT),
            "--results-root", str(HPO_RUNS_ROOT),
            "--selection-only",
            "--no-save-final-artifacts",
        ]
        print(" ".join(command), flush=True)
        if not args.dry_run:
            subprocess.run(command, cwd=REPO_ROOT, check=True)


def screen_configs(protocol: dict, requested: list[str] = None) -> list[dict]:
    configs = []
    for config_id, values in protocol["screen"]["configs"].items():
        configs.append({"config_id": config_id, "parent_config": "", **values})
    if requested is None:
        return configs
    unknown = sorted(set(requested) - {item["config_id"] for item in configs} - {"PMSV3_C3"})
    if unknown:
        raise ValueError(f"Unknown V3 screen configs: {unknown}")
    return [item for item in configs if item["config_id"] in requested]


def select_c3_parent(protocol: dict) -> dict:
    import pandas as pd

    summary_path = SCREEN_ROOT / "config_summary.csv"
    if not summary_path.is_file():
        raise RuntimeError("C3 requires completed C1/C2 summaries")
    summary = pd.read_csv(summary_path).set_index("config_id")
    required = {"PMSV3_C1", "PMSV3_C2"}
    if not required.issubset(summary.index):
        raise RuntimeError("C3 requires both PMSV3_C1 and PMSV3_C2")
    c1 = summary.loc["PMSV3_C1"]
    c2 = summary.loc["PMSV3_C2"]
    relative_gap = abs(float(c1["mean_balanced_rmsse"]) - float(c2["mean_balanced_rmsse"])) / min(
        float(c1["mean_balanced_rmsse"]), float(c2["mean_balanced_rmsse"])
    )
    if relative_gap < 0.002:
        parent = "PMSV3_C1" if c1["median_runtime_seconds"] <= c2["median_runtime_seconds"] else "PMSV3_C2"
        reason = "runtime_tiebreak"
    else:
        parent = "PMSV3_C1" if c1["mean_balanced_rmsse"] < c2["mean_balanced_rmsse"] else "PMSV3_C2"
        reason = "lower_balanced_rmsse"
    base = dict(protocol["screen"]["configs"][parent])
    base.update(protocol["screen"]["dual_resolution_candidate"])
    base.update(config_id="PMSV3_C3", parent_config=parent)
    atomic_write_json(
        SCREEN_ROOT / "c3_parent_selection.json",
        {
            "parent_config": parent,
            "reason": reason,
            "relative_score_gap": relative_gap,
            "test_targets_read": False,
            "config": base,
        },
    )
    return base


def runner_cli(args: argparse.Namespace, output_root: Path, phase: str) -> Namespace:
    return Namespace(
        phase=phase,
        seed=0,
        cpu=False,
        require_cuda=True,
        gpu=int(args.gpu),
        checkpoints=str(output_root / "checkpoints"),
        results_root=str(output_root / "runs"),
        tensorboard_dir=str(output_root / "tensorboard"),
        train_epochs=10,
        patience=3,
        num_workers=int(args.num_workers),
        discard_final_checkpoints=True,
    )


def execute_matrix(
    args: argparse.Namespace,
    protocol: dict,
    tasks: list[str],
    manifest_path: Path,
    configs: list[dict],
    seeds: list[int],
    output_root: Path,
    evaluation_split: str,
    fixed_train_epochs: bool = False,
) -> None:
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "optuna"))
    import run_dataset_optuna as runner

    output_root.mkdir(parents=True, exist_ok=True)
    results_path = output_root / "results.csv"
    complete = completed_keys(results_path)
    cli = runner_cli(args, output_root, phase=output_root.name)
    run_count = 0
    for config in configs:
        for task in tasks:
            dataset_cfg = runner.load_dataset_manifest(manifest_path, task, REPO_ROOT)
            model = config.get("model", "PMS_Mamba-PD")
            params = load_hpo_params(task, model)
            params.update(config.get("parameter_overrides", {}))
            if model == "PMS_Mamba-PD":
                params.update({key: value for key, value in config.items() if key not in {
                    "config_id", "parent_config", "model", "parameter_overrides", "parent_selection"
                }})
            params.update(loss="MSE", horizon_weighting="balanced")
            if fixed_train_epochs:
                params["fixed_train_epochs"] = True
            for seed in seeds:
                cli.seed = int(seed)
                for horizon in protocol["selection_horizons"]:
                    key = (config["config_id"], task, int(seed), int(horizon))
                    if key in complete:
                        continue
                    if args.max_runs and run_count >= args.max_runs:
                        summarize_results(results_path, output_root, protocol["term_groups"])
                        return
                    run_count += 1
                    row = {
                        "config_id": config["config_id"],
                        "task": task,
                        "model": model,
                        "seed": int(seed),
                        "horizon": int(horizon),
                        "forecast_head": params.get("forecast_head", "auto"),
                        "pms_branch_mode": params.get("pms_branch_mode", ""),
                        "parent_config": config.get("parent_config", ""),
                        "params_json": json.dumps(params, sort_keys=True),
                        "evaluation_split": evaluation_split,
                        "status": "failed",
                        "error": "",
                    }
                    print(
                        f"V3 {output_root.name} {config['config_id']} {task} "
                        f"seed={seed} horizon={horizon}",
                        flush=True,
                    )
                    if args.dry_run:
                        row.update(status="dry_run", runtime_seconds=0.0)
                    else:
                        started = time.perf_counter()
                        try:
                            result = runner.run_horizon(
                                cli_args=cli,
                                dataset_cfg=dataset_cfg,
                                model_label=model,
                                params=params,
                                pred_len=int(horizon),
                                stage_tag=(
                                    f"{config['config_id'].lower()}_seed{seed}_h{horizon}"
                                ),
                                save_artifacts=False,
                                eval_flag=evaluation_split,
                            )
                            row.update(result["metrics"], status="complete")
                            row["peak_gpu_memory_mb"] = result["peak_gpu_memory_mb"]
                        except Exception as exc:
                            row["error"] = f"{type(exc).__name__}: {exc}"
                            print(f"FAILED {row['error']}", flush=True)
                        row["runtime_seconds"] = time.perf_counter() - started
                    append_result(results_path, row)
                    if row["status"] == "complete":
                        complete.add(key)
    summarize_results(results_path, output_root, protocol["term_groups"])


def run_screen(
    args: argparse.Namespace,
    protocol: dict,
    tasks: list[str],
    manifest_path: Path,
) -> None:
    seeds = args.seeds or protocol["screen"]["seeds"]
    base_requested = args.config_ids
    base = screen_configs(protocol, base_requested)
    if base:
        execute_matrix(
            args, protocol, tasks, manifest_path, base, seeds, SCREEN_ROOT, "val"
        )
    wants_c3 = args.config_ids is None or "PMSV3_C3" in args.config_ids
    if wants_c3 and not args.dry_run:
        c3 = select_c3_parent(protocol)
        execute_matrix(
            args, protocol, tasks, manifest_path, [c3], seeds, SCREEN_ROOT, "val"
        )


def select_screen_candidate(protocol: dict) -> dict:
    import pandas as pd

    path = SCREEN_ROOT / "config_summary.csv"
    if not path.is_file():
        raise RuntimeError("Missing V3 screen summary")
    summary = pd.read_csv(path)
    candidates = summary[summary["config_id"].isin(["PMSV3_B1", "PMSV3_C1", "PMSV3_C2", "PMSV3_C3"])]
    if len(candidates) != 4:
        raise RuntimeError("The complete B1/C1/C2/C3 screen is required before the merge gate")
    selected_id = str(candidates.sort_values("mean_balanced_rmsse").iloc[0]["config_id"])
    if selected_id == "PMSV3_C3":
        selection = json.loads((SCREEN_ROOT / "c3_parent_selection.json").read_text())
        config = selection["config"]
    else:
        config = {"config_id": selected_id, "parent_config": "", **protocol["screen"]["configs"][selected_id]}
    return config


def strongest_non_pms(protocol: dict, tasks: list[str]) -> str:
    scores = {model: [] for model in protocol["hpo"]["models"] if model != "PMS_Mamba-PD"}
    for task in tasks:
        payload = json.loads(hpo_selection_path(task).read_text(encoding="utf-8"))
        for model in scores:
            scores[model].append(float(payload["models"][model]["best_validation_replay_balanced_rmsse"]))
    return min(scores, key=lambda model: float(np.mean(scores[model])))


def gate_configs(protocol: dict, tasks: list[str]) -> list[dict]:
    candidate = select_screen_candidate(protocol)
    strongest = strongest_non_pms(protocol, tasks)
    configs = [
        {"config_id": "PMSV3_B0", "parent_config": "", **protocol["screen"]["configs"]["PMSV3_B0"]},
        candidate,
        {"config_id": f"RETUNED_{strongest}", "model": strongest, "parent_config": ""},
    ]
    atomic_write_json(
        GATE_ROOT / "frozen_candidates.json",
        {
            "candidate": candidate,
            "strongest_non_pms_mamba": strongest,
            "development_targets_only": True,
            "merge_gate_targets_read": False,
        },
    )
    return configs


def analyze_gate(protocol: dict) -> dict:
    import pandas as pd

    candidates = json.loads((GATE_ROOT / "frozen_candidates.json").read_text())
    candidate_id = candidates["candidate"]["config_id"]
    strongest_id = f"RETUNED_{candidates['strongest_non_pms_mamba']}"
    summary = pd.read_csv(GATE_ROOT / "run_summary.csv")
    indexed = summary.set_index(["config_id", "task", "seed"])
    refs = ["PMSV3_B0", strongest_id]
    aggregate = summary.groupby("config_id")["balanced_rmsse"].mean()
    candidate_score = float(aggregate[candidate_id])
    improvements = {
        ref: float((aggregate[ref] - candidate_score) / aggregate[ref]) for ref in refs
    }
    task_means = summary.groupby(["config_id", "task"])["balanced_rmsse"].mean()
    improved_tasks = {
        ref: int(sum(
            task_means[candidate_id][task] < task_means[ref][task]
            for task in protocol["tasks"]
        ))
        for ref in refs
    }
    term_degradations = {}
    for ref in refs:
        values = {}
        for term in ("short", "middle", "long"):
            candidate_term = float(summary[summary["config_id"] == candidate_id][term].mean())
            reference_term = float(summary[summary["config_id"] == ref][term].mean())
            values[term] = (candidate_term - reference_term) / reference_term
        term_degradations[ref] = values
    rule = protocol["promotion"]
    accuracy_pass = (
        all(value >= rule["minimum_balanced_rmsse_improvement_fraction"] for value in improvements.values())
        and all(value >= rule["minimum_improved_tasks"] for value in improved_tasks.values())
        and all(
            value <= rule["maximum_term_degradation_fraction"]
            for reference in term_degradations.values()
            for value in reference.values()
        )
    )
    payload = {
        "candidate_id": candidate_id,
        "reference_ids": refs,
        "mean_balanced_rmsse": {key: float(value) for key, value in aggregate.items()},
        "improvement_fraction": improvements,
        "improved_tasks": improved_tasks,
        "term_degradation_fraction": term_degradations,
        "accuracy_pass": bool(accuracy_pass),
        "runtime_pass": None,
        "eligible_for_external": False,
        "merge_gate_targets_read": True,
        "financial_2023_2026_targets_read": False,
    }
    atomic_write_json(GATE_ROOT / "promotion_decision.json", payload)
    candidates["merge_gate_targets_read"] = True
    atomic_write_json(GATE_ROOT / "frozen_candidates.json", candidates)
    return payload


def run_gate(
    args: argparse.Namespace,
    protocol: dict,
    tasks: list[str],
    manifest_path: Path,
) -> None:
    if not args.unlock_gate and not args.dry_run:
        raise RuntimeError("Refusing to open the 2022 merge gate without --unlock-gate")
    configs = gate_configs(protocol, tasks)
    seeds = args.seeds or protocol["promotion"]["seeds"]
    execute_matrix(
        args,
        protocol,
        tasks,
        manifest_path,
        configs,
        seeds,
        GATE_ROOT,
        "val",
        fixed_train_epochs=True,
    )
    if not args.dry_run:
        decision = analyze_gate(protocol)
        print(json.dumps(decision, indent=2, sort_keys=True))


def run_profile(args: argparse.Namespace, protocol: dict, tasks: list[str], manifest_path: Path) -> None:
    import pandas as pd
    import torch

    decision_path = GATE_ROOT / "promotion_decision.json"
    if not decision_path.is_file():
        raise RuntimeError("Accuracy gate must complete before profiling")
    decision = json.loads(decision_path.read_text())
    if not decision["accuracy_pass"]:
        print("Accuracy gate failed; runtime profiling cannot promote the candidate")
        return
    frozen = json.loads((GATE_ROOT / "frozen_candidates.json").read_text())
    candidate = frozen["candidate"]
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "optuna"))
    import run_dataset_optuna as runner
    from experiments.exp_long_term_forecasting import Exp_Long_Term_Forecast

    rows = []
    profile = protocol["profiling"]
    for task in tasks:
        dataset_cfg = runner.load_dataset_manifest(manifest_path, task, REPO_ROOT)
        for horizon in protocol["selection_horizons"]:
            for label, model, params in (
                ("PMS_Mamba-V3", "PMS_Mamba-PD", load_hpo_params(task, "PMS_Mamba-PD")),
                (
                    "TimesNet",
                    "TimesNet",
                    json.loads((REPO_ROOT / "results" / "optuna" / task / "baseline_best_params.json").read_text())["models"]["TimesNet"]["params"],
                ),
            ):
                if label == "PMS_Mamba-V3":
                    params.update({key: value for key, value in candidate.items() if key not in {
                        "config_id", "parent_config", "parent_selection"
                    }})
                cli = runner_cli(args, PROFILE_ROOT, "profile")
                cli.seed = 2023
                built = runner.build_base_args(cli, dataset_cfg, model, params, horizon, "matched_profile")
                built.batch_size = int(profile["batch_size"])
                experiment = Exp_Long_Term_Forecast(built)
                model_instance = experiment.model.eval()
                x = torch.randn(
                    profile["batch_size"], built.seq_len, built.enc_in,
                    device=experiment.device,
                )
                decoder = torch.zeros(
                    profile["batch_size"], built.label_len + horizon, built.dec_in,
                    device=experiment.device,
                )
                torch.cuda.reset_peak_memory_stats()
                with torch.inference_mode():
                    for _ in range(profile["warmup_iterations"]):
                        model_instance(x, None, decoder, None)
                    torch.cuda.synchronize()
                    started = time.perf_counter()
                    for _ in range(profile["measured_iterations"]):
                        model_instance(x, None, decoder, None)
                    torch.cuda.synchronize()
                elapsed = time.perf_counter() - started
                rows.append({
                    "task": task,
                    "horizon": horizon,
                    "model": label,
                    "batch_size": profile["batch_size"],
                    "seq_len": built.seq_len,
                    "iterations": profile["measured_iterations"],
                    "latency_ms": 1000.0 * elapsed / profile["measured_iterations"],
                    "throughput_samples_per_second": (
                        profile["batch_size"] * profile["measured_iterations"] / elapsed
                    ),
                    "peak_allocated_memory_mb": torch.cuda.max_memory_allocated() / (1024 ** 2),
                })
                del experiment, model_instance, x, decoder
                torch.cuda.empty_cache()
    PROFILE_ROOT.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    frame.to_csv(PROFILE_ROOT / "matched_inference_profile.csv", index=False)
    medians = frame.groupby("model")["latency_ms"].median()
    runtime_pass = bool(medians["PMS_Mamba-V3"] < medians["TimesNet"])
    decision["runtime_pass"] = runtime_pass
    decision["eligible_for_external"] = bool(decision["accuracy_pass"] and runtime_pass)
    decision["median_inference_latency_ms"] = {
        model: float(value) for model, value in medians.items()
    }
    atomic_write_json(decision_path, decision)


def run_external(args: argparse.Namespace, protocol: dict) -> None:
    decision_path = GATE_ROOT / "promotion_decision.json"
    if not decision_path.is_file():
        raise RuntimeError("Missing promotion decision; external tests remain locked")
    decision = json.loads(decision_path.read_text())
    if not decision.get("eligible_for_external"):
        raise RuntimeError("V3 candidate has not passed both accuracy and runtime gates")
    if not args.unlock_external:
        raise RuntimeError("Refusing to open external test targets without --unlock-external")
    if not EXTERNAL_PROTOCOL.is_file():
        raise RuntimeError(f"Missing frozen external task protocol: {EXTERNAL_PROTOCOL}")
    wrapper = json.loads(EXTERNAL_PROTOCOL.read_text(encoding="utf-8"))
    if wrapper.get("protocol_sha256") != sha256_path(DEFAULT_PROTOCOL):
        raise RuntimeError("External task protocol hash does not match the V3 protocol")
    task_manifest = wrapper["tasks"]
    if not task_manifest:
        raise RuntimeError("Frozen external task protocol contains no tasks")
    flat_manifest = RESULTS_ROOT / "manifests" / "external_tasks_flat.json"
    atomic_write_json(flat_manifest, task_manifest)

    frozen = json.loads((GATE_ROOT / "frozen_candidates.json").read_text())
    recipes = freeze_external_recipes(protocol, frozen)
    execute_external_matrix(args, protocol, task_manifest, flat_manifest, recipes)


def adaptive_external_batch_size(base_batch_size: int, variable_count: int) -> int:
    return max(1, min(int(base_batch_size), 2048 // max(1, int(variable_count))))


def freeze_external_recipes(protocol: dict, frozen_gate: dict) -> dict:
    common = dict(protocol["external"]["fixed_recipes"]["mamba_common"])
    candidate = dict(common)
    candidate.update({
        key: value
        for key, value in frozen_gate["candidate"].items()
        if key not in {"config_id", "parent_config", "parent_selection"}
    })
    b0 = dict(common)
    b0.update(protocol["external"]["fixed_recipes"]["PMS_Mamba-B0"])
    strongest = frozen_gate["strongest_non_pms_mamba"]
    strongest_params = dict(common)
    if strongest == "NS_Mamba-D":
        strongest_params.update(use_adaptive_norm=0, use_decomp=1, use_shift_gate=0)
    elif strongest == "MS_Mamba-MD":
        strongest_params.update(
            ms_scales=[1, 2, 4],
            ms_fusion="mean",
            ms_use_decomp=1,
            ms_use_linear_skip=0,
        )
    recipes = {
        "PMS_Mamba-V3": {"runtime_model": "PMS_Mamba-PD", "params": candidate},
        "PMS_Mamba-B0": {"runtime_model": "PMS_Mamba-PD", "params": b0},
        "strongest_non_pms_mamba": {"runtime_model": strongest, "params": strongest_params},
        "NLinear": {
            "runtime_model": "NLinear",
            "params": dict(protocol["external"]["fixed_recipes"]["NLinear"]),
        },
        "PatchTST": {
            "runtime_model": "PatchTST",
            "params": dict(protocol["external"]["fixed_recipes"]["PatchTST"]),
        },
        "TimesNet": {
            "runtime_model": "TimesNet",
            "params": dict(protocol["external"]["fixed_recipes"]["TimesNet"]),
        },
        "Last-value": {
            "runtime_model": "__last_value__",
            "params": {"seq_len": 336, "batch_size": 32},
        },
    }
    payload = {
        "protocol_version": protocol["protocol_version"],
        "protocol_sha256": sha256_path(DEFAULT_PROTOCOL),
        "selection_source": str((GATE_ROOT / "frozen_candidates.json").relative_to(REPO_ROOT)),
        "architecture_tuning_on_external_data": False,
        "external_targets_read": False,
        "recipes": recipes,
    }
    path = EXTERNAL_ROOT / "frozen_recipes.json"
    if path.is_file():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("recipes") != recipes:
            raise RuntimeError("Frozen external recipes differ from the existing lock")
    else:
        atomic_write_json(path, payload)
    return recipes


def external_completed_keys(path: Path) -> set[tuple[str, str, int, int]]:
    if not path.is_file():
        return set()
    with path.open(newline="", encoding="utf-8") as handle:
        return {
            (row["task"], row["model"], int(row["seed"]), int(row["horizon"]))
            for row in csv.DictReader(handle)
            if row.get("status") == "complete"
        }


def append_external_result(path: Path, row: dict) -> None:
    fields = (
        "task", "physical_dataset", "input_mode", "evidence_status", "model",
        "runtime_model", "seed", "horizon", "term", "mae", "mse", "rmse",
        "rmsse", "terminal_mae", "terminal_mse", "terminal_rmse",
        "terminal_rmsse", "runtime_seconds", "peak_gpu_memory_mb", "setting",
        "params_json", "status", "error",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.is_file()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        if not exists:
            writer.writeheader()
        writer.writerow(row)
        handle.flush()


def execute_external_matrix(
    args: argparse.Namespace,
    protocol: dict,
    task_manifest: dict,
    flat_manifest: Path,
    recipes: dict,
) -> None:
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "optuna"))
    import run_dataset_optuna as runner

    result_path = EXTERNAL_ROOT / "results.csv"
    complete = external_completed_keys(result_path)
    cli = runner_cli(args, EXTERNAL_ROOT, "external_frozen")
    cli.train_epochs = int(protocol["hpo"]["train_epochs"])
    cli.patience = int(protocol["hpo"]["patience"])
    run_count = 0
    for task in sorted(task_manifest):
        config = task_manifest[task]
        dataset_cfg = runner.load_dataset_manifest(flat_manifest, task, REPO_ROOT)
        for model_label, recipe in recipes.items():
            runtime_model = recipe["runtime_model"]
            base_params = json.loads(json.dumps(recipe["params"]))
            base_params["batch_size"] = adaptive_external_batch_size(
                base_params.get("batch_size", 16), config["variable_count"]
            )
            base_params["evaluation_batch_size"] = adaptive_external_batch_size(
                32, config["variable_count"]
            )
            base_params.update(loss="MSE", horizon_weighting="balanced")
            seeds = [0] if runtime_model == "__last_value__" else protocol["external"]["seeds"]
            for seed in seeds:
                cli.seed = int(seed)
                for horizon in dataset_cfg["horizons"]:
                    key = (task, model_label, int(seed), int(horizon))
                    if key in complete:
                        continue
                    if args.max_runs and run_count >= args.max_runs:
                        summarize_external_results(result_path)
                        return
                    run_count += 1
                    row = {
                        "task": task,
                        "physical_dataset": config["physical_dataset"],
                        "input_mode": config["input_mode"],
                        "evidence_status": config["evidence_status"],
                        "model": model_label,
                        "runtime_model": runtime_model,
                        "seed": int(seed),
                        "horizon": int(horizon),
                        "term": next(
                            term for term, horizons in dataset_cfg["term_groups"].items()
                            if int(horizon) in horizons
                        ),
                        "params_json": json.dumps(base_params, sort_keys=True),
                        "status": "failed",
                        "error": "",
                    }
                    print(
                        f"EXTERNAL {task} {model_label} seed={seed} horizon={horizon}",
                        flush=True,
                    )
                    started = time.perf_counter()
                    try:
                        if runtime_model == "__last_value__":
                            result = evaluate_last_value(
                                runner,
                                cli,
                                dataset_cfg,
                                base_params,
                                int(horizon),
                                task,
                            )
                        else:
                            result = runner.run_horizon(
                                cli_args=cli,
                                dataset_cfg=dataset_cfg,
                                model_label=runtime_model,
                                params=base_params,
                                pred_len=int(horizon),
                                stage_tag=f"{task}_{model_label}_seed{seed}_h{horizon}",
                                save_artifacts=True,
                                eval_flag="test",
                                streaming=True,
                            )
                        row.update(result["metrics"], status="complete")
                        row["peak_gpu_memory_mb"] = result["peak_gpu_memory_mb"]
                        row["setting"] = result["setting"]
                    except Exception as exc:
                        row["error"] = f"{type(exc).__name__}: {exc}"
                        print(f"FAILED {row['error']}", flush=True)
                    row["runtime_seconds"] = time.perf_counter() - started
                    append_external_result(result_path, row)
                    if row["status"] == "complete":
                        complete.add(key)
    summarize_external_results(result_path)
    lock = json.loads((EXTERNAL_ROOT / "frozen_recipes.json").read_text())
    lock["external_targets_read"] = True
    atomic_write_json(EXTERNAL_ROOT / "frozen_recipes.json", lock)


def evaluate_last_value(runner, cli, dataset_cfg: dict, params: dict, horizon: int, task: str) -> dict:
    from data_provider.data_factory import data_provider

    built = runner.build_base_args(
        cli,
        dataset_cfg,
        "NLinear",
        {
            "seq_len": params["seq_len"],
            "batch_size": params["batch_size"],
            "evaluation_batch_size": params.get("evaluation_batch_size", 32),
            "learning_rate": 0.005,
        },
        horizon,
        "last_value",
    )
    train_set, _ = data_provider(built, "train")
    test_set, test_loader = data_provider(built, "test")
    insample = np.asarray(train_set.data_x, dtype=np.float64)
    if getattr(train_set, "scale", False) and built.inverse:
        insample = train_set.inverse_transform(insample)
    rmsse_scale = np.maximum(
        np.mean(np.square(insample[1:] - insample[:-1]), axis=0),
        1e-12,
    )
    totals = {"absolute": 0.0, "squared": 0.0, "scaled": 0.0, "count": 0}
    terminal = {"absolute": 0.0, "squared": 0.0, "scaled": 0.0, "count": 0}
    origin_mse = []
    origin_scaled_mse = []
    origin_terminal_mse = []
    started = time.perf_counter()
    for batch_x, batch_y, _, _ in test_loader:
        prediction = batch_x[:, -1:, :].repeat(1, horizon, 1).numpy()
        truth = batch_y[:, -horizon:, :].numpy()
        if getattr(test_set, "scale", False) and built.inverse:
            shape = prediction.shape
            prediction = test_set.inverse_transform(prediction.reshape(-1, shape[-1])).reshape(shape)
            truth = test_set.inverse_transform(truth.reshape(-1, shape[-1])).reshape(shape)
        error = prediction.astype(np.float64) - truth.astype(np.float64)
        squared = np.square(error)
        scaled = squared / rmsse_scale.reshape(1, 1, -1)
        totals["absolute"] += float(np.abs(error).sum())
        totals["squared"] += float(squared.sum())
        totals["scaled"] += float(scaled.sum())
        totals["count"] += int(error.size)
        terminal["absolute"] += float(np.abs(error[:, -1, :]).sum())
        terminal["squared"] += float(squared[:, -1, :].sum())
        terminal["scaled"] += float(scaled[:, -1, :].sum())
        terminal["count"] += int(squared[:, -1, :].size)
        origin_mse.extend(squared.mean(axis=(1, 2)).tolist())
        origin_scaled_mse.extend(scaled.mean(axis=(1, 2)).tolist())
        origin_terminal_mse.extend(squared[:, -1, :].mean(axis=1).tolist())
    mse = totals["squared"] / totals["count"]
    terminal_mse = terminal["squared"] / terminal["count"]
    metrics = {
        "mae": totals["absolute"] / totals["count"],
        "mse": mse,
        "rmse": math.sqrt(mse),
        "rmsse": math.sqrt(totals["scaled"] / totals["count"]),
        "terminal_mae": terminal["absolute"] / terminal["count"],
        "terminal_mse": terminal_mse,
        "terminal_rmse": math.sqrt(terminal_mse),
        "terminal_rmsse": math.sqrt(terminal["scaled"] / terminal["count"]),
    }
    setting = f"EXTERNAL_{task}_Last-value_h{horizon}"
    output = EXTERNAL_ROOT / "runs" / setting
    output.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output / "origin_losses.npz",
        origin_dates=np.arange(len(origin_mse)),
        path_mse=np.asarray(origin_mse, dtype=np.float64),
        path_scaled_mse=np.asarray(origin_scaled_mse, dtype=np.float64),
        terminal_mse=np.asarray(origin_terminal_mse, dtype=np.float64),
    )
    atomic_write_json(
        output / "meta.json",
        {
            "model": "Last-value",
            "task": task,
            "horizon": horizon,
            "evaluation_split": "test",
            "streaming_evaluation": True,
            "metrics": metrics,
        },
    )
    return {
        "metrics": metrics,
        "setting": setting,
        "peak_gpu_memory_mb": 0.0,
        "runtime_seconds": time.perf_counter() - started,
    }


def summarize_external_results(path: Path) -> None:
    import pandas as pd

    if not path.is_file():
        return
    frame = pd.read_csv(path)
    complete = frame[frame["status"] == "complete"].copy()
    if complete.empty:
        return
    by_term = (
        complete.groupby(
            ["evidence_status", "physical_dataset", "input_mode", "model", "seed", "term"],
            as_index=False,
        )
        .agg(rmsse=("rmsse", "mean"), rmse=("rmse", "mean"), mae=("mae", "mean"))
    )
    by_term.to_csv(EXTERNAL_ROOT / "term_summary.csv", index=False)
    task_balanced = (
        by_term.groupby(
            ["evidence_status", "physical_dataset", "input_mode", "model", "seed"],
            as_index=False,
        )
        .agg(balanced_rmsse=("rmsse", "mean"))
    )
    task_balanced.to_csv(EXTERNAL_ROOT / "task_seed_summary.csv", index=False)
    model_summary = (
        task_balanced.groupby(["evidence_status", "model"], as_index=False)
        .agg(
            mean_balanced_rmsse=("balanced_rmsse", "mean"),
            sd_balanced_rmsse=("balanced_rmsse", "std"),
            task_seed_count=("balanced_rmsse", "size"),
        )
        .sort_values(["evidence_status", "mean_balanced_rmsse"])
    )
    model_summary.to_csv(EXTERNAL_ROOT / "model_summary.csv", index=False)


def write_run_manifest(args: argparse.Namespace, protocol: dict, tasks: list[str]) -> None:
    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    path = RESULTS_ROOT / "run_manifest.json"
    payload = {
        "protocol_version": protocol["protocol_version"],
        "protocol_sha256": sha256_path(args.protocol),
        "base_manifest_sha256": sha256_path(args.base_manifest),
        "tasks": tasks,
        "gpu_budget_hours": protocol["gpu_budget_hours"],
        "financial_2023_2026_targets_read": False,
        "external_targets_read": False,
        "command_stage": args.stage,
    }
    atomic_write_json(path, payload)


def main() -> None:
    args = parse_args()
    protocol = load_protocol(args.protocol)
    tasks = selected_tasks(protocol, args.tasks)
    write_run_manifest(args, protocol, tasks)
    development_manifest = stage_manifest(
        protocol, args.protocol, args.base_manifest, "development"
    )
    gate_manifest = stage_manifest(
        protocol, args.protocol, args.base_manifest, "merge_gate"
    )
    if args.stage == "preflight":
        require_cuda()
        for task in tasks:
            if not hpo_selection_path(task).is_file():
                print(f"pending HPO: {task}")
        print("V3 preflight passed")
        return
    if not args.dry_run:
        require_cuda()
    if args.stage in {"hpo", "all"}:
        run_hpo(args, protocol, tasks, development_manifest)
    if args.stage in {"screen", "all"}:
        run_screen(args, protocol, tasks, development_manifest)
    if args.stage in {"gate", "all"}:
        run_gate(args, protocol, tasks, gate_manifest)
    if args.stage in {"profile", "all"}:
        run_profile(args, protocol, tasks, development_manifest)
    if args.stage in {"external", "all"}:
        run_external(args, protocol)


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, KeyError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"PMS-Mamba V3 blocked: {exc}") from None
