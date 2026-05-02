#!/usr/bin/env python
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_CSV = REPO_ROOT / "results" / "gld_baselines.csv"
OPT_CSV = REPO_ROOT / "results" / "gld_source_optimized_best.csv"
MAMBA_HPO_CSV = REPO_ROOT / "results" / "gld_mamba_hpo_best.csv"

FIG_PDF = REPO_ROOT / "manuscript" / "figures" / "gld_result_overview.pdf"
FIG_PNG = REPO_ROOT / "manuscript" / "figures" / "gld_result_overview.png"
OUT_TEX = REPO_ROOT / "manuscript" / "generated" / "gld_complete_metrics_figure.tex"

HORIZONS = [1, 3, 5, 7, 14, 30, 60, 90, 120, 180, 270, 360]
DIAG_HORIZONS = [30, 120, 180, 360]

SHARED_MODELS = [
    "S_Mamba",
    "iTransformer",
    "Autoformer",
    "Transformer",
    "Informer",
    "Reformer",
]
OPT_MODELS = [
    "PatchTST",
    "NLinear",
    "TimesNet",
    "Nonstationary_Transformer",
    "DLinear",
]
MAMBA_MODELS = [
    "MS_Mamba-MD",
    "MS_Mamba-MDG",
    "NS_Mamba-D",
    "S_Mamba",
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


def build_figure():
    shared = index_rows(load_rows(BASELINE_CSV, "model"))
    opt = index_rows(load_rows(OPT_CSV, "model"))
    hpo = index_rows(load_rows(MAMBA_HPO_CSV, "variant"))

    fig, axes = plt.subplots(3, 1, figsize=(8.4, 10.2), constrained_layout=True)

    plot_panel(
        axes[0],
        shared,
        SHARED_MODELS,
        HORIZONS,
        "A. Shared locked-setting baselines",
    )
    plot_panel(
        axes[1],
        opt,
        OPT_MODELS,
        HORIZONS,
        "B. Source-optimized imported baselines",
    )
    plot_panel(
        axes[2],
        hpo,
        MAMBA_MODELS,
        DIAG_HORIZONS,
        "C. Mamba-family best HPO rows on completed diagnostic horizons",
    )
    axes[2].set_xlabel("Forecast horizon (days)")

    legend_items = []
    for model in SHARED_MODELS + OPT_MODELS + MAMBA_MODELS:
        if model in {item.get_label() for item in legend_items}:
            continue
        legend_items.append(
            Line2D(
                [0],
                [0],
                color=COLORS[model],
                marker=MARKERS[model],
                linewidth=1.8,
                markersize=5,
                label=LABELS[model],
            )
        )

    fig.legend(
        handles=legend_items,
        loc="upper center",
        ncol=4,
        frameon=False,
        fontsize=8.5,
        bbox_to_anchor=(0.5, 1.01),
    )

    FIG_PDF.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_PDF, dpi=300, bbox_inches="tight")
    fig.savefig(FIG_PNG, dpi=300, bbox_inches="tight")
    plt.close(fig)


def build_tex():
    lines = []
    lines.append(r"\subsection{Completed Result Overview}")
    lines.append("")
    lines.append(
        r"Figure~\ref{fig:gld-result-overview} replaces the oversized full-results table with a compact visual summary of the completed GLD comparisons."
    )
    lines.append(
        r"Panel A shows the shared locked-setting baselines, Panel B shows the source-optimized imported baselines, and Panel C shows the best completed Mamba-HPO variants."
    )
    lines.append(
        r"All curves are plotted on the original GLD price scale using RMSE. The complete machine-readable records remain available in the result CSV files under \texttt{results/}."
    )
    lines.append("")
    lines.append(r"\begin{figure}[t]")
    lines.append(r"\centering")
    lines.append(r"\includegraphics[width=\linewidth]{figures/gld_result_overview.pdf}")
    lines.append(
        r"\caption{Completed GLD RMSE comparison across the three main evaluation tracks. Panel A: shared locked-setting baselines over all 12 horizons. Panel B: source-optimized imported baselines over all 12 horizons. Panel C: best completed Mamba-HPO variants over the currently completed diagnostic horizons 30, 120, 180, and 360 days. The figure makes the main ranking structure visible without the space cost of a full longtable.}"
    )
    lines.append(r"\label{fig:gld-result-overview}")
    lines.append(r"\end{figure}")
    lines.append("")
    return "\n".join(lines) + "\n"


def main():
    build_figure()
    OUT_TEX.parent.mkdir(parents=True, exist_ok=True)
    OUT_TEX.write_text(build_tex())
    print(f"wrote {FIG_PDF.relative_to(REPO_ROOT)}")
    print(f"wrote {FIG_PNG.relative_to(REPO_ROOT)}")
    print(f"wrote {OUT_TEX.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
