"""Causal state features and labels specified by the SAPR-Mamba protocol."""

from __future__ import annotations

import math

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


def two_window_change_score(history: np.ndarray, period: int | None, epsilon: float = 1e-6) -> float:
    """Causal evidence for a recent level, slope, variance, or seasonal shift.

    Unlike the legacy maximum-feature score, this compares two disjoint
    historical windows and an available previous seasonal cycle.  It is used
    only by the post-V3 simulation protocol; the legacy score remains the
    default for all historical studies.
    """
    x = np.asarray(history, dtype=np.float64).reshape(-1)
    if x.size < 16 or not np.isfinite(x).all():
        raise ValueError("two-window change scoring requires finite history of length at least 16")
    p = max(4, int(period or max(4, x.size // 4)))
    width = min(max(8, p // 2), x.size // 4)
    previous, recent = x[-2 * width:-width], x[-width:]
    differences = np.diff(x)
    scale = _robust_scale(differences, epsilon)
    level = abs(float(np.median(recent) - np.median(previous))) / scale
    slope = abs(_slope(recent) - _slope(previous)) * width / scale
    previous_vol = _robust_scale(np.diff(previous), epsilon)
    recent_vol = _robust_scale(np.diff(recent), epsilon)
    volatility = abs(float(np.log(max(recent_vol, epsilon) / max(previous_vol, epsilon))))
    seasonal = 0.0
    if x.size >= p + width:
        seasonal = float(np.mean(np.abs(recent - x[-p - width:-p]))) / scale
    return float(max(level, slope, volatility, seasonal))


def ar_residual_change_score(history: np.ndarray, period: int | None, epsilon: float = 1e-6) -> float:
    """Causal residual-shift score from an early-history AR-plus-season model."""
    x = np.asarray(history, dtype=np.float64).reshape(-1)
    p = max(4, int(period or max(4, x.size // 4)))
    if x.size < max(4 * p, 48) or not np.isfinite(x).all():
        raise ValueError("AR residual change scoring requires sufficiently long finite history")
    first = p
    times = np.arange(first, x.size, dtype=np.float64)
    design = np.column_stack((np.ones_like(times), times / x.size, x[first - 1:-1], x[:x.size - p]))
    target = x[first:]
    calibration_rows = max(24, design.shape[0] // 2)
    coefficients = np.linalg.lstsq(design[:calibration_rows], target[:calibration_rows], rcond=None)[0]
    residual = target - design @ coefficients
    width = min(max(8, p // 2), residual.size // 3)
    reference = residual[:max(width, residual.size // 2)]
    recent = residual[-width:]
    scale = max(float(np.std(reference, ddof=0)), epsilon)
    mean_shift = abs(float(np.mean(recent) - np.mean(reference))) / scale * np.sqrt(width)
    variance_shift = abs(float(np.log(max(float(np.std(recent, ddof=0)), epsilon) / scale)))
    return float(max(mean_shift, variance_shift))


def bocpd_change_posterior(
    history: np.ndarray,
    period: int | None = None,
    hazard: float = 0.02,
    max_run_length: int = 96,
    prior_mean: float = 0.0,
    prior_kappa: float = 0.25,
    prior_alpha: float = 2.0,
    prior_beta: float = 1.0,
    lookback: int | None = None,
    input_mode: str = "raw",
    recent_run_length: int = 12,
    epsilon: float = 1e-12,
) -> float:
    """Causal Student-t BOCPD probability of a change at the final history step.

    A normal-inverse-gamma predictive model is updated online over a bounded
    run-length support.  The returned posterior is calculated exclusively from
    the supplied history; callers calibrate its binary threshold separately.
    """
    x = np.asarray(history, dtype=np.float64).reshape(-1)
    if lookback is not None:
        x = x[-int(lookback):]
    p = max(2, int(period or max(2, x.size // 4)))
    if input_mode == "difference":
        x = np.diff(x)
    elif input_mode == "seasonal_residual":
        if x.size <= p:
            raise ValueError("seasonal-residual BOCPD needs one complete period")
        x = x[p:] - x[:-p]
    elif input_mode != "raw":
        raise ValueError(f"unknown BOCPD input mode: {input_mode}")
    if x.size < 8 or not np.isfinite(x).all():
        raise ValueError("BOCPD requires at least eight finite historical observations")
    if not 0.0 < float(hazard) < 1.0:
        raise ValueError("BOCPD hazard must be in (0, 1)")
    scale = max(_robust_scale(np.diff(x), epsilon), epsilon)
    values = (x - float(np.median(x))) / scale
    runs = np.array([1.0], dtype=np.float64)
    means = np.array([float(prior_mean)], dtype=np.float64)
    kappas = np.array([float(prior_kappa)], dtype=np.float64)
    alphas = np.array([float(prior_alpha)], dtype=np.float64)
    betas = np.array([float(prior_beta)], dtype=np.float64)
    log_two_pi = float(np.log(np.pi))
    for observation in values:
        degrees = 2.0 * alphas
        predictive_scale = np.sqrt(betas * (kappas + 1.0) / (alphas * kappas))
        standardized = (observation - means) / predictive_scale
        log_density = (
            np.vectorize(math.lgamma)(0.5 * (degrees + 1.0))
            - np.vectorize(math.lgamma)(0.5 * degrees)
            - 0.5 * (np.log(degrees) + log_two_pi)
            - np.log(predictive_scale)
            - 0.5 * (degrees + 1.0) * np.log1p(np.square(standardized) / degrees)
        )
        density = np.exp(np.clip(log_density, -745.0, 50.0))
        evidence = float(np.sum(runs * density))
        cp_mass = float(hazard) * evidence
        growth = (1.0 - float(hazard)) * runs * density
        new_runs = np.concatenate(([cp_mass], growth))
        new_means = np.concatenate(([float(prior_mean)], (kappas * means + observation) / (kappas + 1.0)))
        new_kappas = np.concatenate(([float(prior_kappa)], kappas + 1.0))
        new_alphas = np.concatenate(([float(prior_alpha)], alphas + 0.5))
        new_betas = np.concatenate(([float(prior_beta)], betas + (kappas * np.square(observation - means)) / (2.0 * (kappas + 1.0))))
        if new_runs.size > int(max_run_length) + 1:
            overflow = float(np.sum(new_runs[int(max_run_length) + 1:]))
            new_runs = new_runs[:int(max_run_length) + 1]
            new_runs[-1] += overflow
            new_means = new_means[:int(max_run_length) + 1]
            new_kappas = new_kappas[:int(max_run_length) + 1]
            new_alphas = new_alphas[:int(max_run_length) + 1]
            new_betas = new_betas[:int(max_run_length) + 1]
        normalizer = max(float(np.sum(new_runs)), epsilon)
        runs = new_runs / normalizer
        means, kappas, alphas, betas = new_means, new_kappas, new_alphas, new_betas
    # Under fixed-hazard BOCPD, exact-current change probability is the fixed
    # hazard. The causal state signal is mass on recent short run lengths.
    return float(np.clip(np.sum(runs[:max(1, int(recent_run_length)) + 1]), 0.0, 1.0))


def state_label(phi: np.ndarray, threshold: float) -> tuple[str, float]:
    score = change_score(phi)
    return ("change" if score >= float(threshold) else "stable"), score
