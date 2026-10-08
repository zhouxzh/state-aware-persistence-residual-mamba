#!/usr/bin/env python
"""Run the isolated SAPR-Mamba v1 simulation protocol."""

from __future__ import annotations

import argparse
import csv
import os
import random
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
# Conda NumPy uses MKL while PyTorch/Mamba load GNU OpenMP.  Fix the supported
# GNU threading layer before importing either stack so children inherit it too.
os.environ["MKL_THREADING_LAYER"] = "GNU"

import numpy as np
import torch
from torch.utils.data import DataLoader, RandomSampler

from model.StateAwarePersistenceResidualMamba import build_model
from utils.sapr_mamba.analysis import artifact_entry, summarize_predictions, write_checksum_manifest, write_csv
from utils.sapr_mamba.data import WindowDataset, cap_origins_per_series, make_origins, synthetic_series_info
from utils.sapr_mamba.features import FEATURE_NAMES
from utils.sapr_mamba.io import (
    CONFIG_ROOT,
    DATA_ROOT,
    RESULT_ROOT,
    RUNLOG_ROOT,
    STUDY_SLUG,
    STUDY_VERSION,
    atomic_write_json,
    code_hashes,
    command_output,
    config_hashes,
    git_state,
    load_configs,
    sha256_path,
    utc_now,
    write_task_manifest,
)
from utils.sapr_mamba.real import download_real_panels, load_prepared_panel, prepare_real_panels
from utils.sapr_mamba.synthetic import generate_all, load_split
from utils.sapr_mamba.statistical import fixed_rows_by_series, forecast_selected, select_candidates


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def resolve_device(requested: str) -> torch.device:
    requested = os.environ.get("SAPR_MAMBA_DEVICE", requested)
    if requested.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("SAPR-Mamba training requires CUDA but torch.cuda.is_available() is false")
    return torch.device(requested)


def preflight() -> dict:
    RUNLOG_ROOT.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")
    disk = command_output(["df", "-h", str(REPO_ROOT)])
    payload = {
        "phase": "preflight",
        "timestamp": utc_now(),
        "repository": str(Path.cwd().resolve()),
        "git": git_state(),
        "python": sys.version,
        "conda_prefix": os.environ.get("CONDA_PREFIX", ""),
        "nvidia_smi": command_output(["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used,utilization.gpu", "--format=csv,noheader"]),
        "disk": disk,
        "active_research_processes": command_output(["bash", "-lc", "ps -eo pid,ppid,stat,etime,cmd | rg -i 'python.*(sapr|mamba|optuna)|torchrun' || true"]),
        "config_hashes": config_hashes(),
    }
    atomic_write_json(RUNLOG_ROOT / f"preflight_{timestamp}.json", payload)
    return payload


def freeze_protocol() -> dict:
    configs = load_configs()
    data_manifests = {}
    for path in (
        DATA_ROOT / "synthetic" / "data_manifest.json",
        DATA_ROOT / "real" / "data_manifest.json",
        DATA_ROOT / "real" / "processed" / "prepared_manifest.json",
    ):
        if path.is_file():
            data_manifests[str(path.relative_to(REPO_ROOT))] = sha256_path(path)
    payload = {
        "protocol_lock_version": configs["protocol"]["protocol_version"],
        "frozen_at": utc_now(),
        "git": git_state(),
        "source_hashes": config_hashes(),
        "code_hashes": code_hashes(),
        "data_manifests": data_manifests,
        "configuration": configs,
    }
    lock_path = CONFIG_ROOT / "protocol.lock.json"
    atomic_write_json(lock_path, payload)
    return {"path": str(lock_path), "sha256": sha256_path(lock_path), "source_hashes": payload["source_hashes"]}


def capture_environment() -> dict:
    """Persist the Phase 0 runtime evidence before any simulation is generated."""
    output = REPO_ROOT / "reproducibility" / STUDY_SLUG / "runtime_environment.json"
    mamba_probe = subprocess.run(
        [sys.executable, "-c", "import torch; from mamba_ssm import Mamba; print(torch.__version__); print(torch.version.cuda); print(Mamba.__module__)"],
        cwd=REPO_ROOT, text=True, capture_output=True, check=False,
    )
    payload = {
        "captured_at": utc_now(),
        "git": git_state(),
        "conda_prefix": os.environ.get("CONDA_PREFIX", ""),
        "conda_from_history": command_output(["conda", "env", "export", "--from-history"]),
        "pip_freeze": command_output([sys.executable, "-m", "pip", "freeze"]),
        "nvcc": command_output(["nvcc", "--version"]),
        "nvidia_smi": command_output(["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used,compute_cap", "--format=csv,noheader"]),
        "mamba_probe": {"returncode": mamba_probe.returncode, "stdout": mamba_probe.stdout.strip(), "stderr": mamba_probe.stderr.strip()},
        "config_hashes": config_hashes(),
    }
    atomic_write_json(output, payload)
    return {"path": str(output), "sha256": sha256_path(output), "mamba_probe": payload["mamba_probe"]}


def _smoke_subset(values: np.ndarray, roster: list[dict], limit_per_cell: int) -> tuple[np.ndarray, list[dict]]:
    """Keep a deterministic small independent-sequence subset for Phase 3 only."""
    selected = []
    counts: dict[tuple[str, float], int] = {}
    for index, entry in enumerate(roster):
        cell = (str(entry["mechanism"]), float(entry["strength"]))
        if counts.get(cell, 0) < int(limit_per_cell):
            selected.append(index)
            counts[cell] = counts.get(cell, 0) + 1
    return values[selected], [roster[index] for index in selected]


def _synthetic_bundle(split: str, horizon: int, shuffle_seed: int | None = None, smoke_limit_per_cell: int | None = None) -> tuple[WindowDataset, list[dict]]:
    configs = load_configs()
    synthetic = configs["synthetic"]
    protocol = configs["protocol"]
    values, roster = load_split(split)
    if smoke_limit_per_cell is not None:
        values, roster = _smoke_subset(values, roster, smoke_limit_per_cell)
    infos = synthetic_series_info(roster, values.shape[1], int(synthetic["seasonal_period"]))
    stride = int(synthetic["origin_stride"])
    origins = make_origins(values, infos, int(synthetic["input_length"]), horizon, "all", stride)
    dataset = WindowDataset(
        sequences=values,
        infos=infos,
        origins=origins,
        input_length=int(synthetic["input_length"]),
        horizon=horizon,
        epsilon=float(protocol["state_features"]["epsilon"]),
        change_threshold=float(protocol["state_features"]["change_threshold"]),
        feature_permutation_seed=shuffle_seed,
    )
    metadata = []
    for entry, sequence in zip(roster, values):
        training_std = max(float(np.std(sequence[: int(sequence.size * 0.6)], ddof=0)), 1e-6)
        metadata.append({**entry, "training_std": training_std})
    return dataset, metadata


def _loader(dataset: WindowDataset, batch_size: int, shuffle: bool, samples: int | None, seed: int) -> DataLoader:
    generator = torch.Generator()
    generator.manual_seed(int(seed))
    if shuffle:
        sampler = RandomSampler(dataset, replacement=True, num_samples=int(samples), generator=generator)
        return DataLoader(dataset, batch_size=batch_size, sampler=sampler, num_workers=0, pin_memory=True)
    return DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0, pin_memory=True)


def _to_device(batch: dict, device: torch.device) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    return (
        batch["x"].to(device, non_blocking=True),
        batch["y"].to(device, non_blocking=True),
        batch["phi"].to(device, non_blocking=True),
    )


def _loss(model: torch.nn.Module, x: torch.Tensor, y: torch.Tensor, phi: torch.Tensor) -> torch.Tensor:
    return torch.mean((model(x, phi)["forecast"] - y) ** 2)


def train_model(model: torch.nn.Module, train: WindowDataset, validation: WindowDataset, device: torch.device, seed: int, training: dict, checkpoint: Path) -> dict:
    if not any(parameter.requires_grad for parameter in model.parameters()):
        return {"epochs": 0, "best_validation_mse": float("nan"), "status": "not_trainable"}
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(training["learning_rate"]), weight_decay=float(training["weight_decay"]))
    scaler = torch.amp.GradScaler("cuda", enabled=bool(training["amp"]) and device.type == "cuda")
    effective_batch_size = int(os.environ.get("SAPR_MAMBA_BATCH_SIZE", training["batch_size"]))
    if effective_batch_size < 1:
        raise ValueError("SAPR_MAMBA_BATCH_SIZE must be positive")
    train_loader = _loader(train, effective_batch_size, True, int(training["samples_per_epoch"]), seed)
    validation_loader = _loader(validation, effective_batch_size, False, None, seed)
    best = float("inf")
    stale = 0
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    for epoch in range(1, int(training["max_epochs"]) + 1):
        model.train()
        for batch in train_loader:
            x, y, phi = _to_device(batch, device)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, enabled=bool(training["amp"]) and device.type == "cuda"):
                loss = _loss(model, x, y, phi)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), float(training["gradient_clip_norm"]))
            scaler.step(optimizer)
            scaler.update()
        model.eval()
        weighted_loss = 0.0
        observations = 0
        with torch.no_grad():
            for batch in validation_loader:
                x, y, phi = _to_device(batch, device)
                with torch.autocast(device_type=device.type, enabled=bool(training["amp"]) and device.type == "cuda"):
                    value = _loss(model, x, y, phi)
                weighted_loss += float(value) * len(x)
                observations += len(x)
        validation_mse = weighted_loss / max(observations, 1)
        if validation_mse < best:
            best = validation_mse
            stale = 0
            torch.save({"model": model.state_dict(), "seed": seed, "validation_mse": best}, checkpoint)
        else:
            stale += 1
            if stale >= int(training["patience"]):
                break
    if checkpoint.exists():
        model.load_state_dict(torch.load(checkpoint, map_location=device, weights_only=True)["model"])
    return {"epochs": epoch, "best_validation_mse": best, "batch_size": effective_batch_size, "status": "complete"}


def evaluate_model(model: torch.nn.Module, dataset: WindowDataset, metadata: list[dict], device: torch.device, model_id: str, seed: int, horizons: list[int], output: Path, dataset_name: str, inverse_to_raw: bool = False) -> tuple[list[dict], dict]:
    loader = _loader(dataset, 128, False, None, seed)
    predicted, target, states, gates, residuals, scores, series, origins, phis = [], [], [], [], [], [], [], [], []
    model.eval()
    with torch.no_grad():
        for batch in loader:
            x, y, phi = _to_device(batch, device)
            result = model(x, phi)
            predicted.append(result["forecast"].detach().cpu().numpy())
            target.append(y.detach().cpu().numpy())
            states.append(batch["state"].numpy())
            gates.append(result["gate"].detach().cpu().numpy())
            residuals.append(result["residual"].detach().cpu().numpy())
            scores.append(batch["change_score"].numpy())
            series.append(batch["series_index"].numpy())
            origins.append(batch["origin"].numpy())
            phis.append(batch["phi"].numpy())
    arrays = {
        "prediction": np.concatenate(predicted), "target": np.concatenate(target), "state": np.concatenate(states),
        "gate": np.concatenate(gates), "residual": np.concatenate(residuals), "change_score": np.concatenate(scores),
        "series_index": np.concatenate(series), "origin": np.concatenate(origins), "phi": np.concatenate(phis),
    }
    if inverse_to_raw:
        series_means = np.asarray([float(item["training_mean"]) for item in metadata], dtype=np.float32)
        series_stds = np.asarray([float(item["training_std"]) for item in metadata], dtype=np.float32)
        row_means = series_means[arrays["series_index"]][:, None]
        row_stds = series_stds[arrays["series_index"]][:, None]
        arrays["prediction"] = arrays["prediction"] * row_stds + row_means
        arrays["target"] = arrays["target"] * row_stds + row_means
        arrays["residual"] = arrays["residual"] * row_stds
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
    temporary.replace(output)
    rows = summarize_predictions(
        prediction=arrays["prediction"], target=arrays["target"], state=arrays["state"], gate=arrays["gate"],
        residual=arrays["residual"], change_scores=arrays["change_score"], series_indices=arrays["series_index"],
        series_metadata=metadata, model=model_id, seed=seed, horizons=horizons, dataset=dataset_name,
    )
    return rows, {"prediction_archive": artifact_entry(output), "origins": int(len(arrays["state"]))}


def run_synthetic_task(model_id: str, seed: int, smoke: bool = False) -> dict:
    configs = load_configs()
    protocol, synthetic, specification = configs["protocol"], configs["synthetic"], configs["model_spec"]
    horizon = int(synthetic["max_horizon"])
    output_root = RESULT_ROOT / "synthetic" if not smoke else RESULT_ROOT.parent / "smoke" / STUDY_SLUG
    task_root = output_root / f"{model_id}_seed{seed}"
    manifest = task_root / "task_manifest.json"
    if manifest.exists():
        existing = __import__("json").loads(manifest.read_text(encoding="utf-8"))
        if existing.get("status") == "complete":
            return existing
    device = resolve_device(str(protocol["training"]["device"]))
    set_seed(seed)
    shuffle_seed = seed + 9001 if model_id == "M3-shuffle" else None
    smoke_limits = {"train": 5, "validation": 2, "test": 3} if smoke else {}
    train, _ = _synthetic_bundle("train", horizon, shuffle_seed, smoke_limits.get("train"))
    validation, _ = _synthetic_bundle("validation", horizon, shuffle_seed, smoke_limits.get("validation"))
    test, test_metadata = _synthetic_bundle("test", horizon, shuffle_seed, smoke_limits.get("test"))
    model = build_model(model_id, horizon, len(FEATURE_NAMES), specification, int(synthetic["input_length"]), int(synthetic["seasonal_period"])).to(device)
    checkpoint = task_root / "checkpoint.pt"
    started = utc_now()
    try:
        training = dict(protocol["training"])
        if smoke:
            training.update(max_epochs=2, patience=1, samples_per_epoch=512, validation_samples=512, batch_size=16)
        training_result = train_model(model, train, validation, device, seed, training, checkpoint)
        evaluated_horizons = [min(synthetic["horizons"])] if smoke else synthetic["horizons"]
        metric_rows, artifact = evaluate_model(model, test, test_metadata, device, model_id, seed, evaluated_horizons, task_root / "predictions.npz", "synthetic")
        metrics_path = task_root / "metrics.csv"
        write_csv(metrics_path, metric_rows)
        payload = {
            "status": "complete", "started_at": started, "finished_at": utc_now(), "model": model_id, "seed": seed,
            "device": str(device), "training": training_result, "smoke": smoke,
            "smoke_sequence_limit_per_mechanism_strength": smoke_limits or None,
            "evaluated_horizons": evaluated_horizons,
            "data_manifest": str(DATA_ROOT / "synthetic" / "data_manifest.json"),
            "artifacts": {"metrics": artifact_entry(metrics_path), "checkpoint": artifact_entry(checkpoint) if checkpoint.exists() else None, **artifact},
        }
    except Exception as exc:
        payload = {"status": "failed", "started_at": started, "finished_at": utc_now(), "model": model_id, "seed": seed, "error": repr(exc)}
        write_task_manifest(manifest, payload)
        raise
    write_task_manifest(manifest, payload)
    return payload


def combine_synthetic_metrics(root: Path) -> dict:
    rows = []
    for path in sorted(root.glob("*_seed*/metrics.csv")):
        with path.open(encoding="utf-8", newline="") as handle:
            rows.extend(csv.DictReader(handle))
    output = root / "metrics_all.csv"
    write_csv(output, rows)
    return {"rows": len(rows), "metrics": artifact_entry(output)}


def run_synthetic(models: list[str], seeds: list[int], smoke: bool) -> dict:
    preflight()
    generation = generate_all()
    planned = [(model, seed) for model in models for seed in seeds]
    completed, failures = [], []
    for model, seed in planned:
        for attempt in range(1, 3):
            try:
                completed.append(run_synthetic_task(model, seed, smoke))
                break
            except Exception as exc:
                failures.append({"model": model, "seed": seed, "attempt": attempt, "error": repr(exc)})
    root = RESULT_ROOT / "synthetic" if not smoke else RESULT_ROOT.parent / "smoke" / STUDY_SLUG
    failures_path = root / "failures.csv"
    write_csv(failures_path, failures, ("model", "seed", "attempt", "error"))
    summary = {"generated": generation, "planned": len(planned), "completed": len(completed), "failures": failures, "failures_artifact": artifact_entry(failures_path), "metrics": combine_synthetic_metrics(root) if completed else None}
    atomic_write_json(root / "campaign_manifest.json", summary)
    preflight()
    return summary


def _run_statistical_real_task(panel_id: str, family: str, seed: int) -> dict:
    configs = load_configs()
    protocol = configs["protocol"]
    _, input_length, horizons = _real_panel_definition(panel_id)
    horizon = max(horizons)
    period, _, _ = _real_panel_definition(panel_id)
    task_root = RESULT_ROOT / "real" / panel_id / f"{family}_seed{seed}"
    manifest = task_root / "task_manifest.json"
    if manifest.exists():
        existing = __import__("json").loads(manifest.read_text(encoding="utf-8"))
        if existing.get("status") == "complete":
            return existing
    validation, _ = _real_bundle(panel_id, "validation", horizon)
    test, metadata = _real_bundle(panel_id, "test", horizon)
    def restore_raw(item: dict) -> tuple[np.ndarray, np.ndarray]:
        metadata_row = metadata[int(item["series_index"])]
        std = float(metadata_row["training_std"])
        mean = float(metadata_row["training_mean"])
        return item["x"] * std + mean, item["y"] * std + mean

    selection, failures = select_candidates(
        validation, family, protocol["context_baselines"]["statistical_selection"], period, restore_raw=restore_raw,
    )
    test_rows = []
    selected_rows = []
    for series_index, rows in fixed_rows_by_series(test, int(protocol["evaluation"]["real_maximum_test_origins_per_series"])).items():
        for row_index in rows:
            item = test[row_index]
            history, target = restore_raw(item)
            try:
                forecast = forecast_selected(history, horizon, family, selection[series_index], protocol["context_baselines"]["statistical_selection"], period)
            except Exception as exc:
                forecast = np.repeat(history[-1], horizon).astype(np.float32)
                failures.append({"stage": "test_forecast", "model": family, "series_index": int(series_index), "candidate": str(selection.get(series_index)), "origin": int(item["origin"]), "error": repr(exc)})
            test_rows.append((item, history, target, forecast))
            selected_rows.append({"series_index": int(series_index), "series_id": metadata[int(series_index)]["series_id"], "candidate": str(selection.get(series_index)), "origin": int(item["origin"])})
    arrays = {
        "prediction": np.stack([row[3] for row in test_rows]), "target": np.stack([row[2] for row in test_rows]),
        "state": np.asarray([row[0]["state"] for row in test_rows]), "gate": np.ones((len(test_rows), horizon), dtype=np.float32),
        "residual": np.stack([row[3] - row[1][-1] for row in test_rows]), "change_score": np.asarray([row[0]["change_score"] for row in test_rows]),
        "series_index": np.asarray([row[0]["series_index"] for row in test_rows]), "origin": np.asarray([row[0]["origin"] for row in test_rows]),
    }
    task_root.mkdir(parents=True, exist_ok=True)
    predictions_path = task_root / "predictions.npz"
    with predictions_path.with_name(f".{predictions_path.name}.tmp").open("wb") as handle:
        np.savez_compressed(handle, **arrays)
    predictions_path.with_name(f".{predictions_path.name}.tmp").replace(predictions_path)
    metric_rows = summarize_predictions(
        arrays["prediction"], arrays["target"], arrays["state"], arrays["gate"], arrays["residual"], arrays["change_score"], arrays["series_index"],
        metadata, family, seed, horizons, panel_id,
    )
    metrics_path = task_root / "metrics.csv"
    write_csv(metrics_path, metric_rows)
    selections_path = task_root / "selected_candidates.csv"
    write_csv(selections_path, selected_rows, ("series_index", "series_id", "candidate", "origin"))
    failures_path = task_root / "failures.csv"
    write_csv(failures_path, failures, ("stage", "model", "series_index", "candidate", "origin", "error"))
    payload = {
        "status": "complete", "started_at": utc_now(), "finished_at": utc_now(), "panel": panel_id, "model": family, "seed": seed,
        "selection_split": "validation", "artifacts": {"metrics": artifact_entry(metrics_path), "prediction_archive": artifact_entry(predictions_path), "selections": artifact_entry(selections_path), "failures": artifact_entry(failures_path)},
    }
    write_task_manifest(manifest, payload)
    return payload


def _real_panel_definition(panel_id: str) -> tuple[int, int, list[int]]:
    panels = load_configs()["real_panels"]["panels"]
    if panel_id == "electricity":
        item = panels["electricity"]
        return int(item["period"]), int(item["input_length"]), [int(value) for value in item["horizons"]]
    if panel_id == "beijing_air_quality":
        item = panels["beijing_air_quality"]
        return int(item["period"]), int(item["input_length"]), [int(value) for value in item["horizons"]]
    if panel_id.startswith("ett_"):
        file_id = panel_id.removeprefix("ett_")
        item = panels["ett"]
        period = int(item["period_by_file"][file_id])
        return period, 4 * period, [period // 8, period // 4, period // 2, period]
    # V3.1 panels are additive protocol amendments and intentionally live
    # outside the immutable V3.0 top-level config. Resolve their forecasting
    # geometry from the frozen amendment registry after source integration.
    amendment_path = REPO_ROOT / "configs" / "sapr_mamba_v3" / "amendments" / "v3.1_public_multiseries_sources.json"
    if amendment_path.is_file():
        with amendment_path.open(encoding="utf-8") as handle:
            amendment = __import__("json").load(handle)
        item = amendment.get("datasets", {}).get(panel_id)
        if item is not None:
            return int(item["period"]), int(item["input_length"]), [int(value) for value in item["horizons"]]
    raise ValueError(f"Unknown prepared real panel: {panel_id}")


def _real_bundle(panel_id: str, split: str, horizon: int, shuffle_seed: int | None = None) -> tuple[WindowDataset, list[dict]]:
    protocol = load_configs()["protocol"]
    raw_values, eligibility, infos, metadata = load_prepared_panel(panel_id)
    means = np.asarray([item["training_mean"] for item in metadata], dtype=np.float32)[:, None]
    stds = np.asarray([item["training_std"] for item in metadata], dtype=np.float32)[:, None]
    values = (raw_values - means) / stds
    _, input_length, _ = _real_panel_definition(panel_id)
    origins = make_origins(values, infos, input_length, horizon, split, horizon if split == "test" else max(1, horizon // 4), eligibility)
    if split == "test":
        origins = cap_origins_per_series(origins, int(protocol["evaluation"]["real_maximum_test_origins_per_series"]))
    cache_path = DATA_ROOT / "real" / "feature_cache" / panel_id / f"{split}_h{horizon}.npz"
    cached_features = None
    if cache_path.is_file():
        with np.load(cache_path) as payload:
            cached_origins = payload["origins"]
            if (
                "means" in payload
                and "stds" in payload
                and np.array_equal(cached_origins, origins)
                and np.array_equal(payload["means"], means)
                and np.array_equal(payload["stds"], stds)
            ):
                cached_features = (payload["phi"], payload["state"], payload["change_score"])
    dataset = WindowDataset(
        sequences=values, infos=infos, origins=origins, input_length=input_length, horizon=horizon,
        epsilon=float(protocol["state_features"]["epsilon"]), change_threshold=float(protocol["state_features"]["change_threshold"]),
        eligibility=eligibility, feature_permutation_seed=shuffle_seed, cached_features=cached_features,
    )
    if cached_features is None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = cache_path.with_name(f".{cache_path.name}.tmp")
        phi, state, change_score = dataset.cached_features()
        with temporary.open("wb") as handle:
            np.savez_compressed(handle, origins=origins, means=means, stds=stds, phi=phi, state=state, change_score=change_score)
        temporary.replace(cache_path)
    return dataset, metadata


def run_real_task(panel_id: str, model_id: str, seed: int) -> dict:
    configs = load_configs()
    protocol, specification = configs["protocol"], configs["model_spec"]
    _, _, horizons = _real_panel_definition(panel_id)
    horizon = max(horizons)
    task_root = RESULT_ROOT / "real" / panel_id / f"{model_id}_seed{seed}"
    manifest = task_root / "task_manifest.json"
    if manifest.exists():
        existing = __import__("json").loads(manifest.read_text(encoding="utf-8"))
        if existing.get("status") == "complete":
            return existing
    device = resolve_device(str(protocol["training"]["device"]))
    set_seed(seed)
    shuffle_seed = seed + 9001 if model_id == "M3-shuffle" else None
    train, _ = _real_bundle(panel_id, "train", horizon, shuffle_seed)
    validation, _ = _real_bundle(panel_id, "validation", horizon, shuffle_seed)
    test, metadata = _real_bundle(panel_id, "test", horizon, shuffle_seed)
    period, input_length, _ = _real_panel_definition(panel_id)
    model = build_model(model_id, horizon, len(FEATURE_NAMES), specification, input_length, period).to(device)
    checkpoint = task_root / "checkpoint.pt"
    started = utc_now()
    try:
        training = protocol["training"]
        training_result = train_model(model, train, validation, device, seed, training, checkpoint)
        metric_rows, artifact = evaluate_model(model, test, metadata, device, model_id, seed, horizons, task_root / "predictions.npz", panel_id, inverse_to_raw=True)
        metrics_path = task_root / "metrics.csv"
        write_csv(metrics_path, metric_rows)
        payload = {
            "status": "complete", "started_at": started, "finished_at": utc_now(), "panel": panel_id, "model": model_id,
            "seed": seed, "device": str(device), "training": training_result,
            "artifacts": {"metrics": artifact_entry(metrics_path), "checkpoint": artifact_entry(checkpoint) if checkpoint.exists() else None, **artifact},
        }
    except Exception as exc:
        payload = {"status": "failed", "started_at": started, "finished_at": utc_now(), "panel": panel_id, "model": model_id, "seed": seed, "error": repr(exc)}
        write_task_manifest(manifest, payload)
        raise
    write_task_manifest(manifest, payload)
    return payload


def run_real(models: list[str], seeds: list[int], panel_filter: list[str] | None = None) -> dict:
    preflight()
    prepared = __import__("json").loads((DATA_ROOT / "real" / "processed" / "prepared_manifest.json").read_text(encoding="utf-8"))
    panels = [entry["panel_id"] for entry in prepared["panels"]]
    if panel_filter is not None:
        requested = list(dict.fromkeys(panel_filter))
        invalid_panels = sorted(set(requested) - set(panels))
        if invalid_panels:
            raise SystemExit(f"Unknown prepared real panels: {invalid_panels}")
        panels = [panel for panel in panels if panel in set(requested)]
        if not panels:
            raise SystemExit("At least one real panel is required")
    protocol = load_configs()["protocol"]
    contextual = protocol["context_baselines"]["models"]
    random_models = set(protocol["real_seed_policy"]["five_seeds_for"])
    deterministic_seed = int(protocol["real_seed_policy"]["single_deterministic_seed"])
    learned_contextual = [model for model in contextual if model in {"SeasonalNaive", "Drift", "DLinear"}]
    statistical_contextual = [model for model in contextual if model in {"ETS", "ARIMA"}]
    learned_models = [*models, *learned_contextual]
    planned = [
        (panel, model, seed)
        for panel in panels
        for model in learned_models
        for seed in (seeds if model in random_models else [deterministic_seed])
    ]
    statistical_planned = [(panel, model, deterministic_seed) for panel in panels for model in statistical_contextual]
    complete, failures = [], []
    for panel, model, seed in planned:
        for attempt in range(1, 3):
            try:
                complete.append(run_real_task(panel, model, seed))
                break
            except Exception as exc:
                failures.append({"panel": panel, "model": model, "seed": seed, "attempt": attempt, "error": repr(exc)})
    for panel, model, seed in statistical_planned:
        for attempt in range(1, 3):
            try:
                complete.append(_run_statistical_real_task(panel, model, seed))
                break
            except Exception as exc:
                failures.append({"panel": panel, "model": model, "seed": seed, "attempt": attempt, "error": repr(exc)})
    root = RESULT_ROOT / "real"
    rows = []
    for path in sorted(root.glob("*/*_seed*/metrics.csv")):
        with path.open(encoding="utf-8", newline="") as handle:
            rows.extend(csv.DictReader(handle))
    metrics = root / "metrics_all.csv"
    if rows:
        write_csv(metrics, rows)
    failures_path = root / "failures.csv"
    write_csv(failures_path, failures, ("panel", "model", "seed", "attempt", "error"))
    summary = {"planned": len(planned) + len(statistical_planned), "completed": len(complete), "failures": failures, "failures_artifact": artifact_entry(failures_path), "metrics": artifact_entry(metrics) if rows else None}
    atomic_write_json(root / "campaign_manifest.json", summary)
    preflight()
    return summary


def verify_synthetic() -> dict:
    root = RESULT_ROOT / "synthetic"
    manifests = list(root.glob("*_seed*/task_manifest.json"))
    failed = []
    for path in manifests:
        payload = __import__("json").loads(path.read_text(encoding="utf-8"))
        if payload.get("status") != "complete":
            failed.append(str(path))
            continue
        for artifact in payload.get("artifacts", {}).values():
            if not isinstance(artifact, dict) or "path" not in artifact or "sha256" not in artifact:
                continue
            candidate = Path(artifact["path"])
            if not candidate.is_file() or sha256_path(candidate) != artifact["sha256"]:
                failed.append(str(candidate))
    checksums = write_checksum_manifest(root, root / "SHA256SUMS.json")
    return {"tasks": len(manifests), "failures": failed, "checksums": checksums}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, choices=("preflight", "environment", "freeze", "synthetic-generate", "smoke", "synthetic-run", "real-download", "real-prepare", "real-run", "verify"))
    parser.add_argument("--models", nargs="+", default=None)
    parser.add_argument("--seeds", nargs="+", type=int, default=None)
    parser.add_argument("--panels", nargs="+", default=None, help="restrict real-run to prepared panel IDs")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configs = load_configs()
    if args.stage == "preflight":
        outcome = preflight()
    elif args.stage == "environment":
        outcome = capture_environment()
    elif args.stage == "freeze":
        outcome = freeze_protocol()
    elif args.stage == "synthetic-generate":
        outcome = generate_all()
    elif args.stage == "real-download":
        outcome = download_real_panels()
    elif args.stage == "real-prepare":
        outcome = prepare_real_panels()
    elif args.stage in {"smoke", "synthetic-run"}:
        models = args.models or configs["protocol"]["models"]
        invalid = sorted(set(models) - set(configs["protocol"]["models"]))
        if invalid:
            raise SystemExit(f"Unknown SAPR models: {invalid}")
        seeds = args.seeds or (configs["protocol"]["seeds"][:1] if args.stage == "smoke" else configs["protocol"]["seeds"])
        outcome = run_synthetic(models, seeds, args.stage == "smoke")
    elif args.stage == "real-run":
        models = args.models or configs["protocol"]["models"]
        invalid = sorted(set(models) - set(configs["protocol"]["models"]))
        if invalid:
            raise SystemExit(f"Unknown SAPR models: {invalid}")
        outcome = run_real(models, args.seeds or configs["protocol"]["seeds"], args.panels)
    else:
        outcome = verify_synthetic()
    print(__import__("json").dumps(outcome, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
