#!/usr/bin/env python
"""OCRA-v1 sealed synthetic protocol runner.

Commands deliberately separate sealing, validation-only training/calibration,
and the one-time test evaluation.  No command other than ``evaluate-once``
loads the sealed test numeric array.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import pickle
import random
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("MKL_THREADING_LAYER", "GNU")

import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from torch.utils.data import DataLoader, RandomSampler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model.StateAwarePersistenceResidualMamba import build_model
from utils.sapr_mamba.data import SeriesInfo, WindowDataset, make_origins
from utils.sapr_mamba.io import atomic_write_json, code_hashes, git_state, sha256_path, utc_now
from utils.sapr_mamba.ocra_v1 import (
    OCRA_FEATURE_NAMES,
    OCRA_V1_1_FEATURE_NAMES,
    action_from_probabilities,
    evaluation_set,
    evaluation_set_v1_1,
    evaluation_set_v1_2,
    normalize_from_validation,
    ocra_features,
    ocra_v1_1_features,
    series_id_hash,
    target_action,
    target_action_v1_1,
    target_action_v1_2,
    true_label,
)

CONFIG = ROOT / os.environ.get("OCRA_CONFIG_DIR", "configs/ocra_v1")
CANONICAL_SERIES = ROOT / "reproducibility" / "sapr_canonical_v2" / "sequence_metrics.csv"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def configs() -> tuple[dict, dict, dict]:
    return (read_json(CONFIG / "protocol.json"), read_json(CONFIG / "synthetic.json"), read_json(CONFIG / "model_spec.json"))


def run_root(protocol: dict) -> Path:
    configured = Path(os.environ.get("OCRA_V1_RUN_ROOT", protocol["run_root"]))
    root = (ROOT / configured).resolve() if not configured.is_absolute() else configured.resolve()
    if ROOT not in (root, *root.parents):
        raise RuntimeError("OCRA_V1_RUN_ROOT must remain inside this repository")
    return root


def paths(protocol: dict) -> dict[str, Path]:
    root = run_root(protocol)
    return {
        "root": root,
        "protocol": root / "protocol",
        "data": root / "data",
        "bundles": root / "bundles",
        "forecasts": root / "forecasts",
        "metrics": root / "metrics",
        "bootstrap": root / "bootstrap",
        "tables": root / "tables",
        "figures": root / "figures",
        "reports": root / "reports",
        "logs": root / "logs",
        "failures": root / "failures",
    }


def config_hashes() -> dict[str, str]:
    return {path.name: sha256_path(path) for path in sorted(CONFIG.glob("*.json"))}


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def device_for(protocol: dict) -> torch.device:
    requested = os.environ.get("OCRA_V1_DEVICE", protocol["training"]["device"])
    if requested.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("OCRA-v1 requires CUDA for backbone training")
    return torch.device(requested)


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def save_npz(path: Path, **arrays: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
    temporary.replace(path)


def _split_seed(generator_seed: int, split: str) -> int:
    return int(generator_seed) + {"train": 11, "validation": 29, "test": 47}[split]


def generate_one(mechanism: str, index: int, split: str, settings: dict, prefix: str, rng: np.random.Generator) -> tuple[np.ndarray, dict]:
    base, length, period = settings["base"], int(settings["length"]), int(settings["seasonal_period"])
    noise = rng.normal(0.0, float(base["innovation_std"]), length)
    visible_points = tuple(int(value) for value in base["visible_change_points"])
    future_origins = tuple(int(value) for value in base["future_jump_origins"])
    visible_point = visible_points[index % len(visible_points)]
    future_point = future_origins[index % len(future_origins)] + int(base["future_jump_offset"])
    direction = -1.0 if index % 2 == 0 else 1.0
    if mechanism == "variance_shift":
        noise[visible_point:] *= float(base["variance_multiplier"])
    if mechanism == "random_walk" or (mechanism == "future_jump" and base["future_jump_baseline"] == "random_walk"):
        values, change_point = np.cumsum(noise), (-1 if mechanism == "random_walk" else future_point)
        if mechanism == "future_jump":
            values[future_point:] += direction * float(base["jump_strength"])
    else:
        values = np.empty(length, dtype=np.float64)
        values[0] = noise[0]
        for point in range(1, length):
            values[point] = float(base["ar"]) * values[point - 1] + noise[point]
        timeline = np.arange(length, dtype=np.float64)
        change_point = visible_point
        if mechanism == "continuing_trend":
            values += float(base["trend_slope"]) * timeline
        elif mechanism == "stable_season":
            values += float(base["seasonal_amplitude"]) * np.sin(2 * np.pi * timeline / period)
        elif mechanism == "visible_level_shift":
            values[visible_point:] += float(base["jump_strength"])
        elif mechanism == "future_jump":
            values[future_point:] += direction * float(base["jump_strength"])
            change_point = future_point
        elif mechanism == "trend_break":
            values[visible_point:] += (timeline[visible_point:] - visible_point) * float(base["trend_break_slope"])
        elif mechanism == "seasonal_change":
            values += float(base["seasonal_amplitude"]) * np.sin(2 * np.pi * timeline / period)
            values[visible_point:] += float(base["seasonal_change_amplitude"]) * np.sin(2 * np.pi * timeline[visible_point:] / period + np.pi / 3)
        elif mechanism not in {"stable", "variance_shift"}:
            raise ValueError(f"unknown OCRA mechanism: {mechanism}")
    record = series_record(mechanism, index, split, settings, prefix, change_point)
    return values.astype(np.float32), record


def series_record(mechanism: str, index: int, split: str, settings: dict, prefix: str, change_point: int | None = None) -> dict:
    """Create public split metadata without generating a numeric test series."""
    base = settings["base"]
    if change_point is None:
        visible = tuple(int(value) for value in base["visible_change_points"])[index % len(base["visible_change_points"])]
        future = tuple(int(value) for value in base["future_jump_origins"])[index % len(base["future_jump_origins"])] + int(base["future_jump_offset"])
        change_point = -1 if mechanism in {"stable", "stable_season", "random_walk"} else future if mechanism == "future_jump" else visible
    return {"series_id": f"{prefix}{split}_{mechanism}_{index:04d}", "mechanism": mechanism, "change_point": int(change_point), "period": int(settings["seasonal_period"]), "split": split}


def _canonical_blacklist(protocol: dict) -> tuple[list[str], dict]:
    with CANONICAL_SERIES.open(encoding="utf-8", newline="") as handle:
        old_ids = sorted({row["series_id"] for row in csv.DictReader(handle)})
    observed = series_id_hash(old_ids)
    return old_ids, {
        "canonical_series_count": len(old_ids),
        "canonical_series_hash_expected": protocol["canonical_test_series_hash"],
        "canonical_series_hash_observed": observed,
        "canonical_series_hash_matches": observed == protocol["canonical_test_series_hash"],
    }


def _prior_ocra_ids() -> list[str]:
    identifiers: set[str] = set()
    for roster in sorted((ROOT / "results").glob("ocra_v1*/data/*_roster.json")):
        try:
            identifiers.update(str(record["series_id"]) for record in read_json(roster).get("records", []))
        except (OSError, json.JSONDecodeError, KeyError):
            continue
    return sorted(identifiers)


def _environment() -> dict:
    def command(args: list[str]) -> str:
        try:
            return subprocess.check_output(args, cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            return f"unavailable: {exc}"
    return {
        "captured_at": utc_now(), "python": sys.version, "git": git_state(),
        "torch": torch.__version__, "cuda": torch.version.cuda,
        "nvidia_smi": command(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"]),
        "disk": command(["df", "-h", str(ROOT)]), "code_hashes": code_hashes(),
    }


def seal() -> None:
    protocol, settings, _ = configs()
    destination = paths(protocol)
    protocol_path = destination["protocol"] / "protocol.json"
    if protocol_path.exists():
        raise RuntimeError("protocol already sealed; create ocra_v1.1 for any amendment")
    old_ids, blacklist = _canonical_blacklist(protocol)
    # Snapshot existing protocols before this seal writes its own roster files.
    prior_ids = _prior_ocra_ids()
    if not blacklist["canonical_series_hash_matches"]:
        raise RuntimeError("canonical_v2 series blacklist hash mismatch")
    all_records: dict[str, list[dict]] = {}
    split_manifest: dict[str, dict] = {}
    for split in ("train", "validation", "test"):
        rng = np.random.default_rng(_split_seed(protocol["generator_seed"], split))
        values, records = [], []
        for mechanism in settings["mechanisms"]:
            count = int(settings.get("mechanism_split_overrides", {}).get(mechanism, {}).get(split, settings["splits"][split]))
            for index in range(count):
                if split == "test":
                    records.append(series_record(mechanism, index, split, settings, protocol["series_id_prefix"]))
                else:
                    series, record = generate_one(mechanism, index, split, settings, protocol["series_id_prefix"], rng)
                    values.append(series)
                    records.append(record)
        npz_path, roster_path = destination["data"] / f"{split}.npz", destination["data"] / f"{split}_roster.json"
        atomic_write_json(roster_path, {"split": split, "records": records})
        if split != "test":
            save_npz(npz_path, values=np.stack(values))
        all_records[split] = records
        split_manifest[split] = {"series_count": len(records), "data_sha256": sha256_path(npz_path) if split != "test" else None, "roster_sha256": sha256_path(roster_path), "numeric_data_materialized": split != "test"}
    all_ocra_ids = [record["series_id"] for records in all_records.values() for record in records]
    canonical_intersection = sorted(set(old_ids).intersection(all_ocra_ids))
    prior_intersection = sorted(set(prior_ids).intersection(all_ocra_ids))
    seed_blacklist = set(protocol.get("training_seed_blacklist", protocol["canonical_training_seed_blacklist"]))
    seed_intersection = sorted(seed_blacklist.intersection(protocol["training_seeds"]))
    blacklist.update({"ocra_series_count": len(all_ocra_ids), "ocra_series_prefix_valid": all(value.startswith(protocol["series_id_prefix"]) for value in all_ocra_ids), "canonical_series_id_intersection": canonical_intersection, "prior_ocra_series_count": len(prior_ids), "prior_ocra_series_id_intersection": prior_intersection, "training_seed_intersection": seed_intersection, "passed": not canonical_intersection and not prior_intersection and not seed_intersection})
    if not blacklist["passed"]:
        raise RuntimeError("OCRA blacklist intersection detected")
    split_payload = {"created_at": utc_now(), "generator_seed": protocol["generator_seed"], "splits": split_manifest, "test_numeric_access": False}
    atomic_write_json(destination["protocol"] / "split_manifest.json", split_payload)
    atomic_write_json(destination["protocol"] / "seed_manifest.json", {"generator_seed": protocol["generator_seed"], "training_seeds": protocol["training_seeds"], "canonical_training_seed_blacklist": protocol["canonical_training_seed_blacklist"]})
    atomic_write_json(destination["protocol"] / "blacklist_check.json", blacklist)
    atomic_write_json(destination["protocol"] / "environment.json", _environment())
    runner_hashes = {"scripts/ocra_v1.py": sha256_path(Path(__file__)), "utils/sapr_mamba/ocra_v1.py": sha256_path(ROOT / "utils" / "sapr_mamba" / "ocra_v1.py")}
    feature_names = OCRA_V1_1_FEATURE_NAMES if protocol.get("feature_variant") == "v1_1" else OCRA_FEATURE_NAMES
    audit = {"status": "passed", "created_at": utc_now(), "test_numeric_loaded": False, "certificate_inputs": list(feature_names), "forbidden_inputs": ["future_window", "mechanism", "series_id", "horizon"], "future_field_permutation_changes_action": False, "feature_source": "utils/sapr_mamba/ocra_v1.py:ocra_v1_1_features" if protocol.get("feature_variant") == "v1_1" else "utils/sapr_mamba/ocra_v1.py:ocra_features", "runner_hashes": runner_hashes, "series_id_prefix": protocol["series_id_prefix"]}
    atomic_write_json(destination["protocol"] / "e1_leakage_audit.json", audit)
    (destination["protocol"] / "code_commit.txt").parent.mkdir(parents=True, exist_ok=True)
    (destination["protocol"] / "code_commit.txt").write_text(git_state()["commit"] + "\n", encoding="utf-8")
    sealed = {**protocol, "sealed_at": utc_now(), "effective_run_root": str(destination["root"].relative_to(ROOT)), "config_hashes": config_hashes(), "runner_hashes": runner_hashes, "split_manifest_sha256": sha256_path(destination["protocol"] / "split_manifest.json"), "blacklist_check_sha256": sha256_path(destination["protocol"] / "blacklist_check.json"), "test_access": "locked"}
    atomic_write_json(protocol_path, sealed)
    hashes = {str(path.relative_to(destination["root"])): sha256_path(path) for path in sorted(destination["protocol"].glob("*.json"))}
    atomic_write_json(destination["protocol"] / "file_hashes.json", hashes)
    print(json.dumps({"status": "sealed", "run_root": str(destination["root"]), "blacklist_passed": True}, indent=2))


def _require_sealed() -> tuple[dict, dict, dict, dict[str, Path]]:
    protocol, settings, spec = configs()
    destination = paths(protocol)
    sealed = destination["protocol"] / "protocol.json"
    blacklist = destination["protocol"] / "blacklist_check.json"
    if not sealed.is_file() or not blacklist.is_file() or not read_json(blacklist).get("passed"):
        raise RuntimeError("seal and passing blacklist_check.json are required before this command")
    sealed_payload = read_json(sealed)
    expected_hashes = {
        "scripts/ocra_v1.py": sha256_path(Path(__file__)),
        "utils/sapr_mamba/ocra_v1.py": sha256_path(ROOT / "utils" / "sapr_mamba" / "ocra_v1.py"),
    }
    if sealed_payload.get("runner_hashes") != expected_hashes:
        raise RuntimeError("sealed protocol lacks OCRA runner hashes; preserve this attempt and reseal before training")
    return protocol, settings, spec, destination


def _load_split(destination: dict[str, Path], split: str, *, allow_test: bool = False) -> tuple[np.ndarray, list[dict]]:
    if split == "test" and not allow_test:
        raise RuntimeError("test numeric data is locked until evaluate-once")
    with np.load(destination["data"] / f"{split}.npz") as payload:
        values = np.asarray(payload["values"], dtype=np.float32)
    records = read_json(destination["data"] / f"{split}_roster.json")["records"]
    return values, records


def materialize_test(destination: dict[str, Path], protocol: dict, settings: dict) -> None:
    """Create the numeric test array only after the immutable access record exists."""
    target = destination["data"] / "test.npz"
    if target.exists():
        return
    records = read_json(destination["data"] / "test_roster.json")["records"]
    rng = np.random.default_rng(_split_seed(protocol["generator_seed"], "test"))
    values, generated = [], []
    for mechanism in settings["mechanisms"]:
        count = int(settings.get("mechanism_split_overrides", {}).get(mechanism, {}).get("test", settings["splits"]["test"]))
        for index in range(count):
            series, record = generate_one(mechanism, index, "test", settings, protocol["series_id_prefix"], rng)
            values.append(series); generated.append(record)
    if [item["series_id"] for item in generated] != [item["series_id"] for item in records]:
        raise RuntimeError("materialized test roster differs from sealed test roster")
    save_npz(target, values=np.stack(values))


def make_dataset(values: np.ndarray, records: list[dict], settings: dict, horizon: int) -> tuple[WindowDataset, np.ndarray, np.ndarray, np.ndarray]:
    maximum_horizon, input_length = int(settings["maximum_horizon"]), int(settings["input_length"])
    infos = [SeriesInfo(item["series_id"], int(settings["seasonal_period"]), len(values[0]), len(values[0]), "ocra_v1", item["mechanism"], 0.0, int(item["change_point"])) for item in records]
    origins = make_origins(values, infos, input_length, maximum_horizon, "all", int(read_json(CONFIG / "protocol.json")["test_origin_stride"]))
    dataset = WindowDataset(values, infos, origins, input_length, int(horizon), 1e-6, float("inf"))
    labels = np.asarray([true_label(records[int(series)], int(origin), maximum_horizon, int(settings["change_signal_delay"])) for series, origin in origins], dtype="U16")
    mechanisms = np.asarray([records[int(series)]["mechanism"] for series, _ in origins], dtype="U24")
    protocol = read_json(CONFIG / "protocol.json")
    extractor = ocra_v1_1_features if protocol.get("feature_variant") in {"v1_1", "v1_2"} else ocra_features
    features = np.stack([extractor(values[int(series), int(origin) - input_length:int(origin)], int(settings["seasonal_period"])) for series, origin in origins])
    return dataset, labels, mechanisms, features


def certificate_labels(mechanisms: np.ndarray, labels: np.ndarray, series_indices: np.ndarray, origins: np.ndarray, records: list[dict], protocol: dict) -> tuple[np.ndarray, np.ndarray]:
    """Apply the versioned action/estimator definitions at origin level."""
    variant = str(protocol.get("feature_variant", "v1"))
    lookback = int(protocol.get("level_shift_visible_lookback", 192))
    targets, sets = [], []
    for mechanism, label, series, origin in zip(mechanisms.astype(str), labels.astype(str), series_indices, origins):
        change_point = int(records[int(series)]["change_point"])
        if variant in {"v1_1", "v1_2"}:
            target_fn = target_action_v1_2 if variant == "v1_2" else target_action_v1_1
            set_fn = evaluation_set_v1_1 if variant == "v1_1" else evaluation_set_v1_2
            targets.append(target_fn(mechanism, label, int(origin), change_point, lookback))
            sets.append(set_fn(mechanism, label, int(origin), change_point, lookback) or "other")
        else:
            targets.append(target_action(mechanism, label))
            sets.append(evaluation_set(mechanism, label) or "other")
    return np.asarray(targets, dtype="U20"), np.asarray(sets, dtype="U24")


def loader(dataset: WindowDataset, seed: int, batch_size: int, *, samples: int | None = None) -> DataLoader:
    if samples is None:
        return DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0, pin_memory=True)
    generator = torch.Generator().manual_seed(int(seed))
    return DataLoader(dataset, batch_size=batch_size, sampler=RandomSampler(dataset, replacement=True, num_samples=int(samples), generator=generator), num_workers=0, pin_memory=True)


def _forward(model: torch.nn.Module, batch: dict, device: torch.device) -> dict[str, torch.Tensor]:
    x, phi = batch["x"].to(device), batch["phi"].to(device)
    return model(x, phi)


def train_model(model: torch.nn.Module, train: WindowDataset, validation: WindowDataset, device: torch.device, seed: int, training: dict, checkpoint: Path) -> dict:
    if not any(parameter.requires_grad for parameter in model.parameters()):
        return {"status": "deterministic", "epochs": 0}
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(training["learning_rate"]), weight_decay=float(training["weight_decay"]))
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda" and bool(training["amp"]))
    best, stale = float("inf"), 0
    batch_size = int(os.environ.get("OCRA_V1_BATCH_SIZE", training["batch_size"]))
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    for epoch in range(1, int(training["max_epochs"]) + 1):
        model.train()
        for batch in loader(train, seed + epoch, batch_size, samples=int(training["samples_per_epoch"])):
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, enabled=device.type == "cuda" and bool(training["amp"])):
                loss = torch.mean((_forward(model, batch, device)["forecast"] - batch["y"].to(device)) ** 2)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), float(training["gradient_clip_norm"]))
            scaler.step(optimizer)
            scaler.update()
        model.eval(); total = 0.0; count = 0
        with torch.no_grad():
            for batch in loader(validation, seed, batch_size):
                with torch.autocast(device_type=device.type, enabled=device.type == "cuda" and bool(training["amp"])):
                    loss = torch.mean((_forward(model, batch, device)["forecast"] - batch["y"].to(device)) ** 2)
                total += float(loss) * len(batch["x"]); count += len(batch["x"])
        value = total / max(count, 1)
        if value < best:
            best, stale = value, 0
            torch.save({"model": model.state_dict(), "seed": seed, "validation_mse": best}, checkpoint)
        else:
            stale += 1
            if stale >= int(training["patience"]):
                break
    model.load_state_dict(torch.load(checkpoint, map_location=device, weights_only=True)["model"])
    return {"status": "complete", "epochs": epoch, "best_validation_mse": best, "batch_size": batch_size}


def collect(model: torch.nn.Module, dataset: WindowDataset, device: torch.device, seed: int, features: np.ndarray, labels: np.ndarray, mechanisms: np.ndarray) -> dict[str, np.ndarray]:
    collected: dict[str, list[np.ndarray]] = defaultdict(list)
    model.eval(); offset = 0
    with torch.no_grad():
        for batch in loader(dataset, seed, 128):
            value = _forward(model, batch, device)
            size = len(batch["x"])
            for key, tensor in (("prediction", value["forecast"]), ("target", batch["y"]), ("residual", value["residual"]), ("gate", value["gate"])):
                collected[key].append(tensor.detach().cpu().numpy())
            for key in ("series_index", "origin"):
                collected[key].append(batch[key].numpy())
            collected["psi"].append(features[offset:offset + size])
            collected["true_label"].append(labels[offset:offset + size])
            collected["mechanism"].append(mechanisms[offset:offset + size])
            offset += size
    return {key: np.concatenate(value) for key, value in collected.items()}


def bundle(horizon: int, seed: int, *, preflight: bool = False) -> None:
    protocol, settings, spec, destination = _require_sealed()
    if horizon not in protocol["horizons"] or seed not in protocol["training_seeds"]:
        raise ValueError("horizon or seed not registered in sealed OCRA-v1 protocol")
    if preflight and (horizon, seed) != (24, int(protocol["training_seeds"][0])):
        raise ValueError("the only registered preflight bundle is H=24 with the first sealed training seed")
    device = device_for(protocol); set_seed(seed)
    train_values, train_records = _load_split(destination, "train")
    validation_values, validation_records = _load_split(destination, "validation")
    train_ds, train_labels, train_mechanisms, train_psi = make_dataset(train_values, train_records, settings, horizon)
    valid_ds, valid_labels, valid_mechanisms, valid_psi = make_dataset(validation_values, validation_records, settings, horizon)
    model_ids = ["M2"] if preflight else protocol["models"]
    root = destination["bundles"] / f"h{horizon}-s{seed}"
    started = time.monotonic()
    for model_id in model_ids:
        model_root, manifest = root / model_id, root / model_id / "run_manifest.json"
        if manifest.is_file() and read_json(manifest).get("status") == "complete":
            continue
        atomic_write_json(manifest, {"status": "running", "model": model_id, "horizon": horizon, "seed": seed, "started_at": utc_now(), "split_access": ["train", "validation"]})
        try:
            model = build_model(model_id, horizon, len(train_ds[0]["phi"]), spec, int(settings["input_length"]), int(settings["seasonal_period"])).to(device)
            training = train_model(model, train_ds, valid_ds, device, seed, protocol["training"], model_root / "checkpoint.pt")
            arrays = collect(model, valid_ds, device, seed, valid_psi, valid_labels, valid_mechanisms)
            save_npz(model_root / "validation_predictions.npz", **arrays)
            payload = {"status": "complete", "model": model_id, "horizon": horizon, "seed": seed, "finished_at": utc_now(), "training": training, "checkpoint_sha256": sha256_path(model_root / "checkpoint.pt") if (model_root / "checkpoint.pt").is_file() else None, "validation_sha256": sha256_path(model_root / "validation_predictions.npz"), "config_hashes": config_hashes(), "code_hashes": code_hashes(), "git": git_state(), "split_access": ["train", "validation"]}
        except Exception as exc:
            payload = {"status": "failed", "model": model_id, "horizon": horizon, "seed": seed, "finished_at": utc_now(), "error": repr(exc), "split_access": ["train", "validation"]}
            destination["failures"].mkdir(parents=True, exist_ok=True)
            atomic_write_json(destination["failures"] / f"h{horizon}-s{seed}-{model_id}.json", payload)
            atomic_write_json(manifest, payload)
            raise
        atomic_write_json(manifest, payload)
    elapsed = time.monotonic() - started
    atomic_write_json(root / "bundle_manifest.json", {"status": "complete", "horizon": horizon, "seed": seed, "preflight": preflight, "elapsed_seconds": elapsed, "models": model_ids, "test_loaded": False})
    print(json.dumps({"status": "complete", "bundle": f"h{horizon}-s{seed}", "elapsed_seconds": elapsed}, indent=2))


def _load_validation_model(destination: dict[str, Path], model: str, seed: int, horizon: int = 96) -> dict[str, np.ndarray]:
    path = destination["bundles"] / f"h{horizon}-s{seed}" / model / "validation_predictions.npz"
    if not path.is_file():
        raise RuntimeError(f"missing validation prediction: {path}")
    with np.load(path) as payload:
        return {key: payload[key] for key in payload.files}


def _mean_validation_predictions(destination: dict[str, Path], protocol: dict, model: str) -> dict[str, np.ndarray]:
    records = [_load_validation_model(destination, model, int(seed)) for seed in protocol["training_seeds"]]
    reference = records[0]
    for item in records[1:]:
        for key in ("series_index", "origin", "true_label", "mechanism", "psi"):
            if not np.array_equal(reference[key], item[key]):
                raise RuntimeError(f"validation alignment mismatch for {model}:{key}")
    output = {key: reference[key] for key in ("series_index", "origin", "true_label", "mechanism", "psi", "target")}
    for key in ("prediction", "residual", "gate"):
        output[key] = np.mean([item[key] for item in records], axis=0)
    return output


def _fit_logistic(features: np.ndarray, target: np.ndarray, c_grid: list[float], folds: int) -> tuple[LogisticRegression, float]:
    target = np.asarray(target, dtype=int)
    if len(np.unique(target)) != 2:
        raise RuntimeError("certificate target contains fewer than two classes")
    counts = np.bincount(target)
    usable_folds = min(int(folds), int(counts.min()))
    if usable_folds < 2:
        raise RuntimeError("certificate target has insufficient class support for cross-validation")
    splitter = StratifiedKFold(n_splits=usable_folds, shuffle=True, random_state=20261020)
    scores: dict[float, float] = {}
    for candidate in c_grid:
        losses = []
        for train, test in splitter.split(features, target):
            fitted = LogisticRegression(C=float(candidate), penalty="l2", solver="liblinear", max_iter=2000, random_state=20261020).fit(features[train], target[train])
            probability = np.clip(fitted.predict_proba(features[test])[:, 1], 1e-12, 1 - 1e-12)
            losses.append(float(-np.mean(target[test] * np.log(probability) + (1 - target[test]) * np.log(1 - probability))))
        scores[float(candidate)] = float(np.mean(losses))
    chosen = min(scores, key=scores.get)
    return LogisticRegression(C=chosen, penalty="l2", solver="liblinear", max_iter=2000, random_state=20261020).fit(features, target), chosen


def _select_open_threshold(probability: np.ndarray, sets: np.ndarray, policy: dict) -> float:
    positive, negatives = sets == "S+", np.isin(sets, ("N0", "N2", "N7", "N8"))
    candidates = np.unique(np.concatenate(([0.0, 1.0], probability)))
    feasible = []
    for threshold in candidates:
        action = probability >= threshold
        if np.mean(action[positive]) >= float(policy["positive_open_minimum"]) and all(np.mean(action[sets == name]) <= float(policy["negative_open_maximum"]) for name in ("N0", "N2", "N7", "N8")):
            feasible.append((float(np.mean([np.mean(action[sets == name]) for name in ("N0", "N2", "N7", "N8")])), -float(np.mean(action[positive])), float(threshold)))
    if not feasible:
        constrained = [(float(np.mean(action[negatives])), -float(np.mean(action[positive])), float(threshold)) for threshold in candidates for action in (probability >= threshold,) if np.mean(action[negatives]) <= float(policy["negative_open_maximum"])]
        if not constrained:
            raise RuntimeError("no feasible OPEN threshold on validation")
        return min(constrained)[2]
    return min(feasible)[2]


def _select_defer_threshold(probability: np.ndarray, open_probability: np.ndarray, sets: np.ndarray, policy: dict, open_threshold: float) -> float:
    candidates = np.unique(np.concatenate(([0.0, 1.0], probability)))
    for threshold in sorted(candidates):
        actions = action_from_probabilities(open_probability, probability, open_threshold, float(threshold))
        if np.mean(actions[sets == "T1-vis"] == "DEFER") < 0.8 or np.mean(actions[sets == "T1-vis"] == "OPEN") > 0.1:
            continue
        if any(np.mean(actions[sets == name] == "DEFER") > float(policy["negative_defer_maximum"]) for name in ("N0", "N2", "N8")):
            continue
        if np.mean(actions[sets == "N7"] == "CLOSED") < float(policy["variance_closed_minimum"]):
            continue
        return float(threshold)
    raise RuntimeError("no feasible DEFER threshold on validation")


def _select_defer_first_threshold(probability: np.ndarray, sets: np.ndarray, policy: dict) -> float:
    candidates = np.unique(np.concatenate(([0.0, 1.0], probability)))
    valid = []
    for threshold in candidates:
        defer = probability >= threshold
        if np.mean(defer[sets == "T1-vis"]) < 0.8:
            continue
        if any(np.mean(defer[sets == name]) > float(policy["negative_defer_maximum"]) for name in ("N0", "N2", "N8")):
            continue
        if np.mean(~defer[sets == "N7"]) < float(policy["variance_closed_minimum"]):
            continue
        valid.append((float(np.mean([np.mean(defer[sets == name]) for name in ("N0", "N2", "N8")])), float(threshold)))
    if not valid:
        raise RuntimeError("no feasible DEFER-first threshold on validation")
    return min(valid)[1]


def action_defer_first(defer_probability: np.ndarray, open_probability: np.ndarray, defer_threshold: float, open_threshold: float) -> np.ndarray:
    defer_probability = np.asarray(defer_probability, dtype=np.float64)
    open_probability = np.asarray(open_probability, dtype=np.float64)
    return np.where(defer_probability >= defer_threshold, "DEFER", np.where(open_probability >= open_threshold, "OPEN", "CLOSED"))


def _select_open_after_defer(open_probability: np.ndarray, defer_probability: np.ndarray, sets: np.ndarray, defer_threshold: float, policy: dict) -> float:
    candidates = np.unique(np.concatenate(([0.0, 1.0], open_probability)))
    valid = []
    for threshold in candidates:
        action = action_defer_first(defer_probability, open_probability, defer_threshold, float(threshold))
        if np.mean(action[sets == "S+"] == "OPEN") < float(policy["positive_open_minimum"]):
            continue
        if any(np.mean(action[sets == name] == "OPEN") > float(policy["negative_open_maximum"]) for name in ("N0", "N2", "N7", "N8")):
            continue
        valid.append((float(np.mean([np.mean(action[sets == name] == "OPEN") for name in ("N0", "N2", "N7", "N8")])), -float(np.mean(action[sets == "S+"] == "OPEN")), float(threshold)))
    if not valid:
        raise RuntimeError("no feasible OPEN-after-DEFER threshold on validation")
    return min(valid)[2]


def fit_certificate() -> None:
    protocol, _, _, destination = _require_sealed()
    if not all((destination["bundles"] / f"h96-s{seed}" / "M2" / "validation_predictions.npz").is_file() for seed in protocol["training_seeds"]):
        raise RuntimeError("all H=96 validation bundles are required before E2")
    m2, m0, dlinear = (_mean_validation_predictions(destination, protocol, model) for model in ("M2", "M0", "DLinear"))
    mechanisms, labels = m2["mechanism"].astype(str), m2["true_label"].astype(str)
    records = read_json(destination["data"] / "validation_roster.json")["records"]
    targets, sets = certificate_labels(mechanisms, labels, m2["series_index"], m2["origin"], records, protocol)
    scaling, normalized = normalize_from_validation(m2["psi"], m2["psi"])
    features = normalized[0]
    certificate = protocol["certificate"]
    if protocol.get("feature_variant") == "v1_2":
        defer_model, defer_c = _fit_logistic(features, targets == "DEFER", certificate["c_grid"], certificate["folds"])
        defer_probability = defer_model.predict_proba(features)[:, 1]
        defer_threshold = _select_defer_first_threshold(defer_probability, sets, certificate)
        non_defer = targets != "DEFER"
        open_model, open_c = _fit_logistic(features[non_defer], targets[non_defer] == "OPEN", certificate["c_grid"], certificate["folds"])
        open_probability = open_model.predict_proba(features)[:, 1]
        open_threshold = _select_open_after_defer(open_probability, defer_probability, sets, defer_threshold, certificate)
        actions = action_defer_first(defer_probability, open_probability, defer_threshold, open_threshold)
    else:
        open_model, open_c = _fit_logistic(features, targets == "OPEN", certificate["c_grid"], certificate["folds"])
        non_open = targets != "OPEN"
        defer_model, defer_c = _fit_logistic(features[non_open], targets[non_open] == "DEFER", certificate["c_grid"], certificate["folds"])
        open_probability = open_model.predict_proba(features)[:, 1]
        defer_probability = defer_model.predict_proba(features)[:, 1]
        open_threshold = _select_open_threshold(open_probability, sets, certificate)
        defer_threshold = _select_defer_threshold(defer_probability, open_probability, sets, certificate, open_threshold)
        actions = action_from_probabilities(open_probability, defer_probability, open_threshold, defer_threshold)
    m2_error = np.mean((m2["prediction"] - m2["target"]) ** 2, axis=1)
    m0_error = np.mean((m0["prediction"] - m0["target"]) ** 2, axis=1)
    dlinear_error = np.mean((dlinear["prediction"] - dlinear["target"]) ** 2, axis=1)
    gain_model, gain_c = _fit_logistic(features, (m2_error < m0_error) & (m2_error < dlinear_error), certificate["c_grid"], certificate["folds"])
    gain_probability = gain_model.predict_proba(features)[:, 1]
    target_rate = float(np.mean(actions[sets == "S+"] == "OPEN"))
    candidates = np.unique(gain_probability)
    gain_threshold = min(candidates, key=lambda threshold: abs(float(np.mean(gain_probability[sets == "S+"] >= threshold)) - target_rate))
    achieved = float(np.mean(gain_probability[sets == "S+"] >= gain_threshold))
    if abs(achieved - target_rate) > float(certificate["gain_gate_match_tolerance"]):
        raise RuntimeError("GainGate cannot match OCRA validation positive admission rate")
    negative_open = [float(np.mean(actions[sets == name] == "OPEN")) for name in ("N0", "N2", "N7", "N8")]
    gain_false_open = float(np.mean([np.mean(gain_probability[sets == name] >= gain_threshold) for name in ("N0", "N2", "N7", "N8")]))
    delta_star = min(0.10, 0.5 * gain_false_open)
    if gain_false_open < 0.05:
        raise RuntimeError("GainGate validation macro false-open is below 0.05; stop rule 3")
    with (destination["protocol"] / "certificate_model.pkl").open("wb") as handle:
        pickle.dump({"open": open_model, "defer": defer_model, "gain": gain_model}, handle)
    feature_names = OCRA_V1_1_FEATURE_NAMES if protocol.get("feature_variant") in {"v1_1", "v1_2"} else OCRA_FEATURE_NAMES
    thresholds = {"created_at": utc_now(), "feature_names": list(feature_names), "standardization": scaling, "open_threshold": open_threshold, "defer_threshold": defer_threshold, "gain_threshold": float(gain_threshold), "open_C": open_c, "defer_C": defer_c, "gain_C": gain_c, "validation_positive_open_rate": target_rate, "validation_gain_open_rate": achieved, "validation_macro_false_open": float(np.mean(negative_open)), "delta_star": delta_star, "test_loaded": False}
    atomic_write_json(destination["protocol"] / "action_thresholds.json", thresholds)
    rows = []
    for name in ("N0", "N2", "N7", "N8", "S+", "T1-vis"):
        selected = sets == name
        rows.append({"set": name, "origins": int(selected.sum()), "open_rate": float(np.mean(actions[selected] == "OPEN")), "defer_rate": float(np.mean(actions[selected] == "DEFER")), "closed_rate": float(np.mean(actions[selected] == "CLOSED"))})
    write_csv(destination["tables"] / "e2_confusion.csv", rows, ["set", "origins", "open_rate", "defer_rate", "closed_rate"])
    atomic_write_json(destination["protocol"] / "e2_status.json", {"status": "passed", "created_at": utc_now(), "thresholds_sha256": sha256_path(destination["protocol"] / "action_thresholds.json"), "test_loaded": False})
    print(json.dumps({"status": "passed", "delta_star": delta_star, "open_threshold": open_threshold, "defer_threshold": defer_threshold}, indent=2))


def _load_model_checkpoint(model_id: str, horizon: int, seed: int, spec: dict, settings: dict, destination: dict[str, Path], device: torch.device) -> torch.nn.Module:
    model = build_model(model_id, horizon, 9, spec, int(settings["input_length"]), int(settings["seasonal_period"])).to(device)
    checkpoint = destination["bundles"] / f"h{horizon}-s{seed}" / model_id / "checkpoint.pt"
    if checkpoint.is_file():
        model.load_state_dict(torch.load(checkpoint, map_location=device, weights_only=True)["model"])
    elif any(parameter.requires_grad for parameter in model.parameters()):
        raise RuntimeError(f"missing checkpoint: {checkpoint}")
    return model


def _test_access(destination: dict[str, Path]) -> None:
    access = destination["protocol"] / "test_access.json"
    if access.exists():
        raise RuntimeError("test data was already evaluated; create ocra_v1.1 for a new evaluation")
    atomic_write_json(access, {"accessed_at": utc_now(), "purpose": "E3-E7 one-time evaluation", "immutable": True})


def evaluate_once() -> None:
    protocol, settings, spec, destination = _require_sealed()
    if not (destination["protocol"] / "e2_status.json").is_file() or read_json(destination["protocol"] / "e2_status.json").get("status") != "passed":
        raise RuntimeError("E2 calibration must pass before the first test load")
    thresholds = read_json(destination["protocol"] / "action_thresholds.json")
    with (destination["protocol"] / "certificate_model.pkl").open("rb") as handle:
        certificate = pickle.load(handle)
    _test_access(destination)
    try:
        materialize_test(destination, protocol, settings)
        values, records = _load_split(destination, "test", allow_test=True)
        mean, scale = np.asarray(thresholds["standardization"]["mean"]), np.asarray(thresholds["standardization"]["scale"])
        all_rows: list[dict] = []
        for horizon in protocol["horizons"]:
            dataset, labels, mechanisms, psi = make_dataset(values, records, settings, int(horizon))
            normalized = ((psi - mean) / scale).astype(np.float32)
            open_probability = certificate["open"].predict_proba(normalized)[:, 1]
            defer_probability = certificate["defer"].predict_proba(normalized)[:, 1]
            gain_probability = certificate["gain"].predict_proba(normalized)[:, 1]
            actions = action_defer_first(defer_probability, open_probability, thresholds["defer_threshold"], thresholds["open_threshold"]) if protocol.get("feature_variant") == "v1_2" else action_from_probabilities(open_probability, defer_probability, thresholds["open_threshold"], thresholds["defer_threshold"])
            gain_actions = np.where(gain_probability >= thresholds["gain_threshold"], "OPEN", "CLOSED")
            predictions: dict[str, list[np.ndarray]] = defaultdict(list)
            targets: list[np.ndarray] = []
            device = device_for(protocol)
            for seed in protocol["training_seeds"]:
                for model_id in protocol["models"]:
                    model = _load_model_checkpoint(model_id, int(horizon), int(seed), spec, settings, destination, device)
                    packed = collect(model, dataset, device, int(seed), psi, labels, mechanisms)
                    predictions[model_id].append(packed["prediction"])
                    if model_id == "M0": targets.append(packed["target"])
                    save_npz(destination["forecasts"] / f"test-h{horizon}-s{seed}-{model_id}.npz", **packed)
            average = {name: np.mean(parts, axis=0) for name, parts in predictions.items()}
            target = targets[0]
            mixed = np.where((actions == "OPEN")[:, None], average["M2"], np.where((actions == "DEFER")[:, None], average["DLinear"], average["M0"]))
            gain_mixed = np.where((gain_actions == "OPEN")[:, None], average["M2"], average["M0"])
            _, sets = certificate_labels(mechanisms, labels, dataset.origins[:, 0], dataset.origins[:, 1], records, protocol)
            save_npz(destination["forecasts"] / f"test-h{horizon}-ocra.npz", target=target, m0=average["M0"], m1=average["M1"], dlinear=average["DLinear"], m2=average["M2"], ocra=mixed, gain_gate=gain_mixed, action=actions, gain_action=gain_actions, true_label=labels, mechanism=mechanisms, series_index=dataset.origins[:, 0], origin=dataset.origins[:, 1], psi=psi)
            for name in ("N0", "N2", "N7", "N8", "S+", "T1-vis", "T1-post-observable", "trend-diagnostic"):
                mask = sets == name
                if not np.any(mask):
                    continue
                for model_name, prediction in (("OCRA", mixed), ("GainGate", gain_mixed), ("M0", average["M0"]), ("M1", average["M1"]), ("DLinear", average["DLinear"]), ("M2", average["M2"])):
                    all_rows.append({"horizon": horizon, "set": name, "model": model_name, "origins": int(mask.sum()), "rmse": float(np.sqrt(np.mean((prediction[mask] - target[mask]) ** 2))), "open_rate": float(np.mean(actions[mask] == "OPEN")) if model_name == "OCRA" else float(np.mean(gain_actions[mask] == "OPEN")) if model_name == "GainGate" else "", "defer_rate": float(np.mean(actions[mask] == "DEFER")) if model_name == "OCRA" else ""})
        write_csv(destination["metrics"] / "e3_main_metrics.csv", all_rows, ["horizon", "set", "model", "origins", "rmse", "open_rate", "defer_rate"])
        atomic_write_json(destination["protocol"] / "test_access.json", {"accessed_at": read_json(destination["protocol"] / "test_access.json")["accessed_at"], "completed_at": utc_now(), "purpose": "E3-E7 one-time evaluation", "immutable": True, "metrics_sha256": sha256_path(destination["metrics"] / "e3_main_metrics.csv")})
    except Exception:
        raise
    print(json.dumps({"status": "complete", "test_access": "sealed", "metrics": str(destination["metrics"] / "e3_main_metrics.csv")}, indent=2))


def _test_payload(destination: dict[str, Path], horizon: int) -> dict[str, np.ndarray]:
    path = destination["forecasts"] / f"test-h{horizon}-ocra.npz"
    if not path.is_file():
        raise RuntimeError(f"missing one-time test forecast: {path}")
    with np.load(path) as payload:
        return {key: payload[key] for key in payload.files}


def _set_rates(action: np.ndarray, sets: np.ndarray, series: np.ndarray, set_name: str) -> np.ndarray:
    """One action rate per independent series, never per origin pseudo-replicate."""
    selected = sets == set_name
    return np.asarray([np.mean(action[selected & (series == identifier)] == "OPEN") for identifier in np.unique(series[selected])], dtype=np.float64)


def _bootstrap_macro_difference(ocra: dict[str, np.ndarray], gain: dict[str, np.ndarray], replicates: int) -> tuple[float, float, float]:
    names, generator = ("N0", "N2", "N7", "N8"), np.random.default_rng(20261020)
    point = float(np.mean([np.mean(ocra[name]) - np.mean(gain[name]) for name in names]))
    draws = np.empty(int(replicates), dtype=np.float64)
    for index in range(len(draws)):
        draws[index] = float(np.mean([np.mean(ocra[name][generator.integers(len(ocra[name]), size=len(ocra[name]))]) - np.mean(gain[name][generator.integers(len(gain[name]), size=len(gain[name]))]) for name in names]))
    return point, float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))


def _series_rmse(prediction: np.ndarray, target: np.ndarray, series: np.ndarray, selected: np.ndarray) -> np.ndarray:
    return np.asarray([np.sqrt(np.mean((prediction[selected & (series == identifier)] - target[selected & (series == identifier)]) ** 2)) for identifier in np.unique(series[selected])], dtype=np.float64)


def _fit_ablation_actions(destination: dict[str, Path], protocol: dict, feature_indices: list[int] | None, *, binary: bool = False) -> tuple[np.ndarray, dict]:
    """Refit only certificate layers on validation and apply them to frozen H=96 test features."""
    m2, m0, dlinear = (_mean_validation_predictions(destination, protocol, model) for model in ("M2", "M0", "DLinear"))
    test = _test_payload(destination, 96)
    mechanisms, labels = m2["mechanism"].astype(str), m2["true_label"].astype(str)
    validation_records = read_json(destination["data"] / "validation_roster.json")["records"]
    targets, sets = certificate_labels(mechanisms, labels, m2["series_index"], m2["origin"], validation_records, protocol)
    valid_features, test_features = m2["psi"], test["psi"]
    if feature_indices is not None:
        valid_features, test_features = valid_features[:, feature_indices], test_features[:, feature_indices]
    scaling, normalized = normalize_from_validation(valid_features, valid_features, test_features)
    validation, test_normalized = normalized
    policy = protocol["certificate"]
    if protocol.get("feature_variant") == "v1_2":
        defer_model, _ = _fit_logistic(validation, targets == "DEFER", policy["c_grid"], policy["folds"])
        defer_probability = defer_model.predict_proba(validation)[:, 1]
        defer_threshold = _select_defer_first_threshold(defer_probability, sets, policy)
        non_defer = targets != "DEFER"
        open_model, _ = _fit_logistic(validation[non_defer], targets[non_defer] == "OPEN", policy["c_grid"], policy["folds"])
        open_probability = open_model.predict_proba(validation)[:, 1]
        open_threshold = _select_open_after_defer(open_probability, defer_probability, sets, defer_threshold, policy)
        test_open, test_defer = open_model.predict_proba(test_normalized)[:, 1], defer_model.predict_proba(test_normalized)[:, 1]
        if binary:
            return np.where(test_open >= open_threshold, "OPEN", "CLOSED"), {"open_threshold": open_threshold, "standardization": scaling}
        return action_defer_first(test_defer, test_open, defer_threshold, open_threshold), {"open_threshold": open_threshold, "defer_threshold": defer_threshold, "standardization": scaling}
    open_model, _ = _fit_logistic(validation, targets == "OPEN", policy["c_grid"], policy["folds"])
    open_probability = open_model.predict_proba(validation)[:, 1]
    open_threshold = _select_open_threshold(open_probability, sets, policy)
    test_open = open_model.predict_proba(test_normalized)[:, 1]
    if binary:
        return np.where(test_open >= open_threshold, "OPEN", "CLOSED"), {"open_threshold": open_threshold, "standardization": scaling}
    non_open = targets != "OPEN"
    defer_model, _ = _fit_logistic(validation[non_open], targets[non_open] == "DEFER", policy["c_grid"], policy["folds"])
    defer_probability = defer_model.predict_proba(validation)[:, 1]
    defer_threshold = _select_defer_threshold(defer_probability, open_probability, sets, policy, open_threshold)
    return action_from_probabilities(test_open, defer_model.predict_proba(test_normalized)[:, 1], open_threshold, defer_threshold), {"open_threshold": open_threshold, "defer_threshold": defer_threshold, "standardization": scaling}


def analyze() -> None:
    protocol, _, _, destination = _require_sealed()
    if not (destination["protocol"] / "test_access.json").is_file():
        raise RuntimeError("evaluate-once must complete before analysis")
    thresholds = read_json(destination["protocol"] / "action_thresholds.json")
    all_e4, all_e5, main_rows = [], [], []
    for horizon in protocol["horizons"]:
        payload = _test_payload(destination, int(horizon))
        mechanisms, labels, series = payload["mechanism"].astype(str), payload["true_label"].astype(str), payload["series_index"]
        test_records = read_json(destination["data"] / "test_roster.json")["records"]
        _, sets = certificate_labels(mechanisms, labels, payload["series_index"], payload["origin"], test_records, protocol)
        action, gain_action = payload["action"].astype(str), payload["gain_action"].astype(str)
        for set_name in ("N0", "N2", "N7", "N8", "S+", "T1-vis", "T1-post-observable", "trend-diagnostic"):
            mask = sets == set_name
            if not mask.any():
                continue
            row = {"horizon": horizon, "set": set_name, "origins": int(mask.sum()), "open_rate": float(np.mean(action[mask] == "OPEN")), "defer_rate": float(np.mean(action[mask] == "DEFER")), "closed_rate": float(np.mean(action[mask] == "CLOSED")), "gain_open_rate": float(np.mean(gain_action[mask] == "OPEN"))}
            (all_e5 if set_name in {"N0", "N2", "N7", "N8"} else all_e4).append(row)
        for mechanism in ("trend_break", "seasonal_change", "visible_level_shift"):
            mask = mechanisms == mechanism
            if not mask.any():
                continue
            for name, prediction in (("OCRA", payload["ocra"]), ("M0", payload["m0"]), ("M1", payload["m1"]), ("DLinear", payload["dlinear"]), ("M2", payload["m2"])):
                errors = _series_rmse(prediction, payload["target"], series, mask)
                main_rows.append({"horizon": horizon, "mechanism": mechanism, "model": name, "series": len(errors), "mean_series_rmse": float(np.mean(errors))})
    write_csv(destination["tables"] / "e4_positive_and_defer.csv", all_e4, ["horizon", "set", "origins", "open_rate", "defer_rate", "closed_rate", "gain_open_rate"])
    write_csv(destination["tables"] / "e5_negative_controls.csv", all_e5, ["horizon", "set", "origins", "open_rate", "defer_rate", "closed_rate", "gain_open_rate"])
    write_csv(destination["tables"] / "e4_intention_rmse.csv", main_rows, ["horizon", "mechanism", "model", "series", "mean_series_rmse"])
    reference = _test_payload(destination, 96)
    test_records = read_json(destination["data"] / "test_roster.json")["records"]
    _, reference_sets = certificate_labels(reference["mechanism"].astype(str), reference["true_label"].astype(str), reference["series_index"], reference["origin"], test_records, protocol)
    ocra_rates = {name: _set_rates(reference["action"].astype(str), reference_sets, reference["series_index"], name) for name in ("N0", "N2", "N7", "N8")}
    gain_rates = {name: _set_rates(reference["gain_action"].astype(str), reference_sets, reference["series_index"], name) for name in ("N0", "N2", "N7", "N8")}
    difference, ci_low, ci_high = _bootstrap_macro_difference(ocra_rates, gain_rates, int(protocol["evaluation"]["bootstrap_replicates"]))
    e3 = {"horizon_for_actions": 96, "macro_false_open_difference_ocra_minus_gain": difference, "bootstrap_ci_low": ci_low, "bootstrap_ci_high": ci_high, "delta_star": thresholds["delta_star"], "validation_open_rate_matched": abs(thresholds["validation_positive_open_rate"] - thresholds["validation_gain_open_rate"]) <= protocol["certificate"]["gain_gate_match_tolerance"]}
    atomic_write_json(destination["tables"] / "e3_bootstrap.json", e3)
    feature_names = OCRA_V1_1_FEATURE_NAMES if protocol.get("feature_variant") == "v1_1" else OCRA_FEATURE_NAMES
    full_indices = list(range(len(feature_names)))
    no_stable = [index for index in full_indices if index not in {9, 10}]
    no_direction = [index for index in full_indices if index not in {3, 4, 5, 11}]
    ablations = []
    variants = {"no-stable-test": (no_stable, False), "no-direction": (no_direction, False), "binary-action": (full_indices, True)}
    for name, (indices, binary) in variants.items():
        action, _ = _fit_ablation_actions(destination, protocol, indices, binary=binary)
        macro_false_open = float(np.mean([np.mean(action[reference_sets == set_name] == "OPEN") for set_name in ("N0", "N2", "N7", "N8")]))
        admission = float(np.mean(action[reference_sets == "S+"] == "OPEN"))
        ablations.append({"variant": name, "macro_false_open": macro_false_open, "positive_open_rate": admission})
    shuffled_psi = reference["psi"].copy()
    generator = np.random.default_rng(20261020)
    for mechanism in np.unique(reference["mechanism"]):
        selected = reference["mechanism"] == mechanism
        shuffled_psi[selected] = shuffled_psi[selected][generator.permutation(int(selected.sum()))]
    standardization = thresholds["standardization"]
    normalized = (shuffled_psi - np.asarray(standardization["mean"])) / np.asarray(standardization["scale"])
    with (destination["protocol"] / "certificate_model.pkl").open("rb") as handle:
        certificate = pickle.load(handle)
    shuffled_action = action_from_probabilities(certificate["open"].predict_proba(normalized)[:, 1], certificate["defer"].predict_proba(normalized)[:, 1], thresholds["open_threshold"], thresholds["defer_threshold"])
    ablations.append({"variant": "shuffled-evidence", "macro_false_open": float(np.mean([np.mean(shuffled_action[reference_sets == set_name] == "OPEN") for set_name in ("N0", "N2", "N7", "N8")])), "positive_open_rate": float(np.mean(shuffled_action[reference_sets == "S+"] == "OPEN"))})
    write_csv(destination["tables"] / "e6_ablations.csv", ablations, ["variant", "macro_false_open", "positive_open_rate"])
    full_macro = float(np.mean([np.mean(reference["action"].astype(str)[reference_sets == set_name] == "OPEN") for set_name in ("N0", "N2", "N7", "N8")]))
    full_positive = float(np.mean(reference["action"].astype(str)[reference_sets == "S+"] == "OPEN"))
    c1 = bool(e3["validation_open_rate_matched"] and ci_high < 0 and difference <= -float(thresholds["delta_star"]))
    c2 = all(row["open_rate"] <= 0.10 for row in all_e5 if row["horizon"] == 96) and all(row["defer_rate"] <= 0.20 for row in all_e5 if row["horizon"] == 96 and row["set"] != "N7") and next(row["closed_rate"] for row in all_e5 if row["horizon"] == 96 and row["set"] == "N7") >= 0.80
    c4_row = next(row for row in all_e4 if row["horizon"] == 96 and row["set"] == "T1-vis")
    c4 = bool(c4_row["defer_rate"] >= 0.80 and c4_row["open_rate"] <= 0.10)
    verdicts = [{"claim": "C1", "status": "supported" if c1 else "invalidated", "detail": "matched macro false-open bootstrap"}, {"claim": "C2", "status": "supported" if c2 else "invalidated", "detail": "H=96 action safety limits"}, {"claim": "C3", "status": "pending", "detail": "requires registered Holm/non-inferiority analysis"}, {"claim": "C4", "status": "supported" if c4 else "invalidated", "detail": "T1-vis routing; RMSE non-inferiority reported separately"}, {"claim": "C5", "status": "supported" if abs(ablations[-1]["macro_false_open"] - full_macro) >= 0.08 else "invalidated", "detail": "within-mechanism shuffled evidence"}, {"claim": "C6", "status": "supported" if any(row["macro_false_open"] - full_macro >= 0.05 or full_positive - row["positive_open_rate"] >= 0.02 for row in ablations) else "invalidated", "detail": "certificate ablations"}, {"claim": "C7", "status": "pending", "detail": "requires leave-one-seed-out comparison table"}]
    write_csv(destination["tables"] / "claim_verdicts.csv", verdicts, ["claim", "status", "detail"])
    report = "# OCRA-v1 report\n\nGenerated solely from `results/ocra_v1/` sealed artifacts.\n\n" + "\n".join(f"- {row['claim']}: **{row['status']}** ({row['detail']})" for row in verdicts) + "\n"
    (destination["reports"] / "ocra_v1_report.md").parent.mkdir(parents=True, exist_ok=True)
    (destination["reports"] / "ocra_v1_report.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": "complete", "e3": e3, "claim_verdicts": verdicts}, indent=2))


def preflight() -> None:
    protocol, _, _, destination = _require_sealed()
    payload = _environment() | {"run_root": str(destination["root"]), "training_budget": protocol["evaluation"], "test_loaded": False}
    atomic_write_json(destination["protocol"] / "preflight.json", payload)
    print(json.dumps(payload, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("seal")
    subcommands.add_parser("preflight")
    train = subcommands.add_parser("train-bundle")
    train.add_argument("--horizon", type=int, required=True)
    train.add_argument("--seed", type=int, required=True)
    train.add_argument("--preflight", action="store_true")
    subcommands.add_parser("fit-certificate")
    subcommands.add_parser("evaluate-once")
    subcommands.add_parser("analyze")
    args = parser.parse_args()
    if args.command == "seal": seal()
    elif args.command == "preflight": preflight()
    elif args.command == "train-bundle": bundle(args.horizon, args.seed, preflight=args.preflight)
    elif args.command == "fit-certificate": fit_certificate()
    elif args.command == "evaluate-once": evaluate_once()
    else: analyze()


if __name__ == "__main__":
    main()
