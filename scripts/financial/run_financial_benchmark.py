#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.financial.common import DEFAULT_PROTOCOL, MANIFEST_DIR, atomic_write_json, load_protocol
from scripts.optuna.run_dataset_optuna import evaluate_horizons
from utils.optuna_support import load_dataset_manifest


TRAINING_MANIFEST = MANIFEST_DIR / "training_datasets.json"
RESULTS_ROOT = REPO_ROOT / "results" / "financial_confirmatory" / "runs"
SUMMARY_PATH = REPO_ROOT / "results" / "financial_confirmatory" / "final_runs.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the frozen financial confirmatory benchmark.")
    parser.add_argument(
        "--stage",
        choices=["preflight", "smoke", "hpo", "selection", "final", "all"],
        required=True,
    )
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--manifest", type=Path, default=TRAINING_MANIFEST)
    parser.add_argument("--tasks", nargs="+", default=["ALL"])
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--unlock-test",
        action="store_true",
        help="Required explicit acknowledgement before final neural test evaluation.",
    )
    return parser.parse_args()


def require_cuda() -> None:
    import torch

    if not torch.cuda.is_available() or torch.cuda.device_count() < 1:
        raise SystemExit("CUDA is unavailable; formal financial training is blocked.")


def selected_tasks(manifest_path: Path, requested: list[str]) -> list[str]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    available = sorted(payload)
    if requested == ["ALL"]:
        return available
    invalid = sorted(set(requested) - set(available))
    if invalid:
        raise ValueError(f"Unknown task IDs: {invalid}; available={available}")
    return requested


def run_command(command: list[str], dry_run: bool) -> None:
    print(" ".join(command), flush=True)
    if not dry_run:
        subprocess.run(command, cwd=REPO_ROOT, check=True)


def run_smoke(args: argparse.Namespace, protocol: dict, tasks: list[str]) -> None:
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    runtime_names = {
        "NS_Mamba-D": "NS_Mamba",
        "MS_Mamba-MD": "MS_Mamba",
        "PMS_Mamba-PD": "PMS_Mamba",
    }
    model_options = {
        "NS_Mamba-D": ["--use_adaptive_norm", "0", "--use_decomp", "1", "--use_shift_gate", "0"],
        "MS_Mamba-MD": ["--ms_fusion", "mean", "--ms_use_decomp", "1"],
        "PMS_Mamba-PD": ["--ms_fusion", "mean", "--ms_use_decomp", "1"],
    }
    smoke_models = ("NLinear", "S_Mamba", "NS_Mamba-D", "MS_Mamba-MD", "PMS_Mamba-PD")
    for task in tasks:
        config = manifest[task]
        for model in smoke_models:
            command = [
                sys.executable,
                "run.py",
                "--is_training", "1",
                "--model_id", f"FIN_SMOKE_{task}_{model}",
                "--model", runtime_names.get(model, model),
                "--data", "custom",
                "--root_path", config["root_path"],
                "--data_path", config["data_path"],
                "--features", config["features"],
                "--target", config["target"],
                "--freq", config["freq"],
                "--checkpoints", str(REPO_ROOT / "checkpoints" / "financial_smoke"),
                "--tensorboard_dir", str(REPO_ROOT / "tensorboard" / "financial_smoke"),
                "--split_config", str(args.protocol),
                "--evaluation_split", "val",
                "--require_cuda",
                "--results_root", str(RESULTS_ROOT),
                "--seq_len", "30",
                "--label_len", "15",
                "--pred_len", "5",
                "--enc_in", str(config["enc_in"]),
                "--dec_in", str(config["dec_in"]),
                "--c_out", str(config["c_out"]),
                "--d_model", "32",
                "--d_state", "16",
                "--d_ff", "64",
                "--e_layers", "1",
                "--batch_size", "16",
                "--train_epochs", "1",
                "--patience", "1",
                "--num_workers", str(args.num_workers),
                "--seed", str(protocol["final_seeds"][0]),
                "--des", "financial_smoke",
                "--itr", "1",
            ]
            command.extend(model_options.get(model, []))
            run_command(command, args.dry_run)


def run_hpo(args: argparse.Namespace, protocol: dict, tasks: list[str]) -> None:
    baseline_models = [
        model for model in protocol["level_models"]
        if model in {"DLinear", "NLinear", "PatchTST", "TimesNet", "iTransformer"}
    ]
    mamba_models = [
        model for model in protocol["level_models"]
        if model in {"S_Mamba", "NS_Mamba-D", "MS_Mamba-MD", "PMS_Mamba-PD"}
    ]
    for task in tasks:
        for phase, models in (("baseline", baseline_models), ("mamba", mamba_models)):
            command = [
                sys.executable,
                "scripts/optuna/run_dataset_optuna.py",
                "--dataset", task,
                "--manifest", str(args.manifest),
                "--phase", phase,
                "--models", *models,
                "--trials", str(protocol["hpo"]["trials_per_model_task"]),
                "--top-k-replays", str(protocol["hpo"]["top_k_validation_replays"]),
                "--calibration-horizons", *[str(value) for value in protocol["calibration_horizons"]],
                "--full-horizons", *[str(value) for value in protocol["horizons"]],
                "--seed", str(protocol["hpo"]["sampler_seed"]),
                "--gpu", str(args.gpu),
                "--require-cuda",
                "--train-epochs", str(protocol["hpo"]["train_epochs"]),
                "--patience", str(protocol["hpo"]["patience"]),
                "--num-workers", str(args.num_workers),
                "--study-suffix", protocol["protocol_version"],
                "--results-root", str(RESULTS_ROOT),
                "--selection-only",
                "--no-save-final-artifacts",
            ]
            run_command(command, args.dry_run)


def final_cli_args(
    args: argparse.Namespace,
    protocol: dict,
    phase: str,
    seed: int,
) -> Namespace:
    return Namespace(
        phase=phase,
        seed=seed,
        cpu=False,
        require_cuda=True,
        gpu=args.gpu,
        train_epochs=protocol["hpo"]["train_epochs"],
        patience=protocol["hpo"]["patience"],
        num_workers=args.num_workers,
        tensorboard_dir="./tensorboard/financial_confirmatory",
        checkpoints="./checkpoints/financial_confirmatory",
        results_root=str(RESULTS_ROOT),
        no_save_final_artifacts=False,
        discard_final_checkpoints=True,
    )


def load_final_summary() -> dict:
    if not SUMMARY_PATH.exists():
        return {"runs": {}}
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


def require_complete_selection(protocol: dict, manifest_path: Path, tasks: list[str]) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mamba_models = {"S_Mamba", "NS_Mamba-D", "MS_Mamba-MD", "PMS_Mamba-PD"}
    for task in tasks:
        config = manifest[task]
        for phase in ("baseline", "mamba"):
            expected_models = {
                model for model in protocol["level_models"]
                if (model in mamba_models) == (phase == "mamba")
            }
            path = REPO_ROOT / "results" / "optuna" / task / f"{phase}_best_params.json"
            if not path.is_file():
                raise RuntimeError(f"Missing frozen selection file: {path}")
            selection = json.loads(path.read_text(encoding="utf-8"))
            if selection.get("dataset") != task or selection.get("phase") != phase:
                raise RuntimeError(f"Selection identity mismatch: {path}")
            if selection.get("protocol_version") != protocol["protocol_version"]:
                raise RuntimeError(f"Selection protocol mismatch: {path}")
            if selection.get("protocol_sha256") != config["protocol_sha256"]:
                raise RuntimeError(f"Selection protocol hash mismatch: {path}")
            if selection.get("data_sha256") != config["data_sha256"]:
                raise RuntimeError(f"Selection data hash mismatch: {path}")
            if list(map(int, selection.get("full_horizons", []))) != protocol["horizons"]:
                raise RuntimeError(f"Selection horizon mismatch: {path}")
            if set(selection.get("models", {})) != expected_models:
                raise RuntimeError(f"Incomplete selection model set: {path}")
            for model in expected_models:
                model_selection = selection["models"][model]
                if model_selection.get("selection_eval_flag") != "val":
                    raise RuntimeError(f"Selection did not use validation data: {task}/{model}")
                if model_selection.get("final_eval_flag") != "not_opened":
                    raise RuntimeError(f"Selection accessed test data: {task}/{model}")
                score = float(model_selection.get("best_validation_replay_balanced_rmsse", float("nan")))
                if not math.isfinite(score):
                    raise RuntimeError(f"Selection score is non-finite: {task}/{model}")


def run_final(args: argparse.Namespace, protocol: dict, tasks: list[str]) -> None:
    if args.dry_run:
        try:
            require_complete_selection(protocol, args.manifest, tasks)
        except RuntimeError as exc:
            print(f"FINAL dry-run deferred until HPO selection is complete: {exc}")
            return
    else:
        require_complete_selection(protocol, args.manifest, tasks)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    protocol_hashes = {manifest[task]["protocol_sha256"] for task in tasks}
    if len(protocol_hashes) != 1:
        raise RuntimeError("Training manifest contains inconsistent protocol hashes")
    protocol_sha256 = next(iter(protocol_hashes))
    summary_payload = load_final_summary()
    if summary_payload.get("runs") and (
        summary_payload.get("protocol_version") != protocol["protocol_version"]
        or summary_payload.get("protocol_sha256") != protocol_sha256
    ):
        raise RuntimeError("Existing final summary belongs to a different frozen protocol")
    summary_payload.update(
        protocol_version=protocol["protocol_version"],
        protocol_sha256=protocol_sha256,
        data_cutoff=protocol["data_cutoff"],
        horizons=protocol["horizons"],
        seeds=protocol["final_seeds"],
    )
    runs = summary_payload.setdefault("runs", {})
    mamba_models = {"S_Mamba", "NS_Mamba-D", "MS_Mamba-MD", "PMS_Mamba-PD"}

    for task in tasks:
        dataset_cfg = load_dataset_manifest(args.manifest, task, REPO_ROOT)
        for model in protocol["level_models"]:
            phase = "mamba" if model in mamba_models else "baseline"
            selection_path = REPO_ROOT / "results" / "optuna" / task / f"{phase}_best_params.json"
            selection = json.loads(selection_path.read_text(encoding="utf-8"))
            model_selection = selection["models"][model]
            params = model_selection["params"]

            for seed in protocol["final_seeds"]:
                run_key = f"{task}|{model}|{seed}"
                if runs.get(run_key, {}).get("status") == "complete":
                    print(f"skip complete {run_key}")
                    continue
                if args.dry_run:
                    print(f"FINAL {run_key} horizons={protocol['horizons']} params={params}")
                    continue
                cli_args = final_cli_args(args, protocol, phase, int(seed))
                metrics, aggregate, settings = evaluate_horizons(
                    cli_args=cli_args,
                    dataset_cfg=dataset_cfg,
                    model_label=model,
                    params=params,
                    horizons=protocol["horizons"],
                    stage_tag=f"confirmatory_seed{seed}",
                    save_artifacts=True,
                    eval_flag="test",
                )
                runs[run_key] = {
                    "status": "complete",
                    "dataset": task,
                    "model": model,
                    "phase": phase,
                    "seed": int(seed),
                    "params": params,
                    "per_horizon_metrics": metrics,
                    "aggregate": aggregate,
                    "settings": settings,
                }
                atomic_write_json(SUMMARY_PATH, summary_payload)


def main() -> None:
    args = parse_args()
    protocol = load_protocol(args.protocol)
    tasks = selected_tasks(args.manifest, args.tasks)
    if args.stage == "preflight":
        require_cuda()
        print("CUDA preflight passed")
        return
    if args.stage == "selection":
        require_complete_selection(protocol, args.manifest, tasks)
        print(f"Frozen validation selection passed for {len(tasks)} task(s)")
        return
    if args.stage in {"final", "all"} and not args.dry_run and not args.unlock_test:
        raise SystemExit("Refusing to open the final test split without --unlock-test")
    if not args.dry_run:
        require_cuda()
    if args.stage in {"smoke", "all"}:
        run_smoke(args, protocol, tasks)
    if args.stage in {"hpo", "all"}:
        run_hpo(args, protocol, tasks)
    if args.stage in {"final", "all"}:
        run_final(args, protocol, tasks)


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"Financial benchmark blocked: {exc}") from None
