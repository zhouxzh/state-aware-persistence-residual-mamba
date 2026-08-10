#!/usr/bin/env python
"""Train once, then reproduce publication forecasts from retained checkpoints.

The canonical financial evaluation intentionally discards weights by default.  This
entry point provides an explicit, auditable opt-in for retaining the selected Mamba
candidate weights and replaying their test forecasts without retraining.  Historical
baseline predictions remain available through the frozen metric snapshots; this
checkpoint bundle covers the trainable publication candidates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from argparse import Namespace
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.run_evaluation import build_base_args, format_setting, set_global_seed
from scripts.financial.common import atomic_write_json, sha256_path
import scripts.run_financial_reference_evaluation as publication
from scripts.registry import public_name, runtime_model_name


DEFAULT_OUTPUT_ROOT = REPO_ROOT / "results" / "financial_reference_evaluation_v1"
DEFAULT_CHECKPOINT_ROOT = REPO_ROOT / "checkpoints" / "financial_reference_evaluation_v1"
MANIFEST_NAME = "checkpoint_manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_summary(output_root: Path) -> dict:
    path = output_root / "final_runs.json"
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing {path}; run this command with --mode train first"
        )
    summary = json.loads(path.read_text(encoding="utf-8"))
    if not summary.get("runs"):
        raise RuntimeError(f"No completed candidate runs found in {path}")
    return summary


def build_manifest(output_root: Path, checkpoint_root: Path) -> dict:
    summary = load_summary(output_root)
    entries = []
    missing = []
    for key, record in sorted(summary.get("runs", {}).items()):
        if record.get("status") != "complete":
            continue
        task = record["dataset"]
        model_id = record["model_id"]
        seed = int(record["seed"])
        for horizon_text, setting in sorted(
            record.get("settings", {}).items(), key=lambda item: int(item[0])
        ):
            horizon = int(horizon_text)
            checkpoint = checkpoint_root / setting / "checkpoint.pth"
            meta = output_root / "runs" / setting / "meta.json"
            if not checkpoint.is_file():
                missing.append(f"{task}|{model_id}|{seed}|h{horizon}")
                continue
            entries.append(
                {
                    "dataset": task,
                    "model_id": model_id,
                    "public_name": public_name(model_id),
                    "runtime_model": runtime_model_name(model_id),
                    "seed": seed,
                    "horizon": horizon,
                    "setting": setting,
                    "checkpoint": str(checkpoint.relative_to(checkpoint_root)),
                    "checkpoint_bytes": checkpoint.stat().st_size,
                    "checkpoint_sha256": sha256_file(checkpoint),
                    "run_metadata": str(meta.relative_to(output_root)),
                    "parameter_sha256": record.get("selection_source_sha256", ""),
                    "params": record.get("params", {}),
                }
            )
    manifest = {
        "manifest_version": "checkpoint_replay_v1",
        "protocol_version": summary.get("protocol_version", ""),
        "output_root": str(output_root.relative_to(REPO_ROOT)),
        "checkpoint_root": str(checkpoint_root.relative_to(REPO_ROOT)),
        "entries": entries,
        "missing": missing,
        "expected_entries": len(summary.get("runs", {})) * 6,
    }
    atomic_write_json(checkpoint_root / MANIFEST_NAME, manifest)
    return manifest


def train(args: argparse.Namespace) -> dict:
    args.output_root.mkdir(parents=True, exist_ok=True)
    args.checkpoint_root.mkdir(parents=True, exist_ok=True)
    runner = Namespace(
        stage="final",
        config=args.config,
        output_root=args.output_root,
        checkpoint_root=args.checkpoint_root,
        tasks=args.tasks,
        candidates=args.candidates,
        seeds=args.seeds,
        gpu=args.gpu,
        num_workers=args.num_workers,
        train_epochs=args.train_epochs,
        patience=args.patience,
        max_runs=args.max_runs,
        unlock_retrospective_test=True,
        retain_final_checkpoints=True,
    )
    outcome = publication.run(runner)
    manifest = build_manifest(args.output_root, args.checkpoint_root)
    outcome.update(
        checkpoint_entries=len(manifest["entries"]),
        missing_checkpoints=len(manifest["missing"]),
        checkpoint_manifest=str((args.checkpoint_root / MANIFEST_NAME).relative_to(REPO_ROOT)),
    )
    return outcome


def replay(args: argparse.Namespace) -> dict:
    manifest_path = args.checkpoint_root / MANIFEST_NAME
    if not manifest_path.is_file():
        manifest = build_manifest(args.output_root, args.checkpoint_root)
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("missing"):
        raise RuntimeError(
            "Checkpoint manifest has missing weights; run --mode train first: "
            + ", ".join(manifest["missing"][:5])
        )
    config = publication.load_config(args.config)
    manifest_path_data = REPO_ROOT / config["base_protocol"]["training_manifest"]
    manifest_data = json.loads(manifest_path_data.read_text(encoding="utf-8"))
    selected_tasks = publication.selected(args.tasks, sorted(manifest_data), "task IDs")
    selected_models = publication.selected(
        args.candidates, list(config["candidates"]), "candidate IDs"
    )
    entries = [
        entry for entry in manifest["entries"]
        if entry["dataset"] in selected_tasks and entry["model_id"] in selected_models
    ]
    replay_root = args.replay_output_root.resolve()
    replay_root.mkdir(parents=True, exist_ok=True)
    rows = []
    import torch
    from experiments.exp_long_term_forecasting import Exp_Long_Term_Forecast

    for entry in entries:
        checkpoint = args.checkpoint_root / entry["checkpoint"]
        if not checkpoint.is_file() or sha256_file(checkpoint) != entry["checkpoint_sha256"]:
            raise RuntimeError(f"Checkpoint hash mismatch: {checkpoint}")
        dataset_cfg = publication.load_dataset_manifest(manifest_path_data, entry["dataset"], REPO_ROOT)
        cli = Namespace(
            phase="pub",
            seed=entry["seed"],
            cpu=False,
            require_cuda=True,
            gpu=args.gpu,
            num_workers=args.num_workers,
            train_epochs=1,
            patience=1,
            checkpoints=str(args.checkpoint_root),
            results_root=str(replay_root / "runs"),
            tensorboard_dir=str(replay_root / "tensorboard"),
            discard_final_checkpoints=False,
        )
        set_global_seed(entry["seed"])
        model = runtime_model_name(entry["model_id"])
        model_args = build_base_args(
            cli, dataset_cfg, model, entry["params"], entry["horizon"],
            f"replay_{entry['model_id']}_{entry['seed']}_h{entry['horizon']}",
        )
        setting = entry["setting"]
        exp = Exp_Long_Term_Forecast(model_args)
        try:
            evaluation = exp.evaluate(
                setting=setting,
                load_checkpoint=True,
                save_artifacts=True,
                save_visuals=False,
                write_result_log=False,
                write_tensorboard=False,
                flag="test",
            )
        finally:
            writer = getattr(exp, "writer", None)
            if writer is not None:
                writer.close()
        output_dir = replay_root / "runs" / setting
        metadata_path = output_dir / "meta.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata.update(
            replay_of=str(checkpoint.relative_to(REPO_ROOT)),
            checkpoint_sha256=entry["checkpoint_sha256"],
            replay_protocol_version=manifest["protocol_version"],
        )
        atomic_write_json(metadata_path, metadata)
        rows.append(
            {
                "dataset": entry["dataset"],
                "model_id": entry["model_id"],
                "seed": entry["seed"],
                "horizon": entry["horizon"],
                "setting": setting,
                "mae": float(evaluation["mae"]),
                "mse": float(evaluation["mse"]),
                "rmse": float(evaluation["rmse"]),
                "rmsse": float(evaluation["rmsse"]),
            }
        )
        del exp
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    atomic_write_json(replay_root / "replay_summary.json", {
        "manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "entries": rows,
    })
    return {"status": "replayed", "replayed_entries": len(rows), "output": str(replay_root.relative_to(REPO_ROOT))}


def verify(args: argparse.Namespace) -> dict:
    summary_path = args.output_root / "final_runs.json"
    if not summary_path.is_file():
        return {
            "status": "final_training_not_run",
            "checkpoint_entries": 0,
            "missing_checkpoints": 0,
            "summary": str(summary_path.relative_to(REPO_ROOT)),
            "message": "No protocol-matched final checkpoints exist yet; run --mode train.",
        }
    manifest = build_manifest(args.output_root, args.checkpoint_root)
    return {
        "status": "verified" if not manifest["missing"] else "missing_checkpoints",
        "checkpoint_entries": len(manifest["entries"]),
        "missing_checkpoints": len(manifest["missing"]),
        "manifest": str((args.checkpoint_root / MANIFEST_NAME).relative_to(REPO_ROOT)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["train", "replay", "verify"], required=True)
    parser.add_argument("--config", type=Path, default=publication.PUBLICATION_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--checkpoint-root", type=Path, default=DEFAULT_CHECKPOINT_ROOT)
    parser.add_argument("--replay-output-root", type=Path, default=DEFAULT_OUTPUT_ROOT / "checkpoint_replay")
    parser.add_argument("--tasks", nargs="+", default=["ALL"])
    parser.add_argument("--candidates", nargs="+", default=["ALL"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[2023, 2024, 2025, 2026, 2027])
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--train-epochs", type=int, default=10)
    parser.add_argument("--patience", type=int, default=3)
    parser.add_argument("--max-runs", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.config = args.config.resolve()
    args.output_root = args.output_root.resolve()
    args.checkpoint_root = args.checkpoint_root.resolve()
    args.replay_output_root = args.replay_output_root.resolve()
    outcome = {"train": train, "replay": replay, "verify": verify}[args.mode](args)
    print(json.dumps(outcome, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"Checkpoint workflow blocked: {exc}") from None
