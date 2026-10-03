"""Metric, paired bootstrap, and integrity utilities for SAPR-Mamba evidence."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from .io import atomic_write_json, sha256_path


METRIC_COLUMNS = (
    "dataset", "series_id", "mechanism", "strength", "model", "seed", "horizon", "state",
    "origins", "points", "mae", "rmse", "smae", "srmse", "gate_mean", "gate_median",
    "residual_norm_mean", "change_score_mean",
)


def write_csv(path: Path, rows: list[dict], columns: tuple[str, ...] = METRIC_COLUMNS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def summarize_predictions(
    prediction: np.ndarray,
    target: np.ndarray,
    state: np.ndarray,
    gate: np.ndarray,
    residual: np.ndarray,
    change_scores: np.ndarray,
    series_indices: np.ndarray,
    series_metadata: list[dict],
    model: str,
    seed: int,
    horizons: list[int],
    dataset: str,
) -> list[dict]:
    rows: list[dict] = []
    for series_index in np.unique(series_indices):
        selected_series = series_indices == series_index
        metadata = series_metadata[int(series_index)]
        for horizon in horizons:
            for state_value, state_name in ((None, "all"), (0, "stable"), (1, "change")):
                selected = selected_series if state_value is None else selected_series & (state == state_value)
                if not np.any(selected):
                    continue
                forecast = prediction[selected, :horizon]
                truth = target[selected, :horizon]
                error = forecast - truth
                training_std = float(metadata["training_std"])
                rows.append({
                    "dataset": dataset,
                    "series_id": metadata["series_id"],
                    "mechanism": metadata.get("mechanism", "real"),
                    "strength": metadata.get("strength", float("nan")),
                    "model": model,
                    "seed": int(seed),
                    "horizon": int(horizon),
                    "state": state_name,
                    "origins": int(selected.sum()),
                    "points": int(error.size),
                    "mae": float(np.mean(np.abs(error))),
                    "rmse": float(np.sqrt(np.mean(error ** 2))),
                    "smae": float(np.mean(np.abs(error)) / training_std),
                    "srmse": float(np.sqrt(np.mean(error ** 2)) / training_std),
                    "gate_mean": float(np.mean(gate[selected])),
                    "gate_median": float(np.median(gate[selected])),
                    "residual_norm_mean": float(np.mean(np.linalg.norm(residual[selected, :horizon], axis=1))),
                    "change_score_mean": float(np.mean(change_scores[selected])),
                })
    return rows


def paired_percentile_bootstrap(deltas: np.ndarray, replicates: int, seed: int) -> dict:
    """Paired bootstrap over independent sequence-level deltas; negative favours first model."""
    values = np.asarray(deltas, dtype=np.float64)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return {"n": 0, "estimate": float("nan"), "ci_low": float("nan"), "ci_high": float("nan"), "p_two_sided": float("nan")}
    rng = np.random.default_rng(seed)
    sampled = rng.choice(values, size=(int(replicates), values.size), replace=True).mean(axis=1)
    estimate = float(values.mean())
    p_lower = float(np.mean(sampled >= 0.0))
    p_upper = float(np.mean(sampled <= 0.0))
    return {
        "n": int(values.size),
        "estimate": estimate,
        "ci_low": float(np.quantile(sampled, 0.025)),
        "ci_high": float(np.quantile(sampled, 0.975)),
        "p_two_sided": min(1.0, 2.0 * min(p_lower, p_upper)),
    }


def holm_adjust(p_values: list[float]) -> list[float]:
    valid = [(index, value) for index, value in enumerate(p_values) if np.isfinite(value)]
    ordered = sorted(valid, key=lambda pair: pair[1])
    adjusted = [float("nan")] * len(p_values)
    running = 0.0
    count = len(ordered)
    for rank, (index, value) in enumerate(ordered):
        running = max(running, min(1.0, (count - rank) * value))
        adjusted[index] = running
    return adjusted


def artifact_entry(path: Path) -> dict:
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_path(path)}


def write_checksum_manifest(root: Path, output: Path) -> dict:
    files = [path for path in sorted(root.rglob("*")) if path.is_file() and path != output]
    payload = {
        "root": str(root),
        "file_count": len(files),
        "total_bytes": sum(path.stat().st_size for path in files),
        "files": [{"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha256_path(path)} for path in files],
    }
    atomic_write_json(output, payload)
    return payload
