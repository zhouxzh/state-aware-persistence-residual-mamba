#!/usr/bin/env python
"""Train V7 Traffic confirmation candidates and validate-select them per series."""

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
os.environ.setdefault("SAPR_MAMBA_VERSION", "v7")

from experiments.sapr_mamba.run import _real_bundle, _real_panel_definition, resolve_device, set_seed, train_model
from model.StateAwarePersistenceResidualMamba import build_model
from scripts.sapr_mamba_v4 import _collect, _to_raw
from utils.sapr_mamba.analysis import artifact_entry, summarize_predictions, write_csv
from utils.sapr_mamba.calibration import select_validation_candidate
from utils.sapr_mamba.features import FEATURE_NAMES
from utils.sapr_mamba.io import DATA_ROOT, RESULT_ROOT, atomic_write_json, load_configs, utc_now, write_task_manifest


DEFAULT_PROTOCOL = REPO_ROOT / "configs" / "sapr_mamba_v7" / "confirmation_protocol.json"
ACTIVE_PROTOCOL = DEFAULT_PROTOCOL
ACTIVE_PANEL = "traffic_hourly"


def protocol() -> dict:
    return json.loads(ACTIVE_PROTOCOL.read_text(encoding="utf-8"))


def freeze_protocol() -> dict:
    cfg = protocol()
    source_manifest = DATA_ROOT / "real" / "external_confirmation_manifest.json"
    if not source_manifest.is_file():
        raise RuntimeError("prepare the V7 Traffic source before freezing the protocol")
    from utils.sapr_mamba.io import code_hashes, git_state, sha256_path

    payload = {
        "protocol": cfg,
        "frozen_at": utc_now(),
        "source_manifest": str(source_manifest.relative_to(REPO_ROOT)),
        "source_manifest_sha256": sha256_path(source_manifest),
        "code_hashes": code_hashes(),
        "git": git_state(),
    }
    path = ACTIVE_PROTOCOL.with_name("confirmation_protocol.lock.json")
    if path.is_file():
        prior = json.loads(path.read_text(encoding="utf-8"))
        comparable = {key: value for key, value in payload.items() if key not in {"frozen_at", "git"}}
        old = {key: value for key, value in prior.items() if key not in {"frozen_at", "git"}}
        if comparable != old:
            raise RuntimeError("refusing_to_overwrite_v7_confirmation_protocol_lock")
    else:
        atomic_write_json(path, payload)
    print(json.dumps({"path": str(path.relative_to(REPO_ROOT)), "source_manifest_sha256": payload["source_manifest_sha256"]}, indent=2))
    return payload


def candidate_task(panel: str, model_id: str, seed: int) -> dict:
    cfg = protocol()
    root = RESULT_ROOT / "confirmation" / panel / f"{model_id}_seed{seed}"
    manifest = root / "task_manifest.json"
    if manifest.is_file():
        old = json.loads(manifest.read_text(encoding="utf-8"))
        if old.get("status") == "complete":
            return old
    configs = load_configs()
    period, input_length, horizons = _real_panel_definition(panel)
    horizon = max(horizons)
    device = resolve_device(str(configs["protocol"]["training"]["device"]))
    set_seed(seed)
    train, _ = _real_bundle(panel, "train", horizon)
    validation, _ = _real_bundle(panel, "validation", horizon)
    test, metadata = _real_bundle(panel, "test", horizon)
    model = build_model(model_id, horizon, len(FEATURE_NAMES), configs["model_spec"], input_length, period).to(device)
    started = utc_now()
    try:
        checkpoint = root / "checkpoint.pt"
        outcome = train_model(model, train, validation, device, seed, configs["protocol"]["training"], checkpoint)
        validation_arrays = _collect(model, validation, device, seed)
        test_arrays = _collect(model, test, device, seed)
        raw = _to_raw(test_arrays, metadata)
        raw_residual = raw["forecast"] - raw["baseline"]
        metrics = summarize_predictions(raw["forecast"], raw["target"], test_arrays["state"], test_arrays["gate"], raw_residual, test_arrays["change_score"], test_arrays["series_index"], metadata, model_id, seed, horizons, panel)
        root.mkdir(parents=True, exist_ok=True)
        validation_path = root / "validation_predictions.npz"
        with validation_path.with_name(f".{validation_path.name}.tmp").open("wb") as handle:
            np.savez_compressed(handle, **validation_arrays)
        validation_path.with_name(f".{validation_path.name}.tmp").replace(validation_path)
        metrics_path = root / "metrics.csv"
        write_csv(metrics_path, metrics)
        test_path = root / "test_predictions.npz"
        with test_path.with_name(f".{test_path.name}.tmp").open("wb") as handle:
            np.savez_compressed(handle, **test_arrays)
        test_path.with_name(f".{test_path.name}.tmp").replace(test_path)
        payload = {"status": "complete", "panel": panel, "model": model_id, "seed": seed, "started_at": started, "finished_at": utc_now(), "training": outcome, "artifacts": {"metrics": artifact_entry(metrics_path), "validation": artifact_entry(validation_path), "test": artifact_entry(test_path), "checkpoint": artifact_entry(checkpoint) if checkpoint.exists() else None}}
    except Exception as exc:
        payload = {"status": "failed", "panel": panel, "model": model_id, "seed": seed, "started_at": started, "finished_at": utc_now(), "error": repr(exc)}
        write_task_manifest(manifest, payload)
        raise
    write_task_manifest(manifest, payload)
    return payload


def select_task(panel: str, seed: int) -> dict:
    cfg = protocol()
    candidates = tuple(cfg["candidates"])
    root = RESULT_ROOT / "confirmation" / panel / f"M7-validation-selection_seed{seed}"
    manifest = root / "task_manifest.json"
    if manifest.is_file():
        old = json.loads(manifest.read_text(encoding="utf-8"))
        if old.get("status") == "complete":
            return old
    started = utc_now()
    try:
        base = RESULT_ROOT / "confirmation" / panel
        validation, test = {}, {}
        for model in candidates:
            candidate_root = base / f"{model}_seed{seed}"
            with np.load(candidate_root / "validation_predictions.npz") as arrays:
                validation[model] = {key: arrays[key] for key in arrays.files}
            with np.load(candidate_root / "test_predictions.npz") as arrays:
                test[model] = {key: arrays[key] for key in arrays.files}
        chosen, audit = select_validation_candidate({model: validation[model]["forecast"] for model in candidates}, validation["M0"]["target"], validation["M0"]["series_index"], candidates)
        reference = test["M0"]
        missing = sorted({int(value) for value in np.unique(reference["series_index"])} - set(chosen))
        for index in missing:
            chosen[index] = "M0"
            audit.append({"series_index": index, "validation_origins": 0, "selected_model": "M0", **{f"validation_mse_{model}": float("nan") for model in candidates}})
        names = np.asarray([chosen[int(value)] for value in reference["series_index"]], dtype=object)
        prediction = np.empty_like(reference["forecast"])
        gate = np.empty_like(reference["gate"])
        for model in candidates:
            mask = names == model
            prediction[mask] = test[model]["forecast"][mask]
            gate[mask] = test[model]["gate"][mask]
        _, _, horizons = _real_panel_definition(panel)
        _, metadata = _real_bundle(panel, "test", max(horizons))
        # _collect stores standardized arrays; M0 is the causal persistence path.
        means = np.asarray([float(item["training_mean"]) for item in metadata], dtype=np.float32)[reference["series_index"]][:, None]
        stds = np.asarray([float(item["training_std"]) for item in metadata], dtype=np.float32)[reference["series_index"]][:, None]
        raw_prediction, raw_target = prediction * stds + means, reference["target"] * stds + means
        baseline = test["M0"]["forecast"] * stds + means
        metrics = summarize_predictions(raw_prediction, raw_target, reference["state"], gate, raw_prediction - baseline, reference["change_score"], reference["series_index"], metadata, "M7-validation-selection", seed, horizons, panel)
        root.mkdir(parents=True, exist_ok=True)
        selection_path = root / "validation_model_selection.csv"
        write_csv(selection_path, audit, ("series_index", "validation_origins", "selected_model", *[f"validation_mse_{model}" for model in candidates]))
        metrics_path = root / "metrics.csv"
        write_csv(metrics_path, metrics)
        payload = {"status": "complete", "panel": panel, "model": "M7-validation-selection", "seed": seed, "started_at": started, "finished_at": utc_now(), "selection_split": "validation", "selection_candidates": list(candidates), "test_targets_used_for_selection": False, "no_validation_model_series": len(missing), "artifacts": {"metrics": artifact_entry(metrics_path), "selection": artifact_entry(selection_path)}}
    except Exception as exc:
        payload = {"status": "failed", "panel": panel, "model": "M7-validation-selection", "seed": seed, "started_at": started, "finished_at": utc_now(), "error": repr(exc)}
        write_task_manifest(manifest, payload)
        raise
    write_task_manifest(manifest, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("freeze", "candidates", "select"), required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=None)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--panel", default="traffic_hourly")
    args = parser.parse_args()
    global ACTIVE_PROTOCOL, ACTIVE_PANEL
    ACTIVE_PROTOCOL = args.protocol.resolve()
    ACTIVE_PANEL = str(args.panel)
    if args.stage == "freeze":
        freeze_protocol()
        return
    cfg = protocol()
    seeds = args.seeds or cfg["seeds"]
    completed, failures = [], []
    if args.stage == "candidates":
        for model in cfg["candidates"]:
            for seed in seeds:
                try: completed.append(candidate_task(ACTIVE_PANEL, model, seed))
                except Exception as exc: failures.append({"model": model, "seed": seed, "error": repr(exc)})
    else:
        for seed in seeds:
            try: completed.append(select_task(ACTIVE_PANEL, seed))
            except Exception as exc: failures.append({"model": "M7-validation-selection", "seed": seed, "error": repr(exc)})
    print(json.dumps({"stage": args.stage, "completed": len(completed), "failures": failures}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
