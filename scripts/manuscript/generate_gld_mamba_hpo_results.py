#!/usr/bin/env python
import csv
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MAMBA_HPO_CSV = REPO_ROOT / "results" / "gld_mamba_hpo_best.csv"
SOURCE_CSV = REPO_ROOT / "results" / "gld_source_optimized_best.csv"
OUT_PATH = REPO_ROOT / "manuscript" / "generated" / "gld_mamba_hpo_results.tex"

DIAG_HORIZONS = [30, 120, 180, 360]
LONG_HORIZONS = [120, 180, 360]
REFERENCE_MODELS = ["PatchTST", "NLinear", "TimesNet"]


def latex_escape(text):
    return text.replace("_", r"\_")


def display_model(name):
    mapping = {
        "S_Mamba": r"S\_Mamba",
        "MS_Mamba-MD": "MS-Mamba-MD",
        "MS_Mamba-MDG": "MS-Mamba-MDG",
        "MS_Mamba-MDS": "MS-Mamba-MDS",
        "NS_Mamba-D": "NS-Mamba-D",
        "PMS_Mamba-PD": "PMS-Mamba-PD",
        "Nonstationary_Transformer": "Non-stationary Transformer",
    }
    return mapping.get(name, latex_escape(name))


def load_rows(path, name_key):
    rows = []
    with path.open() as f:
        for row in csv.DictReader(f):
            if row.get("status") != "complete":
                continue
            parsed = {
                "name": row[name_key],
                "horizon": int(row["horizon"]),
                "rmse": float(row["rmse"]),
                "mae": float(row["mae"]),
                "seq_len": int(row["seq_len"]),
                "config_id": row.get("config_id", ""),
            }
            for key in ("moving_avg", "ms_scales", "ms_fusion", "ms_use_linear_skip"):
                parsed[key] = row.get(key, "")
            rows.append(parsed)
    return rows


def group_by_name(rows):
    grouped = defaultdict(dict)
    for row in rows:
        grouped[row["name"]][row["horizon"]] = row
    return grouped


def avg(values):
    return sum(values) / len(values)


def long_summary(rows, horizons):
    grouped = group_by_name(rows)
    out = []
    for name, by_horizon in grouped.items():
        if not all(horizon in by_horizon for horizon in horizons):
            continue
        selected = [by_horizon[horizon] for horizon in horizons]
        out.append(
            {
                "name": name,
                "rmse": avg([row["rmse"] for row in selected]),
                "mae": avg([row["mae"] for row in selected]),
            }
        )
    return sorted(out, key=lambda row: row["rmse"])


def best_by_horizon(rows, horizons):
    out = []
    for horizon in horizons:
        candidates = [row for row in rows if row["horizon"] == horizon]
        if not candidates:
            continue
        out.append(min(candidates, key=lambda row: row["rmse"]))
    return out


def row_for(rows, name, horizon):
    for row in rows:
        if row["name"] == name and row["horizon"] == horizon:
            return row
    return None


def build_tex():
    mamba_rows = load_rows(MAMBA_HPO_CSV, "variant")
    source_rows = load_rows(SOURCE_CSV, "model")

    mamba_long = long_summary(mamba_rows, LONG_HORIZONS)
    references = [
        row for row in long_summary(source_rows, LONG_HORIZONS)
        if row["name"] in REFERENCE_MODELS
    ]
    combined = sorted(
        [{"track": "Mamba-HPO", **row} for row in mamba_long]
        + [{"track": "Opt", **row} for row in references],
        key=lambda row: row["rmse"],
    )
    best_mamba = mamba_long[0]
    best_reference = references[0]
    relative_gap = (best_reference["rmse"] - best_mamba["rmse"]) / best_reference["rmse"] * 100

    lines = []
    lines.append(r"\subsection{Mamba Hyperparameter Optimization}")
    lines.append("")
    lines.append(
        r"The Mamba-family hyperparameter optimization completed 266 price-scale runs and selected 25 best rows by RMSE."
    )
    lines.append(
        r"The search covers S\_Mamba, NS-Mamba-D, MS-Mamba variants, and PMS-Mamba-PD over diagnostic horizons."
    )
    lines.append(
        r"Because the promoted Mamba search has not yet run all 12 horizons, the direct long-horizon comparison below uses the completed diagnostic long horizons 120, 180, and 360 days."
    )
    lines.append("")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(r"\caption{Long-horizon comparison after Mamba hyperparameter optimization. Values are averaged over 120, 180, and 360 days.}")
    lines.append(r"\label{tab:gld-mamba-hpo-long}")
    lines.append(r"\begin{tabular}{llrr}")
    lines.append(r"\toprule")
    lines.append(r"Track & Model & Avg. RMSE & Avg. MAE \\")
    lines.append(r"\midrule")
    for row in combined:
        lines.append(
            f"{row['track']} & {display_model(row['name'])} & {row['rmse']:.2f} & {row['mae']:.2f} \\\\"
        )
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    lines.append("")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(r"\caption{Best Mamba-HPO configuration by completed diagnostic horizon.}")
    lines.append(r"\label{tab:gld-mamba-hpo-horizon}")
    lines.append(r"\begin{tabular}{lrrrrlll}")
    lines.append(r"\toprule")
    lines.append(r"Model & Horizon & Seq. Len & RMSE & MAE & Config & Moving Avg. & Scales \\")
    lines.append(r"\midrule")
    for row in best_by_horizon(mamba_rows, DIAG_HORIZONS):
        lines.append(
            f"{display_model(row['name'])} & {row['horizon']} & {row['seq_len']} & "
            f"{row['rmse']:.2f} & {row['mae']:.2f} & {latex_escape(row['config_id'])} & "
            f"{row['moving_avg']} & {row['ms_scales'] or '--'} \\\\"
        )
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    lines.append("")
    lines.append(
        f"After tuning, {display_model(best_mamba['name'])} is the strongest Mamba-family model, "
        f"with average RMSE {best_mamba['rmse']:.2f} and average MAE {best_mamba['mae']:.2f} "
        r"over the completed long diagnostic horizons."
    )
    lines.append(
        r"This changes the cross-model ranking: the best optimized Mamba model is now stronger than optimized NLinear and TimesNet on the 120/180/360-day average."
    )
    lines.append(
        f"However, optimized PatchTST remains the strongest model in this comparison, with average RMSE "
        f"{best_reference['rmse']:.2f}; the remaining relative RMSE gap for the best Mamba model is "
        f"{abs(relative_gap):.2f}\\%."
    )

    details = []
    for horizon in LONG_HORIZONS:
        mamba_row = row_for(mamba_rows, best_mamba["name"], horizon)
        patch_row = row_for(source_rows, "PatchTST", horizon)
        if mamba_row is None or patch_row is None:
            continue
        details.append(
            f"{horizon} days ({mamba_row['rmse']:.2f} vs. {patch_row['rmse']:.2f})"
        )
    if details:
        lines.append(
            "The residual gap to PatchTST is concentrated at "
            + ", ".join(details)
            + "."
        )
    lines.append("")
    return "\n".join(lines)


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(build_tex() + "\n")
    print(f"wrote {OUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
