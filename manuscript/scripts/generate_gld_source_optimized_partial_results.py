#!/usr/bin/env python
import csv
from collections import defaultdict
from pathlib import Path


MANUSCRIPT_ROOT = Path(__file__).resolve().parents[1]
ALL_CSV = MANUSCRIPT_ROOT / "data" / "gld_source_optimized_all.csv"
BEST_CSV = MANUSCRIPT_ROOT / "data" / "gld_source_optimized_best.csv"
BASELINE_CSV = MANUSCRIPT_ROOT / "data" / "gld_baselines.csv"
OUT_PATH = MANUSCRIPT_ROOT / "sections" / "results_source_optimized.tex"

MODELS = ["PatchTST", "NLinear", "TimesNet", "Nonstationary_Transformer", "DLinear"]
HORIZONS = [1, 3, 5, 7, 14, 30, 60, 90, 120, 180, 270, 360]


def load_rows(path):
    rows = []
    with path.open() as f:
        for row in csv.DictReader(f):
            if row.get("status") != "complete":
                continue
            parsed = row.copy()
            for key in ("horizon", "seq_len"):
                if key in parsed and parsed[key] != "":
                    parsed[key] = int(parsed[key])
            for key in ("rmse", "mae"):
                if key in parsed and parsed[key] != "":
                    parsed[key] = float(parsed[key])
            rows.append(parsed)
    return rows


def display_model(name):
    mapping = {"Nonstationary_Transformer": "Non-stationary Transformer"}
    return mapping.get(name, name)


def avg(values):
    return sum(values) / len(values)


def build_tex():
    all_rows = load_rows(ALL_CSV)
    best_rows = load_rows(BEST_CSV)
    baseline_rows = load_rows(BASELINE_CSV)

    baseline_best = {}
    for horizon in HORIZONS:
        candidates = [row for row in baseline_rows if row["horizon"] == horizon]
        baseline_best[horizon] = min(candidates, key=lambda row: row["rmse"])

    coverage = {}
    for model in MODELS:
        model_all = [row for row in all_rows if row["model"] == model]
        model_best = [row for row in best_rows if row["model"] == model]
        coverage[model] = {
            "sweep_rows": len(model_all),
            "best_rows": len(model_best),
            "max_horizon": max((row["horizon"] for row in model_best), default=0),
        }

    winners = []
    for horizon in HORIZONS:
        candidates = [row for row in best_rows if row["horizon"] == horizon]
        winners.append(min(candidates, key=lambda row: row["rmse"]))

    by_model = defaultdict(list)
    for row in best_rows:
        by_model[row["model"]].append(row)

    lines = []
    lines.append(r"\subsection{Source-Optimized Imported Baselines}")
    lines.append("")
    lines.append(
        r"We also ran a separate source-style optimized sweep for imported comparison models using the hyperparameter ranges from the moved \texttt{nonstationary\_transformer/scripts/GLD.sh} workflow."
    )
    lines.append(
        r"This sweep is intentionally different from the locked shared-setting baseline table because it uses model-specific hyperparameters and a sequence-length sweep."
    )
    lines.append(
        r"At the current stage, the optimized sweep is complete for the five imported models Non-stationary Transformer, TimesNet, PatchTST, DLinear, and NLinear."
    )
    lines.append("")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(
        r"\caption{Completed source-optimized GLD coverage for the imported models. Autoformer and Transformer source-style sweeps are still pending.}"
    )
    lines.append(r"\label{tab:gld-source-optimized-partial}")
    lines.append(r"\small")
    lines.append(r"\begin{tabular}{lrrr}")
    lines.append(r"\toprule")
    lines.append(r"Model & Sweep rows & Best rows & Max horizon \\")
    lines.append(r"\midrule")
    for model in ["PatchTST", "NLinear", "TimesNet", "Nonstationary_Transformer", "DLinear"]:
        row = coverage[model]
        lines.append(
            f"{display_model(model)} & {row['sweep_rows']} & {row['best_rows']} & {row['max_horizon']} \\\\"
        )
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    lines.append("")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(
        r"\caption{Best completed source-optimized imported results by horizon, measured with RMSE and paired with MAE.}"
    )
    lines.append(r"\label{tab:gld-source-optimized-best}")
    lines.append(r"\small")
    lines.append(r"\begin{tabular}{r l r r r}")
    lines.append(r"\toprule")
    lines.append(r"Horizon & Winner & Best seq\_len & RMSE & MAE \\")
    lines.append(r"\midrule")
    for row in winners:
        lines.append(
            f"{row['horizon']} & {display_model(row['model'])} & {row['seq_len']} & {row['rmse']:.2f} & {row['mae']:.2f} \\\\"
        )
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    lines.append("")

    lines.append("The completed optimized imported sweep changes the comparison picture substantially.")
    lines.append("NLinear is the strongest imported model on the short horizons from 1 to 14 days.")
    lines.append("TimesNet is strongest at 30 and 90 days.")
    lines.append("PatchTST is strongest from 60 days onward except for 90 days, and it is the best imported model overall under the completed optimized sweep.")
    lines.append("")
    lines.append("The best lookback pattern also depends strongly on the model.")
    lines.append("NLinear prefers very large windows from 192 to 384.")
    lines.append("PatchTST prefers 16 on short horizons, then 256 to 320 at middle horizons, and 128 at 270 and 360 days.")
    lines.append("TimesNet prefers 16 on short horizons and much larger windows at middle and long horizons.")
    lines.append("Non-stationary Transformer still prefers mostly 16, which appears too short for strong long-horizon GLD performance.")
    lines.append("")

    nlinear_1 = next(row for row in winners if row["horizon"] == 1)
    timesnet_90 = next(row for row in winners if row["horizon"] == 90)
    patch_120 = next(row for row in winners if row["horizon"] == 120)
    patch_360 = next(row for row in winners if row["horizon"] == 360)
    lines.append(
        "Compared with the best locked-setting baseline at each completed horizon, the optimized imported baselines are substantially stronger except for DLinear."
    )
    lines.append(
        f"For example, optimized NLinear reduces RMSE by {(baseline_best[1]['rmse'] - nlinear_1['rmse']) / baseline_best[1]['rmse'] * 100:.2f}\\% at 1 day, "
        f"optimized TimesNet reduces RMSE by {(baseline_best[90]['rmse'] - timesnet_90['rmse']) / baseline_best[90]['rmse'] * 100:.2f}\\% at 90 days, "
        f"optimized PatchTST reduces RMSE by {(baseline_best[120]['rmse'] - patch_120['rmse']) / baseline_best[120]['rmse'] * 100:.2f}\\% at 120 days, "
        f"and optimized PatchTST reduces RMSE by {(baseline_best[360]['rmse'] - patch_360['rmse']) / baseline_best[360]['rmse'] * 100:.2f}\\% at 360 days."
    )
    lines.append(
        "DLinear is weaker than the best locked-setting baseline at every horizon, while Non-stationary Transformer is competitive at short horizons but no longer competitive with the strongest imported models once the full optimized sweep is complete."
    )
    lines.append("")
    return "\n".join(lines)


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(build_tex() + "\n")
    print(f"wrote {OUT_PATH.relative_to(MANUSCRIPT_ROOT)}")


if __name__ == "__main__":
    main()
