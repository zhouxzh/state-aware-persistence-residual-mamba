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
MAMBA_CSV_PATH = DATA_DIR / "gld_mamba_optuna_best.csv"
PARAMS_CSV_PATH = DATA_DIR / "gld_baseline_optuna_hyperparameters.csv"
OUT_DIR = MANUSCRIPT_ROOT / "sections"
OUT_PATH = OUT_DIR / "results_baselines.tex"
APPENDIX_PATH = OUT_DIR / "appendix" / "baseline_optuna_hyperparameters.tex"

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


def parse_result_rows(path):
    with path.open() as f:
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


def load_rows():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE_BEST_CSV, CSV_PATH)
    return parse_result_rows(CSV_PATH)


def load_mamba_rows():
    return parse_result_rows(MAMBA_CSV_PATH)


def latex_escape(text):
    return text.replace("_", r"\_")


def display_model(text):
    mapping = {
        "S_Mamba": "S-Mamba",
        "NS_Mamba-D": "NS-Mamba-D",
        "MS_Mamba-MD": "MS-Mamba-MD",
        "PMS_Mamba-PD": "PMS-Mamba-PD",
        "Nonstationary_Transformer": "Non-stationary Transformer",
    }
    return mapping.get(text, latex_escape(text))


def format_lr(value):
    text = f"{float(value):.0e}"
    mantissa, exponent = text.split("e")
    return f"{int(mantissa)}e{int(exponent)}"


def train_cell(params):
    return f"bs={params['batch_size']}; lr={format_lr(params['learning_rate'])}"


def width_cell(params):
    parts = []
    if "d_model" in params:
        parts.append(f"d\\_model={params['d_model']}")
    if "d_ff" in params:
        parts.append(f"d\\_ff={params['d_ff']}")
    return "; ".join(parts) if parts else "--"


def format_dims(values):
    if not values:
        return ""
    if len(set(values)) == 1:
        return f"{len(values)}x{values[0]}"
    return "x".join(str(value) for value in values)


def baseline_settings_cell(params):
    parts = []
    if "factor" in params:
        parts.append(f"factor={params['factor']}")
    if params.get("moving_avg") is not None:
        parts.append(f"moving avg={params['moving_avg']}")
    if params.get("individual"):
        parts.append("individual")
    if "patch_len" in params:
        parts.append(f"patch={params['patch_len']}")
    if "stride" in params:
        parts.append(f"stride={params['stride']}")
    if "top_k" in params:
        parts.append(f"top-k={params['top_k']}")
    if "num_kernels" in params:
        parts.append(f"kernels={params['num_kernels']}")
    if params.get("use_norm"):
        parts.append("norm")
    if "p_hidden_layers" in params:
        dims = format_dims(params.get("p_hidden_dims", []))
        parts.append(f"projector={dims}" if dims else f"projector layers={params['p_hidden_layers']}")
    return "; ".join(parts) if parts else "--"


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
    return rows


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


def model_summaries(rows, models, track):
    summaries = []
    for model in models:
        model_rows = [
            row for row in rows if row["model"] == model and row["status"] == "complete"
        ]
        if not model_rows:
            continue
        first = sorted(model_rows, key=lambda row: row["horizon"])[0]
        summaries.append(
            {
                "model": model,
                "track": track,
                "short_rmsse": first["short_avg_rmsse"],
                "middle_rmsse": first["middle_avg_rmsse"],
                "long_rmsse": first["long_avg_rmsse"],
                "overall_rmsse": first["overall_balanced_rmsse"],
                "overall_rmse": first["overall_avg_rmse"],
                "overall_mae": first["overall_avg_mae"],
            }
        )
    return summaries


def build_summary(rows, horizon_winners, term_avgs, overall_avgs):
    mamba_rows = load_mamba_rows()
    mamba_models = sorted({row["model"] for row in mamba_rows})
    combined_rows = model_summaries(rows, CORE_MODELS, "Baseline")
    combined_rows += model_summaries(mamba_rows, mamba_models, "Mamba")
    ranked_models = sorted(combined_rows, key=lambda row: row["overall_rmsse"])

    baseline_rows = [row for row in ranked_models if row["track"] == "Baseline"]
    mamba_summary_rows = [row for row in ranked_models if row["track"] == "Mamba"]
    best_overall = ranked_models[0]
    runner_up = ranked_models[1]
    best_baseline = min(baseline_rows, key=lambda row: row["overall_rmsse"])
    best_mamba = min(mamba_summary_rows, key=lambda row: row["overall_rmsse"])
    best_short = min(ranked_models, key=lambda row: row["short_rmsse"])
    best_middle = min(ranked_models, key=lambda row: row["middle_rmsse"])
    best_long = min(ranked_models, key=lambda row: row["long_rmsse"])
    baseline_reduction = (
        (best_baseline["overall_rmsse"] - best_mamba["overall_rmsse"])
        / best_baseline["overall_rmsse"]
        * 100
    )

    lines = []
    lines.append(r"\subsection{Optimized GLD Model Comparison}")
    lines.append("")
    lines.append(
        "The optimized GLD comparison brings the ten Optuna-tuned non-Mamba baseline families and the four completed Mamba-family variants into one test summary."
    )
    lines.append(
        "For each non-Mamba baseline family, 20 Optuna trials were ranked by balanced validation RMSSE over the complete 12-horizon set."
    )
    lines.append(
        "The selected baseline configuration was then replayed on the validation horizons and evaluated once on the held-out test split, yielding 120 complete final baseline test rows."
    )
    lines.append(
        "The Mamba rows use the completed selected configurations for S-Mamba, NS-Mamba-D, MS-Mamba-MD, and PMS-Mamba-PD, evaluated with the same horizon grouping and final test metrics."
    )
    lines.append(
        r"The machine-readable result tables are bundled in \texttt{manuscript/data/gld\_baseline\_optuna\_best.csv} and \texttt{manuscript/data/gld\_mamba\_optuna\_best.csv}; selected hyperparameters are listed in Appendix~A."
    )
    lines.append("")
    lines.append(r"\begin{table}[H]")
    lines.append(r"\centering")
    lines.append(
        r"\caption{Combined optimized GLD model summary grouped by forecast range. Short = 1--7 days, middle = 14--90 days, long = 120--360 days. Lower RMSSE is better.}"
    )
    lines.append(r"\label{tab:gld-term-avg}")
    lines.append(r"\small")
    lines.append(r"\resizebox{\linewidth}{!}{%")
    lines.append(r"\begin{tabular}{lrrrrrr}")
    lines.append(r"\toprule")
    lines.append(
        r"Model & Short RMSSE & Middle RMSSE & Long RMSSE & Overall RMSSE & Overall RMSE & Overall MAE \\"
    )
    lines.append(r"\midrule")
    for row in ranked_models:
        lines.append(
            f"{display_model(row['model'])} & {row['short_rmsse']:.2f} & "
            f"{row['middle_rmsse']:.2f} & {row['long_rmsse']:.2f} & "
            f"{row['overall_rmsse']:.2f} & {row['overall_rmse']:.2f} & {row['overall_mae']:.2f} \\\\"
        )
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"}")
    lines.append(r"\end{table}")
    lines.append("")
    lines.append(
        "The combined table shows that the strongest overall row is a Mamba-family model rather than a non-Mamba baseline."
    )
    lines.append(
        f"{display_model(best_overall['model'])} reaches the lowest balanced 12-horizon test RMSSE ({best_overall['overall_rmsse']:.2f}), followed by {display_model(runner_up['model'])} ({runner_up['overall_rmsse']:.2f})."
    )
    lines.append(
        f"Relative to the strongest non-Mamba baseline, {display_model(best_mamba['model'])} reduces overall RMSSE from {best_baseline['overall_rmsse']:.2f} to {best_mamba['overall_rmsse']:.2f}, a {baseline_reduction:.2f}\\% reduction."
    )
    lines.append(
        f"The strongest non-Mamba rows remain competitive: {display_model(best_baseline['model'])} is the best baseline overall ({best_baseline['overall_rmsse']:.2f}), with iTransformer and PatchTST close behind in the upper part of the ranking."
    )
    lines.append("")
    lines.append(
        "The horizon-range averages show different model strengths rather than a single dominant architecture at every range."
    )
    if best_middle["model"] == best_long["model"]:
        lines.append(
            f"{display_model(best_short['model'])} has the best short-range average RMSSE ({best_short['short_rmsse']:.2f}), while {display_model(best_middle['model'])} leads both the middle range ({best_middle['middle_rmsse']:.2f}) and the long range ({best_long['long_rmsse']:.2f})."
        )
    else:
        lines.append(
            f"{display_model(best_short['model'])} has the best short-range average RMSSE ({best_short['short_rmsse']:.2f}), while {display_model(best_middle['model'])} leads the middle range ({best_middle['middle_rmsse']:.2f}) and {display_model(best_long['model'])} leads the long range ({best_long['long_rmsse']:.2f})."
        )
    lines.append("")
    lines.append(
        "The plain Transformer, Reformer, and Informer configurations remain far weaker on the held-out test split, with overall test RMSSE above 72 despite low validation objectives for some selected trials."
    )
    lines.append(
        "This validation-to-test mismatch is why the manuscript reports final test RMSSE and moves the selected hyperparameters to Appendix~A for exact reproduction."
    )
    return "\n".join(lines) + "\n"


def build_appendix(param_rows):
    lines = []
    lines.append(r"\begin{table}[htbp]")
    lines.append(r"\centering")
    lines.append(
        r"\caption{Selected non-Mamba Optuna configurations for the reported GLD baseline rows. Configurations are selected by balanced validation RMSSE; test RMSSE is reported only for final evaluation. All selected configurations use the study suffix \texttt{fullcal\_v1}.}"
    )
    lines.append(r"\label{tab:gld-baseline-optuna-hparams}")
    lines.append(r"\scriptsize")
    lines.append(r"\begingroup")
    lines.append(r"\setlength{\tabcolsep}{2pt}")
    lines.append(r"\renewcommand{\arraystretch}{1.16}")
    lines.append(r"\begin{tabular}{@{}>{\raggedright\arraybackslash}p{0.16\linewidth}>{\centering\arraybackslash}p{0.06\linewidth}>{\centering\arraybackslash}p{0.06\linewidth}>{\centering\arraybackslash}p{0.045\linewidth}>{\raggedright\arraybackslash}p{0.12\linewidth}>{\raggedright\arraybackslash}p{0.17\linewidth}>{\raggedright\arraybackslash}p{0.29\linewidth}@{}}")
    lines.append(r"\toprule")
    lines.append(r"Model & Val. & Test & Seq. & Training & Width & Family-specific settings \\")
    lines.append(r"\midrule")
    for row in param_rows:
        params = json.loads(row["params_json"])
        lines.append(
            f"{display_model(row['model'])} & "
            f"{float(row['val_balanced_rmsse']):.2f} & {float(row['test_balanced_rmsse']):.2f} & "
            f"{params['seq_len']} & {train_cell(params)} & {width_cell(params)} & {baseline_settings_cell(params)} \\\\"
        )
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\endgroup")
    lines.append(r"\end{table}")
    lines.append("")
    return "\n".join(lines)


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
    param_rows = write_hyperparameter_table()
    horizon_winners, term_avgs, overall_avgs = build_tables(rows)
    content = build_summary(rows, horizon_winners, term_avgs, overall_avgs)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(content)
    APPENDIX_PATH.parent.mkdir(parents=True, exist_ok=True)
    APPENDIX_PATH.write_text(build_appendix(param_rows) + "\n")
    print(f"wrote {OUT_PATH.relative_to(MANUSCRIPT_ROOT)}")
    print(f"wrote {APPENDIX_PATH.relative_to(MANUSCRIPT_ROOT)}")
    print(f"wrote {CSV_PATH.relative_to(MANUSCRIPT_ROOT)}")
    print(f"wrote {PARAMS_CSV_PATH.relative_to(MANUSCRIPT_ROOT)}")


if __name__ == "__main__":
    main()
