"""Independent-sequence synthetic generator frozen for SAPR-Mamba v1."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .io import DATA_ROOT, atomic_write_json, config_hashes, load_configs, sha256_path, utc_now


def _apply_change(
    values: np.ndarray,
    innovations: np.ndarray,
    mechanism: str,
    strength: float,
    change_point: int,
    period: int,
    innovation_std: float,
) -> np.ndarray:
    output = values.copy()
    after = np.arange(values.size) - int(change_point)
    active = after >= 0
    if mechanism == "level_shift":
        output[active] += strength * innovation_std
    elif mechanism == "trend_break":
        output[active] += after[active] * (strength * innovation_std / 96.0)
    elif mechanism == "variance_shift":
        # The multiplier is applied to innovations before AR recursion in generate_sequence.
        pass
    elif mechanism == "gradual_drift":
        ramp = np.clip(after / 96.0, 0.0, 1.0)
        output += ramp * strength * innovation_std
    elif mechanism == "seasonal_change":
        phase = 2.0 * np.pi * np.arange(values.size) / period
        output[active] += strength * innovation_std * np.sin(phase[active] + np.pi / 4.0)
    elif mechanism != "stable":
        raise ValueError(f"Unsupported synthetic mechanism: {mechanism}")
    return output


def generate_sequence(config: dict, mechanism: str, strength: float, rng: np.random.Generator) -> tuple[np.ndarray, dict]:
    base = config["base_process"]
    length = int(config["length"])
    period = int(config["seasonal_period"])
    ar = rng.uniform(*base["ar_coefficient_range"])
    slope = rng.uniform(*base["trend_slope_range"])
    amplitude = rng.uniform(*base["seasonal_amplitude_range"])
    innovation_std = float(base["innovation_std"])
    innovations = rng.normal(0.0, innovation_std, size=length)
    minimum, maximum = map(int, base["change_point_range"])
    change_point = int(rng.integers(minimum, maximum + 1))
    if mechanism == "variance_shift":
        innovations[change_point:] *= float(strength)
    ar_part = np.empty(length, dtype=np.float64)
    ar_part[0] = innovations[0]
    for index in range(1, length):
        ar_part[index] = ar * ar_part[index - 1] + innovations[index]
    time = np.arange(length, dtype=np.float64)
    values = ar_part + slope * time + amplitude * np.sin(2.0 * np.pi * time / period + rng.uniform(0.0, 2.0 * np.pi))
    values = _apply_change(values, innovations, mechanism, float(strength), change_point, period, innovation_std)
    metadata = {
        "mechanism": mechanism,
        "strength": float(strength),
        "change_point": change_point,
        "ar_coefficient": float(ar),
        "trend_slope": float(slope),
        "seasonal_amplitude": float(amplitude),
    }
    return values.astype(np.float32), metadata


def _split_records(config: dict, split: str, rng: np.random.Generator) -> tuple[np.ndarray, list[dict]]:
    entries = []
    records = []
    split_counts = config["splits"][split]
    for index in range(int(split_counts["stable"])):
        sequence, metadata = generate_sequence(config, "stable", 0.0, rng)
        entries.append(sequence)
        records.append({"series_id": f"{split}_stable_{index:04d}", **metadata})
    for mechanism, definition in config["mechanisms"].items():
        if mechanism == "stable":
            continue
        for strength in definition["strengths"]:
            for index in range(int(split_counts["per_mechanism_strength"])):
                sequence, metadata = generate_sequence(config, mechanism, float(strength), rng)
                entries.append(sequence)
                records.append({"series_id": f"{split}_{mechanism}_{strength:g}_{index:04d}", **metadata})
    return np.stack(entries), records


def generate_all(force: bool = False) -> dict:
    configs = load_configs()
    config = configs["synthetic"]
    output_dir = DATA_ROOT / "synthetic"
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(int(config["generator_seed"]))
    output = {"generator_version": config["generator_version"], "created_at": utc_now(), "config_hashes": config_hashes(), "splits": {}}
    for split in ("train", "validation", "test"):
        data_path = output_dir / f"{split}.npz"
        roster_path = output_dir / f"{split}_roster.json"
        if force or not data_path.exists() or not roster_path.exists():
            values, roster = _split_records(config, split, rng)
            np.savez_compressed(data_path, values=values)
            atomic_write_json(roster_path, {"split": split, "records": roster})
        roster = json.loads(roster_path.read_text(encoding="utf-8"))["records"]
        output["splits"][split] = {
            "series_count": len(roster),
            "data": str(data_path.relative_to(DATA_ROOT.parent)),
            "sha256": sha256_path(data_path),
            "roster_sha256": sha256_path(roster_path),
        }
    manifest_path = output_dir / "data_manifest.json"
    atomic_write_json(manifest_path, output)
    output["manifest"] = str(manifest_path.relative_to(DATA_ROOT.parent))
    return output


def load_split(split: str) -> tuple[np.ndarray, list[dict]]:
    root = DATA_ROOT / "synthetic"
    with np.load(root / f"{split}.npz") as payload:
        values = payload["values"]
    roster = json.loads((root / f"{split}_roster.json").read_text(encoding="utf-8"))["records"]
    if len(values) != len(roster):
        raise RuntimeError(f"Synthetic {split} data and roster length mismatch")
    return values, roster
