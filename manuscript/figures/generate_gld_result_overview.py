#!/usr/bin/env python
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


FIG_DIR = Path(__file__).resolve().parent
MANUSCRIPT_ROOT = FIG_DIR.parent
BASELINE_CSV = MANUSCRIPT_ROOT / "data" / "gld_baseline_optuna_best.csv"
MAMBA_OPTUNA_CSV = MANUSCRIPT_ROOT / "data" / "gld_mamba_optuna_best.csv"
FIG_PDF = FIG_DIR / "gld_result_overview.pdf"
FIG_PNG = FIG_DIR / "gld_result_overview.png"

HORIZONS = [1, 3, 5, 7, 14, 30, 60, 90, 120, 180, 270, 360]
DIAG_HORIZONS = [30, 120, 180, 360]

FRONTIER_MODELS = [
    "PatchTST",
    "NLinear",
    "TimesNet",
    "iTransformer",
]
MAMBA_MODELS = [
    "S_Mamba",
    "NS_Mamba-D",
    "MS_Mamba-MD",
    "PMS_Mamba-PD",
]

LABELS = {
    "S_Mamba": "S-Mamba",
    "iTransformer": "iTransformer",
    "Autoformer": "Autoformer",
    "Transformer": "Transformer",
    "Informer": "Informer",
    "Reformer": "Reformer",
    "PatchTST": "PatchTST",
    "NLinear": "NLinear",
    "TimesNet": "TimesNet",
    "Nonstationary_Transformer": "NSTransformer",
    "DLinear": "DLinear",
    "MS_Mamba-MD": "MS-Mamba-MD",
    "MS_Mamba-MDG": "MS-Mamba-MDG",
    "MS_Mamba-MDS": "MS-Mamba-MDS",
    "NS_Mamba-D": "NS-Mamba-D",
    "PMS_Mamba-PD": "PMS-Mamba-PD",
}

COLORS = {
    "S_Mamba": "#0f766e",
    "iTransformer": "#b45309",
    "Autoformer": "#64748b",
    "Transformer": "#7f1d1d",
    "Informer": "#1f2937",
    "Reformer": "#9a3412",
    "PatchTST": "#111827",
    "NLinear": "#c2410c",
    "TimesNet": "#4d7c0f",
    "Nonstationary_Transformer": "#475569",
    "DLinear": "#8b5e34",
    "MS_Mamba-MD": "#0f766e",
    "MS_Mamba-MDG": "#0369a1",
    "MS_Mamba-MDS": "#7c3aed",
    "NS_Mamba-D": "#b45309",
    "PMS_Mamba-PD": "#6b7280",
}

MARKERS = {
    "S_Mamba": "o",
    "iTransformer": "s",
    "Autoformer": "^",
    "Transformer": "D",
    "Informer": "P",
    "Reformer": "X",
    "PatchTST": "o",
    "NLinear": "s",
    "TimesNet": "^",
    "Nonstationary_Transformer": "D",
    "DLinear": "P",
    "MS_Mamba-MD": "o",
    "MS_Mamba-MDG": "s",
    "MS_Mamba-MDS": "P",
    "NS_Mamba-D": "^",
    "PMS_Mamba-PD": "D",
}


def load_rows(path, name_key):
    rows = []
    with path.open() as f:
        for row in csv.DictReader(f):
            if row.get("status") != "complete":
                continue
            rows.append(
                {
                    "name": row[name_key],
                    "horizon": int(row["horizon"]),
                    "rmse": float(row["rmse"]),
                    "rmsse": float(row["rmsse"]) if row.get("rmsse") else None,
                }
            )
    return rows


def index_rows(rows, metric):
    indexed = defaultdict(dict)
    for row in rows:
        value = row.get(metric)
        if value is None:
            continue
        indexed[row["name"]][row["horizon"]] = value
    return indexed


def style_axes(ax, title, ylabel):
    ax.set_title(title, fontsize=10, loc="left")
    ax.set_xscale("linear")
    ax.set_yscale("log")
    ax.grid(True, which="major", axis="both", color="#d1d5db", linewidth=0.7, alpha=0.8)
    ax.grid(True, which="minor", axis="y", color="#e5e7eb", linewidth=0.5, alpha=0.5)
    ax.set_ylabel(ylabel)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def plot_panel(ax, indexed, models, horizons, title, ylabel):
    style_axes(ax, title, ylabel)
    for model in models:
        xs = [h for h in horizons if h in indexed.get(model, {})]
        ys = [indexed[model][h] for h in xs]
        if not xs:
            continue
        ax.plot(
            xs,
            ys,
            color=COLORS[model],
            marker=MARKERS[model],
            linewidth=1.8,
            markersize=4.5,
            alpha=0.95,
        )
    ax.set_xticks(horizons)
    ax.set_xticklabels([str(h) for h in horizons], rotation=0)


def add_panel_legend(ax, models, ncol):
    handles = [
        Line2D(
            [0],
            [0],
            color=COLORS[model],
            marker=MARKERS[model],
            linewidth=1.7,
            markersize=4.5,
            label=LABELS[model],
        )
        for model in models
    ]
    ax.legend(
        handles=handles,
        loc="upper left",
        ncol=ncol,
        frameon=False,
        fontsize=7.6,
        handlelength=1.8,
        columnspacing=0.9,
        borderaxespad=0.3,
    )


def main():
    baseline = index_rows(load_rows(BASELINE_CSV, "model"), "rmsse")
    hpo = index_rows(load_rows(MAMBA_OPTUNA_CSV, "model"), "rmsse")
    baseline_frontier = {
        model: baseline[model]
        for model in FRONTIER_MODELS
        if model in baseline
    }

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.35), constrained_layout=True)

    plot_panel(
        axes[0],
        baseline_frontier,
        list(baseline_frontier.keys()),
        HORIZONS,
        "A. Optuna baseline RMSSE",
        "RMSSE",
    )
    axes[0].set_xlabel("Horizon (days)")
    add_panel_legend(axes[0], list(baseline_frontier.keys()), ncol=2)

    plot_panel(axes[1], hpo, MAMBA_MODELS, HORIZONS, "B. Mamba Optuna RMSSE", "RMSSE")
    axes[1].set_xlabel("Horizon (days)")
    add_panel_legend(axes[1], MAMBA_MODELS, ncol=2)

    fig.savefig(FIG_PDF, dpi=300, bbox_inches="tight")
    fig.savefig(FIG_PNG, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"wrote {FIG_PDF}")
    print(f"wrote {FIG_PNG}")


if __name__ == "__main__":
    main()
