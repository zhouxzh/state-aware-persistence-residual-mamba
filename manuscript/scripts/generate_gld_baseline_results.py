#!/usr/bin/env python
import csv
import json
import shutil
from collections import defaultdict
from pathlib import Path


MANUSCRIPT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = MANUSCRIPT_ROOT.parent
SOURCE_BEST_CSV = REPO_ROOT / "results" / "gld_baseline_optuna_best.csv"
SOURCE_PARAMS_JSON = REPO_ROOT / "results" / "optuna" / "gld" / "baseline_best_params.json"
DATA_DIR = MANUSCRIPT_ROOT / "data"
CSV_PATH = DATA_DIR / "gld_baseline_optuna_best.csv"
PARAMS_CSV_PATH = DATA_DIR / "gld_baseline_optuna_hyperparameters.csv"
OUT_DIR = MANUSCRIPT_ROOT / "sections"
OUT_PATH = OUT_DIR / "results_baselines.tex"

CORE_MODELS = [
    "TimesNet",
    "iTransformer",
    "PatchTST",
    "NLinear",
    "Autoformer",
    "DLinear",
    "Nonstationary_Transformer",
    "Transformer",
    "Reformer",
    "Informer",
]
HORIZONS = [1, 3, 5, 7, 14, 30, 60, 90, 120, 180, 270, 360]
TERMS = ["short", "middle", "long"]


def load_rows():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE_BEST_CSV, CSV_PATH)
    with CSV_PATH.open() as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["horizon"] = int(row["horizon"])
        row["rmse"] = float(row["rmse"])
        row["mae"] = float(row["mae"])
        row["rmsse"] = float(row["rmsse"])
        row["mse"] = float(row["mse"])
        row["overall_balanced_rmsse"] = float(row["overall_balanced_rmsse"])
        row["short_avg_rmsse"] = float(row["short_avg_rmsse"])
        row["middle_avg_rmsse"] = float(row["middle_avg_rmsse"])
        row["long_avg_rmsse"] = float(row["long_avg_rmsse"])
        row["short_avg_rmse"] = float(row["short_avg_rmse"])
        row["middle_avg_rmse"] = float(row["middle_avg_rmse"])
        row["long_avg_rmse"] = float(row["long_avg_rmse"])
        row["overall_avg_rmse"] = float(row["overall_avg_rmse"])
        row["overall_avg_mae"] = float(row["overall_avg_mae"])
    return rows


def latex_escape(text):
    return text.replace("_", r"\_")


def display_model(text):
    mapping = {
        "S_Mamba": "S-Mamba",
        "Nonstationary_Transformer": "Non-stationary Transformer",
    }
    return mapping.get(text, latex_escape(text))


def avg(values):
    return sum(values) / len(values)


def params_compact(params):
    ordered = [
        "seq_len",
        "batch_size",
        "learning_rate",
        "d_model",
        "d_ff",
        "factor",
        "moving_avg",
        "individual",
        "patch_len",
        "stride",
        "top_k",
        "num_kernels",
        "use_norm",
        "p_hidden_layers",
        "p_hidden_dims",
    ]
    parts = []
    for key in ordered:
        if key not in params:
            continue
        value = params[key]
        if isinstance(value, list):
            value = "[" + ",".join(str(item) for item in value) + "]"
        elif isinstance(value, bool):
            value = str(value).lower()
        parts.append(f"{key}={value}")
    return ", ".join(parts)


def write_hyperparameter_table():
    with SOURCE_PARAMS_JSON.open() as f:
        payload = json.load(f)

    rows = []
    for model in CORE_MODELS:
        info = payload["models"][model]
        rows.append(
            {
                "model": model,
                "study_name": info["study_name"],
                "trial_number": info["best_validation_replay_trial"],
                "val_balanced_rmsse": f"{info['best_validation_replay_balanced_rmsse']:.12g}",
                "test_balanced_rmsse": f"{info['final_test_balanced_rmsse']:.12g}",
                "params_json": json.dumps(info["params"], sort_keys=True),
                "params_compact": params_compact(info["params"]),
            }
        )

    fieldnames = [
        "model",
        "study_name",
        "trial_number",
        "val_balanced_rmsse",
        "test_balanced_rmsse",
        "params_json",
        "params_compact",
    ]
    with PARAMS_CSV_PATH.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return rows, payload


def build_tables(rows):
    horizon_winners = []
    for horizon in HORIZONS:
        horizon_rows = sorted(
            [row for row in rows if row["horizon"] == horizon],
            key=lambda row: row["rmsse"],
        )
        best = horizon_rows[0]
        runner_up = horizon_rows[1]
        horizon_winners.append((horizon, best, runner_up))

    term_avgs = defaultdict(dict)
    overall_avgs = {}
    for model in CORE_MODELS:
        model_rows = [row for row in rows if row["model"] == model]
        overall_avgs[model] = {
            "rmse": model_rows[0]["overall_avg_rmse"],
            "mae": model_rows[0]["overall_avg_mae"],
            "rmsse": model_rows[0]["overall_balanced_rmsse"],
        }
        for term in TERMS:
            term_avgs[model][term] = {
                "rmse": model_rows[0][f"{term}_avg_rmse"],
                "rmsse": model_rows[0][f"{term}_avg_rmsse"],
            }

    return horizon_winners, term_avgs, overall_avgs


def build_summary(rows, horizon_winners, term_avgs, overall_avgs, param_rows, payload):
    winner_counts = defaultdict(int)
    for _, best, _ in horizon_winners:
        winner_counts[best["model"]] += 1

    ranked_models = sorted(CORE_MODELS, key=lambda model: overall_avgs[model]["rmsse"])
    best_model = ranked_models[0]
    runner_up_model = ranked_models[1]
    third = ranked_models[2]
    gap = overall_avgs[runner_up_model]["rmsse"] - overall_avgs[best_model]["rmsse"]
    gap_pct = gap / overall_avgs[best_model]["rmsse"] * 100

    lines = []
    lines.append(
        "The refreshed Optuna baseline sweep is complete for ten non-Mamba baseline models."
    )
    lines.append(
        "Each model was tuned with 20 Optuna trials using the full 12-horizon validation objective, then replayed on the full validation horizon set and evaluated once on the held-out test split."
    )
    lines.append(
        r"The machine-readable result tables are bundled in \texttt{manuscript/data/gld\_baseline\_optuna\_best.csv} and \texttt{manuscript/data/gld\_baseline\_optuna\_hyperparameters.csv}."
    )
    lines.append("")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(
        r"\caption{Best and second-best Optuna-tuned GLD baseline models by horizon, measured with test RMSSE. RMSE and MAE are shown for the best model at each horizon.}"
    )
    lines.append(r"\label{tab:gld-horizon-winners}")
    lines.append(r"\small")
    lines.append(r"\begin{tabular}{r l r r r l r}")
    lines.append(r"\toprule")
    lines.append(r"Horizon & Best model & RMSSE & RMSE & MAE & Runner-up & RMSSE \\")
    lines.append(r"\midrule")
    for horizon, best, runner_up in horizon_winners:
        lines.append(
            f"{horizon} & {display_model(best['model'])} & {best['rmsse']:.2f} & "
            f"{best['rmse']:.2f} & {best['mae']:.2f} & "
            f"{display_model(runner_up['model'])} & {runner_up['rmsse']:.2f} \\\\"
        )
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    lines.append("")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(
        r"\caption{Optuna-tuned GLD baseline summary grouped by forecast range. Short = 1--7 days, middle = 14--90 days, long = 120--360 days. Lower RMSSE is better.}"
    )
    lines.append(r"\label{tab:gld-term-avg}")
    lines.append(r"\small")
    lines.append(r"\begin{tabular}{lrrrrr}")
    lines.append(r"\toprule")
    lines.append(
        r"Model & Short RMSSE & Middle RMSSE & Long RMSSE & Overall RMSSE & Overall RMSE \\"
    )
    lines.append(r"\midrule")
    for model in ranked_models:
        lines.append(
            f"{display_model(model)} & {term_avgs[model]['short']['rmsse']:.2f} & "
            f"{term_avgs[model]['middle']['rmsse']:.2f} & {term_avgs[model]['long']['rmsse']:.2f} & "
            f"{overall_avgs[model]['rmsse']:.2f} & {overall_avgs[model]['rmse']:.2f} \\\\"
        )
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    lines.append("")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(
        r"\caption{Selected Optuna hyperparameters used to reproduce the reported GLD baseline rows. All selected configurations use the study suffix \texttt{fullcal\_v1}.}"
    )
    lines.append(r"\label{tab:gld-baseline-optuna-hparams}")
    lines.append(r"\scriptsize")
    lines.append(r"\resizebox{\linewidth}{!}{%")
    lines.append(r"\begin{tabular}{lrrrl}")
    lines.append(r"\toprule")
    lines.append(r"Model & Trial & Test RMSSE & Val RMSSE & Selected hyperparameters \\")
    lines.append(r"\midrule")
    for row in param_rows:
        lines.append(
            f"{display_model(row['model'])} & {row['trial_number']} & "
            f"{float(row['test_balanced_rmsse']):.2f} & {float(row['val_balanced_rmsse']):.2f} & "
            r"\texttt{" + latex_escape(row["params_compact"]) + r"} \\"
        )
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"}")
    lines.append(r"\end{table}")
    lines.append("")
    lines.append(
        f"{display_model(best_model)} is the strongest Optuna-tuned baseline overall, with balanced test RMSSE {overall_avgs[best_model]['rmsse']:.2f}."
    )
    lines.append(
        f"{display_model(runner_up_model)} is effectively tied for first, trailing by only {gap:.2f} RMSSE points ({gap_pct:.2f}\\%), while {display_model(third)} is third with balanced test RMSSE {overall_avgs[third]['rmsse']:.2f}."
    )
    lines.append(
        f"The horizon-level winners show a regime split: NLinear is strongest at 1, 3, and 7 days; Non-stationary Transformer is strongest at 5 days; PatchTST leads at 14, 30, and 90 days; TimesNet leads at 60, 120, and 180 days; and iTransformer leads at 270 and 360 days."
    )
    lines.append("")
    lines.append(
        "The plain Transformer, Reformer, and Informer configurations remain far weaker on the held-out test split despite low validation objectives for some trials."
    )
    lines.append(
        "This validation-to-test mismatch is why the manuscript reports final test RMSSE and keeps the selected hyperparameters visible for exact reproduction."
    )
    return "\n".join(lines) + "\n"


def main():
    rows = load_rows()
    complete_rows = [row for row in rows if row["status"] == "complete"]
    if len(complete_rows) != len(rows):
        raise SystemExit(
            f"expected all rows to be complete, got {len(complete_rows)}/{len(rows)}"
        )
    expected = len(CORE_MODELS) * len(HORIZONS)
    if len(rows) != expected:
        raise SystemExit(f"expected {expected} rows, got {len(rows)}")
    param_rows, payload = write_hyperparameter_table()
    horizon_winners, term_avgs, overall_avgs = build_tables(rows)
    content = build_summary(rows, horizon_winners, term_avgs, overall_avgs, param_rows, payload)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(content)
    print(f"wrote {OUT_PATH.relative_to(MANUSCRIPT_ROOT)}")
    print(f"wrote {CSV_PATH.relative_to(MANUSCRIPT_ROOT)}")
    print(f"wrote {PARAMS_CSV_PATH.relative_to(MANUSCRIPT_ROOT)}")


if __name__ == "__main__":
    main()
