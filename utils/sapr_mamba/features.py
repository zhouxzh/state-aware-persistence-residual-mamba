"""Causal state features and labels specified by the SAPR-Mamba protocol."""

from __future__ import annotations

import numpy as np


FEATURE_NAMES = (
    "latest_level_z",
    "first_difference_z",
    "second_difference_z",
    "short_trend_z",
    "mid_trend_z",
    "long_trend_z",
    "short_to_long_volatility_ratio",
    "max_abs_jump_z",
    "seasonal_deviation_z",
)


def _robust_scale(values: np.ndarray, epsilon: float) -> float:
    values = np.asarray(values, dtype=np.float64)
    if values.size == 0 or not np.isfinite(values).all():
        return float(epsilon)
    mad = np.median(np.abs(values - np.median(values)))
    return float(max(1.4826 * mad, np.std(values, ddof=0), epsilon))


def _slope(values: np.ndarray) -> float:
    if values.size < 2:
        return 0.0
    time = np.arange(values.size, dtype=np.float64)
    centered_time = time - time.mean()
    denominator = float(np.dot(centered_time, centered_time))
    if denominator == 0.0:
        return 0.0
    return float(np.dot(centered_time, values - values.mean()) / denominator)


def causal_features(history: np.ndarray, period: int | None, epsilon: float = 1e-6) -> np.ndarray:
    """Return finite features using only the supplied history, never future values."""
    x = np.asarray(history, dtype=np.float64).reshape(-1)
    if x.size < 4 or not np.isfinite(x).all():
        raise ValueError("causal features require at least four finite historical observations")
    p = max(4, int(period or max(4, x.size // 4)))
    short = max(4, p // 4)
    mid = max(short, p)
    long = min(x.size, max(mid, 4 * p))
    recent = x[-long:]
    level_scale = _robust_scale(recent, epsilon)
    differences = np.diff(recent)
    diff_scale = _robust_scale(differences, epsilon)
    second_differences = np.diff(recent, n=2)
    second_scale = _robust_scale(second_differences, epsilon)
    median = float(np.median(recent))
    slopes = []
    for width in (short, mid, long):
        segment = recent[-min(width, recent.size):]
        slopes.append(_slope(segment) * min(width, recent.size) / level_scale)
    short_diff = np.diff(recent[-min(short, recent.size):])
    short_vol = _robust_scale(short_diff, epsilon)
    long_vol = _robust_scale(differences, epsilon)
    volatility_ratio = short_vol / long_vol if np.max(np.abs(differences), initial=0.0) > epsilon else 0.0
    seasonal = 0.0
    if p < x.size:
        seasonal = (x[-1] - x[-1 - p]) / level_scale
    features = np.array(
        [
            (x[-1] - median) / level_scale,
            differences[-1] / diff_scale if differences.size else 0.0,
            second_differences[-1] / second_scale if second_differences.size else 0.0,
            *slopes,
            volatility_ratio,
            np.max(np.abs(differences)) / diff_scale if differences.size else 0.0,
            seasonal,
        ],
        dtype=np.float32,
    )
    return np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)


def change_score(phi: np.ndarray) -> float:
    values = np.asarray(phi, dtype=np.float64)
    if values.shape[-1] != len(FEATURE_NAMES):
        raise ValueError("unexpected SAPR feature dimension")
    return float(np.max(np.abs(values)))


def state_label(phi: np.ndarray, threshold: float) -> tuple[str, float]:
    score = change_score(phi)
    return ("change" if score >= float(threshold) else "stable"), score
