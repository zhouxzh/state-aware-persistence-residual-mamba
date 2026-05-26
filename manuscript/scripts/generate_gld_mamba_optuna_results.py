#!/usr/bin/env python
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


MANUSCRIPT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = MANUSCRIPT_ROOT / "data"
MAMBA_BEST_CSV = DATA_DIR / "gld_mamba_optuna_best.csv"
MAMBA_HYPER_CSV = DATA_DIR / "gld_mamba_optuna_hyperparameters.csv"
BASELINE_CSV = DATA_DIR / "gld_baseline_optuna_best.csv"
OUT_PATH = MANUSCRIPT_ROOT / "sections" / "results_mamba_optuna.tex"
APPENDIX_PATH = MANUSCRIPT_ROOT / "sections" / "appendix" / "mamba_optuna_hyperparameters.tex"

ALL_HORIZONS = [1, 3, 5, 7, 14, 30, 60, 90, 120, 180, 270, 360]
COMMON_LONG_HORIZONS = [120, 180, 360]
PROMOTED_LONG_HORIZONS = [120, 180, 270, 360]


def latex_escape(text):
    return text.replace("_", r"\_")


def display_model(name):
    return {
        "S_Mamba": "S-Mamba",
        "NS_Mamba-D": "NS-Mamba-D",
        "MS_Mamba-MD": "MS-Mamba-MD",
        "PMS_Mamba-PD": "PMS-Mamba-PD",
        "Nonstationary_Transformer": "Non-stationary Transformer",
    }.get(name, latex_escape(name))


def format_lr(value):
    text = f"{float(value):.0e}"
    mantissa, exponent = text.split("e")
    return f"{int(mantissa)}e{int(exponent)}"


def train_cell(params):
    return f"bs={params['batch_size']}; lr={format_lr(params['learning_rate'])}"


def width_cell(params):
    parts = []
    for key in ["d_model", "d_ff", "d_state"]:
        if key in params:
            parts.append(f"{latex_escape(key)}={params[key]}")
    return "; ".join(parts)


def format_list(values):
    return "[" + ",".join(str(value) for value in values) + "]"


def mamba_settings_cell(params):
    parts = []
    if "factor" in params:
        parts.append(f"factor={params['factor']}")
    if "moving_avg" in params:
        parts.append(f"moving avg={params['moving_avg']}")
    if "ms_scales" in params:
        parts.append(f"scales={format_list(params['ms_scales'])}")
    if "ms_fusion" in params:
        parts.append(f"fusion={params['ms_fusion']}")
    if params.get("ms_use_decomp") or params.get("use_decomp"):
        parts.append("decomp")
    if "ms_use_linear_skip" in params:
        parts.append("linear skip" if params["ms_use_linear_skip"] else "no linear skip")
    if "patch_len" in params:
        parts.append(f"patch={params['patch_len']}")
    if "stride" in params:
        parts.append(f"stride={params['stride']}")
    if params.get("use_norm"):
        parts.append("norm")
    if "use_adaptive_norm" in params and not params["use_adaptive_norm"]:
        parts.append("no adaptive norm")
    if "use_shift_gate" in params and not params["use_shift_gate"]:
        parts.append("no shift gate")
    return "; ".join(parts)


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
                    "seq_len": int(row["seq_len"]),
                    "rmse": float(row["rmse"]),
                    "mae": float(row["mae"]),
                    "rmsse": float(row["rmsse"]),
                    "trial_number": int(row.get("trial_number", 0) or 0),
                    "params_compact": row.get("params_compact", ""),
                    "study_name": row.get("study_name", ""),
                    "overall_balanced_rmsse": float(row.get("overall_balanced_rmsse", 0) or 0),
                    "overall_avg_rmse": float(row.get("overall_avg_rmse", 0) or 0),
                    "overall_avg_mae": float(row.get("overall_avg_mae", 0) or 0),
                    "short_avg_rmsse": float(row.get("short_avg_rmsse", 0) or 0),
                    "middle_avg_rmsse": float(row.get("middle_avg_rmsse", 0) or 0),
                    "long_avg_rmsse": float(row.get("long_avg_rmsse", 0) or 0),
                }
            )
    return rows


def load_hyperparams(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def avg(values):
    return sum(values) / len(values)


def group_by_model(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["name"]].append(row)
    return grouped


def summary_for(rows, horizons):
    grouped = group_by_model(rows)
    summaries = []
    for name, model_rows in grouped.items():
        selected = [row for row in model_rows if row["horizon"] in horizons]
        if len(selected) != len(horizons):
            continue
        summaries.append(
            {
                "name": name,
                "seq_len": selected[0]["seq_len"],
                "rmsse": avg([row["rmsse"] for row in selected]),
                "rmse": avg([row["rmse"] for row in selected]),
                "mae": avg([row["mae"] for row in selected]),
            }
        )
    return sorted(summaries, key=lambda row: row["rmsse"])


def best_by_horizon(rows, horizons):
    out = []
    for horizon in horizons:
        candidates = [row for row in rows if row["horizon"] == horizon]
        if not candidates:
            continue
        out.append(min(candidates, key=lambda row: row["rmsse"]))
    return out


def best_baseline_summary(rows, horizons):
    return summary_for(rows, horizons)[0]


def format_horizon_list(values):
    values = list(values)
    if not values:
        return ""
    if len(values) == 1:
        return str(values[0])
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return ", ".join(str(v) for v in values[:-1]) + f", and {values[-1]}"


def build_tex():
    return (
        "% Mamba-family results are reported in the combined optimized GLD "
        "comparison table generated by generate_gld_baseline_results.py.\n"
    )


def build_appendix(hyper_rows):
    lines = []
    lines.append(r"\begin{table}[htbp]")
    lines.append(r"\centering")
    lines.append(
        r"\caption{Selected Mamba-family Optuna configurations for the completed GLD bundle. Configurations are selected by balanced validation RMSSE; test RMSSE is reported only for final evaluation.}"
    )
    lines.append(r"\label{tab:gld-mamba-optuna-hparams}")
    lines.append(r"\scriptsize")
    lines.append(r"\begingroup")
    lines.append(r"\setlength{\tabcolsep}{2pt}")
    lines.append(r"\renewcommand{\arraystretch}{1.16}")
    lines.append(r"\begin{tabular}{@{}>{\raggedright\arraybackslash}p{0.15\linewidth}>{\centering\arraybackslash}p{0.06\linewidth}>{\centering\arraybackslash}p{0.06\linewidth}>{\centering\arraybackslash}p{0.045\linewidth}>{\raggedright\arraybackslash}p{0.12\linewidth}>{\raggedright\arraybackslash}p{0.20\linewidth}>{\raggedright\arraybackslash}p{0.29\linewidth}@{}}")
    lines.append(r"\toprule")
    lines.append(r"Model & Val. & Test & Seq. & Training & Width & Architecture settings \\")
    lines.append(r"\midrule")
    for row in hyper_rows:
        params = json.loads(row["params_json"])
        lines.append(
            f"{display_model(row['model'])} & "
            f"{float(row['val_balanced_rmsse']):.2f} & {float(row['test_balanced_rmsse']):.2f} & "
            f"{params['seq_len']} & {train_cell(params)} & {width_cell(params)} & {mamba_settings_cell(params)} \\\\"
        )
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\endgroup")
    lines.append(r"\end{table}")
    lines.append("")
    return "\n".join(lines)


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(build_tex() + "\n")
    APPENDIX_PATH.parent.mkdir(parents=True, exist_ok=True)
    APPENDIX_PATH.write_text(build_appendix(load_hyperparams(MAMBA_HYPER_CSV)) + "\n")
    print(f"wrote {OUT_PATH.relative_to(MANUSCRIPT_ROOT)}")
    print(f"wrote {APPENDIX_PATH.relative_to(MANUSCRIPT_ROOT)}")


if __name__ == "__main__":
    main()
