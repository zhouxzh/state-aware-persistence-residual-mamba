#!/usr/bin/env python
import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS_CSV = REPO_ROOT / "results" / "gld_baselines.csv"
DEFAULT_MANUSCRIPT_CSV = REPO_ROOT / "manuscript" / "data" / "gld_baselines.csv"
DEFAULT_OUT_PREFIX = REPO_ROOT / "results" / "gld_baseline_error_models"
DEFAULT_METRICS = ["rmse", "mae", "rmsse"]


@dataclass(frozen=True)
class CandidateModel:
    name: str
    formula: str
    param_names: tuple[str, ...]
    p0_grid: tuple[tuple[float, ...], ...]
    bounds: tuple[tuple[float, ...], tuple[float, ...]]


def linear_fn(x, a, b):
    return a + b * x


def quadratic_fn(x, a, b, c):
    return a + b * x + c * x * x


def log_fn(x, a, b):
    return a + b * np.log1p(x)


def sqrt_fn(x, a, b):
    return a + b * np.sqrt(x)


def power_fn(x, a, b):
    return a * np.power(x, b)


def shifted_power_fn(x, a, b, c):
    return a + b * np.power(x, c)


def exponential_fn(x, a, b):
    return a * np.exp(b * x)


def exponential_offset_fn(x, a, b, c):
    return a + b * np.exp(c * x)


def piecewise_linear_1break_fn(x, a, b1, b2, t):
    t = np.clip(t, np.min(x), np.max(x))
    return a + b1 * np.minimum(x, t) + b2 * np.maximum(0.0, x - t)


CANDIDATES = {
    "linear": (linear_fn, CandidateModel(
        name="linear",
        formula="a + b h",
        param_names=("a", "b"),
        p0_grid=((1.0, 0.01), (10.0, 0.05), (30.0, 0.10)),
        bounds=((-np.inf, 0.0), (np.inf, np.inf)),
    )),
    "quadratic": (quadratic_fn, CandidateModel(
        name="quadratic",
        formula="a + b h + c h^2",
        param_names=("a", "b", "c"),
        p0_grid=((1.0, 0.01, 0.0), (10.0, 0.05, 0.0), (30.0, 0.10, 1e-4)),
        bounds=((-np.inf, -np.inf, 0.0), (np.inf, np.inf, np.inf)),
    )),
    "log": (log_fn, CandidateModel(
        name="log",
        formula="a + b log(1 + h)",
        param_names=("a", "b"),
        p0_grid=((1.0, 1.0), (10.0, 3.0), (30.0, 5.0)),
        bounds=((-np.inf, 0.0), (np.inf, np.inf)),
    )),
    "sqrt": (sqrt_fn, CandidateModel(
        name="sqrt",
        formula="a + b sqrt(h)",
        param_names=("a", "b"),
        p0_grid=((1.0, 0.5), (10.0, 1.0), (30.0, 2.0)),
        bounds=((-np.inf, 0.0), (np.inf, np.inf)),
    )),
    "power": (power_fn, CandidateModel(
        name="power",
        formula="a h^b",
        param_names=("a", "b"),
        p0_grid=((1.0, 0.3), (3.0, 0.5), (10.0, 0.8)),
        bounds=((0.0, 0.0), (np.inf, 5.0)),
    )),
    "shifted_power": (shifted_power_fn, CandidateModel(
        name="shifted_power",
        formula="a + b h^c",
        param_names=("a", "b", "c"),
        p0_grid=((0.0, 1.0, 0.3), (5.0, 1.0, 0.5), (20.0, 0.5, 0.8)),
        bounds=((-np.inf, 0.0, 0.0), (np.inf, np.inf, 5.0)),
    )),
    "exponential": (exponential_fn, CandidateModel(
        name="exponential",
        formula="a exp(b h)",
        param_names=("a", "b"),
        p0_grid=((1.0, 1e-3), (5.0, 5e-3), (10.0, 1e-2)),
        bounds=((0.0, 0.0), (np.inf, 1.0)),
    )),
    "exp_offset": (exponential_offset_fn, CandidateModel(
        name="exp_offset",
        formula="a + b exp(c h)",
        param_names=("a", "b", "c"),
        p0_grid=((0.0, 1.0, 1e-3), (5.0, 3.0, 5e-3), (20.0, 5.0, 1e-2)),
        bounds=((-np.inf, 0.0, 0.0), (np.inf, np.inf, 1.0)),
    )),
    "piecewise_linear_1break": (piecewise_linear_1break_fn, CandidateModel(
        name="piecewise_linear_1break",
        formula="a + b1 min(h, t) + b2 max(0, h - t)",
        param_names=("a", "b1", "b2", "t"),
        p0_grid=((1.0, 0.1, 0.03, 14.0), (10.0, 0.1, 0.05, 30.0), (30.0, 0.05, 0.03, 90.0)),
        bounds=((-np.inf, 0.0, 0.0, 1.0), (np.inf, np.inf, np.inf, 360.0)),
    )),
}


def resolve_input_csv(path_str):
    if path_str:
        return Path(path_str)
    if DEFAULT_RESULTS_CSV.exists():
        return DEFAULT_RESULTS_CSV
    return DEFAULT_MANUSCRIPT_CSV


def load_rows(path):
    with path.open() as f:
        rows = list(csv.DictReader(f))
    parsed = []
    for row in rows:
        if row.get("status") != "complete":
            continue
        try:
            row["horizon"] = int(row["horizon"])
        except (TypeError, ValueError):
            continue
        parsed.append(row)
    return parsed


def group_rows(rows, group_key, metrics, include_average_curve):
    groups = {}
    for row in rows:
        groups.setdefault(row[group_key], []).append(row)

    grouped = {}
    for name, group_rows_ in groups.items():
        group_rows_ = sorted(group_rows_, key=lambda row: row["horizon"])
        horizons = np.array([row["horizon"] for row in group_rows_], dtype=float)
        grouped[name] = {"horizon": horizons}
        for metric in metrics:
            grouped[name][metric] = np.array([float(row[metric]) for row in group_rows_], dtype=float)

    if include_average_curve:
        by_horizon = {}
        for row in rows:
            by_horizon.setdefault(int(row["horizon"]), []).append(row)
        avg_name = "AVG_ALL_MODELS"
        horizons = np.array(sorted(by_horizon), dtype=float)
        grouped[avg_name] = {"horizon": horizons}
        for metric in metrics:
            grouped[avg_name][metric] = np.array(
                [np.mean([float(row[metric]) for row in by_horizon[int(h)]]) for h in horizons],
                dtype=float,
            )

    return grouped


def curve_fit_best(fn, spec, x, y):
    best = None
    for p0 in spec.p0_grid:
        try:
            params, _ = curve_fit(
                fn,
                x,
                y,
                p0=np.asarray(p0, dtype=float),
                bounds=np.asarray(spec.bounds, dtype=float),
                maxfev=200000,
            )
            pred = fn(x, *params)
            rss = float(np.sum((y - pred) ** 2))
            if best is None or rss < best["rss"]:
                best = {"params": params, "pred": pred, "rss": rss}
        except Exception:
            continue
    return best


def fit_stats(y_true, y_pred, n_params):
    eps = 1e-12
    n = len(y_true)
    rss = float(np.sum((y_true - y_pred) ** 2))
    fit_rmse = math.sqrt(rss / n)
    tss = float(np.sum((y_true - np.mean(y_true)) ** 2))
    r2 = 1.0 - rss / tss if tss > eps else 1.0
    aic = n * math.log(max(rss / n, eps)) + 2 * n_params
    if n - n_params - 1 > 0:
        aicc = aic + (2 * n_params * (n_params + 1)) / (n - n_params - 1)
    else:
        aicc = math.inf
    bic = n * math.log(max(rss / n, eps)) + n_params * math.log(n)
    return {
        "rss": rss,
        "fit_rmse": fit_rmse,
        "r2": r2,
        "aic": aic,
        "aicc": aicc,
        "bic": bic,
    }


def format_params(param_names, params):
    return json.dumps({name: float(value) for name, value in zip(param_names, params)})


def fit_all_models(grouped, metrics):
    rows = []
    for group_name, data in grouped.items():
        x = data["horizon"]
        for metric in metrics:
            y = data[metric]
            for candidate_name, (fn, spec) in CANDIDATES.items():
                best = curve_fit_best(fn, spec, x, y)
                if best is None:
                    row = {
                        "group": group_name,
                        "metric": metric,
                        "candidate": candidate_name,
                        "formula": spec.formula,
                        "n_points": len(x),
                        "params_json": "",
                        "rss": "",
                        "fit_rmse": "",
                        "r2": "",
                        "aic": "",
                        "aicc": "",
                        "bic": "",
                    }
                else:
                    stats = fit_stats(y, best["pred"], len(spec.param_names))
                    row = {
                        "group": group_name,
                        "metric": metric,
                        "candidate": candidate_name,
                        "formula": spec.formula,
                        "n_points": len(x),
                        "params_json": format_params(spec.param_names, best["params"]),
                        **stats,
                    }
                rows.append(row)
    return rows


def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.inf


def choose_best_rows(rows):
    keyed = {}
    for row in rows:
        key = (row["group"], row["metric"])
        current = keyed.get(key)
        if current is None or safe_float(row["aicc"]) < safe_float(current["aicc"]):
            keyed[key] = row
    best = list(keyed.values())
    best.sort(key=lambda row: (row["group"], row["metric"]))
    return best


def summarize_candidates(rows, metrics):
    aggregate_rows = []
    for metric in metrics + ["ALL"]:
        for candidate_name, (_, spec) in CANDIDATES.items():
            relevant = [
                row for row in rows
                if row["candidate"] == candidate_name and (metric == "ALL" or row["metric"] == metric)
            ]
            if not relevant:
                continue
            aicc_values = [safe_float(row["aicc"]) for row in relevant if math.isfinite(safe_float(row["aicc"]))]
            fit_rmse_values = [
                safe_float(row["fit_rmse"]) for row in relevant if math.isfinite(safe_float(row["fit_rmse"]))
            ]
            if not aicc_values:
                continue
            aggregate_rows.append(
                {
                    "metric": metric,
                    "candidate": candidate_name,
                    "formula": spec.formula,
                    "curve_count": len(aicc_values),
                    "mean_aicc": float(np.mean(aicc_values)),
                    "median_aicc": float(np.median(aicc_values)),
                    "mean_fit_rmse": float(np.mean(fit_rmse_values)),
                }
            )
    aggregate_rows.sort(key=lambda row: (row["metric"], row["mean_aicc"]))
    return aggregate_rows


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_report(best_rows, summary_rows):
    print("Best candidate per curve:")
    for row in best_rows:
        print(
            f"  {row['group']} / {row['metric']}: "
            f"{row['candidate']} ({row['formula']}), AICc={safe_float(row['aicc']):.4f}"
        )

    print("\nAggregate candidate ranking by metric:")
    for metric in sorted({row["metric"] for row in summary_rows}, key=lambda item: (item != "ALL", item)):
        metric_rows = [row for row in summary_rows if row["metric"] == metric]
        if not metric_rows:
            continue
        best = min(metric_rows, key=lambda row: row["mean_aicc"])
        print(
            f"  {metric}: {best['candidate']} ({best['formula']}), "
            f"mean AICc={best['mean_aicc']:.4f}, mean fit RMSE={best['mean_fit_rmse']:.4f}"
        )


def parse_args():
    parser = argparse.ArgumentParser(description="Fit candidate math models to GLD horizon-error curves.")
    parser.add_argument("--csv", type=str, default="", help="Input CSV. Default: results/gld_baselines.csv")
    parser.add_argument(
        "--metrics",
        nargs="+",
        default=DEFAULT_METRICS,
        help="Metrics to fit, e.g. rmse mae rmsse",
    )
    parser.add_argument("--group-key", type=str, default="model", help="Grouping column in the CSV")
    parser.add_argument(
        "--out-prefix",
        type=str,
        default=str(DEFAULT_OUT_PREFIX),
        help="Output prefix for *_all.csv, *_best.csv, *_summary.csv",
    )
    parser.add_argument(
        "--no-average-curve",
        action="store_true",
        help="Do not fit the AVG_ALL_MODELS aggregate curve",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    csv_path = resolve_input_csv(args.csv)
    rows = load_rows(csv_path)
    grouped = group_rows(
        rows,
        group_key=args.group_key,
        metrics=args.metrics,
        include_average_curve=not args.no_average_curve,
    )
    fit_rows = fit_all_models(grouped, args.metrics)
    best_rows = choose_best_rows(fit_rows)
    summary_rows = summarize_candidates(fit_rows, args.metrics)

    out_prefix = Path(args.out_prefix)
    write_csv(
        out_prefix.with_name(out_prefix.name + "_all.csv"),
        fit_rows,
        [
            "group",
            "metric",
            "candidate",
            "formula",
            "n_points",
            "params_json",
            "rss",
            "fit_rmse",
            "r2",
            "aic",
            "aicc",
            "bic",
        ],
    )
    write_csv(
        out_prefix.with_name(out_prefix.name + "_best.csv"),
        best_rows,
        [
            "group",
            "metric",
            "candidate",
            "formula",
            "n_points",
            "params_json",
            "rss",
            "fit_rmse",
            "r2",
            "aic",
            "aicc",
            "bic",
        ],
    )
    write_csv(
        out_prefix.with_name(out_prefix.name + "_summary.csv"),
        summary_rows,
        ["metric", "candidate", "formula", "curve_count", "mean_aicc", "median_aicc", "mean_fit_rmse"],
    )

    print(f"Loaded {len(rows)} complete rows from {csv_path.relative_to(REPO_ROOT)}")
    print(f"Fit {len(CANDIDATES)} candidate models across {len(grouped)} curves")
    print_report(best_rows, summary_rows)


if __name__ == "__main__":
    main()
