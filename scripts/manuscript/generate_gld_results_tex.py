#!/usr/bin/env python
import csv
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = REPO_ROOT / "results" / "gld_baselines.csv"
OUT_DIR = REPO_ROOT / "manuscript" / "generated"
OUT_PATH = OUT_DIR / "gld_baseline_results.tex"

CORE_MODELS = ["S_Mamba", "iTransformer", "Autoformer", "Transformer", "Informer", "Reformer"]
HORIZONS = [1, 3, 5, 7, 14, 30, 60, 90, 120, 180, 270, 360]
TERMS = ["short", "middle", "long"]


def load_rows():
    with CSV_PATH.open() as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["horizon"] = int(row["horizon"])
        row["rmse"] = float(row["rmse"])
        row["mae"] = float(row["mae"])
    return rows


def latex_escape(text):
    return text.replace("_", r"\_")


def avg(values):
    return sum(values) / len(values)


def build_tables(rows):
    horizon_winners = []
    for horizon in HORIZONS:
        horizon_rows = sorted(
            [row for row in rows if row["horizon"] == horizon],
            key=lambda row: row["rmse"],
        )
        best = horizon_rows[0]
        runner_up = horizon_rows[1]
        horizon_winners.append((horizon, best, runner_up))

    term_avgs = defaultdict(dict)
    overall_avgs = {}
    for model in CORE_MODELS:
        model_rows = [row for row in rows if row["model"] == model]
        overall_avgs[model] = avg([row["rmse"] for row in model_rows])
        for term in TERMS:
            term_rows = [row for row in model_rows if row["term"] == term]
            term_avgs[model][term] = avg([row["rmse"] for row in term_rows])

    return horizon_winners, term_avgs, overall_avgs


def build_summary(rows, horizon_winners, term_avgs, overall_avgs):
    winner_counts = defaultdict(int)
    for _, best, _ in horizon_winners:
        winner_counts[best["model"]] += 1

    s_mamba = [row for row in rows if row["model"] == "S_Mamba"]
    itransformer = [row for row in rows if row["model"] == "iTransformer"]
    autoformer = [row for row in rows if row["model"] == "Autoformer"]

    s_mamba_avg_rmse = avg([row["rmse"] for row in s_mamba])
    s_mamba_avg_mae = avg([row["mae"] for row in s_mamba])
    itransformer_avg_rmse = avg([row["rmse"] for row in itransformer])
    itransformer_avg_mae = avg([row["mae"] for row in itransformer])
    autoformer_avg_rmse = avg([row["rmse"] for row in autoformer])

    h120_sm = next(row for row in rows if row["model"] == "S_Mamba" and row["horizon"] == 120)
    h120_it = next(row for row in rows if row["model"] == "iTransformer" and row["horizon"] == 120)
    h360_sm = next(row for row in rows if row["model"] == "S_Mamba" and row["horizon"] == 360)
    h360_it = next(row for row in rows if row["model"] == "iTransformer" and row["horizon"] == 360)
    h120_gap = (h120_sm["rmse"] - h120_it["rmse"]) / h120_sm["rmse"] * 100
    h360_gap = (h360_sm["rmse"] - h360_it["rmse"]) / h360_sm["rmse"] * 100

    lines = []
    lines.append(
        "The GLD baseline evaluation is complete under the locked shared setting."
    )
    lines.append(
        "All 72 runs finished successfully, corresponding to 6 core models evaluated across 12 horizons."
    )
    lines.append(
        r"The machine-readable result table is stored in \texttt{results/gld\_baselines.csv}."
    )
    lines.append("")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(
        r"\caption{Best and second-best GLD baseline models by horizon, measured with RMSE.}"
    )
    lines.append(r"\label{tab:gld-horizon-winners}")
    lines.append(r"\small")
    lines.append(r"\begin{tabular}{r l r l r}")
    lines.append(r"\toprule")
    lines.append(r"Horizon & Best model & RMSE & Runner-up & RMSE \\")
    lines.append(r"\midrule")
    for horizon, best, runner_up in horizon_winners:
        lines.append(
            f"{horizon} & {latex_escape(best['model'])} & {best['rmse']:.2f} & "
            f"{latex_escape(runner_up['model'])} & {runner_up['rmse']:.2f} \\\\"
        )
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    lines.append("")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(
        r"\caption{Average GLD baseline RMSE grouped by forecast range. Short = 1--7 days, middle = 14--120 days, long = 180--360 days.}"
    )
    lines.append(r"\label{tab:gld-term-avg}")
    lines.append(r"\small")
    lines.append(r"\begin{tabular}{lrrrr}")
    lines.append(r"\toprule")
    lines.append(
        r"Model & Short Avg. RMSE & Middle Avg. RMSE & Long Avg. RMSE & Overall Avg. RMSE \\"
    )
    lines.append(r"\midrule")
    for model in CORE_MODELS:
        lines.append(
            f"{latex_escape(model)} & {term_avgs[model]['short']:.2f} & "
            f"{term_avgs[model]['middle']:.2f} & {term_avgs[model]['long']:.2f} & "
            f"{overall_avgs[model]:.2f} \\\\"
        )
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    lines.append("")
    lines.append("The main pattern is a two-model regime.")
    lines.append(
        f"S\\_Mamba is the strongest RMSE baseline for {winner_counts['S_Mamba']} horizons, covering every horizon from 1 to 90 days, while iTransformer is strongest for the remaining {winner_counts['iTransformer']} horizons from 120 to 360 days."
    )
    lines.append(
        f"The handover is narrow rather than abrupt: at 120 days the RMSE gap is about {h120_gap:.2f}\\% in favor of iTransformer, while at 360 days the gap is only about {h360_gap:.2f}\\%."
    )
    lines.append(
        "This means the long-horizon comparison between the two models is highly competitive rather than dominated by one side."
    )
    lines.append("")
    lines.append(
        "Autoformer is a stable third-place baseline across all 12 horizons."
    )
    lines.append(
        f"However, its overall average RMSE of {autoformer_avg_rmse:.2f} is far above the two leading models, whose overall average RMSE values are {s_mamba_avg_rmse:.2f} for S\\_Mamba and {itransformer_avg_rmse:.2f} for iTransformer."
    )
    lines.append(
        "The plain attention baselines are substantially weaker on GLD under the locked shared setting, with overall average RMSE above 69 for Transformer and above 76 for Informer and Reformer."
    )
    lines.append("")
    lines.append("The MAE pattern is similar.")
    lines.append(
        f"S\\_Mamba and iTransformer remain nearly tied overall, and S\\_Mamba holds a slightly lower average MAE, {s_mamba_avg_mae:.2f} versus {itransformer_avg_mae:.2f}."
    )
    lines.append(
        "These baseline results identify S\\_Mamba and iTransformer as the two reference models that NS-Mamba must improve upon."
    )
    return "\n".join(lines) + "\n"


def main():
    rows = load_rows()
    complete_rows = [row for row in rows if row["status"] == "complete"]
    if len(complete_rows) != len(rows):
        raise SystemExit(
            f"expected all rows to be complete, got {len(complete_rows)}/{len(rows)}"
        )
    horizon_winners, term_avgs, overall_avgs = build_tables(rows)
    content = build_summary(rows, horizon_winners, term_avgs, overall_avgs)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(content)
    print(f"wrote {OUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
