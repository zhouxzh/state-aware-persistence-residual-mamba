#!/usr/bin/env python3
"""Generate fixed-model horizon profiles for the manuscript."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results"
MANUSCRIPT_DIR = REPO_ROOT / "manuscript"
OUTPUT_DIR = MANUSCRIPT_DIR / "figures"
LAST_VALUE_PATH = MANUSCRIPT_DIR / "data" / "last_value_baseline.csv"
DATASETS = (("gld", "GLD"), ("exchange", "Exchange"))
DISPLAY_NAMES = {
    "PMS_Mamba-PD": "PMS-Mamba-PD",
    "S_Mamba": "S-Mamba",
}
STYLES = {
    "baseline": {"color": "#0072B2", "marker": "o", "linestyle": "-"},
    "mamba": {"color": "#D55E00", "marker": "s", "linestyle": "--"},
    "last_value": {"color": "#000000", "marker": "^", "linestyle": ":"},
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def read_model_rows(dataset: str) -> list[dict[str, str]]:
    rows = []
    for phase in ("baseline", "mamba"):
        rows.extend(read_csv(RESULTS_DIR / f"{dataset}_{phase}_optuna_best.csv"))
    return rows


def best_model(rows: list[dict[str, str]], phase: str) -> str:
    scores = {
        row["model"]: float(row["overall_balanced_rmsse"])
        for row in rows
        if row["phase"] == phase
    }
    return min(scores, key=scores.get)


def model_profile(rows: list[dict[str, str]], model: str) -> tuple[list[int], list[float]]:
    selected = [row for row in rows if row["model"] == model]
    selected.sort(key=lambda row: int(row["horizon"]))
    return [int(row["horizon"]) for row in selected], [float(row["rmsse"]) for row in selected]


def display_model(model: str) -> str:
    return DISPLAY_NAMES.get(model, model)


def main() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.labelsize": 8.5,
            "axes.titlesize": 9.5,
            "legend.fontsize": 7.5,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "axes.linewidth": 0.8,
        }
    )

    last_value_rows = read_csv(LAST_VALUE_PATH)
    figure, axes = plt.subplots(1, 2, figsize=(7.2, 3.35), layout="constrained")

    for index, ((dataset, label), axis) in enumerate(zip(DATASETS, axes)):
        rows = read_model_rows(dataset)
        baseline_model = best_model(rows, "baseline")
        mamba_model = best_model(rows, "mamba")
        profiles = [
            (baseline_model, "baseline", model_profile(rows, baseline_model)),
            (mamba_model, "mamba", model_profile(rows, mamba_model)),
            (
                "Last-value",
                "last_value",
                model_profile(
                    [row for row in last_value_rows if row["dataset"] == dataset],
                    "Last-value",
                ),
            ),
        ]

        expected_horizons = profiles[0][2][0]
        x_values = np.arange(len(expected_horizons))
        for model, style_name, (horizons, values) in profiles:
            if horizons != expected_horizons:
                raise ValueError(f"Horizon mismatch for {dataset}/{model}")
            style = STYLES[style_name]
            axis.plot(
                x_values,
                values,
                label=display_model(model),
                color=style["color"],
                marker=style["marker"],
                linestyle=style["linestyle"],
                linewidth=1.5,
                markersize=4.0,
                markeredgecolor="white" if style_name != "last_value" else "black",
                markeredgewidth=0.45,
            )

        axis.set_xticks(x_values, [str(value) for value in expected_horizons], rotation=45, ha="right")
        axis.set_ylim(bottom=0)
        axis.set_xlabel("Forecast horizon (observations)")
        axis.set_ylabel("RMSSE")
        axis.set_title(f"{chr(ord('A') + index)}  {label}", loc="left")
        axis.grid(axis="y", color="#D9D9D9", linewidth=0.6)
        axis.set_axisbelow(True)
        axis.legend(frameon=False, loc="upper left")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = OUTPUT_DIR / "benchmark_family_comparison.pdf"
    png_path = OUTPUT_DIR / "benchmark_family_comparison.png"
    figure.savefig(pdf_path, facecolor="white")
    figure.savefig(png_path, dpi=300, facecolor="white")
    plt.close(figure)
    print(f"wrote {pdf_path.relative_to(REPO_ROOT)}")
    print(f"wrote {png_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
