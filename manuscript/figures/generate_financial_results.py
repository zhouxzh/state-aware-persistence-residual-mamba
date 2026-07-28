#!/usr/bin/env python
from __future__ import annotations

import json
import hashlib
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import numpy as np
import pandas as pd


FIGURE_DIR = Path(__file__).resolve().parent
REPO_ROOT = FIGURE_DIR.parents[1]
ANALYSIS_ROOT = REPO_ROOT / "results" / "financial_confirmatory" / "analysis"
PROTOCOL_PATH = REPO_ROOT / "configs" / "financial_benchmark.json"
MODEL_ORDER = [
    "DLinear",
    "NLinear",
    "PatchTST",
    "TimesNet",
    "iTransformer",
    "S_Mamba",
    "NS_Mamba-D",
    "MS_Mamba-MD",
    "PMS_Mamba-PD",
]


def require_file(path: Path) -> None:
    if not path.is_file():
        raise RuntimeError(f"missing required analysis artifact: {path}")


def matrix(table: pd.DataFrame, value: str, models: list[str], horizons: list[int]) -> np.ndarray:
    pivot = table.pivot(index="model", columns="horizon", values=value).reindex(
        index=models, columns=horizons
    )
    values = pivot.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise RuntimeError(f"non-finite or missing values in figure matrix {value}")
    return values


def draw_heatmap(
    axis: plt.Axes,
    values: np.ndarray,
    models: list[str],
    horizons: list[int],
    title: str,
    color_label: str,
) -> None:
    bound = max(float(np.max(np.abs(values))), 1e-12)
    image = axis.imshow(
        values,
        aspect="auto",
        cmap="RdBu",
        norm=TwoSlopeNorm(vmin=-bound, vcenter=0.0, vmax=bound),
    )
    axis.set_title(title, fontsize=10)
    axis.set_xticks(np.arange(len(horizons)), [str(value) for value in horizons])
    axis.set_yticks(np.arange(len(models)), models)
    axis.set_xlabel("Forecast horizon (trading days)")
    for row in range(values.shape[0]):
        for column in range(values.shape[1]):
            value = values[row, column]
            color = "white" if abs(value) > 0.58 * bound else "black"
            axis.text(column, row, f"{value:.2f}", ha="center", va="center", fontsize=6.5, color=color)
    colorbar = axis.figure.colorbar(image, ax=axis, fraction=0.035, pad=0.03)
    colorbar.set_label(color_label, fontsize=8)


def save_figure(figure: plt.Figure, stem: str) -> None:
    metadata = {
        "Title": stem.replace("_", " ").title(),
        "Author": "Generated from financial_confirmatory_v1 analysis artifacts",
        "Subject": "Nonstationary financial forecasting benchmark",
    }
    figure.savefig(FIGURE_DIR / f"{stem}.pdf", bbox_inches="tight", metadata=metadata)
    figure.savefig(FIGURE_DIR / f"{stem}.png", bbox_inches="tight", dpi=300, metadata={"Software": "Matplotlib"})
    plt.close(figure)


def main() -> None:
    aggregate_path = ANALYSIS_ROOT / "aggregate_metrics.csv"
    mode_path = ANALYSIS_ROOT / "s_ms_comparison.csv"
    analysis_manifest_path = ANALYSIS_ROOT / "analysis_manifest.json"
    for path in (PROTOCOL_PATH, aggregate_path, mode_path, analysis_manifest_path):
        require_file(path)
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    analysis_manifest = json.loads(analysis_manifest_path.read_text(encoding="utf-8"))
    if analysis_manifest.get("protocol_version") != protocol["protocol_version"]:
        raise RuntimeError("analysis protocol version mismatch")
    if analysis_manifest.get("protocol_sha256") != hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest():
        raise RuntimeError("analysis protocol hash mismatch")
    horizons = [int(value) for value in protocol["horizons"]]

    aggregate = pd.read_csv(aggregate_path)
    aggregate = aggregate[aggregate["model"].isin(MODEL_ORDER)].copy()
    aggregate["mode"] = aggregate["dataset"].str.extract(r"_(s|ms)$", expand=False)
    grouped = aggregate.groupby(["mode", "model", "horizon"], as_index=False)["skill_vs_last_value"].mean()

    figure, axes = plt.subplots(1, 2, figsize=(11.2, 5.6), constrained_layout=True)
    for axis, mode, title in zip(axes, ("s", "ms"), ("Univariate input (S)", "Multivariate input (MS)")):
        subset = grouped[grouped["mode"] == mode]
        values = matrix(subset, "skill_vs_last_value", MODEL_ORDER, horizons)
        draw_heatmap(
            axis,
            values,
            MODEL_ORDER,
            horizons,
            title,
            "Mean skill vs. last value",
        )
    save_figure(figure, "financial_skill_heatmap")

    mode_pairs = pd.read_csv(mode_path)
    mode_pairs = mode_pairs[mode_pairs["model"].isin(MODEL_ORDER)]
    mode_grouped = mode_pairs.groupby(["model", "horizon"], as_index=False)["ms_minus_s_skill"].mean()
    values = matrix(mode_grouped, "ms_minus_s_skill", MODEL_ORDER, horizons)
    figure, axis = plt.subplots(figsize=(6.4, 5.5), constrained_layout=True)
    draw_heatmap(
        axis,
        values,
        MODEL_ORDER,
        horizons,
        "Incremental skill from multivariate inputs",
        "Mean MS skill minus S skill",
    )
    save_figure(figure, "financial_s_ms_skill_delta")
    print("wrote financial result figures")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"Financial figure generation blocked: {exc}") from None
