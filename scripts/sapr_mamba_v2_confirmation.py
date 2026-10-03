#!/usr/bin/env python
"""Independently recompute SAPR-Mamba V2 metrics and replay frozen tasks.

The confirmation pass is read-only with respect to data, predictions, and
checkpoints. It creates compact verification matrices under docs/analysis only.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("SAPR_MAMBA_VERSION", "v2")

import numpy as np
import torch

from experiments.sapr_mamba.run import _real_bundle, _real_panel_definition, _synthetic_bundle, resolve_device
from model.StateAwarePersistenceResidualMamba import build_model
from scripts.sapr_mamba_real_analysis import (
    ANALYSIS_ROOT,
    REAL_ROOT,
    expected_tasks,
    metric_rows_match,
    panel_horizons,
    panel_metadata,
    read_rows,
)
from utils.sapr_mamba.analysis import summarize_predictions, write_csv
from utils.sapr_mamba.features import FEATURE_NAMES
from utils.sapr_mamba.io import DATA_ROOT, RESULT_ROOT, atomic_write_json, load_configs, utc_now
from utils.sapr_mamba.statistical import forecast_selected
from utils.sapr_mamba.synthetic import load_split


SYNTHETIC_ROOT = RESULT_ROOT / "synthetic"


def require_v2_environment() -> None:
    if os.environ.get("SAPR_MAMBA_VERSION") != "v2":
        raise SystemExit("Set SAPR_MAMBA_VERSION=v2 explicitly before confirmation verification.")


def synthetic_metadata() -> list[dict]:
    values, roster = load_split("test")
    metadata = []
    for entry, sequence in zip(roster, values):
        metadata.append({
            **entry,
            "training_std": max(float(np.std(sequence[: int(sequence.size * 0.6)], ddof=0)), 1e-6),
        })
    return metadata


def synthetic_metric_recompute(configs: dict) -> list[dict]:
    metadata = synthetic_metadata()
    rows = []
    for model in configs["protocol"]["models"]:
        for seed in configs["protocol"]["seeds"]:
            task_root = SYNTHETIC_ROOT / f"{model}_seed{seed}"
            archive, metrics = task_root / "predictions.npz", task_root / "metrics.csv"
            passed, detail = False, "missing_archive_or_metrics"
            if archive.is_file() and metrics.is_file():
                with np.load(archive) as arrays:
                    expected = summarize_predictions(
                        prediction=arrays["prediction"], target=arrays["target"], state=arrays["state"],
                        gate=arrays["gate"], residual=arrays["residual"], change_scores=arrays["change_score"],
                        series_indices=arrays["series_index"], series_metadata=metadata, model=model, seed=int(seed),
                        horizons=configs["synthetic"]["horizons"], dataset="synthetic",
                    )
                passed, detail = metric_rows_match(expected, read_rows(metrics))
            rows.append({
                "model": model, "seed": int(seed), "metrics_recomputed": passed, "detail": detail,
                "archive": str(archive.relative_to(REPO_ROOT)),
            })
    return rows


def _batch(item: dict, device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
    return (
        torch.from_numpy(item["x"]).unsqueeze(0).to(device),
        torch.from_numpy(item["phi"]).unsqueeze(0).to(device),
    )


def _allclose_detail(actual: np.ndarray, expected: np.ndarray) -> tuple[bool, float]:
    if actual.shape != expected.shape:
        return False, float("inf")
    max_abs = float(np.max(np.abs(actual - expected))) if actual.size else 0.0
    # Checkpoints and archives were produced with CUDA float32 kernels. A 1e-4
    # absolute/relative bound admits normal replay rounding while remaining far
    # below a meaningful forecast or residual change on these raw scales.
    return bool(np.allclose(actual, expected, rtol=1e-4, atol=1e-4)), max_abs


def _neural_prediction(
    model_id: str,
    task_root: Path,
    dataset,
    archive: Path,
    specification: dict,
    horizon: int,
    input_length: int,
    period: int,
    device: torch.device,
    inverse_to_raw: bool,
    metadata: list[dict] | None,
) -> dict:
    model = build_model(model_id, horizon, len(FEATURE_NAMES), specification, input_length, period).to(device)
    checkpoint = task_root / "checkpoint.pt"
    if checkpoint.is_file():
        model.load_state_dict(torch.load(checkpoint, map_location=device, weights_only=True)["model"])
    elif model_id not in {"M0", "SeasonalNaive", "Drift"}:
        return {"passed": False, "detail": "missing_checkpoint", "max_abs": float("inf")}
    model.eval()
    item = dataset[0]
    with torch.no_grad():
        x, phi = _batch(item, device)
        output = model(x, phi)
    prediction = output["forecast"].cpu().numpy()[0]
    residual = output["residual"].cpu().numpy()[0]
    gate = output["gate"].cpu().numpy()[0]
    if inverse_to_raw:
        if metadata is None:
            raise ValueError("real replay requires panel metadata")
        metadata_row = metadata[int(item["series_index"])]
        prediction = prediction * float(metadata_row["training_std"]) + float(metadata_row["training_mean"])
        residual = residual * float(metadata_row["training_std"])
    with np.load(archive) as arrays:
        checks = [
            _allclose_detail(prediction, arrays["prediction"][0]),
            _allclose_detail(residual, arrays["residual"][0]),
            _allclose_detail(gate, arrays["gate"][0]),
        ]
    return {
        "passed": all(passed for passed, _ in checks),
        "detail": "" if all(passed for passed, _ in checks) else "forward_output_mismatch",
        "max_abs": max(max_abs for _, max_abs in checks),
        "origin": int(item["origin"]),
    }


def synthetic_forward_replay(configs: dict, device: torch.device) -> list[dict]:
    output = []
    horizon = int(configs["synthetic"]["max_horizon"])
    period = int(configs["synthetic"]["seasonal_period"])
    seed = int(configs["protocol"]["seeds"][0])
    for model in configs["protocol"]["models"]:
        shuffle_seed = seed + 9001 if model == "M3-shuffle" else None
        dataset, _ = _synthetic_bundle("test", horizon, shuffle_seed)
        task_root = SYNTHETIC_ROOT / f"{model}_seed{seed}"
        replay = _neural_prediction(
            model, task_root, dataset, task_root / "predictions.npz", configs["model_spec"], horizon,
            int(configs["synthetic"]["input_length"]), period, device, False, None,
        )
        output.append({
            "scope": "synthetic", "dataset": "synthetic", "model": model, "seed": seed,
            "covered_horizons": ";".join(map(str, configs["synthetic"]["horizons"])), **replay,
        })
    return output


def _selected_candidate(task_root: Path, series_index: int, origin: int) -> object | None:
    for row in read_rows(task_root / "selected_candidates.csv"):
        if int(row["series_index"]) == series_index and int(row["origin"]) == origin:
            candidate = row["candidate"]
            if candidate == "None":
                return None
            return ast.literal_eval(candidate) if candidate.startswith("(") else candidate
    raise RuntimeError("selected candidate is missing for the replay origin")


def _statistical_prediction(
    panel: str,
    family: str,
    task_root: Path,
    dataset,
    metadata: list[dict],
    horizon: int,
    period: int,
    selection_config: dict,
) -> dict:
    item = dataset[0]
    series_index, origin = int(item["series_index"]), int(item["origin"])
    meta = metadata[series_index]
    history = item["x"] * float(meta["training_std"]) + float(meta["training_mean"])
    candidate = _selected_candidate(task_root, series_index, origin)
    failures_path = task_root / "failures.csv"
    fallback = any(
        row["stage"] == "test_forecast" and int(row["series_index"]) == series_index and int(row["origin"]) == origin
        for row in read_rows(failures_path)
    )
    if fallback:
        prediction = np.repeat(history[-1], horizon).astype(np.float32)
    else:
        prediction = forecast_selected(history, horizon, family, candidate, selection_config, period)
    residual = prediction - history[-1]
    with np.load(task_root / "predictions.npz") as arrays:
        checks = [
            _allclose_detail(prediction, arrays["prediction"][0]),
            _allclose_detail(residual, arrays["residual"][0]),
            _allclose_detail(np.ones(horizon, dtype=np.float32), arrays["gate"][0]),
        ]
    return {
        "passed": all(passed for passed, _ in checks),
        "detail": "" if all(passed for passed, _ in checks) else "statistical_output_mismatch",
        "max_abs": max(max_abs for _, max_abs in checks),
        "origin": origin,
    }


def real_forward_replay(configs: dict, device: torch.device) -> list[dict]:
    prepared = json.loads((DATA_ROOT / "real" / "processed" / "prepared_manifest.json").read_text(encoding="utf-8"))
    protocol = configs["protocol"]
    models = [*protocol["models"], "SeasonalNaive", "Drift", "DLinear", "ETS", "ARIMA"]
    seed = int(protocol["real_seed_policy"]["single_deterministic_seed"])
    output = []
    for entry in prepared["panels"]:
        panel = str(entry["panel_id"])
        period, input_length, horizons = _real_panel_definition(panel)
        horizon = max(horizons)
        metadata = panel_metadata(panel)
        cached_datasets = {}
        for model in models:
            shuffle_seed = seed + 9001 if model == "M3-shuffle" else None
            if shuffle_seed not in cached_datasets:
                cached_datasets[shuffle_seed] = _real_bundle(panel, "test", horizon, shuffle_seed)[0]
            dataset = cached_datasets[shuffle_seed]
            task_root = REAL_ROOT / panel / f"{model}_seed{seed}"
            if model in {"ETS", "ARIMA"}:
                replay = _statistical_prediction(
                    panel, model, task_root, dataset, metadata, horizon, period,
                    protocol["context_baselines"]["statistical_selection"],
                )
            else:
                replay = _neural_prediction(
                    model, task_root, dataset, task_root / "predictions.npz", configs["model_spec"],
                    horizon, input_length, period, device, True, metadata,
                )
            output.append({
                "scope": "real", "dataset": panel, "model": model, "seed": seed,
                "covered_horizons": ";".join(map(str, horizons)), **replay,
            })
    return output


def verify() -> dict:
    require_v2_environment()
    configs = load_configs()
    device = resolve_device(str(configs["protocol"]["training"]["device"]))
    synthetic_metrics = synthetic_metric_recompute(configs)
    synthetic_replay = synthetic_forward_replay(configs, device)
    real_replay = real_forward_replay(configs, device)
    ANALYSIS_ROOT.mkdir(parents=True, exist_ok=True)
    write_csv(ANALYSIS_ROOT / "synthetic_recompute_matrix.csv", synthetic_metrics, (
        "model", "seed", "metrics_recomputed", "detail", "archive",
    ))
    replay_rows = [*synthetic_replay, *real_replay]
    write_csv(ANALYSIS_ROOT / "forward_replay_matrix.csv", replay_rows, (
        "scope", "dataset", "model", "seed", "covered_horizons", "passed", "detail", "max_abs", "origin",
    ))
    real_verification = json.loads((ANALYSIS_ROOT / "real_verification_manifest.json").read_text(encoding="utf-8"))
    failures = {
        "synthetic_metric_recompute": [row for row in synthetic_metrics if not row["metrics_recomputed"]],
        "forward_replay": [row for row in replay_rows if not row["passed"]],
        "real_metric_recompute": real_verification["metric_recompute_failures"],
    }
    summary = {
        "verified_at": utc_now(),
        "study": "sapr_mamba_v2",
        "python_executable": sys.executable,
        "conda_prefix": os.environ.get("CONDA_PREFIX", ""),
        "device": str(device),
        "synthetic_metric_tasks": len(synthetic_metrics),
        "real_metric_tasks": int(real_verification["tasks"]),
        "forward_replay_tasks": len(replay_rows),
        "failures": failures,
        "status": "verified" if not any(failures.values()) else "failed",
    }
    atomic_write_json(ANALYSIS_ROOT / "confirmation_verification_manifest.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if summary["status"] != "verified":
        raise SystemExit("Confirmation verification failed")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("verify",), default="verify")
    parser.parse_args()
    verify()


if __name__ == "__main__":
    main()
