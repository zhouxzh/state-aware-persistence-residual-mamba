#!/usr/bin/env python
"""Generate evidence-bound figures used by the repository documentation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = REPO_ROOT / "reproducibility" / "nonstationary_analysis_v1" / "final" / "aggregate_metrics.csv"
OUTPUT_ROOT = REPO_ROOT / "docs" / "figures"
PMS_MODEL = "PMS_Mamba-PD"
TERM_MAP = {1: "Short", 5: "Short", 20: "Middle", 60: "Middle", 120: "Long", 252: "Long"}
FAMILY_ORDER = ("cross_asset", "crypto", "fx", "yields")
TERM_ORDER = ("Short", "Middle", "Long")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def task_label(task: str) -> str:
    return task.removeprefix("financial_").replace("_", " ").upper()


def build_tables(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = frame.copy()
    frame["term"] = frame["horizon"].map(TERM_MAP)
    if frame["term"].isna().any():
        raise ValueError("Unexpected horizon in frozen aggregate metrics")

    term_scores = (
        frame.groupby(["dataset", "model", "term"], as_index=False)["path_rmsse_mean"]
        .mean()
    )
    balanced = (
        term_scores.groupby(["dataset", "model"], as_index=False)["path_rmsse_mean"]
        .mean()
        .rename(columns={"path_rmsse_mean": "balanced_path_rmsse"})
    )
    task_rows = []
    for task, group in balanced.groupby("dataset", sort=False):
        pms = group[group["model"] == PMS_MODEL]
        if len(pms) != 1:
            raise ValueError(f"Expected one PMS row for {task}")
        ordered = group.sort_values(["balanced_path_rmsse", "model"]).reset_index(drop=True)
        pms_score = float(pms.iloc[0]["balanced_path_rmsse"])
        winner = ordered.iloc[0]
        task_rows.append({
            "dataset": task,
            "family": task.removeprefix("financial_").removesuffix("_ms").removesuffix("_s"),
            "mode": "MS" if task.endswith("_ms") else "S",
            "pms_balanced_path_rmsse": pms_score,
            "winner": winner["model"],
            "winner_balanced_path_rmsse": float(winner["balanced_path_rmsse"]),
            "pms_rank": int(ordered.index[ordered["model"] == PMS_MODEL][0] + 1),
            "model_count": int(len(ordered)),
            "gap_to_winner_pct": 100.0 * (
                pms_score - float(winner["balanced_path_rmsse"])
            ) / float(winner["balanced_path_rmsse"]),
        })
    task_summary = pd.DataFrame(task_rows)
    task_summary["family_order"] = task_summary["family"].map(
        {family: index for index, family in enumerate(FAMILY_ORDER)}
    )
    task_summary["mode_order"] = task_summary["mode"].map({"MS": 0, "S": 1})
    task_summary = task_summary.sort_values(["family_order", "mode_order"]).drop(
        columns=["family_order", "mode_order"]
    )

    cell_rows = []
    for (task, horizon), group in frame.groupby(["dataset", "horizon"], sort=False):
        ordered = group.sort_values(["path_rmsse_mean", "model"]).reset_index(drop=True)
        pms = ordered[ordered["model"] == PMS_MODEL]
        if len(pms) != 1:
            raise ValueError(f"Expected one PMS row for {task}/{horizon}")
        pms_score = float(pms.iloc[0]["path_rmsse_mean"])
        winner_score = float(ordered.iloc[0]["path_rmsse_mean"])
        cell_rows.append({
            "dataset": task,
            "horizon": int(horizon),
            "term": TERM_MAP[int(horizon)],
            "pms_path_rmsse": pms_score,
            "winner": ordered.iloc[0]["model"],
            "winner_path_rmsse": winner_score,
            "pms_rank": int(ordered.index[ordered["model"] == PMS_MODEL][0] + 1),
            "gap_to_winner_pct": 100.0 * (pms_score - winner_score) / winner_score,
        })
    cells = pd.DataFrame(cell_rows)
    term_summary = (
        cells.groupby("term")
        .agg(
            cells=("horizon", "size"),
            mean_gap_to_winner_pct=("gap_to_winner_pct", "mean"),
            median_gap_to_winner_pct=("gap_to_winner_pct", "median"),
            within_5pct_of_winner=("gap_to_winner_pct", lambda values: int((values <= 5.0).sum())),
            top3_cells=("pms_rank", lambda values: int((values <= 3).sum())),
        )
        .reindex(TERM_ORDER)
        .reset_index()
    )
    return task_summary, term_summary


def make_figure(task_summary: pd.DataFrame, term_summary: pd.DataFrame) -> tuple[Path, Path]:
    style = {
        "font.family": "DejaVu Sans",
        "font.size": 7.5,
        "axes.labelsize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
    colors = {"MS": "#0072B2", "S": "#D55E00"}
    markers = {"MS": "o", "S": "s"}
    term_colors = {"Short": "#D55E00", "Middle": "#009E73", "Long": "#0072B2"}
    with mpl.rc_context(style):
        fig, (ax_a, ax_b) = plt.subplots(
            1, 2,
            figsize=(180 / 25.4, 84 / 25.4),
            layout="constrained",
            gridspec_kw={"width_ratios": [1.35, 0.85]},
        )
        y = np.arange(len(task_summary))
        for mode in ("MS", "S"):
            subset = task_summary[task_summary["mode"] == mode]
            positions = [task_summary.index.get_loc(index) for index in subset.index]
            ax_a.scatter(
                subset["gap_to_winner_pct"], positions,
                color=colors[mode], marker=markers[mode], s=28,
                edgecolor="white", linewidth=0.4, label=mode, zorder=3,
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
                row["mean_gap_to_winner_pct"], index,
                color=term_colors[row["term"]], marker=("o", "s", "^")[index],
                s=34, edgecolor="white", linewidth=0.4, zorder=3,
            )
            ax_b.text(
                row["mean_gap_to_winner_pct"] + 0.5, index,
                f"within 5%: {int(row['within_5pct_of_winner'])}/{int(row['cells'])}",
                va="center", fontsize=6.8,
            )
        ax_b.axvline(0, color="#333333", linestyle="--", linewidth=0.8)
        ax_b.set_yticks(y_term, term_summary["term"])
        ax_b.invert_yaxis()
        ax_b.set_xlabel("Mean gap to cell winner (%)\nLower is better; zero is best")
        ax_b.grid(axis="x", color="#DDDDDD", linewidth=0.6)
        ax_b.text(-0.17, 1.03, "B", transform=ax_b.transAxes, fontweight="bold", fontsize=9)

        base = OUTPUT_ROOT / "pms_mamba_performance_summary"
        pdf_path = base.with_suffix(".pdf")
        png_path = base.with_suffix(".png")
        fig.savefig(pdf_path, facecolor="white")
        fig.savefig(png_path, dpi=300, facecolor="white")
        plt.close(fig)
    with Image.open(png_path) as image:
        image.convert("RGB").save(png_path, dpi=(300, 300))
    return pdf_path, png_path


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(SOURCE)
    task_summary, term_summary = build_tables(frame)
    task_path = OUTPUT_ROOT / "pms_mamba_task_summary.csv"
    term_path = OUTPUT_ROOT / "pms_mamba_term_summary.csv"
    task_summary.to_csv(task_path, index=False)
    term_summary.to_csv(term_path, index=False)
    pdf_path, png_path = make_figure(task_summary, term_summary)
    manifest = {
        "figure_id": "DOC-FIG-PMS-001",
        "status": "provisional general scientific figure; target journal not specified",
        "source": str(SOURCE.relative_to(REPO_ROOT)),
        "source_sha256": sha256_path(SOURCE),
        "analysis_population": "48 frozen V1 task-horizon cells across eight S/MS tasks",
        "transformations": [
            "task balanced RMSSE is the unweighted mean of short, middle, and long term means",
            "gap percent is 100 * (PMS RMSSE - winner RMSSE) / winner RMSSE",
            "term summaries average the 16 task-horizon gaps in each horizon group",
        ],
        "missing_data": "none in the primary 48-cell matrix",
        "uncertainty": "not shown; figure reports descriptive five-seed means",
        "figure_size_mm": [180, 84],
        "png_dpi": 300,
        "png_mode": "RGB",
        "color_redundancy": "S/MS use color and marker shape; terms use direct labels and marker shape",
        "alt_text": (
            "Two-panel dot plot of PMS-Mamba test performance. Cross-asset tasks have the "
            "smallest task-level gaps among the eight tasks, while FX has the largest. "
            "Middle horizons are closest to cell winners and long horizons have the largest mean gap."
        ),
        "human_review_required": True,
        "outputs": {
            path.name: sha256_path(path)
            for path in (task_path, term_path, pdf_path, png_path)
        },
        "versions": {
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "matplotlib": mpl.__version__,
        },
    }
    manifest_path = OUTPUT_ROOT / "pms_mamba_performance_summary.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote documentation figure and source tables under {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
