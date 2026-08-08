#!/usr/bin/env python
"""Generate evidence-bound comparison tables and figures for repository documentation."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = REPO_ROOT / "reproducibility" / "nonstationary_analysis_v1" / "final" / "aggregate_metrics.csv"
PROFILE_SOURCE = (
    REPO_ROOT
    / "reproducibility"
    / "nonstationary_analysis_v1"
    / "final"
    / "neural_metrics_by_seed.csv"
)
RUNTIME_SUMMARY_SOURCE = (
    REPO_ROOT
    / "reproducibility"
    / "nonstationary_analysis_v1"
    / "final"
    / "runtime_summary.csv"
)
RUNTIME_ENVIRONMENT_SOURCE = (
    REPO_ROOT
    / "reproducibility"
    / "nonstationary_analysis_v1"
    / "final"
    / "runtime_environment.json"
)
SEED_STABILITY_SOURCE = (
    REPO_ROOT
    / "reproducibility"
    / "nonstationary_analysis_v1"
    / "final"
    / "seed_stability.csv"
)
QUALITY_SOURCE = REPO_ROOT / "data" / "financial" / "manifests" / "quality_report.json"
DIAGNOSTIC_SOURCE = (
    REPO_ROOT / "data" / "financial" / "manifests" / "nonstationarity_diagnostics_full.csv"
)
TRAINING_SOURCE = REPO_ROOT / "data" / "financial" / "manifests" / "training_datasets.json"
PROTOCOL_SOURCE = REPO_ROOT / "configs" / "financial_benchmark.json"
OUTPUT_ROOT = REPO_ROOT / "docs" / "figures"
PMS_MODEL = "PMS_Mamba-PD"
TERM_MAP = {1: "Short", 5: "Short", 20: "Middle", 60: "Middle", 120: "Long", 252: "Long"}
HORIZON_ORDER = (1, 5, 20, 60, 120, 252)
FAMILY_ORDER = ("cross_asset", "crypto", "fx", "yields")
TERM_ORDER = ("Short", "Middle", "Long")
TASK_ORDER = tuple(
    f"financial_{family}_{mode.lower()}"
    for family in FAMILY_ORDER
    for mode in ("MS", "S")
)
METRICS = {
    "path_mae_mean": "MAE",
    "path_mse_mean": "MSE",
    "path_rmse_mean": "RMSE",
    "path_rmsse_mean": "RMSSE",
    "terminal_mae_mean": "Terminal MAE",
    "terminal_mse_mean": "Terminal MSE",
    "terminal_rmse_mean": "Terminal RMSE",
    "terminal_rmsse_mean": "Terminal RMSSE",
}
DISPLAY_METRICS = ("path_mae_mean", "path_rmse_mean", "path_rmsse_mean")
HORIZON_METRICS = (
    ("path_mae_mean", "MAE", "Target units"),
    ("path_mse_mean", "MSE", "Squared target units"),
    ("path_rmse_mean", "RMSE", "Target units"),
    ("path_rmsse_mean", "RMSSE", "Scale-free"),
)
MAMBA_MODELS = {"S_Mamba", "NS_Mamba-D", "MS_Mamba-MD", PMS_MODEL}
STATISTICAL_MODELS = {"Last-value", "Random-walk-drift", "ARIMA", "VAR-difference"}
MODEL_ORDER = (
    "Last-value",
    "Random-walk-drift",
    "ARIMA",
    "VAR-difference",
    "DLinear",
    "NLinear",
    "PatchTST",
    "TimesNet",
    "iTransformer",
    "S_Mamba",
    "NS_Mamba-D",
    "MS_Mamba-MD",
    PMS_MODEL,
)
PROFILE_MODEL_ORDER = (
    "NLinear",
    "DLinear",
    "PatchTST",
    "iTransformer",
    "S_Mamba",
    "NS_Mamba-D",
    "MS_Mamba-MD",
    PMS_MODEL,
    "TimesNet",
)
STYLE = {
    "font.family": "DejaVu Sans",
    "font.size": 7.5,
    "axes.labelsize": 8,
    "axes.titlesize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "axes.spines.top": False,
    "axes.spines.right": False,
}


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_category(model: str) -> str:
    if model in MAMBA_MODELS:
        return "mamba"
    if model in STATISTICAL_MODELS:
        return "statistical_or_naive"
    return "non_mamba_learned"


def task_label(task: str) -> str:
    return task.removeprefix("financial_").replace("_", " ").upper()


def short_task_label(task: str) -> str:
    name = task.removeprefix("financial_")
    mode = "MS" if name.endswith("_ms") else "S"
    family = name.removesuffix("_ms").removesuffix("_s").replace("_", " ").title()
    return f"{family} {mode}"


def validate_source(frame: pd.DataFrame) -> None:
    required = {"dataset", "model", "horizon", *METRICS}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Frozen aggregate metrics are missing columns: {missing}")
    if frame.duplicated(["dataset", "model", "horizon"]).any():
        raise ValueError("Duplicate dataset/model/horizon rows in frozen aggregate metrics")
    if set(frame["dataset"]) != set(TASK_ORDER):
        raise ValueError("Unexpected task set in frozen aggregate metrics")
    if set(frame["horizon"]) != set(HORIZON_ORDER):
        raise ValueError("Unexpected horizon set in frozen aggregate metrics")
    if len(frame[frame["model"] == PMS_MODEL]) != 48:
        raise ValueError("Expected 48 PMS-Mamba task-horizon rows")
    values = frame[list(METRICS)].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("Primary path metrics must be finite and positive")


def validate_profile_source(frame: pd.DataFrame) -> None:
    required = {
        "dataset",
        "model",
        "seed",
        "horizon",
        "origin_count",
        "runtime_seconds",
        "peak_gpu_memory_mb",
    }
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Frozen profile data are missing columns: {missing}")
    if len(frame) != 2160:
        raise ValueError(f"Expected 2,160 learned-model profile rows, found {len(frame)}")
    if set(frame["dataset"]) != set(TASK_ORDER):
        raise ValueError("Unexpected task set in frozen profile data")
    if set(frame["model"]) != set(PROFILE_MODEL_ORDER):
        raise ValueError("Unexpected learned-model set in frozen profile data")
    if set(frame["horizon"]) != set(HORIZON_ORDER):
        raise ValueError("Unexpected horizon set in frozen profile data")
    if set(frame["seed"]) != {2023, 2024, 2025, 2026, 2027}:
        raise ValueError("Unexpected seed set in frozen profile data")
    if frame.duplicated(["dataset", "model", "seed", "horizon"]).any():
        raise ValueError("Duplicate task/model/seed/horizon rows in frozen profile data")
    counts = frame.groupby("model").size()
    if not (counts == 240).all():
        raise ValueError("Every learned model must have 240 frozen profile rows")
    values = frame[["origin_count", "runtime_seconds", "peak_gpu_memory_mb"]].to_numpy(
        dtype=float
    )
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("Profile counts, runtimes, and peak-memory values must be finite and positive")


def add_dimensions(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    output["term"] = output["horizon"].map(TERM_MAP)
    output["family"] = (
        output["dataset"].str.removeprefix("financial_").str.removesuffix("_ms").str.removesuffix("_s")
    )
    output["mode"] = np.where(output["dataset"].str.endswith("_ms"), "MS", "S")
    output["model_category"] = output["model"].map(model_category)
    return output


def build_all_model_cell_gaps(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for metric, metric_label in METRICS.items():
        for (dataset, horizon), group in frame.groupby(["dataset", "horizon"], sort=False):
            ordered = group.sort_values([metric, "model"]).reset_index(drop=True)
            winner = ordered.iloc[0]
            ranks = ordered[metric].rank(method="min")
            winner_value = float(winner[metric])
            for index, row in ordered.iterrows():
                value = float(row[metric])
                rank = int(ranks.iloc[index])
                rows.append(
                    {
                        "dataset": dataset,
                        "family": row["family"],
                        "mode": row["mode"],
                        "horizon": int(horizon),
                        "term": row["term"],
                        "model": row["model"],
                        "model_category": row["model_category"],
                        "metric": metric_label,
                        "metric_column": metric,
                        "value": value,
                        "winner_model": winner["model"],
                        "winner_value": winner_value,
                        "rank": rank,
                        "model_count": int(len(ordered)),
                        "gap_to_winner_pct": 100.0 * (value - winner_value) / winner_value,
                        "is_winner": rank == 1,
                        "is_top3": rank <= 3,
                    }
                )
    output = pd.DataFrame(rows)
    task_order = {task: index for index, task in enumerate(TASK_ORDER)}
    metric_order = {label: index for index, label in enumerate(METRICS.values())}
    output["_task"] = output["dataset"].map(task_order)
    output["_metric"] = output["metric"].map(metric_order)
    return (
        output.sort_values(["_metric", "_task", "horizon", "rank", "model"])
        .drop(columns=["_task", "_metric"])
        .reset_index(drop=True)
    )


def build_model_metric_summary(cell_gaps: pd.DataFrame) -> pd.DataFrame:
    summary = (
        cell_gaps.groupby(["metric", "metric_column", "model", "model_category"], as_index=False)
        .agg(
            cells=("dataset", "size"),
            wins=("is_winner", "sum"),
            top3=("is_top3", "sum"),
            average_rank=("rank", "mean"),
            median_rank=("rank", "median"),
            mean_gap_to_winner_pct=("gap_to_winner_pct", "mean"),
            median_gap_to_winner_pct=("gap_to_winner_pct", "median"),
            maximum_gap_to_winner_pct=("gap_to_winner_pct", "max"),
            within_5pct_of_winner=("gap_to_winner_pct", lambda values: int((values <= 5.0).sum())),
        )
    )
    metric_order = {label: index for index, label in enumerate(METRICS.values())}
    summary["_metric"] = summary["metric"].map(metric_order)
    return (
        summary.sort_values(["_metric", "average_rank", "median_gap_to_winner_pct", "model"])
        .drop(columns="_metric")
        .reset_index(drop=True)
    )


def build_term_model_metric_summary(cell_gaps: pd.DataFrame) -> pd.DataFrame:
    summary = (
        cell_gaps.groupby(
            ["metric", "metric_column", "term", "model", "model_category"],
            as_index=False,
        )
        .agg(
            cells=("dataset", "size"),
            wins=("is_winner", "sum"),
            top3=("is_top3", "sum"),
            average_rank=("rank", "mean"),
            median_rank=("rank", "median"),
            mean_gap_to_winner_pct=("gap_to_winner_pct", "mean"),
            median_gap_to_winner_pct=("gap_to_winner_pct", "median"),
            within_5pct_of_winner=("gap_to_winner_pct", lambda values: int((values <= 5.0).sum())),
        )
    )
    metric_order = {label: index for index, label in enumerate(METRICS.values())}
    term_order = {term: index for index, term in enumerate(TERM_ORDER)}
    summary["_metric"] = summary["metric"].map(metric_order)
    summary["_term"] = summary["term"].map(term_order)
    return (
        summary.sort_values(
            ["_metric", "_term", "average_rank", "median_gap_to_winner_pct", "model"]
        )
        .drop(columns=["_metric", "_term"])
        .reset_index(drop=True)
    )


def build_pms_term_task_summary(cell_gaps: pd.DataFrame) -> pd.DataFrame:
    pms = cell_gaps[cell_gaps["model"] == PMS_MODEL]

    def winner_list(values: pd.Series) -> str:
        return ";".join(sorted(set(values)))

    summary = (
        pms.groupby(["metric", "metric_column", "term", "dataset"], as_index=False)
        .agg(
            horizons=("horizon", lambda values: ";".join(str(value) for value in sorted(values))),
            horizon_cells=("horizon", "size"),
            pms_mean_value=("value", "mean"),
            mean_cell_winner_value=("winner_value", "mean"),
            winner_models=("winner_model", winner_list),
            average_rank=("rank", "mean"),
            best_rank=("rank", "min"),
            worst_rank=("rank", "max"),
            mean_gap_to_winner_pct=("gap_to_winner_pct", "mean"),
            median_gap_to_winner_pct=("gap_to_winner_pct", "median"),
            within_5pct_of_winner=("gap_to_winner_pct", lambda values: int((values <= 5.0).sum())),
        )
    )
    metric_order = {label: index for index, label in enumerate(METRICS.values())}
    term_order = {term: index for index, term in enumerate(TERM_ORDER)}
    task_order = {task: index for index, task in enumerate(TASK_ORDER)}
    summary["_metric"] = summary["metric"].map(metric_order)
    summary["_term"] = summary["term"].map(term_order)
    summary["_task"] = summary["dataset"].map(task_order)
    return (
        summary.sort_values(["_metric", "_term", "_task"])
        .drop(columns=["_metric", "_term", "_task"])
        .reset_index(drop=True)
    )


def build_pms_head_to_head(frame: pd.DataFrame) -> pd.DataFrame:
    pms = frame[frame["model"] == PMS_MODEL].set_index(["dataset", "horizon"])
    rows: list[dict[str, object]] = []
    for comparator in sorted(set(frame["model"]) - {PMS_MODEL}):
        other = frame[frame["model"] == comparator].set_index(["dataset", "horizon"])
        common = pms.join(other, lsuffix="_pms", rsuffix="_comparator", how="inner")
        for metric, label in METRICS.items():
            pms_values = common[f"{metric}_pms"].to_numpy(dtype=float)
            comparator_values = common[f"{metric}_comparator"].to_numpy(dtype=float)
            tied = np.isclose(pms_values, comparator_values, rtol=1e-12, atol=0.0)
            relative = 100.0 * (pms_values / comparator_values - 1.0)
            rows.append(
                {
                    "comparator": comparator,
                    "comparator_category": model_category(comparator),
                    "metric": label,
                    "metric_column": metric,
                    "common_cells": int(len(common)),
                    "pms_lower_cells": int(((pms_values < comparator_values) & ~tied).sum()),
                    "ties": int(tied.sum()),
                    "pms_higher_cells": int(((pms_values > comparator_values) & ~tied).sum()),
                    "mean_pms_vs_comparator_pct": float(relative.mean()),
                    "median_pms_vs_comparator_pct": float(np.median(relative)),
                }
            )
    return pd.DataFrame(rows).sort_values(["metric", "comparator"]).reset_index(drop=True)


def build_pms_rmse_advantage_by_term(frame: pd.DataFrame) -> pd.DataFrame:
    pms = frame[frame["model"] == PMS_MODEL][
        ["dataset", "horizon", "term", "path_rmse_mean"]
    ].rename(columns={"path_rmse_mean": "pms_rmse"})
    rows: list[dict[str, object]] = []
    for comparator in sorted(set(frame["model"]) - {PMS_MODEL}):
        other = frame[frame["model"] == comparator][
            ["dataset", "horizon", "path_rmse_mean"]
        ].rename(columns={"path_rmse_mean": "comparator_rmse"})
        common = pms.merge(other, on=["dataset", "horizon"], validate="one_to_one")
        scopes = [("Overall", common)] + [
            (term, common[common["term"] == term]) for term in TERM_ORDER
        ]
        for term, group in scopes:
            relative = 100.0 * (group["pms_rmse"] / group["comparator_rmse"] - 1.0)
            rows.append(
                {
                    "comparator": comparator,
                    "comparator_category": model_category(comparator),
                    "term": term,
                    "common_cells": int(len(group)),
                    "pms_lower_cells": int((relative < 0).sum()),
                    "pms_higher_cells": int((relative > 0).sum()),
                    "mean_pms_vs_comparator_pct": float(relative.mean()),
                    "median_pms_vs_comparator_pct": float(relative.median()),
                }
            )
    term_order = {term: index for index, term in enumerate(("Overall", *TERM_ORDER))}
    output = pd.DataFrame(rows)
    output["_term"] = output["term"].map(term_order)
    return output.sort_values(["comparator", "_term"]).drop(columns="_term").reset_index(drop=True)


def build_pms_rmse_advantage_by_task(frame: pd.DataFrame) -> pd.DataFrame:
    pms = frame[frame["model"] == PMS_MODEL][
        ["dataset", "horizon", "path_rmse_mean"]
    ].rename(columns={"path_rmse_mean": "pms_rmse"})
    rows: list[dict[str, object]] = []
    for comparator in sorted(set(frame["model"]) - {PMS_MODEL}):
        other = frame[frame["model"] == comparator][
            ["dataset", "horizon", "path_rmse_mean"]
        ].rename(columns={"path_rmse_mean": "comparator_rmse"})
        common = pms.merge(other, on=["dataset", "horizon"], validate="one_to_one")
        for dataset, group in common.groupby("dataset", sort=False):
            relative = 100.0 * (group["pms_rmse"] / group["comparator_rmse"] - 1.0)
            rows.append(
                {
                    "dataset": dataset,
                    "comparator": comparator,
                    "comparator_category": model_category(comparator),
                    "common_cells": int(len(group)),
                    "pms_lower_cells": int((relative < 0).sum()),
                    "pms_higher_cells": int((relative > 0).sum()),
                    "mean_pms_vs_comparator_pct": float(relative.mean()),
                    "median_pms_vs_comparator_pct": float(relative.median()),
                }
            )
    output = pd.DataFrame(rows)
    task_order = {task: index for index, task in enumerate(TASK_ORDER)}
    output["_task"] = output["dataset"].map(task_order)
    return output.sort_values(["comparator", "_task"]).drop(columns="_task").reset_index(drop=True)


def build_dataset_reference_summary() -> pd.DataFrame:
    quality = json.loads(QUALITY_SOURCE.read_text(encoding="utf-8"))
    diagnostics = pd.read_csv(DIAGNOSTIC_SOURCE).set_index("dataset")
    training = json.loads(TRAINING_SOURCE.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL_SOURCE.read_text(encoding="utf-8"))
    rows: list[dict[str, object]] = []
    for record in quality["datasets"]:
        dataset = record["dataset"]
        task = training[f"financial_{dataset}_s"]
        diagnostic = diagnostics.loc[dataset]
        specification = protocol["datasets"][dataset]
        rows.append(
            {
                "dataset": dataset,
                "label": specification["label"],
                "target": record["target"],
                "columns": ";".join(record["columns"]),
                "variable_count": len(record["columns"]),
                "start": record["start"],
                "end": record["end"],
                "rows": int(record["rows"]),
                "train_rows": int(record["split_counts"]["train"]),
                "validation_rows": int(record["split_counts"]["validation"]),
                "test_rows": int(record["split_counts"]["test"]),
                "missing_cells": int(record["missing_cells"]),
                "duplicate_dates": int(record["duplicate_dates"]),
                "maximum_calendar_gap_days": int(record["maximum_calendar_gap_days"]),
                "target_min": float(record["target_min"]),
                "target_max": float(record["target_max"]),
                "target_mean": float(record["target_mean"]),
                "target_std": float(record["target_std"]),
                "validation_mean_shift_train_sd": float(
                    diagnostic["validation_mean_shift_train_sd"]
                ),
                "test_mean_shift_train_sd": float(diagnostic["test_mean_shift_train_sd"]),
                "validation_difference_std_ratio": float(
                    diagnostic["validation_difference_std_ratio"]
                ),
                "test_difference_std_ratio": float(diagnostic["test_difference_std_ratio"]),
                "train_level_adf_p_value": float(diagnostic["train_level_adf_p_value"]),
                "train_level_kpss_p_value": float(diagnostic["train_level_kpss_p_value"]),
                "train_difference_adf_p_value": float(
                    diagnostic["train_difference_adf_p_value"]
                ),
                "train_difference_kpss_p_value": float(
                    diagnostic["train_difference_kpss_p_value"]
                ),
                "calendar": specification["calendar"],
                "redistribution": specification["redistribution"],
                "data_sha256": task["data_sha256"],
                "tasks": "S;MS",
                "horizons": ";".join(str(value) for value in task["horizons"]),
            }
        )
    order = {family: index for index, family in enumerate(FAMILY_ORDER)}
    output = pd.DataFrame(rows)
    output["_order"] = output["dataset"].map(order)
    return output.sort_values("_order").drop(columns="_order").reset_index(drop=True)


def build_task_model_metric_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for metric, label in METRICS.items():
        term_scores = (
            frame.groupby(["dataset", "model", "model_category", "term"], as_index=False)[metric]
            .mean()
        )
        balanced = (
            term_scores.groupby(["dataset", "model", "model_category"], as_index=False)[metric]
            .mean()
            .rename(columns={metric: "balanced_value"})
        )
        for dataset, group in balanced.groupby("dataset", sort=False):
            ordered = group.sort_values(["balanced_value", "model"]).reset_index(drop=True)
            winner = ordered.iloc[0]
            ranks = ordered["balanced_value"].rank(method="min")
            winner_value = float(winner["balanced_value"])
            for index, row in ordered.iterrows():
                value = float(row["balanced_value"])
                rows.append(
                    {
                        "dataset": dataset,
                        "model": row["model"],
                        "model_category": row["model_category"],
                        "metric": label,
                        "metric_column": metric,
                        "balanced_value": value,
                        "winner_model": winner["model"],
                        "winner_value": winner_value,
                        "rank": int(ranks.iloc[index]),
                        "model_count": int(len(ordered)),
                        "gap_to_winner_pct": 100.0 * (value - winner_value) / winner_value,
                    }
                )
    output = pd.DataFrame(rows)
    task_order = {task: index for index, task in enumerate(TASK_ORDER)}
    metric_order = {label: index for index, label in enumerate(METRICS.values())}
    output["_task"] = output["dataset"].map(task_order)
    output["_metric"] = output["metric"].map(metric_order)
    return (
        output.sort_values(["_metric", "_task", "rank", "model"])
        .drop(columns=["_task", "_metric"])
        .reset_index(drop=True)
    )


def summarize_profile_groups(
    frame: pd.DataFrame, group_columns: list[str]
) -> pd.DataFrame:
    return (
        frame.groupby(group_columns, as_index=False, sort=False)
        .agg(
            run_count=("runtime_seconds", "size"),
            total_origin_forecasts=("origin_count", "sum"),
            median_origin_count=("origin_count", "median"),
            total_runtime_seconds=("runtime_seconds", "sum"),
            mean_runtime_seconds=("runtime_seconds", "mean"),
            minimum_runtime_seconds=("runtime_seconds", "min"),
            runtime_q1_seconds=("runtime_seconds", lambda values: values.quantile(0.25)),
            median_runtime_seconds=("runtime_seconds", "median"),
            runtime_q3_seconds=("runtime_seconds", lambda values: values.quantile(0.75)),
            maximum_runtime_seconds=("runtime_seconds", "max"),
            mean_peak_gpu_memory_mb=("peak_gpu_memory_mb", "mean"),
            minimum_peak_gpu_memory_mb=("peak_gpu_memory_mb", "min"),
            peak_gpu_memory_q1_mb=(
                "peak_gpu_memory_mb",
                lambda values: values.quantile(0.25),
            ),
            median_peak_gpu_memory_mb=("peak_gpu_memory_mb", "median"),
            peak_gpu_memory_q3_mb=(
                "peak_gpu_memory_mb",
                lambda values: values.quantile(0.75),
            ),
            maximum_peak_gpu_memory_mb=("peak_gpu_memory_mb", "max"),
        )
    )


def build_computational_profile_model_summary(
    profile: pd.DataFrame, model_metric_summary: pd.DataFrame
) -> pd.DataFrame:
    summary = summarize_profile_groups(profile, ["model"])
    total_runtime = float(summary["total_runtime_seconds"].sum())
    summary["total_runtime_minutes"] = summary["total_runtime_seconds"] / 60.0
    summary["total_runtime_hours"] = summary["total_runtime_seconds"] / 3600.0
    summary["runtime_share_pct"] = 100.0 * summary["total_runtime_seconds"] / total_runtime

    stability = pd.read_csv(SEED_STABILITY_SOURCE)
    rmsse = model_metric_summary[
        (model_metric_summary["metric"] == "RMSSE")
        & (model_metric_summary["model"].isin(PROFILE_MODEL_ORDER))
    ][["model", "average_rank", "median_gap_to_winner_pct"]].rename(
        columns={
            "average_rank": "average_path_rmsse_rank",
            "median_gap_to_winner_pct": "median_path_rmsse_gap_to_winner_pct",
        }
    )
    summary = summary.merge(stability, on="model", validate="one_to_one")
    summary = summary.merge(rmsse, on="model", validate="one_to_one")

    frozen = pd.read_csv(RUNTIME_SUMMARY_SOURCE).set_index("model")
    check = summary.set_index("model")
    for column in (
        "total_runtime_seconds",
        "median_runtime_seconds",
        "maximum_runtime_seconds",
        "median_peak_gpu_memory_mb",
        "maximum_peak_gpu_memory_mb",
    ):
        if not np.allclose(check.loc[frozen.index, column], frozen[column], rtol=1e-12, atol=1e-12):
            raise ValueError(f"Derived profile column does not match frozen runtime summary: {column}")

    order = {model: index for index, model in enumerate(PROFILE_MODEL_ORDER)}
    summary["_order"] = summary["model"].map(order)
    return summary.sort_values("_order").drop(columns="_order").reset_index(drop=True)


def build_computational_profile_by_horizon(profile: pd.DataFrame) -> pd.DataFrame:
    summary = summarize_profile_groups(profile, ["model", "horizon"])
    model_order = {model: index for index, model in enumerate(PROFILE_MODEL_ORDER)}
    summary["_model"] = summary["model"].map(model_order)
    return (
        summary.sort_values(["_model", "horizon"])
        .drop(columns="_model")
        .reset_index(drop=True)
    )


def build_computational_profile_by_task(profile: pd.DataFrame) -> pd.DataFrame:
    summary = summarize_profile_groups(profile, ["dataset", "model"])
    summary["family"] = (
        summary["dataset"]
        .str.removeprefix("financial_")
        .str.removesuffix("_ms")
        .str.removesuffix("_s")
    )
    summary["mode"] = np.where(summary["dataset"].str.endswith("_ms"), "MS", "S")
    task_order = {task: index for index, task in enumerate(TASK_ORDER)}
    model_order = {model: index for index, model in enumerate(PROFILE_MODEL_ORDER)}
    summary["_task"] = summary["dataset"].map(task_order)
    summary["_model"] = summary["model"].map(model_order)
    return (
        summary.sort_values(["_task", "_model"])
        .drop(columns=["_task", "_model"])
        .reset_index(drop=True)
    )


def build_pms_efficiency_comparison(
    model_profile: pd.DataFrame, head_to_head: pd.DataFrame
) -> pd.DataFrame:
    indexed = model_profile.set_index("model")
    pms = indexed.loc[PMS_MODEL]
    rmse = head_to_head[head_to_head["metric"] == "RMSE"].set_index("comparator")
    rows: list[dict[str, object]] = []
    for comparator in PROFILE_MODEL_ORDER:
        if comparator == PMS_MODEL:
            continue
        other = indexed.loc[comparator]
        comparison = rmse.loc[comparator]
        rows.append(
            {
                "comparator": comparator,
                "pms_lower_rmse_cells": int(comparison["pms_lower_cells"]),
                "common_rmse_cells": int(comparison["common_cells"]),
                "median_pms_rmse_difference_pct": float(
                    comparison["median_pms_vs_comparator_pct"]
                ),
                "pms_to_comparator_median_runtime_ratio": float(
                    pms["median_runtime_seconds"] / other["median_runtime_seconds"]
                ),
                "pms_median_runtime_change_pct": float(
                    100.0
                    * (pms["median_runtime_seconds"] / other["median_runtime_seconds"] - 1.0)
                ),
                "pms_to_comparator_median_memory_ratio": float(
                    pms["median_peak_gpu_memory_mb"] / other["median_peak_gpu_memory_mb"]
                ),
                "pms_median_memory_change_pct": float(
                    100.0
                    * (
                        pms["median_peak_gpu_memory_mb"]
                        / other["median_peak_gpu_memory_mb"]
                        - 1.0
                    )
                ),
                "pms_to_comparator_maximum_memory_ratio": float(
                    pms["maximum_peak_gpu_memory_mb"] / other["maximum_peak_gpu_memory_mb"]
                ),
                "pms_maximum_memory_change_pct": float(
                    100.0
                    * (
                        pms["maximum_peak_gpu_memory_mb"]
                        / other["maximum_peak_gpu_memory_mb"]
                        - 1.0
                    )
                ),
                "pms_to_comparator_seed_cv_ratio": float(
                    pms["median_seed_cv"] / other["median_seed_cv"]
                ),
            }
        )
    return pd.DataFrame(rows)


def build_legacy_tables(
    task_model_summary: pd.DataFrame, cell_gaps: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    task_summary = task_model_summary[
        (task_model_summary["metric"] == "RMSSE") & (task_model_summary["model"] == PMS_MODEL)
    ].copy()
    task_summary["family"] = (
        task_summary["dataset"].str.removeprefix("financial_").str.removesuffix("_ms").str.removesuffix("_s")
    )
    task_summary["mode"] = np.where(task_summary["dataset"].str.endswith("_ms"), "MS", "S")
    task_summary = task_summary.rename(
        columns={
            "balanced_value": "pms_balanced_path_rmsse",
            "winner_model": "winner",
            "winner_value": "winner_balanced_path_rmsse",
            "rank": "pms_rank",
        }
    )[
        [
            "dataset",
            "family",
            "mode",
            "pms_balanced_path_rmsse",
            "winner",
            "winner_balanced_path_rmsse",
            "pms_rank",
            "model_count",
            "gap_to_winner_pct",
        ]
    ]

    pms_cells = cell_gaps[
        (cell_gaps["metric"] == "RMSSE") & (cell_gaps["model"] == PMS_MODEL)
    ]
    term_summary = (
        pms_cells.groupby("term")
        .agg(
            cells=("horizon", "size"),
            mean_gap_to_winner_pct=("gap_to_winner_pct", "mean"),
            median_gap_to_winner_pct=("gap_to_winner_pct", "median"),
            within_5pct_of_winner=("gap_to_winner_pct", lambda values: int((values <= 5.0).sum())),
            top3_cells=("rank", lambda values: int((values <= 3).sum())),
        )
        .reindex(TERM_ORDER)
        .reset_index()
    )
    return task_summary, term_summary


def save_figure(fig: plt.Figure, stem: str) -> tuple[Path, Path]:
    base = OUTPUT_ROOT / stem
    pdf_path = base.with_suffix(".pdf")
    png_path = base.with_suffix(".png")
    fig.savefig(
        pdf_path,
        facecolor="white",
        metadata={
            "Creator": "scripts/financial/generate_docs_figures.py",
            "CreationDate": None,
            "ModDate": None,
        },
    )
    fig.savefig(png_path, dpi=300, facecolor="white")
    plt.close(fig)
    with Image.open(png_path) as image:
        image.convert("RGB").save(png_path, dpi=(301, 301))
    return pdf_path, png_path


def make_performance_figure(
    task_summary: pd.DataFrame, term_summary: pd.DataFrame
) -> tuple[Path, Path]:
    colors = {"MS": "#0072B2", "S": "#D55E00"}
    markers = {"MS": "o", "S": "s"}
    term_colors = {"Short": "#D55E00", "Middle": "#009E73", "Long": "#0072B2"}
    with mpl.rc_context(STYLE):
        fig, (ax_a, ax_b) = plt.subplots(
            1,
            2,
            figsize=(180 / 25.4, 84 / 25.4),
            layout="constrained",
            gridspec_kw={"width_ratios": [1.35, 0.85]},
        )
        y = np.arange(len(task_summary))
        for mode in ("MS", "S"):
            subset = task_summary[task_summary["mode"] == mode]
            positions = [task_summary.index.get_loc(index) for index in subset.index]
            ax_a.scatter(
                subset["gap_to_winner_pct"],
                positions,
                color=colors[mode],
                marker=markers[mode],
                s=28,
                edgecolor="white",
                linewidth=0.4,
                label=mode,
                zorder=3,
            )
        ax_a.axvline(0, color="#333333", linestyle="--", linewidth=0.8)
        ax_a.set_yticks(y, [task_label(task) for task in task_summary["dataset"]])
        ax_a.invert_yaxis()
        ax_a.set_xlabel("PMS-Mamba gap to task winner (%)\nLower is better; zero is best")
        ax_a.grid(axis="x", color="#DDDDDD", linewidth=0.6)
        ax_a.legend(frameon=False, title="Input mode", loc="lower right")
        ax_a.text(-0.13, 1.03, "A", transform=ax_a.transAxes, fontweight="bold", fontsize=9)

        y_term = np.arange(len(term_summary))
        for index, row in term_summary.iterrows():
            ax_b.scatter(
                row["mean_gap_to_winner_pct"],
                index,
                color=term_colors[row["term"]],
                marker=("o", "s", "^")[index],
                s=34,
                edgecolor="white",
                linewidth=0.4,
                zorder=3,
            )
            ax_b.text(
                row["mean_gap_to_winner_pct"] + 0.5,
                index,
                f"within 5%: {int(row['within_5pct_of_winner'])}/{int(row['cells'])}",
                va="center",
                fontsize=6.8,
            )
        ax_b.axvline(0, color="#333333", linestyle="--", linewidth=0.8)
        ax_b.set_yticks(y_term, term_summary["term"])
        ax_b.invert_yaxis()
        ax_b.set_xlabel("Mean gap to cell winner (%)\nLower is better; zero is best")
        ax_b.grid(axis="x", color="#DDDDDD", linewidth=0.6)
        ax_b.text(-0.17, 1.03, "B", transform=ax_b.transAxes, fontweight="bold", fontsize=9)
        return save_figure(fig, "pms_mamba_performance_summary")


def make_model_position_figure(summary: pd.DataFrame) -> tuple[Path, Path]:
    display = summary[summary["metric_column"].isin(DISPLAY_METRICS)].copy()
    rmsse = display[display["metric"] == "RMSSE"].sort_values("average_rank")
    model_order = list(rmsse["model"])
    specifications = (
        ("MAE", "#0072B2", "o", -0.20),
        ("RMSE", "#D55E00", "s", 0.00),
        ("RMSSE", "#009E73", "^", 0.20),
    )
    with mpl.rc_context(STYLE):
        fig, (ax_rank, ax_gap) = plt.subplots(
            1,
            2,
            figsize=(180 / 25.4, 112 / 25.4),
            layout="constrained",
            sharey=True,
            gridspec_kw={"width_ratios": [0.95, 1.05]},
        )
        y = np.arange(len(model_order))
        pms_y = model_order.index(PMS_MODEL)
        for axis in (ax_rank, ax_gap):
            axis.axhspan(pms_y - 0.43, pms_y + 0.43, color="#EFEFEF", zorder=0)
            axis.grid(axis="x", color="#DDDDDD", linewidth=0.6, zorder=0)
        for metric, color, marker, offset in specifications:
            subset = display[display["metric"] == metric].set_index("model").loc[model_order]
            ax_rank.scatter(
                subset["average_rank"], y + offset, color=color, marker=marker,
                s=22, edgecolor="white", linewidth=0.35, label=metric, zorder=3,
            )
            ax_gap.scatter(
                subset["median_gap_to_winner_pct"], y + offset, color=color, marker=marker,
                s=22, edgecolor="white", linewidth=0.35, label=metric, zorder=3,
            )
        labels = [f"{model}*" if model == "VAR-difference" else model for model in model_order]
        ax_rank.set_yticks(y, labels)
        ax_rank.invert_yaxis()
        ax_rank.axvline(1, color="#333333", linestyle="--", linewidth=0.8)
        ax_rank.set_xlabel("Average task-horizon rank\nLower is better")
        ax_gap.axvline(0, color="#333333", linestyle="--", linewidth=0.8)
        ax_gap.set_xlabel("Median gap to cell winner (%)\nLower is better")
        ax_gap.legend(frameon=False, ncol=3, loc="lower right")
        ax_rank.text(-0.12, 1.02, "A", transform=ax_rank.transAxes, fontweight="bold", fontsize=9)
        ax_gap.text(-0.10, 1.02, "B", transform=ax_gap.transAxes, fontweight="bold", fontsize=9)
        return save_figure(fig, "all_model_metric_position")


def make_pms_cell_gap_figure(cell_gaps: pd.DataFrame) -> tuple[Path, Path]:
    pms = cell_gaps[
        (cell_gaps["model"] == PMS_MODEL) & cell_gaps["metric_column"].isin(DISPLAY_METRICS)
    ]
    maximum = math.ceil(pms["gap_to_winner_pct"].max() / 5.0) * 5.0
    norm = mpl.colors.Normalize(vmin=0, vmax=maximum)
    cmap = mpl.colormaps["YlOrRd"]
    with mpl.rc_context(STYLE):
        fig, axes = plt.subplots(
            1, 3, figsize=(180 / 25.4, 125 / 25.4), layout="constrained", sharey=True
        )
        image = None
        for panel, (axis, metric) in enumerate(zip(axes, DISPLAY_METRICS)):
            label = METRICS[metric]
            subset = pms[pms["metric_column"] == metric]
            gap = subset.pivot(index="dataset", columns="horizon", values="gap_to_winner_pct").loc[
                list(TASK_ORDER), list(HORIZON_ORDER)
            ]
            ranks = subset.pivot(index="dataset", columns="horizon", values="rank").loc[
                list(TASK_ORDER), list(HORIZON_ORDER)
            ]
            counts = subset.pivot(index="dataset", columns="horizon", values="model_count").loc[
                list(TASK_ORDER), list(HORIZON_ORDER)
            ]
            image = axis.imshow(gap, cmap=cmap, norm=norm, aspect="auto", interpolation="nearest")
            for row in range(len(TASK_ORDER)):
                for column in range(len(HORIZON_ORDER)):
                    value = float(gap.iloc[row, column])
                    color = "white" if norm(value) > 0.55 else "#222222"
                    axis.text(
                        column,
                        row,
                        f"{value:.1f}%\n{int(ranks.iloc[row, column])}/{int(counts.iloc[row, column])}",
                        ha="center",
                        va="center",
                        fontsize=5.2,
                        color=color,
                    )
            axis.set_title(label)
            axis.set_xticks(np.arange(len(HORIZON_ORDER)), HORIZON_ORDER)
            axis.set_xlabel("Forecast horizon")
            axis.text(-0.16, 1.02, chr(ord("A") + panel), transform=axis.transAxes, fontweight="bold", fontsize=9)
        axes[0].set_yticks(np.arange(len(TASK_ORDER)), [short_task_label(task) for task in TASK_ORDER])
        fig.colorbar(image, ax=axes, label="PMS-Mamba gap to cell winner (%)", shrink=0.82)
        return save_figure(fig, "pms_mamba_cell_metric_gaps")


def make_task_model_gap_figure(task_model: pd.DataFrame) -> tuple[Path, Path]:
    table = task_model[task_model["metric"] == "RMSSE"].copy()
    model_order = list(
        table.groupby("model")["rank"].mean().sort_values().index
    )
    gaps = table.pivot(index="dataset", columns="model", values="gap_to_winner_pct").loc[
        list(TASK_ORDER), model_order
    ]
    vmax = 60.0
    norm = mpl.colors.Normalize(vmin=0, vmax=vmax, clip=True)
    cmap = mpl.colormaps["YlGnBu"]
    with mpl.rc_context(STYLE):
        fig, axis = plt.subplots(figsize=(180 / 25.4, 94 / 25.4), layout="constrained")
        image = axis.imshow(gaps, cmap=cmap, norm=norm, aspect="auto", interpolation="nearest")
        for row in range(gaps.shape[0]):
            for column in range(gaps.shape[1]):
                if pd.isna(gaps.iloc[row, column]):
                    axis.text(column, row, "NA", ha="center", va="center", fontsize=5.2, color="#555555")
                    continue
                value = float(gaps.iloc[row, column])
                color = "white" if min(value, vmax) > 32 else "#222222"
                axis.text(column, row, f"{value:.0f}", ha="center", va="center", fontsize=5.2, color=color)
        pms_column = model_order.index(PMS_MODEL)
        axis.add_patch(
            Rectangle(
                (pms_column - 0.5, -0.5), 1, len(TASK_ORDER), fill=False,
                edgecolor="#D55E00", linewidth=1.5,
            )
        )
        axis.set_xticks(np.arange(len(model_order)), model_order, rotation=55, ha="right")
        axis.set_yticks(np.arange(len(TASK_ORDER)), [short_task_label(task) for task in TASK_ORDER])
        axis.set_xlabel("Model (PMS-Mamba column outlined)")
        fig.colorbar(
            image,
            ax=axis,
            label="Balanced path-RMSSE gap to task winner (%)\nColor capped at 60%; cell text is uncapped",
            extend="max",
        )
        return save_figure(fig, "task_model_balanced_rmsse_gaps")


def make_head_to_head_figure(head_to_head: pd.DataFrame) -> tuple[Path, Path]:
    table = head_to_head[head_to_head["metric_column"].isin(DISPLAY_METRICS)].copy()
    rmsse = table[table["metric"] == "RMSSE"].sort_values("median_pms_vs_comparator_pct")
    comparator_order = list(rmsse["comparator"])
    metric_order = [METRICS[metric] for metric in DISPLAY_METRICS]
    values = table.pivot(index="comparator", columns="metric", values="median_pms_vs_comparator_pct").loc[
        comparator_order, metric_order
    ]
    wins = table.pivot(index="comparator", columns="metric", values="pms_lower_cells").loc[
        comparator_order, metric_order
    ]
    cells = table.pivot(index="comparator", columns="metric", values="common_cells").loc[
        comparator_order, metric_order
    ]
    bound = math.ceil(np.nanmax(np.abs(values.to_numpy(dtype=float))) / 5.0) * 5.0
    norm = mpl.colors.TwoSlopeNorm(vmin=-bound, vcenter=0, vmax=bound)
    cmap = mpl.colormaps["RdYlGn_r"]
    with mpl.rc_context(STYLE):
        fig, axis = plt.subplots(figsize=(180 / 25.4, 118 / 25.4), layout="constrained")
        image = axis.imshow(values, cmap=cmap, norm=norm, aspect="auto", interpolation="nearest")
        for row in range(values.shape[0]):
            for column in range(values.shape[1]):
                value = float(values.iloc[row, column])
                color = "white" if abs(value) > 0.58 * bound else "#222222"
                axis.text(
                    column,
                    row,
                    f"{value:+.1f}%\n{int(wins.iloc[row, column])}/{int(cells.iloc[row, column])}",
                    ha="center",
                    va="center",
                    fontsize=6.0,
                    color=color,
                )
        axis.set_xticks(np.arange(len(metric_order)), metric_order)
        axis.set_yticks(np.arange(len(comparator_order)), comparator_order)
        axis.set_xlabel("Metric")
        fig.colorbar(image, ax=axis, label="Median PMS-Mamba relative difference (%)")
        return save_figure(fig, "pms_mamba_head_to_head")


def make_term_model_figure(
    term_summary: pd.DataFrame, term: str
) -> tuple[Path, Path]:
    table = term_summary[
        (term_summary["metric"] == "RMSSE") & (term_summary["term"] == term)
    ].sort_values(["average_rank", "median_gap_to_winner_pct", "model"])
    model_order = list(table["model"])
    y = np.arange(len(table))
    category_styles = {
        "statistical_or_naive": ("#4D4D4D", "o", "Statistical/naive"),
        "non_mamba_learned": ("#0072B2", "s", "Non-Mamba learned"),
        "mamba": ("#009E73", "^", "Mamba"),
    }
    horizon_text = {
        "Short": "horizons 1 and 5",
        "Middle": "horizons 20 and 60",
        "Long": "horizons 120 and 252",
    }[term]
    stem = f"{term.lower()}_term_model_rmsse_comparison"
    with mpl.rc_context(STYLE):
        fig, (axis, table_axis) = plt.subplots(
            1,
            2,
            figsize=(180 / 25.4, 106 / 25.4),
            layout="constrained",
            sharey=True,
            gridspec_kw={"width_ratios": [1.22, 0.78], "wspace": 0.03},
        )
        pms_y = model_order.index(PMS_MODEL)
        for target in (axis, table_axis):
            target.axhspan(pms_y - 0.43, pms_y + 0.43, color="#EFEFEF", zorder=0)
        for category, (color, marker, label) in category_styles.items():
            subset = table[(table["model_category"] == category) & (table["model"] != PMS_MODEL)]
            positions = [model_order.index(model) for model in subset["model"]]
            axis.scatter(
                subset["average_rank"], positions, color=color, marker=marker,
                s=27, edgecolor="white", linewidth=0.4, label=label, zorder=3,
            )
        pms = table[table["model"] == PMS_MODEL].iloc[0]
        axis.scatter(
            [pms["average_rank"]], [pms_y], color="#D55E00", marker="D",
            s=36, edgecolor="white", linewidth=0.5, label="PMS-Mamba", zorder=4,
        )
        labels = [f"{model}*" if model == "VAR-difference" else model for model in model_order]
        axis.set_yticks(y, labels)
        axis.invert_yaxis()
        axis.set_xlim(0.5, 13.5)
        axis.set_xticks([1, 3, 5, 7, 9, 11, 13])
        axis.set_xlabel("Average task-horizon RMSSE rank\nLower is better")
        axis.axvline(1, color="#333333", linestyle="--", linewidth=0.8)
        axis.grid(axis="x", color="#DDDDDD", linewidth=0.6)
        axis.legend(frameon=False, ncol=2, loc="upper right", fontsize=6.2)
        axis.set_title(f"{term}-term comparison: {horizon_text}", loc="left", fontweight="bold")

        table_axis.set_xlim(0, 1)
        table_axis.tick_params(left=False, labelleft=False, bottom=False, labelbottom=False)
        for spine in table_axis.spines.values():
            spine.set_visible(False)
        headers = ((0.04, "Median gap"), (0.49, "Wins"), (0.75, "Top 3"))
        for x_value, header in headers:
            table_axis.text(
                x_value, 1.015, header, transform=table_axis.transAxes,
                fontsize=6.6, fontweight="bold", va="bottom",
            )
        transform = table_axis.get_yaxis_transform()
        for position, (_, row) in enumerate(table.iterrows()):
            table_axis.text(
                0.04, position, f"{row['median_gap_to_winner_pct']:.2f}%",
                transform=transform, va="center", fontsize=6.7,
            )
            table_axis.text(
                0.49, position, f"{int(row['wins'])}/{int(row['cells'])}",
                transform=transform, va="center", fontsize=6.7,
            )
            table_axis.text(
                0.75, position, f"{int(row['top3'])}/{int(row['cells'])}",
                transform=transform, va="center", fontsize=6.7,
            )
        return save_figure(fig, stem)


def make_pms_term_task_figure(pms_term_task: pd.DataFrame) -> tuple[Path, Path]:
    table = pms_term_task[pms_term_task["metric"] == "RMSSE"]
    gaps = table.pivot(index="dataset", columns="term", values="mean_gap_to_winner_pct").loc[
        list(TASK_ORDER), list(TERM_ORDER)
    ]
    ranks = table.pivot(index="dataset", columns="term", values="average_rank").loc[
        list(TASK_ORDER), list(TERM_ORDER)
    ]
    within = table.pivot(index="dataset", columns="term", values="within_5pct_of_winner").loc[
        list(TASK_ORDER), list(TERM_ORDER)
    ]
    maximum = math.ceil(gaps.to_numpy(dtype=float).max() / 5.0) * 5.0
    norm = mpl.colors.Normalize(vmin=0, vmax=maximum)
    cmap = mpl.colormaps["YlOrRd"]
    with mpl.rc_context(STYLE):
        fig, axis = plt.subplots(figsize=(150 / 25.4, 102 / 25.4), layout="constrained")
        image = axis.imshow(gaps, cmap=cmap, norm=norm, aspect="auto", interpolation="nearest")
        for row in range(gaps.shape[0]):
            for column in range(gaps.shape[1]):
                value = float(gaps.iloc[row, column])
                color = "white" if norm(value) > 0.58 else "#222222"
                axis.text(
                    column,
                    row,
                    f"{value:.1f}%\nr {ranks.iloc[row, column]:.1f}\n<=5% {int(within.iloc[row, column])}/2",
                    ha="center",
                    va="center",
                    fontsize=5.8,
                    color=color,
                )
        axis.set_xticks(np.arange(len(TERM_ORDER)), ["Short\n1, 5", "Middle\n20, 60", "Long\n120, 252"])
        axis.set_yticks(np.arange(len(TASK_ORDER)), [short_task_label(task) for task in TASK_ORDER])
        axis.set_xlabel("Forecast term and horizons")
        fig.colorbar(image, ax=axis, label="Mean PMS-Mamba gap to cell winner (%)")
        return save_figure(fig, "pms_mamba_term_task_rmsse")


def make_pms_rmse_advantage_by_term_figure(
    advantage: pd.DataFrame,
) -> tuple[Path, Path]:
    term_order = ["Overall", *TERM_ORDER]
    overall = advantage[advantage["term"] == "Overall"].sort_values(
        "median_pms_vs_comparator_pct"
    )
    comparator_order = list(overall["comparator"])
    values = advantage.pivot(
        index="comparator", columns="term", values="median_pms_vs_comparator_pct"
    ).loc[comparator_order, term_order]
    wins = advantage.pivot(
        index="comparator", columns="term", values="pms_lower_cells"
    ).loc[comparator_order, term_order]
    cells = advantage.pivot(
        index="comparator", columns="term", values="common_cells"
    ).loc[comparator_order, term_order]
    bound = math.ceil(np.nanmax(np.abs(values.to_numpy(dtype=float))) / 5.0) * 5.0
    norm = mpl.colors.TwoSlopeNorm(vmin=-bound, vcenter=0, vmax=bound)
    cmap = mpl.colormaps["RdYlGn_r"]
    with mpl.rc_context(STYLE):
        fig, axis = plt.subplots(figsize=(180 / 25.4, 122 / 25.4), layout="constrained")
        image = axis.imshow(values, cmap=cmap, norm=norm, aspect="auto", interpolation="nearest")
        for row in range(values.shape[0]):
            for column in range(values.shape[1]):
                value = float(values.iloc[row, column])
                color = "white" if abs(value) > 0.58 * bound else "#222222"
                axis.text(
                    column,
                    row,
                    f"{value:+.1f}%\n{int(wins.iloc[row, column])}/{int(cells.iloc[row, column])}",
                    ha="center",
                    va="center",
                    fontsize=5.8,
                    color=color,
                )
        axis.set_xticks(
            np.arange(len(term_order)),
            ["Overall", "Short\n1, 5", "Middle\n20, 60", "Long\n120, 252"],
        )
        axis.set_yticks(np.arange(len(comparator_order)), comparator_order)
        axis.set_xlabel("Scope; cell text is median difference and PMS wins/common cells")
        fig.colorbar(
            image,
            ax=axis,
            label="Median PMS-Mamba RMSE difference (%)\nNegative favors PMS-Mamba",
        )
        return save_figure(fig, "pms_mamba_rmse_advantage_by_term")


def make_dataset_reference_figure(dataset_summary: pd.DataFrame) -> tuple[Path, Path]:
    labels = [value.replace("_", " ").title() for value in dataset_summary["dataset"]]
    y = np.arange(len(dataset_summary))
    split_colors = ("#0072B2", "#E69F00", "#009E73")
    with mpl.rc_context(STYLE):
        fig, (ax_counts, ax_shift, ax_scale) = plt.subplots(
            1,
            3,
            figsize=(180 / 25.4, 91 / 25.4),
            layout="constrained",
            sharey=True,
            gridspec_kw={"width_ratios": [1.25, 1.0, 1.0]},
        )
        left = np.zeros(len(dataset_summary), dtype=float)
        for column, color, label in zip(
            ("train_rows", "validation_rows", "test_rows"),
            split_colors,
            ("Train", "Validation", "Test"),
        ):
            values = dataset_summary[column].to_numpy(dtype=float)
            ax_counts.barh(y, values, left=left, color=color, label=label, height=0.62)
            left += values
        for row, total in enumerate(dataset_summary["rows"]):
            ax_counts.text(float(total) + 80, row, f"n={int(total):,}", va="center", fontsize=6.2)
        ax_counts.set_yticks(y, labels)
        ax_counts.invert_yaxis()
        ax_counts.set_xlabel("Retained observations")
        ax_counts.set_title("A  Dataset size and frozen splits", loc="left", fontweight="bold")
        ax_counts.legend(frameon=False, ncol=3, loc="lower right", fontsize=6.2)
        ax_counts.grid(axis="x", color="#DDDDDD", linewidth=0.6)

        for column, color, marker, label in (
            ("validation_mean_shift_train_sd", "#E69F00", "o", "Validation"),
            ("test_mean_shift_train_sd", "#009E73", "s", "Test"),
        ):
            ax_shift.scatter(
                dataset_summary[column], y, color=color, marker=marker, s=28,
                edgecolor="white", linewidth=0.4, label=label, zorder=3,
            )
        ax_shift.axvline(0, color="#333333", linestyle="--", linewidth=0.8)
        ax_shift.set_xlabel("Target mean shift\n(training SD units)")
        ax_shift.set_title("B  Level shift", loc="left", fontweight="bold")
        ax_shift.grid(axis="x", color="#DDDDDD", linewidth=0.6)
        ax_shift.legend(frameon=False, fontsize=6.4, loc="lower right")
        ax_shift.tick_params(left=False, labelleft=False)

        for column, color, marker, label in (
            ("validation_difference_std_ratio", "#E69F00", "o", "Validation"),
            ("test_difference_std_ratio", "#009E73", "s", "Test"),
        ):
            ax_scale.scatter(
                dataset_summary[column], y, color=color, marker=marker, s=28,
                edgecolor="white", linewidth=0.4, label=label, zorder=3,
            )
        ax_scale.axvline(1, color="#333333", linestyle="--", linewidth=0.8)
        ax_scale.set_xlabel("First-difference SD ratio\n(relative to training)")
        ax_scale.set_title("C  Volatility shift", loc="left", fontweight="bold")
        ax_scale.grid(axis="x", color="#DDDDDD", linewidth=0.6)
        ax_scale.tick_params(left=False, labelleft=False)
        return save_figure(fig, "dataset_reference_overview")


def make_family_metric_horizon_figure(
    frame: pd.DataFrame, family: str
) -> tuple[Path, Path]:
    colors = mpl.colormaps["tab20"](np.linspace(0.0, 0.95, len(MODEL_ORDER)))
    markers = ("o", "s", "^", "v", "D", "P", "X", "*", "<", ">", "h", "p", "d")
    style_by_model = {
        model: {
            "color": color,
            "marker": marker,
            "linestyle": (
                ":" if model in STATISTICAL_MODELS else "--" if model in MAMBA_MODELS else "-"
            ),
            "linewidth": 2.2 if model == PMS_MODEL else 1.0,
            "markersize": 4.8 if model == PMS_MODEL else 3.2,
            "zorder": 5 if model == PMS_MODEL else 2,
        }
        for model, color, marker in zip(MODEL_ORDER, colors, markers)
    }
    style_by_model[PMS_MODEL]["color"] = "#D55E00"
    positions = np.arange(len(HORIZON_ORDER))
    with mpl.rc_context(STYLE):
        fig, axes = plt.subplots(
            len(HORIZON_METRICS),
            2,
            figsize=(180 / 25.4, 215 / 25.4),
            layout="constrained",
            sharex=True,
        )
        legend_handles: dict[str, mpl.lines.Line2D] = {}
        for column, mode in enumerate(("MS", "S")):
            dataset = f"financial_{family}_{mode.lower()}"
            task = frame[frame["dataset"] == dataset]
            for row, (metric, label, unit) in enumerate(HORIZON_METRICS):
                axis = axes[row, column]
                for model in MODEL_ORDER:
                    model_rows = task[task["model"] == model].sort_values("horizon")
                    if model_rows.empty:
                        continue
                    line = axis.plot(
                        positions,
                        model_rows[metric],
                        label=model,
                        **style_by_model[model],
                    )[0]
                    legend_handles.setdefault(model, line)
                axis.set_yscale("log")
                axis.grid(which="major", color="#DDDDDD", linewidth=0.55)
                axis.grid(which="minor", color="#EEEEEE", linewidth=0.35)
                axis.set_ylabel(f"{label}\n{unit}" if column == 0 else "")
                axis.text(
                    0.98,
                    0.93,
                    "log y-axis",
                    transform=axis.transAxes,
                    ha="right",
                    va="top",
                    fontsize=5.8,
                    color="#555555",
                )
                if row == 0:
                    input_text = "all variables" if mode == "MS" else "target only"
                    axis.set_title(f"{mode}: {input_text} -> target", fontweight="bold")
                if row == len(HORIZON_METRICS) - 1:
                    axis.set_xticks(positions, [str(value) for value in HORIZON_ORDER])
                    axis.set_xlabel("Forecast horizon (retained observations)")
        handles = [legend_handles[model] for model in MODEL_ORDER if model in legend_handles]
        labels = [model for model in MODEL_ORDER if model in legend_handles]
        fig.legend(
            handles,
            labels,
            loc="outside lower center",
            ncol=4,
            frameon=False,
            fontsize=6.2,
        )
        family_label = family.replace("_", " ").title()
        fig.suptitle(
            f"{family_label}: all-model path metrics by forecast horizon",
            fontsize=10,
            fontweight="bold",
        )
        return save_figure(fig, f"{family}_all_models_metrics_by_horizon")


def profile_model_style(model: str) -> dict[str, object]:
    styles = {
        "NLinear": ("#0072B2", "o"),
        "DLinear": ("#56B4E9", "s"),
        "PatchTST": ("#009E73", "^"),
        "iTransformer": ("#CC79A7", "v"),
        "S_Mamba": ("#111111", ">"),
        "NS_Mamba-D": ("#117A65", "<"),
        "MS_Mamba-MD": ("#777777", "P"),
        PMS_MODEL: ("#D55E00", "D"),
        "TimesNet": ("#6A51A3", "X"),
    }
    color, marker = styles[model]
    return {
        "color": color,
        "marker": marker,
        "linestyle": "--" if model in MAMBA_MODELS else "-",
        "linewidth": 2.2 if model == PMS_MODEL else 1.1,
    }


def make_computational_profile_overview(
    model_profile: pd.DataFrame,
) -> tuple[Path, Path]:
    table = model_profile.set_index("model").loc[list(PROFILE_MODEL_ORDER)].reset_index()
    y = np.arange(len(table))
    colors = [profile_model_style(model)["color"] for model in table["model"]]
    with mpl.rc_context(STYLE):
        fig, (runtime_axis, memory_axis) = plt.subplots(
            1,
            2,
            figsize=(180 / 25.4, 108 / 25.4),
            layout="constrained",
            sharey=True,
        )
        for axis, median, q1, q3, maximum, xlabel, title in (
            (
                runtime_axis,
                "median_runtime_seconds",
                "runtime_q1_seconds",
                "runtime_q3_seconds",
                "maximum_runtime_seconds",
                "Seconds per train/evaluation run (log scale)",
                "A  Runtime distribution",
            ),
            (
                memory_axis,
                "median_peak_gpu_memory_mb",
                "peak_gpu_memory_q1_mb",
                "peak_gpu_memory_q3_mb",
                "maximum_peak_gpu_memory_mb",
                "Peak allocated GPU memory, MB (log scale)",
                "B  Peak-memory distribution",
            ),
        ):
            values = table[median].to_numpy(dtype=float)
            lower = values - table[q1].to_numpy(dtype=float)
            upper = table[q3].to_numpy(dtype=float) - values
            for row, color in enumerate(colors):
                axis.errorbar(
                    values[row],
                    row,
                    xerr=np.asarray([[lower[row]], [upper[row]]]),
                    fmt="D" if table.loc[row, "model"] == PMS_MODEL else "o",
                    color=color,
                    ecolor=color,
                    capsize=2.2,
                    markersize=4.5,
                    linewidth=1.2,
                    zorder=3,
                )
                axis.scatter(
                    table.loc[row, maximum],
                    row,
                    marker="x",
                    color=color,
                    s=22,
                    linewidth=1.0,
                    zorder=4,
                )
            axis.set_xscale("log")
            axis.grid(which="major", axis="x", color="#D8D8D8", linewidth=0.6)
            axis.grid(which="minor", axis="x", color="#EEEEEE", linewidth=0.35)
            axis.set_xlabel(xlabel)
            axis.set_title(title, loc="left", fontweight="bold")
        runtime_axis.set_yticks(y, table["model"])
        runtime_axis.invert_yaxis()
        memory_axis.tick_params(left=False, labelleft=False)
        fig.suptitle(
            "Learned-model computational profile",
            fontsize=10,
            fontweight="bold",
        )
        return save_figure(fig, "computational_profile_overview")


def make_computational_profile_by_horizon_figure(
    horizon_profile: pd.DataFrame,
) -> tuple[Path, Path]:
    positions = np.arange(len(HORIZON_ORDER))
    with mpl.rc_context(STYLE):
        fig, (runtime_axis, memory_axis) = plt.subplots(
            1,
            2,
            figsize=(180 / 25.4, 103 / 25.4),
            layout="constrained",
        )
        handles: list[mpl.lines.Line2D] = []
        labels: list[str] = []
        for model in PROFILE_MODEL_ORDER:
            rows = horizon_profile[horizon_profile["model"] == model].sort_values("horizon")
            style = profile_model_style(model)
            runtime_line = runtime_axis.plot(
                positions,
                rows["median_runtime_seconds"],
                markersize=4.8 if model == PMS_MODEL else 3.2,
                label=model,
                **style,
            )[0]
            memory_axis.plot(
                positions,
                rows["median_peak_gpu_memory_mb"],
                markersize=4.8 if model == PMS_MODEL else 3.2,
                **style,
            )
            handles.append(runtime_line)
            labels.append(model)
        for axis, ylabel, title in (
            (runtime_axis, "Median runtime (seconds, log scale)", "A  Runtime by horizon"),
            (memory_axis, "Median peak GPU memory (MB, log scale)", "B  Memory by horizon"),
        ):
            axis.set_yscale("log")
            axis.set_xticks(positions, [str(value) for value in HORIZON_ORDER])
            axis.set_xlabel("Forecast horizon (retained observations)")
            axis.set_ylabel(ylabel)
            axis.set_title(title, loc="left", fontweight="bold")
            axis.grid(which="major", color="#D8D8D8", linewidth=0.6)
            axis.grid(which="minor", color="#EEEEEE", linewidth=0.35)
        fig.legend(
            handles,
            labels,
            loc="outside lower center",
            ncol=3,
            frameon=False,
            fontsize=6.2,
        )
        fig.suptitle(
            "Computational profile across forecast horizons",
            fontsize=10,
            fontweight="bold",
        )
        return save_figure(fig, "computational_profile_by_horizon")


def make_computational_profile_by_task_figure(
    task_profile: pd.DataFrame,
) -> tuple[Path, Path]:
    task_labels = [short_task_label(task) for task in TASK_ORDER]
    runtime = (
        task_profile.pivot(index="model", columns="dataset", values="median_runtime_seconds")
        .reindex(index=PROFILE_MODEL_ORDER, columns=TASK_ORDER)
    )
    memory = (
        task_profile.pivot(
            index="model", columns="dataset", values="median_peak_gpu_memory_mb"
        )
        .reindex(index=PROFILE_MODEL_ORDER, columns=TASK_ORDER)
    )
    with mpl.rc_context(STYLE):
        fig, axes = plt.subplots(
            2,
            1,
            figsize=(180 / 25.4, 150 / 25.4),
            layout="constrained",
        )
        for axis, values, title, label, formatter in (
            (
                axes[0],
                runtime,
                "A  Median train/evaluation runtime by task",
                "Seconds (log color scale)",
                lambda value: f"{value:.2f}" if value < 10 else f"{value:.1f}",
            ),
            (
                axes[1],
                memory,
                "B  Median peak allocated GPU memory by task",
                "MB (log color scale)",
                lambda value: f"{value:.0f}",
            ),
        ):
            numeric = values.to_numpy(dtype=float)
            image = axis.imshow(
                numeric,
                norm=mpl.colors.LogNorm(vmin=float(numeric.min()), vmax=float(numeric.max())),
                cmap="viridis",
                aspect="auto",
                interpolation="nearest",
            )
            midpoint = math.sqrt(float(numeric.min()) * float(numeric.max()))
            for row in range(numeric.shape[0]):
                for column in range(numeric.shape[1]):
                    color = "white" if numeric[row, column] < midpoint else "#111111"
                    axis.text(
                        column,
                        row,
                        formatter(numeric[row, column]),
                        ha="center",
                        va="center",
                        fontsize=5.5,
                        color=color,
                    )
            pms_row = list(PROFILE_MODEL_ORDER).index(PMS_MODEL)
            axis.add_patch(
                Rectangle(
                    (-0.49, pms_row - 0.49),
                    len(TASK_ORDER) - 0.02,
                    0.98,
                    fill=False,
                    edgecolor="#D55E00",
                    linewidth=1.8,
                )
            )
            axis.set_yticks(np.arange(len(PROFILE_MODEL_ORDER)), PROFILE_MODEL_ORDER)
            axis.set_xticks(np.arange(len(TASK_ORDER)), task_labels, rotation=35, ha="right")
            axis.set_title(title, loc="left", fontweight="bold")
            fig.colorbar(image, ax=axis, label=label, pad=0.015)
        fig.suptitle(
            "Complete task-level computational profile",
            fontsize=10,
            fontweight="bold",
        )
        return save_figure(fig, "computational_profile_by_task")


def write_manifest(paths: list[Path]) -> Path:
    manifest = {
        "release_id": "DOC-FIG-MODEL-COMPARISON-004",
        "status": "provisional general scientific figures; target journal not specified",
        "source": str(SOURCE.relative_to(REPO_ROOT)),
        "source_sha256": sha256_path(SOURCE),
        "sources": {
            str(path.relative_to(REPO_ROOT)): sha256_path(path)
            for path in (
                SOURCE,
                QUALITY_SOURCE,
                DIAGNOSTIC_SOURCE,
                TRAINING_SOURCE,
                PROTOCOL_SOURCE,
                PROFILE_SOURCE,
                RUNTIME_SUMMARY_SOURCE,
                RUNTIME_ENVIRONMENT_SOURCE,
                SEED_STABILITY_SOURCE,
            )
        },
        "analysis_population": (
            "600 frozen V1 model-task-horizon rows and 4,800 metric comparisons: "
            "13 models, eight S/MS tasks, six horizons, four path and four terminal metrics; "
            "VAR-difference covers only 24 multivariate cells. Computational profiles use "
            "2,160 learned-model task-horizon-seed runs: 240 per model"
        ),
        "metrics": {
            "MAE": "path mean absolute error in original target units",
            "MSE": "path mean squared error in squared target units",
            "RMSE": "path root mean squared error in original target units",
            "RMSSE": "path RMSE divided by the task's training naive-difference scale",
            "Terminal MAE": "absolute error at the final forecast endpoint",
            "Terminal MSE": "squared error at the final forecast endpoint",
            "Terminal RMSE": "root squared error at the final forecast endpoint",
            "Terminal RMSSE": "terminal RMSE divided by the task's training naive-difference scale",
        },
        "transformations": [
            "within-cell rank uses lower-is-better metric values with minimum rank for ties",
            "gap percent is 100 * (model metric / cell winner metric - 1)",
            "task-balanced metrics average short-, middle-, and long-term means with equal term weight",
            "head-to-head percent is 100 * (PMS metric / comparator metric - 1)",
            "term head-to-head summaries use path RMSE and preserve the frozen short, middle, and long horizon groups",
            "dataset shifts express validation or test target means in training target SD units",
            "dataset volatility shifts divide validation or test first-difference SD by training first-difference SD",
            "all-model horizon figures use equally spaced frozen horizon categories and logarithmic y-axes for positive error metrics",
            "task-model RMSSE heatmap clips color at 60% but prints the rounded unclipped value in each cell",
            "profile summaries report observed runtime and CUDA maximum allocated memory without workload normalization",
            "profile IQR is the 25th to 75th percentile across completed runs",
            "model summaries pool 240 runs; horizon summaries pool 40 runs per model-horizon; task summaries pool 30 runs per model-task",
            "profile figures use logarithmic axes or color normalization and print untransformed runtime or memory values",
        ],
        "missing_data": "none in primary metrics; VAR-difference is structurally unavailable for S tasks",
        "uncertainty": (
            "accuracy figures report descriptive five-seed means from the frozen aggregate table; "
            "profile figures report empirical run distributions without confidence intervals; "
            "confirmatory bootstrap contrasts remain in the V1 release"
        ),
        "profile_scope": (
            "runtime starts before experiment construction and ends after training and final evaluation; "
            "peak memory is torch.cuda.max_memory_allocated after resetting CUDA peak statistics. "
            "Configurations are independently validation-selected, and these are not matched-size "
            "inference-latency, throughput, FLOP, energy, or kernel-level measurements"
        ),
        "exports": "PDF at native physical dimensions and RGB PNG with at least 300 dpi metadata",
        "human_review_required": True,
        "figures": {
            "DOC-FIG-PMS-001": {
                "stem": "pms_mamba_performance_summary",
                "size_mm": [180, 84],
                "alt_text": (
                    "Two-panel dot plot showing that PMS-Mamba is closest to task winners on crypto "
                    "and cross-asset tasks and closest to cell winners at middle horizons."
                ),
            },
            "DOC-FIG-MODEL-002": {
                "stem": "all_model_metric_position",
                "size_mm": [180, 112],
                "alt_text": (
                    "Two-panel dot plot of average rank and median gap to winner for every model. "
                    "PMS-Mamba sits behind persistence, ARIMA, NLinear, NS-Mamba, and S-Mamba by average rank."
                ),
            },
            "DOC-FIG-PMS-003": {
                "stem": "pms_mamba_cell_metric_gaps",
                "size_mm": [180, 125],
                "alt_text": (
                    "Three heatmaps showing PMS-Mamba MAE, RMSE, and RMSSE gaps and ranks for every "
                    "task and horizon; middle horizons are generally closest to the winner."
                ),
            },
            "DOC-FIG-TASK-004": {
                "stem": "task_model_balanced_rmsse_gaps",
                "size_mm": [180, 94],
                "alt_text": (
                    "Heatmap of every model's balanced RMSSE gap in each task. Persistence and ARIMA "
                    "lead most tasks, while PatchTST leads both cross-asset tasks."
                ),
            },
            "DOC-FIG-PMS-005": {
                "stem": "pms_mamba_head_to_head",
                "size_mm": [180, 118],
                "alt_text": (
                    "Heatmap of median PMS-Mamba differences and cell wins against every comparator. "
                    "PMS-Mamba usually beats PatchTST, DLinear, TimesNet, and iTransformer but rarely "
                    "beats persistence or random-walk drift."
                ),
            },
            "DOC-FIG-TERM-006": {
                "stem": "short_term_model_rmsse_comparison",
                "size_mm": [180, 106],
                "alt_text": (
                    "Short-term all-model comparison showing PMS-Mamba near the lower half of the "
                    "ranking, behind persistence, ARIMA, NLinear, S-Mamba, and NS-Mamba."
                ),
            },
            "DOC-FIG-TERM-007": {
                "stem": "middle_term_model_rmsse_comparison",
                "size_mm": [180, 106],
                "alt_text": (
                    "Middle-term all-model comparison showing PMS-Mamba close to NS-Mamba and "
                    "NLinear, with 14 of 16 cells within five percent of the winner."
                ),
            },
            "DOC-FIG-TERM-008": {
                "stem": "long_term_model_rmsse_comparison",
                "size_mm": [180, 106],
                "alt_text": (
                    "Long-term all-model comparison showing PMS-Mamba fifth among full-coverage "
                    "models by average rank but with a 12.82 percent median gap to the winner."
                ),
            },
            "DOC-FIG-TERM-009": {
                "stem": "pms_mamba_term_task_rmsse",
                "size_mm": [150, 102],
                "alt_text": (
                    "Heatmap of PMS-Mamba short-, middle-, and long-term RMSSE gaps by task. "
                    "Middle-term gaps are smallest; long-term crypto remains close while "
                    "cross-asset and FX have large long-term gaps."
                ),
            },
            "DOC-FIG-PMS-010": {
                "stem": "pms_mamba_rmse_advantage_by_term",
                "size_mm": [180, 122],
                "alt_text": (
                    "Heatmap of signed median PMS-Mamba RMSE differences versus every comparator, "
                    "overall and at short, middle, and long horizons. PMS-Mamba is consistently "
                    "better than four deep baselines but remains behind persistence references."
                ),
            },
            "DOC-FIG-DATA-011": {
                "stem": "dataset_reference_overview",
                "size_mm": [180, 91],
                "alt_text": (
                    "Three-panel overview of retained observations and frozen splits, target mean "
                    "shift in training standard-deviation units, and first-difference volatility "
                    "ratios for the four current reference datasets."
                ),
            },
            "DOC-FIG-HORIZON-012": {
                "stem": "cross_asset_all_models_metrics_by_horizon",
                "size_mm": [180, 215],
                "alt_text": (
                    "Eight-panel cross-asset figure showing MAE, MSE, RMSE, and RMSSE "
                    "for every available model across six horizons in MS and S tasks."
                ),
            },
            "DOC-FIG-HORIZON-013": {
                "stem": "crypto_all_models_metrics_by_horizon",
                "size_mm": [180, 215],
                "alt_text": (
                    "Eight-panel cryptoasset figure showing MAE, MSE, RMSE, and RMSSE "
                    "for every available model across six horizons in MS and S tasks."
                ),
            },
            "DOC-FIG-HORIZON-014": {
                "stem": "fx_all_models_metrics_by_horizon",
                "size_mm": [180, 215],
                "alt_text": (
                    "Eight-panel foreign-exchange figure showing MAE, MSE, RMSE, and "
                    "RMSSE for every available model across six horizons in MS and S tasks."
                ),
            },
            "DOC-FIG-HORIZON-015": {
                "stem": "yields_all_models_metrics_by_horizon",
                "size_mm": [180, 215],
                "alt_text": (
                    "Eight-panel Treasury-yield figure showing MAE, MSE, RMSE, and RMSSE "
                    "for every available model across six horizons in MS and S tasks."
                ),
            },
            "DOC-FIG-PROFILE-016": {
                "stem": "computational_profile_overview",
                "size_mm": [180, 108],
                "alt_text": (
                    "Two-panel learned-model profile showing median, interquartile range, and "
                    "maximum train/evaluation runtime and peak allocated GPU memory across 240 "
                    "runs per model. PMS-Mamba is faster and smaller than TimesNet but slower "
                    "than all other learned models."
                ),
            },
            "DOC-FIG-PROFILE-017": {
                "stem": "computational_profile_by_horizon",
                "size_mm": [180, 103],
                "alt_text": (
                    "Two line panels showing median runtime and peak allocated GPU memory for "
                    "all nine learned models at each of six forecast horizons. PMS-Mamba remains "
                    "between TimesNet and the faster learned baselines at every horizon."
                ),
            },
            "DOC-FIG-PROFILE-018": {
                "stem": "computational_profile_by_task",
                "size_mm": [180, 150],
                "alt_text": (
                    "Two annotated heatmaps showing median runtime and peak allocated GPU memory "
                    "for every learned model and all eight forecasting tasks. The PMS-Mamba row "
                    "is outlined in orange."
                ),
            },
        },
        "outputs": {str(path.relative_to(OUTPUT_ROOT)): sha256_path(path) for path in sorted(paths)},
        "versions": {
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "matplotlib": mpl.__version__,
        },
    }
    path = OUTPUT_ROOT / "detailed_model_comparison.manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    frame = add_dimensions(pd.read_csv(SOURCE))
    validate_source(frame)
    profile = pd.read_csv(PROFILE_SOURCE)
    validate_profile_source(profile)

    cell_gaps = build_all_model_cell_gaps(frame)
    model_summary = build_model_metric_summary(cell_gaps)
    term_model_summary = build_term_model_metric_summary(cell_gaps)
    pms_summary = model_summary[model_summary["model"] == PMS_MODEL].reset_index(drop=True)
    pms_term_task = build_pms_term_task_summary(cell_gaps)
    head_to_head = build_pms_head_to_head(frame)
    rmse_advantage_by_term = build_pms_rmse_advantage_by_term(frame)
    rmse_advantage_by_task = build_pms_rmse_advantage_by_task(frame)
    dataset_summary = build_dataset_reference_summary()
    task_model = build_task_model_metric_summary(frame)
    pms_task = task_model[task_model["model"] == PMS_MODEL].reset_index(drop=True)
    task_summary, term_summary = build_legacy_tables(task_model, cell_gaps)
    computational_profile = build_computational_profile_model_summary(profile, model_summary)
    computational_profile_by_horizon = build_computational_profile_by_horizon(profile)
    computational_profile_by_task = build_computational_profile_by_task(profile)
    pms_efficiency = build_pms_efficiency_comparison(computational_profile, head_to_head)

    tables = {
        "all_model_cell_metric_gaps.csv": cell_gaps,
        "model_metric_position_summary.csv": model_summary,
        "term_model_metric_summary.csv": term_model_summary,
        "pms_mamba_metric_position_summary.csv": pms_summary,
        "pms_mamba_term_task_summary.csv": pms_term_task,
        "pms_mamba_head_to_head.csv": head_to_head,
        "pms_mamba_rmse_advantage_by_term.csv": rmse_advantage_by_term,
        "pms_mamba_rmse_advantage_by_task.csv": rmse_advantage_by_task,
        "dataset_reference_summary.csv": dataset_summary,
        "task_model_metric_summary.csv": task_model,
        "pms_mamba_task_metric_summary.csv": pms_task,
        "pms_mamba_task_summary.csv": task_summary,
        "pms_mamba_term_summary.csv": term_summary,
        "computational_profile_model_summary.csv": computational_profile,
        "computational_profile_by_horizon.csv": computational_profile_by_horizon,
        "computational_profile_by_task.csv": computational_profile_by_task,
        "pms_mamba_efficiency_comparison.csv": pms_efficiency,
    }
    written: list[Path] = []
    for filename, table in tables.items():
        path = OUTPUT_ROOT / filename
        table.to_csv(path, index=False)
        written.append(path)

    figure_pairs = (
        make_performance_figure(task_summary, term_summary),
        make_model_position_figure(model_summary),
        make_pms_cell_gap_figure(cell_gaps),
        make_task_model_gap_figure(task_model),
        make_head_to_head_figure(head_to_head),
        make_pms_term_task_figure(pms_term_task),
        make_pms_rmse_advantage_by_term_figure(rmse_advantage_by_term),
        make_dataset_reference_figure(dataset_summary),
        make_computational_profile_overview(computational_profile),
        make_computational_profile_by_horizon_figure(computational_profile_by_horizon),
        make_computational_profile_by_task_figure(computational_profile_by_task),
        *(make_family_metric_horizon_figure(frame, family) for family in FAMILY_ORDER),
        *(make_term_model_figure(term_model_summary, term) for term in TERM_ORDER),
    )
    for paths in figure_pairs:
        written.extend(paths)

    write_manifest(written)
    legacy_manifest = OUTPUT_ROOT / "pms_mamba_performance_summary.manifest.json"
    if legacy_manifest.exists():
        legacy_manifest.unlink()
    print(
        f"Wrote {len(tables)} comparison tables and {len(figure_pairs)} figures under {OUTPUT_ROOT}; "
        "sources=frozen V1 aggregate metrics and run-level computational profiles"
    )


if __name__ == "__main__":
    main()
