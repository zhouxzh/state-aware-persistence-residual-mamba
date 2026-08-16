#!/usr/bin/env python
"""Render evidence-bound figures from a verified S-only financial release."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_LABELS = {
    "financial_cross_asset_s": "Cross-asset (GLD)",
    "financial_crypto_s": "Crypto (BTCUSDT)",
    "financial_fx_s": "Foreign exchange (GBPUSD)",
    "financial_yields_s": "Treasury yields (DGS10)",
}
TASK_ABBREVIATIONS = {
    "financial_cross_asset_s": "Cross asset",
    "financial_crypto_s": "Crypto",
    "financial_fx_s": "FX",
    "financial_yields_s": "Yields",
}
MODEL_LABELS = {
    "RegimeGatedMamba": "Regime-Gated Mamba",
    "UngatedRegimeLinearMamba": "Ungated Regime-Linear Mamba",
    "MultiScalePatchMamba": "Multi-Scale Patch Mamba",
    "InvertedMamba": "Inverted Mamba",
    "DecompositionMamba": "Decomposition Mamba",
    "MultiScaleDecompositionMamba": "Multi-Scale Decomposition Mamba",
    "DLinear": "DLinear",
    "NLinear": "NLinear",
    "PatchTST": "PatchTST",
    "TimesNet": "TimesNet",
    "iTransformer": "iTransformer",
    "LastValue": "Last-value",
    "RandomWalkDrift": "Random-walk-with-drift",
    "ARIMA": "ARIMA",
}
MODEL_STYLES = {
    "RegimeGatedMamba": {"color": "#000000", "marker": "D", "linestyle": "-", "linewidth": 2.4, "zorder": 5},
    "UngatedRegimeLinearMamba": {"color": "#666666", "marker": "d", "linestyle": "--", "linewidth": 1.5},
    "MultiScalePatchMamba": {"color": "#0072B2", "marker": "o", "linestyle": "-", "linewidth": 1.2},
    "InvertedMamba": {"color": "#009E73", "marker": "s", "linestyle": "-", "linewidth": 1.2},
    "DecompositionMamba": {"color": "#56B4E9", "marker": "^", "linestyle": "-", "linewidth": 1.2},
    "MultiScaleDecompositionMamba": {"color": "#CC79A7", "marker": "v", "linestyle": "-", "linewidth": 1.2},
    "DLinear": {"color": "#E69F00", "marker": "P", "linestyle": "--", "linewidth": 1.2},
    "NLinear": {"color": "#D55E00", "marker": "X", "linestyle": "--", "linewidth": 1.2},
    "PatchTST": {"color": "#8C564B", "marker": "<", "linestyle": "-.", "linewidth": 1.2},
    "TimesNet": {"color": "#984EA3", "marker": ">", "linestyle": "-.", "linewidth": 1.2},
    "iTransformer": {"color": "#4D4D4D", "marker": "h", "linestyle": "-.", "linewidth": 1.2},
    "LastValue": {"color": "#1B9E77", "marker": "o", "linestyle": ":", "linewidth": 1.4},
    "RandomWalkDrift": {"color": "#7570B3", "marker": "s", "linestyle": ":", "linewidth": 1.4},
    "ARIMA": {"color": "#E7298A", "marker": "^", "linestyle": ":", "linewidth": 1.4},
}
FORECAST_MODEL_IDS = ("RegimeGatedMamba", "PatchTST", "TimesNet")
FORECAST_COLORS = {
    "RegimeGatedMamba": "#000000",
    "PatchTST": "#8C564B",
    "TimesNet": "#984EA3",
    "ARIMA": "#E7298A",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_release(release: str) -> tuple[Path, pd.DataFrame, pd.DataFrame, dict]:
    root = REPO_ROOT / "reproducibility" / release
    status_path = root / "release_status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    if status.get("status") != "verified":
        raise RuntimeError(f"Figures require a verified release, found {status.get('status')!r}")
    aggregate_path = root / "metrics" / "metrics_aggregate.csv"
    seed_path = root / "metrics" / "metrics_by_seed.csv"
    if not aggregate_path.is_file() or not seed_path.is_file():
        raise FileNotFoundError("Verified release is missing aggregate or seed-level metrics")
    return root, pd.read_csv(aggregate_path), pd.read_csv(seed_path), status


def model_order(table: pd.DataFrame) -> list[str]:
    ranks = table.groupby("model_id", as_index=True)["path_rmsse_rank"].mean().sort_values()
    return ranks.index.tolist()


def save_figure(figure: plt.Figure, output_dir: Path, stem: str) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for suffix, dpi in (("pdf", None), ("png", 450)):
        path = output_dir / f"{stem}.{suffix}"
        figure.savefig(path, dpi=dpi, facecolor="white")
        if suffix == "png":
            with Image.open(path) as image:
                image.convert("RGB").save(path, format="PNG", dpi=image.info.get("dpi", (dpi, dpi)))
        paths.append(path)
    plt.close(figure)
    return paths


def plot_rank_heatmap(table: pd.DataFrame, output_dir: Path, release: str) -> list[Path]:
    tasks = sorted(table["dataset"].unique())
    horizons = sorted(table["horizon"].unique())
    models = model_order(table)
    columns = [(task, horizon) for task in tasks for horizon in horizons]
    matrix = np.array(
        [
            [
                table.loc[(table["model_id"] == model) & (table["dataset"] == task) & (table["horizon"] == horizon), "path_rmsse_rank"].iloc[0]
                for task, horizon in columns
            ]
            for model in models
        ],
        dtype=float,
    )
    max_rank = int(np.nanmax(matrix))
    figure, axis = plt.subplots(figsize=(12.4, 6.35), layout="constrained")
    cmap = plt.colormaps["viridis_r"].resampled(max_rank)
    image = axis.imshow(
        matrix,
        aspect="auto",
        cmap=cmap,
        norm=BoundaryNorm(np.arange(0.5, max_rank + 1.5), cmap.N),
        interpolation="nearest",
    )
    axis.set_xticks(
        np.arange(len(columns)),
        [f"{TASK_ABBREVIATIONS.get(task, task)}\n{horizon}" for task, horizon in columns],
        fontsize=6.5,
    )
    axis.set_yticks(np.arange(len(models)), [MODEL_LABELS.get(model, model) for model in models], fontsize=7)
    axis.set_xlabel("Forecast horizon (retained observations)")
    axis.set_ylabel("Model")
    axis.set_title("S-only v1 path-RMSSE rank by task and horizon", loc="left", fontsize=12, weight="bold", pad=27)
    axis.text(
        0,
        1.005,
        "Rank 1 is the lowest path RMSSE in a task-horizon cell; learned rows are five-seed means.",
        transform=axis.transAxes,
        fontsize=8,
        va="bottom",
    )
    for boundary in range(len(horizons), len(columns), len(horizons)):
        axis.axvline(boundary - 0.5, color="white", linewidth=2.0)
    for row_index, model in enumerate(models):
        for column_index, rank in enumerate(matrix[row_index]):
            text_color = "white" if rank >= max_rank * 0.65 else "black"
            axis.text(column_index, row_index, f"{int(rank)}", ha="center", va="center", fontsize=5.2, color=text_color)
        if model == "RegimeGatedMamba":
            axis.add_patch(plt.Rectangle((-0.5, row_index - 0.5), len(columns), 1, fill=False, edgecolor="#000000", linewidth=1.2))
    colorbar = figure.colorbar(image, ax=axis, pad=0.01, fraction=0.03)
    colorbar.set_label("Path-RMSSE rank (1 = best)", fontsize=8)
    colorbar.ax.tick_params(labelsize=7)
    return save_figure(figure, output_dir, f"{release}_path_rmsse_rank_heatmap")


def plot_all_models_by_horizon(table: pd.DataFrame, output_dir: Path, release: str) -> list[Path]:
    tasks = sorted(table["dataset"].unique())
    horizons = sorted(table["horizon"].unique())
    models = model_order(table)
    figure = plt.figure(figsize=(12.4, 9.0), layout="constrained")
    main, legend_band = figure.subfigures(2, 1, height_ratios=[12, 1.6])
    axes = main.subplots(2, 2, sharex=True)
    legend_handles = []
    for axis, task in zip(axes.flat, tasks):
        subset = table[table["dataset"] == task]
        for model in models:
            values = subset[subset["model_id"] == model].sort_values("horizon")
            style = dict(MODEL_STYLES[model])
            line = axis.plot(values["horizon"], values["path_rmsse_mean"], label=MODEL_LABELS[model], markersize=4.4, **style)[0]
            if len(legend_handles) < len(models):
                legend_handles.append(line)
        axis.set_xscale("log")
        axis.set_xticks(horizons)
        axis.set_xticklabels([str(value) for value in horizons])
        axis.grid(axis="y", color="#D9D9D9", linewidth=0.6)
        axis.set_title(TASK_LABELS.get(task, task), loc="left", fontsize=10, weight="bold")
        axis.set_ylabel("Path RMSSE")
    for axis in axes[-1, :]:
        axis.set_xlabel("Forecast horizon (retained observations; log scale)")
    main.suptitle("S-only v1 path-RMSSE trajectories for every model", x=0.01, ha="left", fontsize=13, weight="bold")
    legend_axis = legend_band.subplots()
    legend_axis.axis("off")
    legend_axis.legend(
        legend_handles,
        [handle.get_label() for handle in legend_handles],
        loc="center",
        ncol=4,
        fontsize=7,
        frameon=False,
    )
    return save_figure(figure, output_dir, f"{release}_path_rmsse_by_task_horizon")


def plot_accuracy_efficiency(table: pd.DataFrame, output_dir: Path, release: str) -> list[Path]:
    learned = table[table["seed_count"] > 0]
    summary = (
        learned.groupby("model_id", as_index=False)
        .agg(mean_path_rmsse_rank=("path_rmsse_rank", "mean"), runtime_seconds=("runtime_seconds_mean", "mean"))
        .sort_values("runtime_seconds")
    )
    figure = plt.figure(figsize=(7.6, 5.65), layout="constrained")
    main, note_band = figure.subfigures(2, 1, height_ratios=[10, 1.6])
    axis = main.subplots()
    for row in summary.itertuples(index=False):
        style = MODEL_STYLES[row.model_id]
        axis.scatter(
            row.runtime_seconds,
            row.mean_path_rmsse_rank,
            s=58 if row.model_id == "RegimeGatedMamba" else 42,
            color=style["color"],
            marker=style["marker"],
            edgecolor="white",
            linewidth=0.6,
            zorder=4 if row.model_id == "RegimeGatedMamba" else 3,
        )
        offset, alignment = (5, 4), "left"
        if row.model_id == "RegimeGatedMamba":
            offset = (9, -16)
        elif row.model_id == "UngatedRegimeLinearMamba":
            offset = (7, 12)
        label = "Ungated RLM" if row.model_id == "UngatedRegimeLinearMamba" else MODEL_LABELS[row.model_id]
        axis.annotate(
            label,
            (row.runtime_seconds, row.mean_path_rmsse_rank),
            xytext=offset,
            textcoords="offset points",
            fontsize=7,
            ha=alignment,
        )
    axis.set_xscale("log")
    axis.invert_yaxis()
    axis.grid(color="#D9D9D9", linewidth=0.6)
    axis.set_xlabel("Mean end-to-end runtime per task-horizon-seed bundle (s; log scale)")
    axis.set_ylabel("Mean path-RMSSE rank across 24 cells\n(lower rank is better)")
    axis.set_title("S-only v1 accuracy position and campaign runtime", loc="left", fontsize=12, weight="bold")
    note_axis = note_band.subplots()
    note_axis.axis("off")
    note_axis.text(
        0,
        0.55,
        "Runtime includes each horizon's training and evaluation run; deterministic references are excluded because they have no seed-level training time.",
        fontsize=7,
        va="center",
    )
    return save_figure(figure, output_dir, f"{release}_accuracy_efficiency")


def learned_forecast(root: Path, seed_table: pd.DataFrame, task: str, model_id: str, horizon: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    row = seed_table.loc[
        (seed_table["dataset"] == task)
        & (seed_table["model_id"] == model_id)
        & (seed_table["seed"].astype(str) == "2023")
        & (seed_table["horizon"] == horizon)
    ]
    if len(row) != 1:
        raise RuntimeError(f"Missing seed-2023 forecast for {task}/{model_id}/h{horizon}")
    run_path = REPO_ROOT / "results" / "financial_s_only_retrospective_v1" / "runs" / row.iloc[0]["setting"]
    origins = np.load(run_path / "origin_dates.npy", allow_pickle=False).astype(str)
    dates = np.load(run_path / "forecast_dates.npy", allow_pickle=False).astype(str)
    prediction = np.load(run_path / "pred.npy", allow_pickle=False)
    truth = np.load(run_path / "true.npy", allow_pickle=False)
    return origins, dates, prediction, truth


def arima_forecast(root: Path, task: str, horizon: int) -> tuple[np.ndarray, np.ndarray]:
    metrics_path = root / "metrics" / "deterministic_metrics.csv"
    table = pd.read_csv(metrics_path)
    row = table.loc[(table["dataset"] == task) & (table["model_id"] == "ARIMA") & (table["horizon"] == horizon)]
    if len(row) != 1:
        raise RuntimeError(f"Missing ARIMA forecast for {task}/h{horizon}")
    bundle = REPO_ROOT / row.iloc[0]["bundle"]
    payload = np.load(bundle, allow_pickle=False)
    return payload["origin_dates"].astype(str), payload["prediction"]


def plot_forecast_examples(root: Path, seed_table: pd.DataFrame, output_dir: Path, release: str) -> list[Path]:
    if release != "financial_s_only_v1":
        return []
    manifest = json.loads((root / "training_datasets.json").read_text(encoding="utf-8"))
    tasks = sorted(manifest)
    horizon = 252
    figure = plt.figure(figsize=(12.4, 8.55), layout="constrained")
    main, legend_band = figure.subfigures(2, 1, height_ratios=[12, 1.6])
    axes = main.subplots(2, 2)
    legend_handles: dict[str, plt.Line2D] = {}
    for axis, task in zip(axes.flat, tasks):
        origins, forecast_dates, _, truth = learned_forecast(root, seed_table, task, "RegimeGatedMamba", horizon)
        final_origin = origins[-1]
        entry = manifest[task]
        frame = pd.read_csv(REPO_ROOT / entry["root_path"] / entry["data_path"], usecols=["date", entry["target"]])
        dates = pd.to_datetime(frame["date"], errors="raise")
        origin_index = int(np.flatnonzero(dates.astype(str).to_numpy() == final_origin)[0])
        history_start = max(0, origin_index - 96)
        history_line = axis.plot(dates.iloc[history_start:origin_index + 1], frame[entry["target"]].iloc[history_start:origin_index + 1], color="#4D4D4D", linewidth=1.6, label="Observed history")[0]
        truth_dates = pd.to_datetime(forecast_dates[-1])
        truth_line = axis.plot(truth_dates, truth[-1, :, 0], color="#000000", linewidth=1.8, linestyle="--", label="Observed future")[0]
        legend_handles.setdefault("Observed history", history_line)
        legend_handles.setdefault("Observed future", truth_line)
        for model_id in FORECAST_MODEL_IDS:
            model_origins, model_dates, prediction, _ = learned_forecast(root, seed_table, task, model_id, horizon)
            index = int(np.flatnonzero(model_origins == final_origin)[0])
            line = axis.plot(pd.to_datetime(model_dates[index]), prediction[index, :, 0], color=FORECAST_COLORS[model_id], linewidth=1.3, label=MODEL_LABELS[model_id])[0]
            legend_handles.setdefault(MODEL_LABELS[model_id], line)
        arima_origins, arima_prediction = arima_forecast(root, task, horizon)
        arima_index = int(np.flatnonzero(arima_origins == final_origin)[0])
        arima_line = axis.plot(truth_dates, arima_prediction[arima_index], color=FORECAST_COLORS["ARIMA"], linewidth=1.2, label="ARIMA")[0]
        legend_handles.setdefault("ARIMA", arima_line)
        axis.axvline(pd.Timestamp(str(final_origin)), color="#7F7F7F", linewidth=0.8)
        axis.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        axis.grid(axis="y", color="#D9D9D9", linewidth=0.6)
        axis.set_title(TASK_LABELS.get(task, task), loc="left", fontsize=10, weight="bold")
        axis.set_ylabel(entry["target"] + " level")
    for axis in axes[-1, :]:
        axis.set_xlabel("Date")
    main.suptitle("Illustrative latest-origin 252-observation forecasts", x=0.01, ha="left", fontsize=13, weight="bold")
    legend_axis = legend_band.subplots()
    legend_axis.axis("off")
    legend_axis.legend(list(legend_handles.values()), list(legend_handles), loc="center", ncol=3, fontsize=8, frameon=False)
    return save_figure(figure, output_dir, f"{release}_illustrative_forecasts_h252")


def render(release: str, output_dir: Path) -> dict:
    root, aggregate_table, seed_table, status = load_release(release)
    outputs = []
    outputs.extend(plot_rank_heatmap(aggregate_table, output_dir, release))
    outputs.extend(plot_all_models_by_horizon(aggregate_table, output_dir, release))
    outputs.extend(plot_accuracy_efficiency(aggregate_table, output_dir, release))
    outputs.extend(plot_forecast_examples(root, seed_table, output_dir, release))
    source_paths = [
        root / "metrics" / "metrics_aggregate.csv",
        root / "metrics" / "metrics_by_seed.csv",
        root / "metrics" / "deterministic_metrics.csv",
        root / "release_status.json",
    ]
    manifest = {
        "release": release,
        "release_status": status["status"],
        "source_files": [{"path": str(path.relative_to(REPO_ROOT)), "sha256": sha256(path)} for path in source_paths],
        "output_files": [{"path": str(path.relative_to(REPO_ROOT)), "sha256": sha256(path)} for path in outputs],
        "figures": {
            f"{release}_path_rmsse_rank_heatmap": {
                "description": "All model path-RMSSE ranks for every v1 task-horizon cell.",
                "alt_text": "A heatmap of ranks one through fourteen for every model across four task groups and six horizons.",
            },
            f"{release}_path_rmsse_by_task_horizon": {
                "description": "All model path-RMSSE trajectories within each v1 target-only task.",
                "alt_text": "Four line charts, one per S-only task, with path RMSSE across six forecast horizons for all models.",
            },
            f"{release}_accuracy_efficiency": {
                "description": "Learned-model mean rank versus campaign runtime.",
                "alt_text": "A log-runtime scatterplot of learned model accuracy rank, with lower rank better.",
            },
            f"{release}_illustrative_forecasts_h252": {
                "description": "Latest-origin h252 trajectory examples, seed 2023 for learned models.",
                "alt_text": "Four time-series panels showing observed history and future alongside selected model forecasts at the latest h252 origin.",
            },
        },
        "notes": [
            "All rank and metric figures use the checksum-covered release tables.",
            "The forecast trajectory display is illustrative and is not used for aggregate performance claims.",
            "Raw MAE and RMSE remain task-specific; only RMSSE ranks are compared across task families.",
        ],
    }
    manifest_path = output_dir / f"{release}_figure_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"release": release, "figure_count": len(outputs), "outputs": [str(path.relative_to(REPO_ROOT)) for path in outputs], "manifest": str(manifest_path.relative_to(REPO_ROOT))}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", default="financial_s_only_v1", choices=("financial_s_only_v1", "financial_s_only_v2"))
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "docs" / "figures")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(json.dumps(render(args.release, args.output_dir.resolve()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
