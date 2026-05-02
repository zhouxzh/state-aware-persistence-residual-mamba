#!/usr/bin/env python
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


FIG_DIR = Path(__file__).resolve().parent
BASELINE_CSV = FIG_DIR / "gld_baselines.csv"
OPT_CSV = FIG_DIR / "gld_source_optimized_best.csv"
MAMBA_HPO_CSV = FIG_DIR / "gld_mamba_hpo_best.csv"
FIG_PDF = FIG_DIR / "gld_result_overview.pdf"
FIG_PNG = FIG_DIR / "gld_result_overview.png"

HORIZONS = [1, 3, 5, 7, 14, 30, 60, 90, 120, 180, 270, 360]
DIAG_HORIZONS = [30, 120, 180, 360]

FRONTIER_MODELS = [
    "PatchTST",
    "NLinear",
    "TimesNet",
    "S_Mamba",
    "iTransformer",
    "MS_Mamba-MD",
]
MAMBA_MODELS = [
    "NS_Mamba-D",
    "MS_Mamba-MD",
    "MS_Mamba-MDG",
    "MS_Mamba-MDS",
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
                }
            )
    return rows


def index_rows(rows):
    indexed = defaultdict(dict)
    for row in rows:
        indexed[row["name"]][row["horizon"]] = row["rmse"]
    return indexed


def style_axes(ax, title):
    ax.set_title(title, fontsize=10, loc="left")
    ax.set_xscale("linear")
    ax.set_yscale("log")
    ax.grid(True, which="major", axis="both", color="#d1d5db", linewidth=0.7, alpha=0.8)
    ax.grid(True, which="minor", axis="y", color="#e5e7eb", linewidth=0.5, alpha=0.5)
    ax.set_ylabel("RMSE")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def plot_panel(ax, indexed, models, horizons, title):
    style_axes(ax, title)
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
    shared = index_rows(load_rows(BASELINE_CSV, "model"))
    opt = index_rows(load_rows(OPT_CSV, "model"))
    hpo = index_rows(load_rows(MAMBA_HPO_CSV, "variant"))

    frontier = {}
    for model in FRONTIER_MODELS:
        if model in shared:
            frontier[model] = shared[model]
        elif model in opt:
            frontier[model] = opt[model]
        elif model in hpo:
            frontier[model] = hpo[model]

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.35), constrained_layout=True)

    plot_panel(
        axes[0],
        frontier,
        FRONTIER_MODELS,
        HORIZONS,
        "A. Best overall model frontier",
    )
    axes[0].set_xlabel("Horizon (days)")
    add_panel_legend(axes[0], FRONTIER_MODELS, ncol=2)

    plot_panel(
        axes[1],
        hpo,
        MAMBA_MODELS,
        DIAG_HORIZONS,
        "B. Mamba-family variants",
    )
    axes[1].set_xlabel("Horizon (days)")
    add_panel_legend(axes[1], MAMBA_MODELS, ncol=2)

    fig.savefig(FIG_PDF, dpi=300, bbox_inches="tight")
    fig.savefig(FIG_PNG, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"wrote {FIG_PDF}")
    print(f"wrote {FIG_PNG}")


if __name__ == "__main__":
    main()
