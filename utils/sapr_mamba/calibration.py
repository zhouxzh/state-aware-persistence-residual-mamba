"""Validation-only calibration helpers for post-V3 safety experiments."""

from __future__ import annotations

import numpy as np


def select_residual_shrinkage(
    baseline: np.ndarray,
    forecast: np.ndarray,
    target: np.ndarray,
    series_index: np.ndarray,
    candidates: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0),
) -> tuple[dict[int, float], list[dict[str, float | int]]]:
    """Select a per-series residual multiplier using validation data only.

    Ties resolve toward the smallest multiplier, which is the more
    conservative persistence-adjacent forecast. Inputs are aligned windows in
    the same scale, so the selection criterion is series-local mean squared
    error and cannot use held-out test targets.
    """
    baseline = np.asarray(baseline, dtype=np.float64)
    forecast = np.asarray(forecast, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    series_index = np.asarray(series_index, dtype=np.int64)
    if baseline.shape != forecast.shape or baseline.shape != target.shape:
        raise ValueError("baseline, forecast, and target must have equal shape")
    if baseline.ndim != 2 or series_index.shape != (baseline.shape[0],):
        raise ValueError("windows must be [origin, horizon] with aligned series indices")
    if not candidates or tuple(sorted(candidates)) != candidates:
        raise ValueError("candidates must be a nonempty increasing tuple")

    residual = forecast - baseline
    selected: dict[int, float] = {}
    audit: list[dict[str, float | int]] = []
    for value in np.unique(series_index):
        mask = series_index == value
        losses = [float(np.mean((baseline[mask] + alpha * residual[mask] - target[mask]) ** 2)) for alpha in candidates]
        best = int(np.argmin(losses))
        selected[int(value)] = float(candidates[best])
        audit.append({
            "series_index": int(value),
            "validation_origins": int(mask.sum()),
            "selected_alpha": float(candidates[best]),
            "selected_validation_mse": losses[best],
            "persistence_validation_mse": losses[0],
            "unshrunk_validation_mse": losses[-1],
        })
    return selected, audit


def select_validation_candidate(
    forecasts: dict[str, np.ndarray],
    target: np.ndarray,
    series_index: np.ndarray,
    candidate_order: tuple[str, ...],
) -> tuple[dict[int, str], list[dict[str, float | int | str]]]:
    """Select one forecast family per series on validation targets only."""
    if not candidate_order or set(candidate_order) != set(forecasts):
        raise ValueError("candidate_order must exactly name forecast families")
    target = np.asarray(target, dtype=np.float64)
    series_index = np.asarray(series_index, dtype=np.int64)
    if target.ndim != 2 or series_index.shape != (target.shape[0],):
        raise ValueError("target and series_index have incompatible shapes")
    arrays = {name: np.asarray(value, dtype=np.float64) for name, value in forecasts.items()}
    if any(value.shape != target.shape for value in arrays.values()):
        raise ValueError("every forecast must match target shape")
    selected: dict[int, str] = {}
    audit: list[dict[str, float | int | str]] = []
    for value in np.unique(series_index):
        mask = series_index == value
        losses = {name: float(np.mean((arrays[name][mask] - target[mask]) ** 2)) for name in candidate_order}
        chosen = min(candidate_order, key=lambda name: losses[name])
        selected[int(value)] = chosen
        audit.append({"series_index": int(value), "validation_origins": int(mask.sum()), "selected_model": chosen, **{f"validation_mse_{name}": losses[name] for name in candidate_order}})
    return selected, audit
