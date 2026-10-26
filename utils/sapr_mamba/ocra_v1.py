"""Pure OCRA-v1 protocol helpers.

This module deliberately has no result-path side effects.  The runner owns all
I/O so feature and action logic can be unit-tested without materializing data.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

import numpy as np

from .features import FEATURE_NAMES, causal_features


OCRA_FEATURE_NAMES = (
    *FEATURE_NAMES,
    "delta_mean",
    "early_late_mean",
    "dir_agree",
    "post_jump_stability",
    "season_shape_dist",
    "season_phase_shift",
    "rw_proxy",
)

OCRA_V1_1_FEATURE_NAMES = (
    *OCRA_FEATURE_NAMES,
    "recent_jump_score",
    "recent_jump_age_fraction",
)

NEGATIVE_MECHANISMS = {"stable", "future_jump", "variance_shift", "random_walk"}
POSITIVE_OPEN_MECHANISMS = {"trend_break", "seasonal_change"}


def robust_scale(values: np.ndarray, epsilon: float = 1e-6) -> float:
    """Protocol scale: robust MAD, population SD, then the numerical floor."""
    values = np.asarray(values, dtype=np.float64).reshape(-1)
    if not values.size or not np.isfinite(values).all():
        return float(epsilon)
    mad = float(np.median(np.abs(values - np.median(values))))
    return float(max(1.4826 * mad, np.std(values, ddof=0), epsilon))


def _slope(values: np.ndarray) -> float:
    if len(values) < 2:
        return 0.0
    time = np.arange(len(values), dtype=np.float64)
    centered = time - time.mean()
    denominator = float(np.dot(centered, centered))
    return 0.0 if denominator == 0.0 else float(np.dot(centered, values - values.mean()) / denominator)


def ocra_features(history: np.ndarray, period: int = 48, epsilon: float = 1e-6) -> np.ndarray:
    """Return the frozen 16-dimensional causal OCRA evidence vector."""
    x = np.asarray(history, dtype=np.float64).reshape(-1)
    if len(x) < 192 or not np.isfinite(x).all():
        raise ValueError("OCRA features require 192 finite historical observations")
    p, ws, wm, wl = int(period), 12, 48, 192
    recent = x[-wl:]
    scale = robust_scale(recent, epsilon)
    before = recent[:wm]
    late = recent[-wm:]
    delta_mean = (float(np.median(late)) - float(np.median(before))) / scale
    early, later = recent[: 2 * wl // 3], recent[2 * wl // 3 :]
    early_late_mean = (float(np.mean(later)) - float(np.mean(early))) / scale
    slopes = [_slope(recent[-width:]) for width in (ws, wm, wl)]
    dir_agree = float(all(value > 0 for value in slopes) or all(value < 0 for value in slopes))
    diffs = np.diff(recent)
    jump = int(np.argmax(np.abs(diffs))) + 1 if diffs.size else 0
    left, right = recent[:jump], recent[jump:]
    post_jump_stability = 1.0 if min(len(left), len(right)) < 4 else robust_scale(right, epsilon) / robust_scale(left, epsilon)
    season_shape_dist, season_phase_shift = 0.0, 0.0
    if len(x) >= 2 * p:
        previous, current = x[-2 * p:-p], x[-p:]
        previous = previous - np.mean(previous)
        current = current - np.mean(current)
        season_shape_dist = float(np.linalg.norm(current - previous) / scale)
        correlations = np.asarray([np.dot(current, np.roll(previous, lag)) for lag in range(p)], dtype=np.float64)
        season_phase_shift = float(int(np.argmax(correlations)) / p)
    levels = float(np.var(recent, ddof=0))
    difference_variance = float(np.var(diffs, ddof=0)) if diffs.size else 0.0
    rw_proxy = levels / max(difference_variance, epsilon)
    features = np.concatenate(
        (
            causal_features(x, p, epsilon).astype(np.float64),
            np.asarray(
                (delta_mean, early_late_mean, dir_agree, post_jump_stability, season_shape_dist, season_phase_shift, rw_proxy),
                dtype=np.float64,
            ),
        )
    )
    return np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)


def ocra_v1_1_features(history: np.ndarray, period: int = 48, epsilon: float = 1e-6) -> np.ndarray:
    """Add causal magnitude and recency evidence for a level jump.

    v1.1 separates a recent, still-observable step from a label whose original
    change has already left the historical window.  Both terms use only the
    supplied history and are independent of series identity or future values.
    """
    x = np.asarray(history, dtype=np.float64).reshape(-1)
    base = ocra_features(x, period, epsilon).astype(np.float64)
    recent = x[-192:]
    differences = np.diff(recent)
    if differences.size == 0:
        jump_score, jump_age = 0.0, 1.0
    else:
        jump_index = int(np.argmax(np.abs(differences)))
        jump_score = abs(float(differences[jump_index])) / robust_scale(differences, epsilon)
        jump_age = float((len(differences) - 1 - jump_index) / max(len(differences) - 1, 1))
    return np.nan_to_num(
        np.concatenate((base, np.asarray((jump_score, jump_age), dtype=np.float64))),
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    ).astype(np.float32)


def true_label(record: dict, origin: int, horizon: int, delay: int) -> str:
    mechanism, change_point = str(record["mechanism"]), int(record["change_point"])
    if mechanism in {"stable", "stable_season", "random_walk", "variance_shift"}:
        return "stable"
    if mechanism == "continuing_trend":
        return "visible_change"
    if mechanism == "future_jump":
        return "unseen_change" if origin <= change_point < origin + horizon else "stable"
    return "visible_change" if origin >= change_point + int(delay) else "stable"


def target_action(mechanism: str, label: str) -> str:
    """Map generator truth to the protocol's three actions without detector input."""
    if label != "visible_change":
        return "CLOSED"
    if mechanism in POSITIVE_OPEN_MECHANISMS:
        return "OPEN"
    return "DEFER"


def target_action_v1_1(mechanism: str, label: str, origin: int, change_point: int, visible_lookback: int = 192) -> str:
    """v1.1 defers a level shift only while the shift remains observable."""
    if label != "visible_change":
        return "CLOSED"
    if mechanism in POSITIVE_OPEN_MECHANISMS:
        return "OPEN"
    if mechanism == "visible_level_shift" and int(origin) - int(change_point) > int(visible_lookback):
        return "CLOSED"
    return "DEFER"


def target_action_v1_2(mechanism: str, label: str, origin: int, change_point: int, visible_lookback: int = 96) -> str:
    return target_action_v1_1(mechanism, label, origin, change_point, visible_lookback)


def evaluation_set(mechanism: str, label: str) -> str | None:
    if mechanism == "stable" and label == "stable":
        return "N0"
    if mechanism == "future_jump" and label == "unseen_change":
        return "N2"
    if mechanism == "variance_shift":
        return "N7"
    if mechanism == "random_walk":
        return "N8"
    if mechanism in POSITIVE_OPEN_MECHANISMS and label == "visible_change":
        return "S+"
    if mechanism == "visible_level_shift" and label == "visible_change":
        return "T1-vis"
    if mechanism == "continuing_trend" and label == "visible_change":
        return "trend-diagnostic"
    return None


def evaluation_set_v1_1(mechanism: str, label: str, origin: int, change_point: int, visible_lookback: int = 192) -> str | None:
    """v1.1 reports level-shift routing only for visible evidence windows."""
    if mechanism == "visible_level_shift" and label == "visible_change":
        return "T1-vis" if int(origin) - int(change_point) <= int(visible_lookback) else "T1-post-observable"
    return evaluation_set(mechanism, label)


def evaluation_set_v1_2(mechanism: str, label: str, origin: int, change_point: int, visible_lookback: int = 96) -> str | None:
    return evaluation_set_v1_1(mechanism, label, origin, change_point, visible_lookback)


def series_id_hash(series_ids: Iterable[str]) -> str:
    payload = "\n".join(sorted(str(value) for value in series_ids)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def normalize_from_validation(validation_features: np.ndarray, *feature_sets: np.ndarray) -> tuple[dict, list[np.ndarray]]:
    validation_features = np.asarray(validation_features, dtype=np.float64)
    mean = np.mean(validation_features, axis=0)
    scale = np.std(validation_features, axis=0, ddof=0)
    scale = np.where(scale > 1e-6, scale, 1.0)
    return {"mean": mean.tolist(), "scale": scale.tolist()}, [((np.asarray(item, dtype=np.float64) - mean) / scale).astype(np.float32) for item in feature_sets]


def action_from_probabilities(open_probability: np.ndarray, defer_probability: np.ndarray, open_threshold: float, defer_threshold: float) -> np.ndarray:
    open_probability = np.asarray(open_probability, dtype=np.float64)
    defer_probability = np.asarray(defer_probability, dtype=np.float64)
    return np.where(open_probability >= open_threshold, "OPEN", np.where(defer_probability >= defer_threshold, "DEFER", "CLOSED"))
