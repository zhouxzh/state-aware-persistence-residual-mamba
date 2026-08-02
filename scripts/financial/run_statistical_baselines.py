#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import io
import importlib.metadata
import json
import math
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.financial.common import (
    DEFAULT_PROTOCOL,
    MANIFEST_DIR,
    atomic_write_bytes,
    atomic_write_json,
    load_protocol,
)


TRAINING_MANIFEST = MANIFEST_DIR / "training_datasets.json"
OUTPUT_ROOT = REPO_ROOT / "results" / "financial_confirmatory" / "statistical"
FINAL_SUMMARY = REPO_ROOT / "results" / "financial_confirmatory" / "final_runs.json"
MAMBA_MODELS = {"S_Mamba", "NS_Mamba-D", "MS_Mamba-MD", "PMS_Mamba-PD"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run frozen statistical financial baselines.")
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--manifest", type=Path, default=TRAINING_MANIFEST)
    parser.add_argument("--tasks", nargs="+", default=["ALL"])
    parser.add_argument(
        "--unlock-test",
        action="store_true",
        help="Required explicit acknowledgement before reading final test targets.",
    )
    return parser.parse_args()


def require_frozen_neural_selection(protocol: dict, manifest: dict) -> None:
    for task in manifest:
        for phase in ("baseline", "mamba"):
            path = REPO_ROOT / "results" / "optuna" / task / f"{phase}_best_params.json"
            if not path.exists():
                raise RuntimeError(f"Missing frozen selection file: {path}")
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("dataset") != task or payload.get("phase") != phase:
                raise RuntimeError(f"Selection identity mismatch in {path}")
            expected = [
                model for model in protocol["level_models"]
                if (model in MAMBA_MODELS) == (phase == "mamba")
            ]
            if set(payload.get("models", {})) != set(expected):
                raise RuntimeError(f"Incomplete selection model set in {path}")
            if payload.get("protocol_version") != protocol["protocol_version"]:
                raise RuntimeError(f"Selection protocol mismatch in {path}")
            if payload.get("protocol_sha256") != manifest[task]["protocol_sha256"]:
                raise RuntimeError(f"Selection protocol hash mismatch in {path}")
            if payload.get("data_sha256") != manifest[task]["data_sha256"]:
                raise RuntimeError(f"Selection data hash mismatch in {path}")
            if list(map(int, payload.get("full_horizons", []))) != protocol["horizons"]:
                raise RuntimeError(f"Selection horizon mismatch in {path}")
            for model in expected:
                model_selection = payload["models"][model]
                if model_selection.get("selection_eval_flag") != "val":
                    raise RuntimeError(f"Selection did not use validation data: {task}/{model}")
                if model_selection.get("final_eval_flag") != "not_opened":
                    raise RuntimeError(f"Selection accessed test data: {task}/{model}")
                score = float(model_selection.get("best_validation_replay_balanced_rmsse", float("nan")))
                if not math.isfinite(score):
                    raise RuntimeError(f"Selection score is non-finite: {task}/{model}")


def require_complete_neural_final(protocol: dict, manifest: dict) -> None:
    if not FINAL_SUMMARY.is_file():
        raise RuntimeError(f"Missing final neural summary: {FINAL_SUMMARY}")
    payload = json.loads(FINAL_SUMMARY.read_text(encoding="utf-8"))
    if payload.get("protocol_version") != protocol["protocol_version"]:
        raise RuntimeError("Final neural summary protocol mismatch")
    protocol_hashes = {config["protocol_sha256"] for config in manifest.values()}
    if len(protocol_hashes) != 1 or payload.get("protocol_sha256") != protocol_hashes.pop():
        raise RuntimeError("Final neural summary protocol hash mismatch")
    if payload.get("horizons") != protocol["horizons"]:
        raise RuntimeError("Final neural summary horizon mismatch")
    if payload.get("seeds") != protocol["final_seeds"]:
        raise RuntimeError("Final neural summary seed mismatch")
    expected = {
        f"{task}|{model}|{seed}"
        for task in manifest
        for model in protocol["level_models"]
        for seed in protocol["final_seeds"]
    }
    complete = {
        key for key, record in payload.get("runs", {}).items()
        if record.get("status") == "complete"
    }
    if complete != expected:
        raise RuntimeError(
            f"Final neural matrix is incomplete: complete={len(complete)}, expected={len(expected)}"
        )


def selected_tasks(manifest: dict, requested: list[str]) -> list[str]:
    if requested == ["ALL"]:
        return sorted(manifest)
    invalid = sorted(set(requested) - set(manifest))
    if invalid:
        raise ValueError(f"Unknown task IDs: {invalid}")
    return requested


def read_existing_rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_metric_rows(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    rows = sorted(rows, key=lambda row: (row["dataset"], row["model"], int(row["horizon"])))
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    atomic_write_bytes(path, buffer.getvalue().encode("utf-8"))


def task_is_complete(task: str, config: dict, protocol: dict, rows: list[dict]) -> bool:
    task_rows = [row for row in rows if row.get("dataset") == task]
    models = ["Last-value", "Random-walk-drift", "ARIMA"]
    if config["features"] == "MS":
        models.append("VAR-difference")
    expected = {(model, int(horizon)) for model in models for horizon in protocol["horizons"]}
    observed = {(row.get("model"), int(row.get("horizon", -1))) for row in task_rows}
    if observed != expected or len(task_rows) != len(expected):
        return False
    for row in task_rows:
        bundle = REPO_ROOT / row["bundle"]
        metadata_path = bundle.with_name("meta.json")
        if not bundle.is_file() or not metadata_path.is_file():
            return False
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        checks = {
            "protocol_version": protocol["protocol_version"],
            "dataset": task,
            "data_sha256": config["data_sha256"],
            "model": row["model"],
            "horizon": int(row["horizon"]),
            "evaluation_split": "test",
        }
        if any(metadata.get(field) != expected_value for field, expected_value in checks.items()):
            return False
        if row["model"] == "ARIMA":
            selection = metadata.get("arima_selection", {})
            if (
                metadata.get("coefficient_fit_converged") is not True
                or selection.get("selected_converged") is not True
                or int(selection.get("converged_candidate_count", 0)) <= 0
            ):
                return False
    return True


def metric_row(truth: np.ndarray, prediction: np.ndarray, train_target: np.ndarray) -> dict:
    error = truth - prediction
    scale = float(np.mean(np.diff(train_target) ** 2))
    mse = float(np.mean(error ** 2))
    return {
        "mae": float(np.mean(np.abs(error))),
        "mse": mse,
        "rmse": math.sqrt(mse),
        "rmsse": math.sqrt(mse / scale),
    }


def rolling_naive(
    values: np.ndarray,
    dates: np.ndarray,
    test_start: int,
    horizon: int,
    drift: bool,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    origins = range(test_start, len(values) - horizon + 1)
    predictions, truths, origin_dates = [], [], []
    for origin in origins:
        last = values[origin - 1]
        if drift and origin > 1:
            slope = (last - values[0]) / (origin - 1)
            prediction = last + slope * np.arange(1, horizon + 1)
        else:
            prediction = np.repeat(last, horizon)
        predictions.append(prediction)
        truths.append(values[origin:origin + horizon])
        origin_dates.append(dates[origin])
    return np.asarray(predictions), np.asarray(truths), np.asarray(origin_dates)


def select_arima_order(train_target: np.ndarray) -> tuple[tuple[int, int, int], dict]:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tools.sm_exceptions import ConvergenceWarning

    candidates = []
    attempted = 0
    failed = 0
    nonconverged = 0
    for d in (0, 1):
        for p in range(4):
            for q in range(4):
                if p == q == 0 and d == 0:
                    continue
                attempted += 1
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", ConvergenceWarning)
                        fit = ARIMA(
                            train_target,
                            order=(p, d, q),
                            trend="t" if d == 1 else "ct",
                        ).fit()
                    converged = bool(fit.mle_retvals.get("converged", False))
                    if converged and np.isfinite(fit.aic):
                        candidates.append((float(fit.aic), p, d, q))
                    else:
                        nonconverged += 1
                except Exception:
                    failed += 1
                    continue
    if not candidates:
        raise RuntimeError("No ARIMA candidate converged")
    selected_aic, p, d, q = min(candidates)
    return (p, d, q), {
        "attempted_candidate_count": attempted,
        "converged_candidate_count": len(candidates),
        "nonconverged_candidate_count": nonconverged,
        "failed_candidate_count": failed,
        "selected_converged": True,
        "selected_aic": selected_aic,
    }


def rolling_arima(
    values: np.ndarray,
    dates: np.ndarray,
    train_end: int,
    test_start: int,
    horizon: int,
    order: tuple[int, int, int],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    from statsmodels.tsa.arima.model import ARIMA

    history = values[:test_start]
    result = ARIMA(history, order=order, trend="t" if order[1] == 1 else "ct").fit()
    if not bool(result.mle_retvals.get("converged", False)):
        raise RuntimeError(f"Pre-test ARIMA fit did not converge for order {order}")
    predictions, truths, origin_dates = [], [], []
    for origin in range(test_start, len(values) - horizon + 1):
        predictions.append(np.asarray(result.forecast(horizon), dtype=float))
        truths.append(values[origin:origin + horizon])
        origin_dates.append(dates[origin])
        result = result.append([values[origin]], refit=False)
    return np.asarray(predictions), np.asarray(truths), np.asarray(origin_dates)


def select_var_lag(train_values: np.ndarray) -> int:
    from statsmodels.tsa.api import VAR

    differences = np.diff(train_values, axis=0)
    candidates = []
    for lag in range(1, 11):
        try:
            fit = VAR(differences).fit(lag, trend="ct")
            if np.isfinite(fit.bic):
                candidates.append((float(fit.bic), lag))
        except Exception:
            continue
    if not candidates:
        raise RuntimeError("No VAR lag candidate converged")
    return min(candidates)[1]


def rolling_var(
    values: np.ndarray,
    dates: np.ndarray,
    test_start: int,
    horizon: int,
    lag: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    from statsmodels.tsa.api import VAR

    differences = np.diff(values[:test_start], axis=0)
    fit = VAR(differences).fit(lag, trend="ct")
    target_index = values.shape[1] - 1
    predictions, truths, origin_dates = [], [], []
    for origin in range(test_start, len(values) - horizon + 1):
        available_differences = np.diff(values[:origin], axis=0)
        difference_forecast = fit.forecast(available_differences[-lag:], steps=horizon)
        level_forecast = values[origin - 1] + np.cumsum(difference_forecast, axis=0)
        predictions.append(level_forecast[:, target_index])
        truths.append(values[origin:origin + horizon, target_index])
        origin_dates.append(dates[origin])
    return np.asarray(predictions), np.asarray(truths), np.asarray(origin_dates)


def save_prediction_bundle(
    task: str,
    model: str,
    horizon: int,
    prediction: np.ndarray,
    truth: np.ndarray,
    origin_dates: np.ndarray,
    metadata: dict,
) -> str:
    directory = OUTPUT_ROOT / task / model / f"h{horizon}"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "predictions.npz"
    np.savez_compressed(path, prediction=prediction, truth=truth, origin_dates=origin_dates)
    atomic_write_json(directory / "meta.json", metadata)
    return str(path.relative_to(REPO_ROOT))


def main() -> None:
    args = parse_args()
    if not args.unlock_test:
        raise SystemExit("Refusing to read final test targets without --unlock-test")
    protocol = load_protocol(args.protocol)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    require_frozen_neural_selection(protocol, manifest)
    require_complete_neural_final(protocol, manifest)
    tasks = selected_tasks(manifest, args.tasks)
    output_csv = OUTPUT_ROOT / "metrics.csv"
    rows = read_existing_rows(output_csv)

    for task in tasks:
        config = manifest[task]
        if task_is_complete(task, config, protocol, rows):
            print(f"skip complete statistical baselines for {task}")
            continue
        rows = [row for row in rows if row.get("dataset") != task]
        task_rows = []
        frame = pd.read_csv(REPO_ROOT / config["root_path"] / config["data_path"])
        dates = np.asarray(
            pd.to_datetime(frame.pop("date")).dt.strftime("%Y-%m-%d").tolist(),
            dtype="U10",
        )
        values = frame.to_numpy(dtype=float)
        target = frame[config["target"]].to_numpy(dtype=float)
        target_index = frame.columns.get_loc(config["target"])
        date_index = pd.Index(dates)
        train_end = int(date_index.searchsorted(protocol["splits"]["train_end"], side="right"))
        test_start = int(date_index.searchsorted(protocol["splits"]["test_start"], side="left"))
        arima_order, arima_selection = select_arima_order(target[:train_end])
        var_lag = select_var_lag(values[:train_end]) if config["features"] == "MS" else None
        pretest_end = str(dates[test_start - 1])

        for horizon in protocol["horizons"]:
            methods = {
                "Last-value": rolling_naive(target, dates, test_start, horizon, drift=False),
                "Random-walk-drift": rolling_naive(target, dates, test_start, horizon, drift=True),
                "ARIMA": rolling_arima(target, dates, train_end, test_start, horizon, arima_order),
            }
            if var_lag is not None:
                methods["VAR-difference"] = rolling_var(values, dates, test_start, horizon, var_lag)
            for model, (prediction, truth, origins) in methods.items():
                metrics = metric_row(truth, prediction, target[:train_end])
                bundle = save_prediction_bundle(
                    task,
                    model,
                    horizon,
                    prediction,
                    truth,
                    origins,
                    {
                        "protocol_version": protocol["protocol_version"],
                        "dataset": task,
                        "data_sha256": config["data_sha256"],
                        "model": model,
                        "horizon": horizon,
                        "target": config["target"],
                        "arima_order": list(arima_order) if model == "ARIMA" else None,
                        "arima_selection": arima_selection if model == "ARIMA" else None,
                        "coefficient_fit_converged": True if model == "ARIMA" else None,
                        "var_lag": var_lag if model == "VAR-difference" else None,
                        "order_selection_end": (
                            protocol["splits"]["train_end"]
                            if model in {"ARIMA", "VAR-difference"}
                            else None
                        ),
                        "coefficient_fit_end": (
                            pretest_end if model in {"ARIMA", "VAR-difference"} else None
                        ),
                        "sequential_update_refit": (
                            False if model in {"ARIMA", "VAR-difference"} else None
                        ),
                        "evaluation_split": "test",
                        "python_version": sys.version,
                        "numpy_version": np.__version__,
                        "pandas_version": pd.__version__,
                        "statsmodels_version": importlib.metadata.version("statsmodels"),
                    },
                )
                task_rows.append(
                    {
                        "dataset": task,
                        "model": model,
                        "horizon": horizon,
                        "origin_count": len(origins),
                        **metrics,
                        "bundle": bundle,
                    }
                )
        rows.extend(task_rows)
        write_metric_rows(output_csv, rows)
        print(f"completed statistical baselines for {task}")

    print(f"wrote {output_csv}")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"Statistical benchmark blocked: {exc}") from None
