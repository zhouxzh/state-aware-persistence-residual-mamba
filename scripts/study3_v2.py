#!/usr/bin/env python
"""Sealed runner for Study 3 future-jump and summary-negative-control simulation.

Only ``evaluate-once`` materializes numeric test data.  Every other command is
limited to train/validation data or metadata-only test rosters.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import torch
from sklearn.model_selection import StratifiedKFold
from torch import nn
from torch.utils.data import DataLoader, Dataset, RandomSampler

from mamba_ssm import Mamba
from utils.sapr_mamba.features import causal_features
from utils.sapr_mamba.io import atomic_write_json, sha256_path, utc_now


CONFIG = ROOT / os.environ.get("STUDY3_CONFIG_DIR", "configs/study3_v2")
RUN = ROOT / os.environ.get("STUDY3_RUN_ROOT", "results/study3_v2")
RUN_ID = os.environ.get("STUDY3_RUN_ID", "study3_v2")
MECHANISMS = (
    "stable", "visible_level_shift", "future_jump", "continuing_trend",
    "trend_break", "stable_season", "seasonal_change", "variance_shift", "random_walk",
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def configs() -> tuple[dict, dict, dict]:
    return tuple(read_json(CONFIG / f"{name}.json") for name in ("protocol", "synthetic", "model_spec"))


def paths() -> dict[str, Path]:
    root = RUN.resolve()
    if ROOT not in (root, *root.parents):
        raise RuntimeError("Study 3 run root must stay inside this repository")
    return {name: root / name for name in (
        "data", "protocol", "bundles", "failures", "forecasts", "metrics", "resources", "reports", "logs"
    )} | {"root": root}


def digest(path: Path) -> str:
    return sha256_path(path)


def source_hashes() -> dict[str, str]:
    return {
        "runner": digest(Path(__file__)),
        "features": digest(ROOT / "utils/sapr_mamba/features.py"),
        "mamba_model": digest(ROOT / "model/StateAwarePersistenceResidualMamba.py"),
        "protocol_config": digest(CONFIG / "protocol.json"),
        "synthetic_config": digest(CONFIG / "synthetic.json"),
        "model_spec": digest(CONFIG / "model_spec.json"),
    }


def seed_all(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def split_seed(seed: int, split: str) -> int:
    return int(seed) + {"train": 11, "validation": 29, "test": 47}[split]


def conditions(protocol: dict) -> list[dict]:
    values = list(protocol["registered_conditions"])
    if len(values) != 8 or len({(int(item["lookback"]), item["model"]) for item in values}) != 8:
        raise RuntimeError("Study 3 requires exactly eight unique registered conditions")
    return values


def registered_cells(protocol: dict) -> list[dict]:
    return [
        {"lookback": int(condition["lookback"]), "model": condition["model"], "seed": int(seed)}
        for condition in conditions(protocol)
        for seed in protocol["training_seeds"]
    ]


def model_key(lookback: int, model: str, seed: int) -> str:
    return f"L{lookback}-H24-{model}-s{seed}"


def make_records(split: str, synthetic: dict, prefix: str) -> list[dict]:
    records = []
    base = synthetic["base"]
    for mechanism in MECHANISMS:
        count = int(synthetic["split_series_counts"][split][mechanism])
        for index in range(count):
            visible = int(base["visible_change_points"][index % len(base["visible_change_points"])])
            future_origin = int(base["future_jump_origins"][index % len(base["future_jump_origins"])])
            change_point = future_origin + int(base["future_jump_offset"]) if mechanism == "future_jump" else (
                -1 if mechanism in {"stable", "stable_season", "random_walk"} else visible
            )
            records.append({
                "series_id": f"{prefix}{split}_{mechanism}_{index:04d}",
                "split": split,
                "mechanism": mechanism,
                "index": index,
                "change_point": int(change_point),
                "future_event_offset": int(base["future_jump_offset"]) if mechanism == "future_jump" else None,
            })
    return records


def random_walk(innovations: np.ndarray, increment_ar: float) -> np.ndarray:
    increments = np.empty_like(innovations)
    increments[0] = innovations[0]
    for index in range(1, len(innovations)):
        increments[index] = float(increment_ar) * increments[index - 1] + innovations[index]
    return np.cumsum(increments)


def generate_one(record: dict, synthetic: dict, rng: np.random.Generator) -> np.ndarray:
    base, mechanism = synthetic["base"], record["mechanism"]
    length, period = int(synthetic["length"]), int(synthetic["seasonal_period"])
    noise = rng.normal(0.0, float(base["innovation_std"]), length)
    direction = -1.0 if int(record["index"]) % 2 == 0 else 1.0
    change_point = int(record["change_point"])
    if mechanism == "random_walk":
        return random_walk(noise, float(base["near_random_walk_increment_ar"])).astype(np.float32)
    if mechanism == "future_jump":
        values = random_walk(noise, 0.0)
        values[change_point:] += direction * float(base["jump_strength"])
        return values.astype(np.float32)
    if mechanism == "variance_shift":
        noise[change_point:] *= float(base["variance_multiplier"])
    values = np.empty(length, dtype=np.float64)
    values[0] = noise[0]
    for index in range(1, length):
        values[index] = float(base["ar"]) * values[index - 1] + noise[index]
    time_index = np.arange(length, dtype=np.float64)
    if mechanism == "continuing_trend":
        values += float(base["trend_slope"]) * time_index
    elif mechanism == "stable_season":
        values += float(base["seasonal_amplitude"]) * np.sin(2 * np.pi * time_index / period)
    elif mechanism == "visible_level_shift":
        values[change_point:] += direction * float(base["jump_strength"])
    elif mechanism == "trend_break":
        values[change_point:] += direction * (time_index[change_point:] - change_point) * float(base["trend_break_slope"])
    elif mechanism == "seasonal_change":
        values += float(base["seasonal_amplitude"]) * np.sin(2 * np.pi * time_index / period)
        values[change_point:] += direction * float(base["seasonal_change_amplitude"]) * np.sin(
            2 * np.pi * time_index[change_point:] / period + np.pi / 3
        )
    return values.astype(np.float32)


def materialize(records: list[dict], synthetic: dict, split: str) -> np.ndarray:
    protocol, _, _ = configs()
    rng = np.random.default_rng(split_seed(int(protocol["generator_seed"]), split))
    return np.stack([generate_one(record, synthetic, rng) for record in records])


def origins_for(records: list[dict], protocol: dict, synthetic: dict) -> np.ndarray:
    start = int(protocol["common_origin_lookback"])
    stop = int(synthetic["length"]) - int(protocol["horizon"]) + 1
    sequence_origins = np.arange(start, stop, int(synthetic["origin_stride"]), dtype=np.int64)
    return np.asarray([(series, origin) for series in range(len(records)) for origin in sequence_origins], dtype=np.int64)


def group_for(record: dict, origin: int, protocol: dict, synthetic: dict) -> str:
    mechanism, point = record["mechanism"], int(record["change_point"])
    horizon, delay = int(protocol["horizon"]), int(synthetic["change_signal_delay"])
    visible = origin - 96 <= point < origin and origin >= point + delay
    if mechanism == "future_jump" and 0 < point - origin <= horizon:
        return "N2"
    if mechanism == "random_walk":
        return "N8"
    if mechanism == "trend_break" and visible:
        return "S4"
    if mechanism == "seasonal_change" and visible:
        return "S6"
    return "other"


def origin_groups(records: list[dict], origins: np.ndarray, protocol: dict, synthetic: dict) -> np.ndarray:
    return np.asarray([group_for(records[int(series)], int(origin), protocol, synthetic) for series, origin in origins])


class OriginDataset(Dataset):
    def __init__(self, values: np.ndarray, origins: np.ndarray, lookback: int, horizon: int, summary_on: bool):
        self.values, self.origins, self.lookback, self.horizon = values, origins, int(lookback), int(horizon)
        self.features = np.stack([
            causal_features(values[int(series), int(origin) - 96:int(origin)], 48).astype(np.float32)
            if summary_on else np.zeros(9, dtype=np.float32)
            for series, origin in origins
        ])

    def __len__(self) -> int:
        return len(self.origins)

    def __getitem__(self, index: int) -> dict:
        series, origin = map(int, self.origins[index])
        return {
            "x": torch.from_numpy(self.values[series, origin - self.lookback:origin].copy()),
            "y": torch.from_numpy(self.values[series, origin:origin + self.horizon].copy()),
            "phi": torch.from_numpy(self.features[index].copy()),
        }


class TransformerHead(nn.Module):
    def __init__(self, lookback: int, summary_on: bool, spec: dict, horizon: int):
        super().__init__()
        self.lookback, self.summary_on, self.horizon = int(lookback), bool(summary_on), int(horizon)
        settings = spec["transformer"]
        width = int(settings["d_model"])
        self.projection = nn.Linear(10, width)
        layer = nn.TransformerEncoderLayer(
            width, int(settings["heads"]), int(settings["ff"]), dropout=float(settings["dropout"]),
            batch_first=True, norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(layer, int(settings["layers"]))
        self.head = nn.Linear(width, self.horizon)
        positions = torch.arange(self.lookback, dtype=torch.float32).unsqueeze(1)
        divisors = torch.exp(torch.arange(0, width, 2, dtype=torch.float32) * (-math.log(10000.0) / width))
        positional = torch.zeros(self.lookback, width)
        positional[:, 0::2], positional[:, 1::2] = torch.sin(positions * divisors), torch.cos(positions * divisors)
        self.register_buffer("position", positional.unsqueeze(0), persistent=True)

    def forward(self, values: torch.Tensor, phi: torch.Tensor) -> torch.Tensor:
        base = values[:, -1:]
        scale = values.std(1, keepdim=True, unbiased=False).clamp_min(1e-6)
        normalized = (values - base) / scale
        if not self.summary_on:
            phi = torch.zeros_like(phi)
        feature = phi[:, None, :].expand(-1, self.lookback, -1)
        encoded = self.encoder(self.projection(torch.cat((normalized.unsqueeze(-1), feature), -1)) + self.position)[:, -1]
        return base.expand(-1, self.horizon) + self.head(encoded) * scale


class MambaHead(nn.Module):
    def __init__(self, lookback: int, summary_on: bool, spec: dict, horizon: int):
        super().__init__()
        self.lookback, self.summary_on, self.horizon = int(lookback), bool(summary_on), int(horizon)
        settings = spec["mamba"]
        width = int(settings["d_model"])
        self.projection = nn.Linear(10, width)
        self.blocks = nn.ModuleList([Mamba(d_model=width, d_state=int(settings["d_state"]), d_conv=int(settings["d_conv"]), expand=int(settings["expand"])) for _ in range(int(settings["layers"]))])
        self.norms = nn.ModuleList([nn.LayerNorm(width) for _ in self.blocks])
        self.dropout = nn.Dropout(float(settings["dropout"]))
        self.head = nn.Linear(width, self.horizon)

    def forward(self, values: torch.Tensor, phi: torch.Tensor) -> torch.Tensor:
        base = values[:, -1:]
        scale = values.std(1, keepdim=True, unbiased=False).clamp_min(1e-6)
        normalized = (values - base) / scale
        if not self.summary_on:
            phi = torch.zeros_like(phi)
        feature = phi[:, None, :].expand(-1, self.lookback, -1)
        hidden = self.projection(torch.cat((normalized.unsqueeze(-1), feature), -1))
        for block, norm in zip(self.blocks, self.norms):
            hidden = norm(hidden + self.dropout(block(hidden)))
        return base.expand(-1, self.horizon) + self.head(hidden[:, -1]) * scale


def build_model(model: str, lookback: int, spec: dict, horizon: int) -> nn.Module:
    if model.startswith("Mamba"):
        return MambaHead(lookback, model == "MambaPhi", spec, horizon)
    if model.startswith("Transformer"):
        return TransformerHead(lookback, model == "TransformerPhi", spec, horizon)
    raise ValueError(f"unregistered model: {model}")


def prior_ids_and_seeds() -> tuple[set[str], set[int]]:
    identifiers, seeds = set(), set()
    for roster in ROOT.glob("results/*/data/*_roster.json"):
        try:
            identifiers.update(str(row["series_id"]) for row in read_json(roster).get("records", []))
        except (OSError, json.JSONDecodeError, KeyError):
            continue
    for manifest in ROOT.glob("results/*/protocol/*.json"):
        try:
            payload = read_json(manifest)
        except (OSError, json.JSONDecodeError):
            continue
        for key in ("generator_seed",):
            if key in payload:
                seeds.add(int(payload[key]))
        seeds.update(int(seed) for seed in payload.get("training_seeds", []))
    return identifiers, seeds


def require_sealed() -> tuple[dict, dict, dict, dict[str, Path]]:
    protocol, synthetic, spec = configs()
    destination = paths()
    sealed = destination["protocol"] / "protocol.json"
    if not sealed.is_file():
        raise RuntimeError("Study 3 must be sealed before this command")
    payload = read_json(sealed)
    if payload.get("status") not in {"sealed_before_training", "training", "release_gate_passed", "test_evaluated", "complete"}:
        raise RuntimeError("unexpected sealed protocol status")
    if payload.get("source_hashes") != source_hashes():
        raise RuntimeError("source or configuration hash differs from sealed Study 3 protocol")
    return protocol, synthetic, spec, destination


def seal() -> None:
    protocol, synthetic, spec = configs()
    destination = paths()
    sealed = destination["protocol"] / "protocol.json"
    if sealed.exists():
        raise RuntimeError("Study 3 protocol already sealed; create a new namespace for any revision")
    if len(registered_cells(protocol)) != int(protocol["release_gate"]["expected_training_cells"]):
        raise RuntimeError("registered training-cell count differs from frozen protocol")
    records = {split: make_records(split, synthetic, protocol["series_id_prefix"]) for split in ("train", "validation", "test")}
    previous_ids, previous_seeds = prior_ids_and_seeds()
    all_ids = {item["series_id"] for items in records.values() for item in items}
    streams = {int(protocol["generator_seed"]), *map(int, protocol["training_seeds"])} | {split_seed(int(protocol["generator_seed"]), split) for split in records}
    overlap, seed_overlap = sorted(all_ids & previous_ids), sorted(streams & previous_seeds)
    if overlap or seed_overlap:
        raise RuntimeError(f"Study 3 blacklist collision: ids={len(overlap)}, seeds={seed_overlap}")
    for key in destination.values():
        key.mkdir(parents=True, exist_ok=True)
    values = {split: materialize(records[split], synthetic, split) for split in ("train", "validation")}
    origins = {split: origins_for(records[split], protocol, synthetic) for split in records}
    groups = origin_groups(records["test"], origins["test"], protocol, synthetic)
    coverage = {name: sorted({records["test"][int(series)]["series_id"] for (series, _), group in zip(origins["test"], groups) if group == name}) for name in ("N2", "N8", "S4", "S6")}
    minimum = int(protocol["release_gate"]["minimum_test_series_per_primary_group"])
    if any(len(ids) != minimum for ids in coverage.values()):
        raise RuntimeError(f"primary test coverage is not frozen at {minimum}: { {key: len(value) for key, value in coverage.items()} }")
    np.savez_compressed(destination["data"] / "train.npz", values=values["train"])
    np.savez_compressed(destination["data"] / "validation.npz", values=values["validation"])
    for split in records:
        atomic_write_json(destination["data"] / f"{split}_roster.json", {"records": records[split]})
        atomic_write_json(destination["protocol"] / f"{split}_origins.json", {"origins": origins[split].tolist()})
    coverage_payload = {
        "status": "passed", "created_at": utc_now(), "primary_group_series": {key: len(value) for key, value in coverage.items()},
        "primary_group_series_ids": coverage, "future_jump_offset": int(synthetic["base"]["future_jump_offset"]),
        "near_random_walk_increment_ar": float(synthetic["base"]["near_random_walk_increment_ar"]), "test_numeric_loaded": False,
    }
    atomic_write_json(destination["protocol"] / "coverage.json", coverage_payload)
    blacklist = {"passed": True, "prior_series_count": len(previous_ids), "prior_seed_count": len(previous_seeds), "new_series_count": len(all_ids), "series_intersection": overlap, "seed_intersection": seed_overlap, "new_seed_streams": sorted(streams)}
    atomic_write_json(destination["protocol"] / "blacklist_check.json", blacklist)
    parameter_counts = {f"L{item['lookback']}_{item['model']}": sum(parameter.numel() for parameter in build_model(item["model"], item["lookback"], spec, int(protocol["horizon"])).parameters()) for item in conditions(protocol)}
    sealed_payload = dict(protocol) | {
        "status": "sealed_before_training", "sealed_at": utc_now(), "run_id": RUN_ID, "source_hashes": source_hashes(),
        "registered_cells": registered_cells(protocol), "parameter_counts": parameter_counts,
        "roster_hashes": {split: digest(destination["data"] / f"{split}_roster.json") for split in records},
        "origin_hashes": {split: digest(destination["protocol"] / f"{split}_origins.json") for split in records},
        "coverage_sha256": digest(destination["protocol"] / "coverage.json"), "test_numeric_materialized": False,
    }
    atomic_write_json(sealed, sealed_payload)
    atomic_write_json(destination["protocol"] / "e1_audit.json", {"status": "passed", "created_at": utc_now(), "blacklist_sha256": digest(destination["protocol"] / "blacklist_check.json"), "future_fields_used": False, "test_numeric_loaded": False})
    print(json.dumps({"status": "sealed", "training_cells": len(sealed_payload["registered_cells"]), "coverage": coverage_payload["primary_group_series"], "test_numeric_materialized": False}, indent=2))


def preflight() -> None:
    protocol, synthetic, spec, destination = require_sealed()
    if (destination["data"] / "test.npz").exists():
        raise RuntimeError("test numeric data exists before Study 3 release gate")
    train = np.load(destination["data"] / "train.npz")["values"]
    origins = np.asarray(read_json(destination["protocol"] / "train_origins.json")["origins"], dtype=np.int64)
    device = torch.device(protocol["training"]["device"])
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("Study 3 requires the configured CUDA device")
    model = build_model("MambaPhi", 96, spec, int(protocol["horizon"])).to(device)
    sample = OriginDataset(train, origins[:2], 96, int(protocol["horizon"]), True)
    batch = next(iter(DataLoader(sample, batch_size=2)))
    prediction = model(batch["x"].to(device), batch["phi"].to(device))
    loss = ((prediction - batch["y"].to(device)) ** 2).mean()
    loss.backward()
    if not torch.isfinite(prediction).all() or not torch.isfinite(loss):
        raise RuntimeError("nonfinite Study 3 preflight forward/backward result")
    report = {"status": "passed", "created_at": utc_now(), "device": str(device), "train_shape": list(train.shape), "sample_prediction_shape": list(prediction.shape), "loss": float(loss.detach().cpu()), "test_numeric_loaded": False}
    atomic_write_json(destination["protocol"] / "preflight.json", report)
    print(json.dumps(report, indent=2))


def train_cell(lookback: int, model_name: str, seed: int) -> None:
    protocol, _, spec, destination = require_sealed()
    cell = {"lookback": int(lookback), "model": model_name, "seed": int(seed)}
    if cell not in registered_cells(protocol):
        raise ValueError(f"unregistered Study 3 cell: {cell}")
    if not read_json(destination["protocol"] / "e1_audit.json").get("status") == "passed":
        raise RuntimeError("E1 audit must pass before training")
    output = destination["bundles"] / model_key(lookback, model_name, seed)
    manifest = output / "manifest.json"
    if manifest.is_file() and read_json(manifest).get("status") == "complete":
        print(json.dumps({"status": "already_complete", "cell": cell}))
        return
    train, validation = (np.load(destination["data"] / f"{split}.npz")["values"] for split in ("train", "validation"))
    origins_train = np.asarray(read_json(destination["protocol"] / "train_origins.json")["origins"], dtype=np.int64)
    origins_validation = np.asarray(read_json(destination["protocol"] / "validation_origins.json")["origins"], dtype=np.int64)
    summary_on = model_name.endswith("Phi")
    horizon, device = int(protocol["horizon"]), torch.device(protocol["training"]["device"])
    seed_all(seed)
    model = build_model(model_name, lookback, spec, horizon).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(protocol["training"]["learning_rate"]), weight_decay=float(protocol["training"]["weight_decay"]))
    train_data = OriginDataset(train, origins_train, lookback, horizon, summary_on)
    validation_data = OriginDataset(validation, origins_validation, lookback, horizon, summary_on)
    generator = torch.Generator().manual_seed(seed)
    sampler = RandomSampler(train_data, replacement=True, num_samples=int(protocol["training"]["samples_per_epoch"]), generator=generator)
    train_loader = DataLoader(train_data, batch_size=int(protocol["training"]["batch_size"]), sampler=sampler, num_workers=0)
    validation_loader = DataLoader(validation_data, batch_size=128, shuffle=False, num_workers=0)
    output.mkdir(parents=True, exist_ok=True)
    atomic_write_json(manifest, {"status": "running", "cell": cell, "started_at": utc_now(), "split_access": ["train", "validation"], "test_numeric_loaded": False})
    use_amp = bool(protocol["training"]["amp"])
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    torch.cuda.reset_peak_memory_stats(device)
    started, best, stale, best_epoch, best_state = time.monotonic(), float("inf"), 0, 0, None
    for epoch in range(1, int(protocol["training"]["max_epochs"]) + 1):
        model.train()
        for batch in train_loader:
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, enabled=use_amp):
                loss = ((model(batch["x"].to(device), batch["phi"].to(device)) - batch["y"].to(device)) ** 2).mean()
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), float(protocol["training"]["gradient_clip_norm"]))
            scaler.step(optimizer)
            scaler.update()
        model.eval()
        total, count = 0.0, 0
        with torch.no_grad():
            for batch in validation_loader:
                with torch.autocast(device_type=device.type, enabled=use_amp):
                    prediction = model(batch["x"].to(device), batch["phi"].to(device))
                total += float(((prediction - batch["y"].to(device)) ** 2).sum())
                count += int(prediction.numel())
        score = total / max(count, 1)
        if score < best:
            best, stale, best_epoch = score, 0, epoch
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
        else:
            stale += 1
            if stale >= int(protocol["training"]["patience"]):
                break
    if best_state is None:
        raise RuntimeError("training completed without a finite validation checkpoint")
    model.load_state_dict(best_state, strict=True)
    checkpoint = output / "checkpoint.pt"
    torch.save({"state_dict": model.state_dict(), "cell": cell, "parameter_count": sum(parameter.numel() for parameter in model.parameters())}, checkpoint)
    torch.cuda.synchronize(device)
    payload = {"status": "complete", "completed_at": utc_now(), "cell": cell, "best_validation_mse": best, "best_epoch": best_epoch, "elapsed_seconds": time.monotonic() - started, "peak_memory_mib": torch.cuda.max_memory_allocated(device) / 2**20, "checkpoint_sha256": digest(checkpoint), "parameter_count": sum(parameter.numel() for parameter in model.parameters()), "split_access": ["train", "validation"], "test_numeric_loaded": False}
    atomic_write_json(manifest, payload)
    print(json.dumps(payload, indent=2))


def train_matrix() -> None:
    protocol, _, _, destination = require_sealed()
    max_seconds = float(protocol["budget"]["max_gpu_hours"]) * 3600
    completed, failed = 0, 0
    for cell in registered_cells(protocol):
        manifests = list(destination["bundles"].glob("*/manifest.json"))
        elapsed = sum(float(read_json(path).get("elapsed_seconds", 0.0)) for path in manifests if read_json(path).get("status") == "complete")
        if elapsed >= max_seconds:
            atomic_write_json(destination["protocol"] / "matrix_status.json", {"status": "budget_stopped", "completed": completed, "failed": failed, "training_seconds": elapsed, "test_numeric_loaded": False})
            raise RuntimeError("Study 3 GPU-hour budget reached; test remains locked")
        try:
            train_cell(cell["lookback"], cell["model"], cell["seed"])
            completed += 1
        except Exception as exc:
            failed += 1
            failure = destination["failures"] / f"{model_key(**cell)}.json"
            atomic_write_json(failure, {"status": "failed", "cell": cell, "error": repr(exc), "occurred_at": utc_now(), "test_numeric_loaded": False})
            raise
        atomic_write_json(destination["protocol"] / "matrix_status.json", {"status": "training", "completed_this_invocation": completed, "failed": failed, "cells_total": len(registered_cells(protocol)), "test_numeric_loaded": False, "updated_at": utc_now()})


def release_gate() -> None:
    protocol, synthetic, spec, destination = require_sealed()
    test_path, ledger = destination["data"] / "test.npz", destination["protocol"] / "test_access_ledger.json"
    cells = registered_cells(protocol)
    manifests, errors = [], []
    if test_path.exists() or ledger.exists():
        errors.append("test numeric material or access ledger exists before release gate")
    if list(destination["failures"].glob("*.json")):
        errors.append("failure records exist")
    if len(cells) != int(protocol["release_gate"]["expected_training_cells"]):
        errors.append("registered cell count mismatch")
    device = torch.device("cpu")
    for cell in cells:
        output = destination["bundles"] / model_key(**cell)
        manifest, checkpoint = output / "manifest.json", output / "checkpoint.pt"
        if not manifest.is_file() or not checkpoint.is_file():
            errors.append(f"missing artifact: {cell}")
            continue
        result = read_json(manifest)
        if result.get("status") != "complete":
            errors.append(f"incomplete cell: {cell}")
            continue
        model = build_model(cell["model"], cell["lookback"], spec, int(protocol["horizon"])).to(device)
        checkpoint_payload = torch.load(checkpoint, map_location=device, weights_only=True)
        try:
            model.load_state_dict(checkpoint_payload["state_dict"], strict=True)
        except RuntimeError as exc:
            errors.append(f"strict-load failure {cell}: {exc}")
            continue
        if int(checkpoint_payload.get("parameter_count", -1)) != sum(parameter.numel() for parameter in model.parameters()):
            errors.append(f"parameter mismatch: {cell}")
        if not all(torch.isfinite(value).all() for value in model.state_dict().values() if torch.is_floating_point(value)):
            errors.append(f"nonfinite checkpoint: {cell}")
        manifests.append({"cell": cell, "manifest_sha256": digest(manifest), "checkpoint_sha256": digest(checkpoint)})
    coverage = read_json(destination["protocol"] / "coverage.json")
    minimum = int(protocol["release_gate"]["minimum_test_series_per_primary_group"])
    if coverage.get("status") != "passed" or any(int(count) != minimum for count in coverage.get("primary_group_series", {}).values()):
        errors.append("frozen primary coverage mismatch")
    for split in ("train", "validation", "test"):
        if digest(destination["data"] / f"{split}_roster.json") != read_json(destination["protocol"] / "protocol.json")["roster_hashes"][split]:
            errors.append(f"roster hash mismatch: {split}")
        if digest(destination["protocol"] / f"{split}_origins.json") != read_json(destination["protocol"] / "protocol.json")["origin_hashes"][split]:
            errors.append(f"origin hash mismatch: {split}")
    report = {"status": "passed" if not errors else "failed", "created_at": utc_now(), "errors": errors, "checked_cells": manifests, "test_numeric_loaded": False}
    atomic_write_json(destination["protocol"] / "release_gate.json", report)
    if errors:
        raise RuntimeError("Study 3 release gate failed: " + "; ".join(errors))
    sealed = read_json(destination["protocol"] / "protocol.json")
    sealed["status"] = "release_gate_passed"
    atomic_write_json(destination["protocol"] / "protocol.json", sealed)
    print(json.dumps(report, indent=2))


def checkpoint_model(cell: dict, spec: dict, protocol: dict, destination: dict[str, Path], device: torch.device) -> nn.Module:
    model = build_model(cell["model"], cell["lookback"], spec, int(protocol["horizon"])).to(device)
    checkpoint = destination["bundles"] / model_key(**cell) / "checkpoint.pt"
    model.load_state_dict(torch.load(checkpoint, map_location=device, weights_only=True)["state_dict"], strict=True)
    return model.eval()


def evaluate_once() -> None:
    protocol, synthetic, spec, destination = require_sealed()
    gate = destination["protocol"] / "release_gate.json"
    test_path, ledger = destination["data"] / "test.npz", destination["protocol"] / "test_access_ledger.json"
    if not gate.is_file() or read_json(gate).get("status") != "passed":
        raise RuntimeError("a passed Study 3 release gate is required before test access")
    if ledger.exists() or test_path.exists():
        raise RuntimeError("Study 3 test access has already been attempted")
    records = read_json(destination["data"] / "test_roster.json")["records"]
    values = materialize(records, synthetic, "test")
    np.savez_compressed(test_path, values=values)
    origins = np.asarray(read_json(destination["protocol"] / "test_origins.json")["origins"], dtype=np.int64)
    groups = origin_groups(records, origins, protocol, synthetic)
    atomic_write_json(ledger, {"status": "authorized_and_materialized_once", "created_at": utc_now(), "test_roster_sha256": digest(destination["data"] / "test_roster.json"), "test_numeric_sha256": digest(test_path)})
    device, horizon = torch.device(protocol["training"]["device"]), int(protocol["horizon"])
    rows, prediction_store, resources = [], {}, []
    for cell in registered_cells(protocol):
        model = checkpoint_model(cell, spec, protocol, destination, device)
        dataset = OriginDataset(values, origins, cell["lookback"], horizon, cell["model"].endswith("Phi"))
        loader = DataLoader(dataset, batch_size=128, shuffle=False, num_workers=0)
        torch.cuda.synchronize(device)
        started, pieces = time.monotonic(), []
        with torch.no_grad():
            for batch in loader:
                pieces.append(model(batch["x"].to(device), batch["phi"].to(device)).cpu().numpy())
        torch.cuda.synchronize(device)
        prediction = np.concatenate(pieces)
        prediction_store[model_key(**cell)] = prediction
        resources.append({"lookback": cell["lookback"], "model": cell["model"], "seed": cell["seed"], "parameters": sum(parameter.numel() for parameter in model.parameters()), "test_inference_seconds": time.monotonic() - started, **read_json(destination["bundles"] / model_key(**cell) / "manifest.json")})
        for group in ("S4", "S6", "N2", "N8", "other"):
            selected = groups == group
            for series in sorted(set(origins[selected, 0])):
                mask = selected & (origins[:, 0] == series)
                target = np.stack([values[int(index), int(origin):int(origin) + horizon] for index, origin in origins[mask]])
                rmse = float(np.sqrt(np.mean((prediction[mask] - target) ** 2)))
                rows.append({"lookback": cell["lookback"], "horizon": horizon, "model": cell["model"], "seed": cell["seed"], "group": group, "series_id": records[int(series)]["series_id"], "path_rmse": rmse, "origin_count": int(mask.sum())})
    base = values[origins[:, 0], origins[:, 1] - 1][:, None]
    for lookback in protocol["lookbacks"]:
        for group in ("S4", "S6", "N2", "N8", "other"):
            selected = groups == group
            for series in sorted(set(origins[selected, 0])):
                mask = selected & (origins[:, 0] == series)
                target = np.stack([values[int(index), int(origin):int(origin) + horizon] for index, origin in origins[mask]])
                rows.append({"lookback": lookback, "horizon": horizon, "model": "M0", "seed": "persistence", "group": group, "series_id": records[int(series)]["series_id"], "path_rmse": float(np.sqrt(np.mean((np.broadcast_to(base, (len(origins), horizon))[mask] - target) ** 2))), "origin_count": int(mask.sum())})
    predictions = destination["forecasts"] / "test_predictions_once.npz"
    np.savez_compressed(predictions, origins=origins, groups=groups, **prediction_store)
    metric = destination["metrics"] / "sequence_rmse.csv"
    with metric.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("lookback", "horizon", "model", "seed", "group", "series_id", "path_rmse", "origin_count"))
        writer.writeheader(); writer.writerows(rows)
    resource = destination["resources"] / "resource_metrics.csv"
    with resource.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=sorted({key for row in resources for key in row}))
        writer.writeheader(); writer.writerows(resources)
    atomic_write_json(ledger, read_json(ledger) | {"sequence_metrics_sha256": digest(metric), "predictions_sha256": digest(predictions), "resources_sha256": digest(resource), "test_numeric_materialized": True})
    sealed = read_json(destination["protocol"] / "protocol.json"); sealed["status"] = "test_evaluated"; sealed["test_numeric_materialized"] = True; atomic_write_json(destination["protocol"] / "protocol.json", sealed)
    print(json.dumps({"status": "test_evaluated_once", "metric_rows": len(rows), "test_numeric_loaded": True}, indent=2))


def holm(values: list[float]) -> list[float]:
    order, adjusted, running = np.argsort(values), [0.0] * len(values), 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (len(values) - rank) * float(values[index])))
        adjusted[int(index)] = running
    return adjusted


def bootstrap(delta: np.ndarray, replicates: int, seed: int) -> tuple[float, float, float]:
    rng, values = np.random.default_rng(seed), np.asarray(delta, dtype=np.float64)
    sampled = values[rng.integers(0, len(values), size=(replicates, len(values)))].mean(axis=1)
    return float(values.mean()), float(np.quantile(sampled, 0.025)), float(np.quantile(sampled, 0.975))


def sign_flip(delta: np.ndarray, replicates: int, seed: int) -> float:
    rng, values, observed = np.random.default_rng(seed), np.asarray(delta, dtype=np.float64), abs(float(np.mean(delta)))
    null = np.abs((rng.choice(np.asarray([-1.0, 1.0]), size=(replicates, len(values))) * values).mean(axis=1))
    return float((1 + np.sum(null >= observed)) / (1 + replicates))


def one_sided_upper_bound(delta: np.ndarray, replicates: int, seed: int, level: float) -> float:
    rng, values = np.random.default_rng(seed), np.asarray(delta, dtype=np.float64)
    sampled = values[rng.integers(0, len(values), size=(replicates, len(values)))].mean(axis=1)
    return float(np.quantile(sampled, float(level)))


def noninferiority_sign_flip(delta: np.ndarray, margin: float, replicates: int, seed: int) -> float:
    """One-sided paired test of H0: mean(delta) >= margin versus H1: < margin."""
    rng = np.random.default_rng(seed)
    centered = np.asarray(delta, dtype=np.float64) - float(margin)
    observed = float(np.mean(centered))
    null = (rng.choice(np.asarray([-1.0, 1.0]), size=(replicates, len(centered))) * centered).mean(axis=1)
    return float((1 + np.sum(null <= observed)) / (1 + replicates))


def analysis() -> None:
    protocol, _, _, destination = require_sealed()
    ledger = destination["protocol"] / "test_access_ledger.json"
    if not ledger.is_file() or not read_json(ledger).get("test_numeric_materialized"):
        raise RuntimeError("Study 3 analysis requires the one-time test evaluation")
    with (destination["metrics"] / "sequence_rmse.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    grouped: dict[tuple[int, str, str, str], list[float]] = {}
    for row in rows:
        key = (int(row["lookback"]), row["model"], row["group"], row["series_id"])
        grouped.setdefault(key, []).append(float(row["path_rmse"]))
    means = {key: float(np.mean(values)) for key, values in grouped.items()}
    evaluation, output = protocol["evaluation"], []
    replicates, bootstrap_seed, sign_seed = int(evaluation["bootstrap_replicates"]), int(evaluation["bootstrap_seed"]), int(evaluation["sign_flip_seed"])

    def contrast(family: str, label: str, group: str, lookback: int, left: str, right: str, safety: bool = False) -> None:
        left_map = {series: value for (length, model, label_group, series), value in means.items() if length == lookback and model == left and label_group == group}
        right_map = {series: value for (length, model, label_group, series), value in means.items() if length == lookback and model == right and label_group == group}
        identifiers = sorted(set(left_map) & set(right_map))
        if not identifiers:
            raise RuntimeError(f"empty paired contrast: {label}")
        delta = np.asarray([left_map[item] - right_map[item] for item in identifiers])
        index = len(output)
        estimate, low, high = bootstrap(delta, replicates, bootstrap_seed + index)
        margin = float(evaluation["summary_noninferiority_margin_raw_path_rmse"])
        output.append({
            "family": family,
            "contrast": label,
            "group": group,
            "lookback": lookback,
            "left_model": left,
            "right_model": right,
            "n_series": len(identifiers),
            "estimate": estimate,
            "ci_low": low,
            "ci_high": high,
            "one_sided_upper_ci": one_sided_upper_bound(delta, replicates, bootstrap_seed + index, float(evaluation["summary_noninferiority_confidence"]["level"])) if safety else "",
            "noninferiority_margin": margin if safety else "",
            "p_signflip_raw": sign_flip(delta, replicates, sign_seed + index),
            "p_noninferiority_raw": noninferiority_sign_flip(delta, margin, replicates, sign_seed + index) if safety else "",
            "p_holm": None,
            "decision": "pending",
        })

    for condition in conditions(protocol):
        contrast("P1_future_jump", f"{condition['model']} minus M0 at L{condition['lookback']}", "N2", int(condition["lookback"]), condition["model"], "M0")
    for lookback in protocol["lookbacks"]:
        for group in ("N2", "N8"):
            contrast("P2_summary_safety", f"MambaPhi minus Mamba0 at L{lookback}", group, int(lookback), "MambaPhi", "Mamba0", safety=True)
        for group in ("S4", "S6"):
            contrast("P2_summary_visible", f"MambaPhi minus Mamba0 at L{lookback}", group, int(lookback), "MambaPhi", "Mamba0")
    for family in sorted({row["family"] for row in output}):
        indices = [index for index, row in enumerate(output) if row["family"] == family]
        p_values = [output[index]["p_noninferiority_raw"] if family == "P2_summary_safety" else output[index]["p_signflip_raw"] for index in indices]
        for index, value in zip(indices, holm(p_values)):
            output[index]["p_holm"] = value
    for row in output:
        if row["family"] == "P1_future_jump":
            row["decision"] = "leakage_review" if row["estimate"] < 0 and row["ci_high"] < 0 and row["p_holm"] < 0.05 else "no_leakage_trigger"
        elif row["family"] == "P2_summary_safety":
            row["decision"] = "noninferior_within_prespecified_margin" if row["one_sided_upper_ci"] < row["noninferiority_margin"] and row["p_holm"] < float(evaluation["summary_noninferiority_test"]["alpha_familywise"]) else "margin_not_met"
        else:
            row["decision"] = "summary_superiority" if row["ci_high"] < 0 and row["p_holm"] < 0.05 else "summary_difference_not_confirmed"
    comparison = destination["metrics"] / "paired_comparisons.csv"
    with comparison.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(output[0])); writer.writeheader(); writer.writerows(output)
    binding = {"status": "complete", "created_at": utc_now(), "protocol_version": protocol["protocol_version"], "source_hashes": source_hashes(), "test_access_ledger_sha256": digest(ledger), "release_gate_sha256": digest(destination["protocol"] / "release_gate.json"), "sequence_rmse_sha256": digest(destination["metrics"] / "sequence_rmse.csv"), "paired_comparisons_sha256": digest(comparison), "resource_metrics_sha256": digest(destination["resources"] / "resource_metrics.csv"), "test_numeric_loaded": True}
    atomic_write_json(destination["reports"] / "release_binding.json", binding)
    sealed = read_json(destination["protocol"] / "protocol.json"); sealed["status"] = "complete"; atomic_write_json(destination["protocol"] / "protocol.json", sealed)
    print(json.dumps(binding, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    command = parser.add_subparsers(dest="command", required=True)
    command.add_parser("seal")
    command.add_parser("preflight")
    train = command.add_parser("train")
    train.add_argument("--lookback", type=int, required=True)
    train.add_argument("--model", required=True)
    train.add_argument("--seed", type=int, required=True)
    command.add_parser("train-matrix")
    command.add_parser("release-gate")
    command.add_parser("evaluate-once")
    command.add_parser("analyze")
    args = parser.parse_args()
    if args.command == "seal": seal()
    elif args.command == "preflight": preflight()
    elif args.command == "train": train_cell(args.lookback, args.model, args.seed)
    elif args.command == "train-matrix": train_matrix()
    elif args.command == "release-gate": release_gate()
    elif args.command == "evaluate-once": evaluate_once()
    else: analysis()


if __name__ == "__main__":
    main()
