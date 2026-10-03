"""Frozen validation-selected ETS and ARIMA contextual baselines."""

from __future__ import annotations

from collections import defaultdict
import warnings

import numpy as np


def _fit_without_numerical_warnings(fit_callable):
    """Treat numerical/convergence warnings as failed statistical fits.

    The protocol requires non-convergence to be recorded and to use the fixed
    persistence fallback; returning a warned optimizer result would hide that
    failure from the evidence matrix.
    """
    from statsmodels.tools.sm_exceptions import ConvergenceWarning

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        fitted = fit_callable()
    problematic = [
        warning for warning in captured
        if issubclass(warning.category, (ConvergenceWarning, RuntimeWarning))
    ]
    if problematic:
        messages = "; ".join(str(warning.message) for warning in problematic[:3])
        raise RuntimeError(f"statistical fit emitted convergence/numerical warning: {messages}")
    return fitted


def _history(history: np.ndarray, maximum_length: int) -> np.ndarray:
    values = np.asarray(history, dtype=np.float64)
    return values[-min(values.size, int(maximum_length)):]


def forecast_ets(history: np.ndarray, horizon: int, candidate: str, maximum_length: int) -> np.ndarray:
    from statsmodels.tsa.holtwinters import Holt, SimpleExpSmoothing

    values = _history(history, maximum_length)
    if candidate == "simple":
        fitted = _fit_without_numerical_warnings(
            lambda: SimpleExpSmoothing(values, initialization_method="estimated").fit(optimized=True)
        )
    elif candidate == "additive_trend":
        fitted = _fit_without_numerical_warnings(
            lambda: Holt(values, damped_trend=False, initialization_method="estimated").fit(optimized=True)
        )
    elif candidate == "additive_trend_damped":
        fitted = _fit_without_numerical_warnings(
            lambda: Holt(values, damped_trend=True, initialization_method="estimated").fit(optimized=True)
        )
    else:
        raise ValueError(f"Unknown ETS candidate: {candidate}")
    return np.asarray(fitted.forecast(int(horizon)), dtype=np.float32)


def forecast_arima(history: np.ndarray, horizon: int, order: tuple[int, int, int], maximum_length: int, maximum_iterations: int) -> np.ndarray:
    from statsmodels.tsa.arima.model import ARIMA

    values = _history(history, maximum_length)
    fitted = _fit_without_numerical_warnings(
        lambda: ARIMA(values, order=tuple(order), trend="n" if int(order[1]) else "c").fit(
            method_kwargs={"maxiter": int(maximum_iterations)}
        )
    )
    return np.asarray(fitted.forecast(int(horizon)), dtype=np.float32)


def fixed_rows_by_series(dataset, maximum_per_series: int) -> dict[int, list[int]]:
    """Evenly choose at most a fixed number of already-valid origins for each series."""
    grouped: dict[int, list[int]] = defaultdict(list)
    for row_index, (series_index, _) in enumerate(dataset.origins):
        grouped[int(series_index)].append(row_index)
    result: dict[int, list[int]] = {}
    for series_index, rows in grouped.items():
        if len(rows) <= maximum_per_series:
            result[series_index] = rows
        else:
            indices = np.linspace(0, len(rows) - 1, int(maximum_per_series), dtype=int)
            result[series_index] = [rows[index] for index in indices]
    return result


def select_candidates(dataset, family: str, selection_config: dict, period: int, maximum_origins: int = 20, restore_raw=None) -> tuple[dict[int, object], list[dict]]:
    """Choose one candidate per series using validation windows only."""
    if family not in {"ETS", "ARIMA"}:
        raise ValueError(f"Unsupported statistical family: {family}")
    candidates = selection_config["ets_candidates"] if family == "ETS" else [tuple(order) for order in selection_config["arima_orders"]]
    selected: dict[int, object] = {}
    failures: list[dict] = []
    history_length = 8 * int(period)
    for series_index, rows in fixed_rows_by_series(dataset, maximum_origins).items():
        losses: dict[str, list[float]] = defaultdict(list)
        candidate_failures: set[str] = set()
        for candidate in candidates:
            label = str(candidate)
            for row_index in rows:
                item = dataset[row_index]
                try:
                    history, target = restore_raw(item) if restore_raw is not None else (item["x"], item["y"])
                    if family == "ETS":
                        forecast = forecast_ets(history, dataset.horizon, str(candidate), history_length)
                    else:
                        forecast = forecast_arima(history, dataset.horizon, tuple(candidate), history_length, selection_config["maximum_iterations"])
                    losses[label].append(float(np.mean((forecast - target) ** 2)))
                except Exception as exc:
                    candidate_failures.add(label)
                    failures.append({"stage": "validation_selection", "model": family, "series_index": series_index, "candidate": label, "origin": int(item["origin"]), "error": repr(exc)})
        valid = [
            (np.mean(losses[str(candidate)]), candidate)
            for candidate in candidates
            if losses[str(candidate)] and str(candidate) not in candidate_failures
        ]
        if valid:
            selected[series_index] = min(valid, key=lambda item: item[0])[1]
        else:
            selected[series_index] = None
            failures.append({"stage": "validation_selection", "model": family, "series_index": series_index, "candidate": "none", "origin": "", "error": "all configured candidates failed; persistence fallback"})
    return selected, failures


def forecast_selected(history: np.ndarray, horizon: int, family: str, candidate: object | None, selection_config: dict, period: int) -> np.ndarray:
    if candidate is None:
        return np.repeat(np.asarray(history, dtype=np.float32)[-1], int(horizon))
    if family == "ETS":
        return forecast_ets(history, horizon, str(candidate), 8 * int(period))
    if family == "ARIMA":
        return forecast_arima(history, horizon, tuple(candidate), 8 * int(period), selection_config["maximum_iterations"])
    raise ValueError(f"Unsupported statistical family: {family}")
