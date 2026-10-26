#!/usr/bin/env python
"""Run V4 validation-calibrated residual shrinkage from immutable V3 M3 checkpoints."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("SAPR_MAMBA_VERSION", "v3")

from experiments.sapr_mamba.run import _real_bundle, _real_panel_definition, _to_device, resolve_device, set_seed
from model.StateAwarePersistenceResidualMamba import build_model
from utils.sapr_mamba.analysis import artifact_entry, summarize_predictions, write_csv
from utils.sapr_mamba.calibration import select_residual_shrinkage
from utils.sapr_mamba.features import FEATURE_NAMES
from utils.sapr_mamba.io import atomic_write_json, load_configs, sha256_path, utc_now, write_task_manifest


V3_RESULTS = REPO_ROOT / "results" / "sapr_mamba_v3" / "real"
V4_RESULTS = REPO_ROOT / "results" / "sapr_mamba_v4"
V4_CONFIG = REPO_ROOT / "configs" / "sapr_mamba_v4" / "protocol.json"


def _protocol() -> dict:
    return json.loads(V4_CONFIG.read_text(encoding="utf-8"))


def _collect(model: torch.nn.Module, dataset, device: torch.device, seed: int) -> dict[str, np.ndarray]:
    loader = DataLoader(dataset, batch_size=128, shuffle=False, num_workers=0, pin_memory=True)
    parts: dict[str, list[np.ndarray]] = {key: [] for key in ("baseline", "forecast", "target", "gate", "change_score", "state", "series_index", "origin")}
    model.eval()
    with torch.no_grad():
        for batch in loader:
            x, y, phi = _to_device(batch, device)
            result = model(x, phi)
            parts["baseline"].append(x[:, -1:].expand_as(y).detach().cpu().numpy())
            parts["forecast"].append(result["forecast"].detach().cpu().numpy())
            parts["target"].append(y.detach().cpu().numpy())
            parts["gate"].append(result["gate"].detach().cpu().numpy())
            for key in ("change_score", "state", "series_index", "origin"):
                parts[key].append(batch[key].numpy())
    return {key: np.concatenate(value) for key, value in parts.items()}


def _to_raw(arrays: dict[str, np.ndarray], metadata: list[dict]) -> dict[str, np.ndarray]:
    indices = arrays["series_index"]
    means = np.asarray([float(item["training_mean"]) for item in metadata], dtype=np.float32)[indices, None]
    stds = np.asarray([float(item["training_std"]) for item in metadata], dtype=np.float32)[indices, None]
    result = dict(arrays)
    for key in ("baseline", "forecast", "target"):
        result[key] = arrays[key] * stds + means
    return result


def run_task(panel: str, seed: int) -> dict:
    protocol = _protocol()
    output = V4_RESULTS / "real" / panel / f"M4-validation-shrinkage_seed{seed}"
    manifest = output / "task_manifest.json"
    if manifest.is_file():
        existing = json.loads(manifest.read_text(encoding="utf-8"))
        if existing.get("status") == "complete":
            return existing
    configs = load_configs()
    specification = configs["model_spec"]
    _, input_length, horizons = _real_panel_definition(panel)
    period, _, _ = _real_panel_definition(panel)
    horizon = max(horizons)
    checkpoint = V3_RESULTS / panel / f"M3_seed{seed}" / "checkpoint.pt"
    if not checkpoint.is_file():
        raise FileNotFoundError(f"missing immutable V3 M3 checkpoint: {checkpoint}")
    device = resolve_device(str(configs["protocol"]["training"]["device"]))
    set_seed(seed)
    validation, _ = _real_bundle(panel, "validation", horizon)
    test, metadata = _real_bundle(panel, "test", horizon)
    model = build_model("M3", horizon, len(FEATURE_NAMES), specification, input_length, period).to(device)
    model.load_state_dict(torch.load(checkpoint, map_location=device, weights_only=True)["model"])
    started = utc_now()
    try:
        validation_arrays = _collect(model, validation, device, seed)
        candidates = tuple(float(value) for value in protocol["shrinkage_candidates"])
        alphas, audit = select_residual_shrinkage(
            validation_arrays["baseline"], validation_arrays["forecast"], validation_arrays["target"],
            validation_arrays["series_index"], candidates,
        )
        test_arrays = _collect(model, test, device, seed)
        test_series = {int(value) for value in np.unique(test_arrays["series_index"])}
        missing_validation_series = sorted(test_series - set(alphas))
        # A sequence with no eligible validation origin cannot receive a
        # learned calibration. Use the predeclared conservative fallback,
        # persistence (alpha=0), without inspecting its test targets.
        for series_index in missing_validation_series:
            alphas[series_index] = 0.0
            audit.append({
                "series_index": series_index,
                "validation_origins": 0,
                "selected_alpha": 0.0,
                "selected_validation_mse": float("nan"),
                "persistence_validation_mse": float("nan"),
                "unshrunk_validation_mse": float("nan"),
            })
        alpha = np.asarray([alphas[int(value)] for value in test_arrays["series_index"]], dtype=np.float32)[:, None]
        residual = test_arrays["forecast"] - test_arrays["baseline"]
        adjusted = test_arrays["baseline"] + alpha * residual
        raw = _to_raw(test_arrays, metadata)
        raw_prediction = raw["baseline"] + alpha * (raw["forecast"] - raw["baseline"])
        raw_residual = raw_prediction - raw["baseline"]
        metrics = summarize_predictions(
            prediction=raw_prediction, target=raw["target"], state=test_arrays["state"],
            gate=test_arrays["gate"] * alpha, residual=raw_residual, change_scores=test_arrays["change_score"],
            series_indices=test_arrays["series_index"], series_metadata=metadata,
            model="M4-validation-shrinkage", seed=seed, horizons=horizons, dataset=panel,
        )
        output.mkdir(parents=True, exist_ok=True)
        selection_path = output / "validation_shrinkage.csv"
        write_csv(selection_path, audit, ("series_index", "validation_origins", "selected_alpha", "selected_validation_mse", "persistence_validation_mse", "unshrunk_validation_mse"))
        metrics_path = output / "metrics.csv"
        write_csv(metrics_path, metrics)
        prediction_path = output / "predictions.npz"
        with prediction_path.with_name(f".{prediction_path.name}.tmp").open("wb") as handle:
            np.savez_compressed(handle, prediction=raw_prediction, target=raw["target"], baseline=raw["baseline"], residual=raw_residual,
                                alpha=alpha, state=test_arrays["state"], gate=test_arrays["gate"] * alpha,
                                change_score=test_arrays["change_score"], series_index=test_arrays["series_index"], origin=test_arrays["origin"])
        prediction_path.with_name(f".{prediction_path.name}.tmp").replace(prediction_path)
        payload = {
            "status": "complete", "started_at": started, "finished_at": utc_now(), "panel": panel, "model": "M4-validation-shrinkage", "seed": seed,
            "selection_split": "validation", "selection_candidates": list(candidates), "test_targets_used_for_selection": False,
            "no_validation_alpha_fallback": "persistence_alpha_zero", "no_validation_alpha_series": len(missing_validation_series),
            "v3_checkpoint": artifact_entry(checkpoint),
            "artifacts": {"metrics": artifact_entry(metrics_path), "selection": artifact_entry(selection_path), "prediction_archive": artifact_entry(prediction_path)},
        }
    except Exception as exc:
        payload = {"status": "failed", "started_at": started, "finished_at": utc_now(), "panel": panel, "model": "M4-validation-shrinkage", "seed": seed, "error": repr(exc)}
        write_task_manifest(manifest, payload)
        raise
    write_task_manifest(manifest, payload)
    return payload


def run(panels: list[str] | None, seeds: list[int] | None) -> dict:
    protocol = _protocol()
    prepared = json.loads((REPO_ROOT / "data" / "sapr_mamba_v3" / "real" / "processed" / "prepared_manifest.json").read_text(encoding="utf-8"))
    available = [str(row["panel_id"]) for row in prepared["panels"]]
    selected_panels = available if panels is None else panels
    invalid = sorted(set(selected_panels) - set(available))
    if invalid:
        raise SystemExit(f"unknown panels: {invalid}")
    selected_seeds = [int(value) for value in (seeds or protocol["evaluation"]["seeds"])]
    completed, failures = [], []
    for panel in selected_panels:
        for seed in selected_seeds:
            try:
                completed.append(run_task(panel, seed))
            except Exception as exc:
                failures.append({"panel": panel, "seed": seed, "error": repr(exc)})
    root = V4_RESULTS / "real"
    rows = []
    for path in sorted(root.glob("*/M4-validation-shrinkage_seed*/metrics.csv")):
        with path.open(encoding="utf-8", newline="") as handle:
            rows.extend(csv.DictReader(handle))
    if rows:
        write_csv(root / "metrics_all.csv", rows)
    write_csv(root / "failures.csv", failures, ("panel", "seed", "error"))
    payload = {"study": "sapr_mamba_v4", "completed": len(completed), "failures": failures, "panels": selected_panels, "seeds": selected_seeds, "finished_at": utc_now()}
    atomic_write_json(root / "campaign_manifest.json", payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panels", nargs="+", default=None)
    parser.add_argument("--seeds", nargs="+", type=int, default=None)
    args = parser.parse_args()
    run(args.panels, args.seeds)


if __name__ == "__main__":
    main()
