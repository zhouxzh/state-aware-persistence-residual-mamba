#!/usr/bin/env python
"""Validation-select among immutable V3 M0/M1/M2/M3 forecast families."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("SAPR_MAMBA_VERSION", "v3")

from experiments.sapr_mamba.run import _real_bundle, _real_panel_definition, resolve_device, set_seed
from model.StateAwarePersistenceResidualMamba import build_model
from scripts.sapr_mamba_v4 import _collect, _to_raw
from utils.sapr_mamba.analysis import artifact_entry, summarize_predictions, write_csv
from utils.sapr_mamba.calibration import select_validation_candidate
from utils.sapr_mamba.features import FEATURE_NAMES
from utils.sapr_mamba.io import atomic_write_json, load_configs, utc_now, write_task_manifest


V3_RESULTS = REPO_ROOT / "results" / "sapr_mamba_v3" / "real"
DEFAULT_RESULTS = REPO_ROOT / "results" / "sapr_mamba_v5" / "real"
DEFAULT_PROTOCOL = REPO_ROOT / "configs" / "sapr_mamba_v5" / "protocol.json"
ACTIVE_RESULTS = DEFAULT_RESULTS
ACTIVE_PROTOCOL = DEFAULT_PROTOCOL


def _protocol() -> dict:
    return json.loads(ACTIVE_PROTOCOL.read_text(encoding="utf-8"))


def _model(panel: str, model_id: str, seed: int, device: torch.device) -> torch.nn.Module:
    configs = load_configs()
    period, input_length, horizons = _real_panel_definition(panel)
    model = build_model(model_id, max(horizons), len(FEATURE_NAMES), configs["model_spec"], input_length, period).to(device)
    if model_id not in {"M0", "SeasonalNaive", "Drift"}:
        checkpoint = V3_RESULTS / panel / f"{model_id}_seed{seed}" / "checkpoint.pt"
        if not checkpoint.is_file():
            raise FileNotFoundError(f"missing immutable V3 checkpoint: {checkpoint}")
        model.load_state_dict(torch.load(checkpoint, map_location=device, weights_only=True)["model"])
    return model


def run_task(panel: str, seed: int) -> dict:
    protocol = _protocol()
    candidates = tuple(protocol["candidates"])
    model_label = str(protocol["new_model"])
    output = ACTIVE_RESULTS / panel / f"{model_label}_seed{seed}"
    manifest = output / "task_manifest.json"
    if manifest.is_file():
        existing = json.loads(manifest.read_text(encoding="utf-8"))
        if existing.get("status") == "complete":
            return existing
    configs = load_configs()
    device = resolve_device(str(configs["protocol"]["training"]["device"]))
    set_seed(seed)
    _, _, horizons = _real_panel_definition(panel)
    horizon = max(horizons)
    validation, _ = _real_bundle(panel, "validation", horizon)
    test, metadata = _real_bundle(panel, "test", horizon)
    started = utc_now()
    try:
        validation_outputs = {name: _collect(_model(panel, name, seed, device), validation, device, seed) for name in candidates}
        chosen, audit = select_validation_candidate(
            {name: arrays["forecast"] for name, arrays in validation_outputs.items()},
            validation_outputs["M0"]["target"], validation_outputs["M0"]["series_index"], candidates,
        )
        test_outputs = {name: _collect(_model(panel, name, seed, device), test, device, seed) for name in candidates}
        reference = test_outputs["M0"]
        test_series = {int(value) for value in np.unique(reference["series_index"])}
        missing_validation_series = sorted(test_series - set(chosen))
        for series_index in missing_validation_series:
            chosen[series_index] = "M0"
            audit.append({
                "series_index": series_index,
                "validation_origins": 0,
                "selected_model": "M0",
                **{f"validation_mse_{name}": float("nan") for name in candidates},
            })
        selected_names = np.asarray([chosen[int(value)] for value in reference["series_index"]], dtype=object)
        prediction = np.empty_like(reference["forecast"])
        gate = np.empty_like(reference["gate"])
        for name in candidates:
            mask = selected_names == name
            prediction[mask] = test_outputs[name]["forecast"][mask]
            gate[mask] = test_outputs[name]["gate"][mask]
        raw = _to_raw(reference, metadata)
        means = np.asarray([float(item["training_mean"]) for item in metadata], dtype=np.float32)[reference["series_index"]][:, None]
        stds = np.asarray([float(item["training_std"]) for item in metadata], dtype=np.float32)[reference["series_index"]][:, None]
        raw_prediction = prediction * stds + means
        raw_residual = raw_prediction - raw["baseline"]
        metrics = summarize_predictions(
            prediction=raw_prediction, target=raw["target"], state=reference["state"], gate=gate,
            residual=raw_residual, change_scores=reference["change_score"], series_indices=reference["series_index"],
            series_metadata=metadata, model=model_label, seed=seed, horizons=horizons, dataset=panel,
        )
        output.mkdir(parents=True, exist_ok=True)
        selection_path = output / "validation_model_selection.csv"
        columns = ("series_index", "validation_origins", "selected_model", *[f"validation_mse_{name}" for name in candidates])
        write_csv(selection_path, audit, columns)
        metrics_path = output / "metrics.csv"
        write_csv(metrics_path, metrics)
        prediction_path = output / "predictions.npz"
        with prediction_path.with_name(f".{prediction_path.name}.tmp").open("wb") as handle:
            np.savez_compressed(handle, prediction=raw_prediction, target=raw["target"], baseline=raw["baseline"], residual=raw_residual,
                                selected_model=selected_names, state=reference["state"], gate=gate, change_score=reference["change_score"],
                                series_index=reference["series_index"], origin=reference["origin"])
        prediction_path.with_name(f".{prediction_path.name}.tmp").replace(prediction_path)
        payload = {
            "status": "complete", "started_at": started, "finished_at": utc_now(), "panel": panel, "model": model_label, "seed": seed,
            "selection_split": "validation", "selection_candidates": list(candidates), "test_targets_used_for_selection": False,
            "no_validation_model_fallback": "M0_persistence", "no_validation_model_series": len(missing_validation_series),
            "artifacts": {"metrics": artifact_entry(metrics_path), "selection": artifact_entry(selection_path), "prediction_archive": artifact_entry(prediction_path)},
        }
    except Exception as exc:
        payload = {"status": "failed", "started_at": started, "finished_at": utc_now(), "panel": panel, "model": model_label, "seed": seed, "error": repr(exc)}
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
    rows = []
    model_label = str(protocol["new_model"])
    for path in sorted(ACTIVE_RESULTS.glob(f"*/{model_label}_seed*/metrics.csv")):
        with path.open(encoding="utf-8", newline="") as handle:
            rows.extend(csv.DictReader(handle))
    if rows:
        write_csv(ACTIVE_RESULTS / "metrics_all.csv", rows)
    write_csv(ACTIVE_RESULTS / "failures.csv", failures, ("panel", "seed", "error"))
    payload = {"study": str(protocol["protocol_version"]), "completed": len(completed), "failures": failures, "panels": selected_panels, "seeds": selected_seeds, "finished_at": utc_now()}
    atomic_write_json(ACTIVE_RESULTS / "campaign_manifest.json", payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panels", nargs="+", default=None)
    parser.add_argument("--seeds", nargs="+", type=int, default=None)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_RESULTS)
    args = parser.parse_args()
    global ACTIVE_PROTOCOL, ACTIVE_RESULTS
    ACTIVE_PROTOCOL = args.protocol.resolve()
    ACTIVE_RESULTS = args.output_root.resolve()
    run(args.panels, args.seeds)


if __name__ == "__main__":
    main()
