#!/usr/bin/env python
import csv
from collections import defaultdict
from pathlib import Path


MANUSCRIPT_ROOT = Path(__file__).resolve().parents[1]
ALL_CSV = MANUSCRIPT_ROOT / "data" / "gld_mamba_hpo_all.csv"
MAMBA_HPO_CSV = MANUSCRIPT_ROOT / "data" / "gld_mamba_hpo_best.csv"
SOURCE_CSV = MANUSCRIPT_ROOT / "data" / "gld_source_optimized_best.csv"
OUT_PATH = MANUSCRIPT_ROOT / "sections" / "results_mamba_hpo.tex"

COMMON_LONG_HORIZONS = [120, 180, 360]
PROMOTED_LONG_HORIZONS = [120, 180, 270, 360]
REFERENCE_MODELS = ["PatchTST", "NLinear", "TimesNet"]


def latex_escape(text):
    return text.replace("_", r"\_")


def display_model(name):
    mapping = {
        "S_Mamba": "S-Mamba",
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


def complete_count(path):
    with path.open() as f:
        return sum(1 for row in csv.DictReader(f) if row.get("status") == "complete")


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
    complete_runs = complete_count(ALL_CSV)
    completed_horizons = sorted({row["horizon"] for row in mamba_rows})

    mamba_long = long_summary(mamba_rows, COMMON_LONG_HORIZONS)
    references = [
        row for row in long_summary(source_rows, COMMON_LONG_HORIZONS)
        if row["name"] in REFERENCE_MODELS
    ]
    combined = sorted(
        [{"track": "Mamba-HPO", **row} for row in mamba_long]
        + [{"track": "Opt", **row} for row in references],
        key=lambda row: row["rmse"],
    )
    best_mamba_common = mamba_long[0]
    best_reference_common = references[0]

    promoted_name = "MS_Mamba-MD"
    promoted_rows = [row for row in mamba_rows if row["name"] == promoted_name]
    promoted_long = long_summary(promoted_rows, PROMOTED_LONG_HORIZONS)[0]
    promoted_references = [
        row for row in long_summary(source_rows, PROMOTED_LONG_HORIZONS)
        if row["name"] in REFERENCE_MODELS
    ]
    best_reference_promoted = promoted_references[0]
    relative_gap = (
        best_reference_promoted["rmse"] - promoted_long["rmse"]
    ) / best_reference_promoted["rmse"] * 100
    horizon_best = best_by_horizon(mamba_rows, completed_horizons)
    winner_counts = defaultdict(int)
    for row in horizon_best:
        winner_counts[row["name"]] += 1

    lines = []
    lines.append(r"\subsection{Current Mamba Hyperparameter Search}")
    lines.append("")
    lines.append(
        f"The refreshed Mamba-family hyperparameter summary now contains {complete_runs} complete price-scale runs and {len(mamba_rows)} best-per-variant/per-horizon rows in \\texttt{{results/gld\\_mamba\\_hpo\\_best.csv}}."
    )
    lines.append(
        r"This search covers S-Mamba, NS-Mamba-D, MS-Mamba-MD, MS-Mamba-MDG, MS-Mamba-MDS, and PMS-Mamba-PD."
    )
    lines.append(
        r"MS-Mamba-MD now covers all 12 horizons, while the other Mamba-family variants still cover only the diagnostic subset. Accordingly, this section reports two complementary views: a common 120/180/360-day subset for all currently completed variants, and a promoted 120/180/270/360-day summary for MS-Mamba-MD against the optimized imported references."
    )
    lines.append("")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(r"\caption{Current long-horizon comparison after Mamba hyperparameter search. Values are averaged over the completed common long horizons 120, 180, and 360 days.}")
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
    lines.append(r"\caption{Promoted long-horizon summary for MS-Mamba-MD and optimized reference models. Values are averaged over 120, 180, 270, and 360 days.}")
    lines.append(r"\label{tab:gld-mamba-hpo-promoted}")
    lines.append(r"\begin{tabular}{lrr}")
    lines.append(r"\toprule")
    lines.append(r"Model & Avg. RMSE & Avg. MAE \\")
    lines.append(r"\midrule")
    lines.append(f"{display_model(promoted_name)} & {promoted_long['rmse']:.2f} & {promoted_long['mae']:.2f} \\\\")
    for row in promoted_references:
        lines.append(f"{display_model(row['name'])} & {row['rmse']:.2f} & {row['mae']:.2f} \\\\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    lines.append("")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(r"\caption{Best currently completed Mamba-HPO row by horizon.}")
    lines.append(r"\label{tab:gld-mamba-hpo-horizon}")
    lines.append(r"\small")
    lines.append(r"\resizebox{\linewidth}{!}{%")
    lines.append(r"\begin{tabular}{lrrrrlll}")
    lines.append(r"\toprule")
    lines.append(r"Model & Horizon & Seq. Len & RMSE & MAE & Config & Moving Avg. & Scales \\")
    lines.append(r"\midrule")
    for row in horizon_best:
        lines.append(
            f"{display_model(row['name'])} & {row['horizon']} & {row['seq_len']} & "
            f"{row['rmse']:.2f} & {row['mae']:.2f} & {latex_escape(row['config_id'])} & "
            f"{row['moving_avg']} & {row['ms_scales'] or '--'} \\\\"
        )
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"}")
    lines.append(r"\end{table}")
    lines.append("")
    lines.append(
        "The current search changes the Mamba-family picture substantially."
    )
    lines.append(
        f"{display_model('MS_Mamba-MD')} is the strongest completed Mamba variant on {winner_counts['MS_Mamba-MD']} of the {len(horizon_best)} horizons that currently have HPO-best rows, while {display_model('S_Mamba')} is strongest at 5 days and {display_model('MS_Mamba-MDG')} is strongest at 30 days."
    )
    lines.append(
        f"Relative to the fixed-setting diagnostic NS-Mamba-D row, the tuned NS-Mamba-D row improves the 120/180/360 average from 26.74 to {next(row for row in mamba_long if row['name'] == 'NS_Mamba-D')['rmse']:.2f}."
    )
    lines.append(
        f"On the completed common long-horizon subset, {display_model(best_mamba_common['name'])} is the strongest Mamba-family model with average RMSE {best_mamba_common['rmse']:.2f} and average MAE {best_mamba_common['mae']:.2f}."
    )
    lines.append(
        f"On the promoted four-horizon summary 120/180/270/360, {display_model(promoted_name)} reaches average RMSE {promoted_long['rmse']:.2f} and average MAE {promoted_long['mae']:.2f}."
    )
    lines.append(
        f"This is stronger than optimized NLinear ({next(row for row in promoted_references if row['name'] == 'NLinear')['rmse']:.2f}) and optimized TimesNet ({next(row for row in promoted_references if row['name'] == 'TimesNet')['rmse']:.2f}) on the same four-horizon average, but it still trails optimized PatchTST ({best_reference_promoted['rmse']:.2f})."
    )

    details = []
    for horizon in PROMOTED_LONG_HORIZONS:
        mamba_row = row_for(mamba_rows, promoted_name, horizon)
        patch_row = row_for(source_rows, "PatchTST", horizon)
        if mamba_row is None or patch_row is None:
            continue
        details.append(
            f"{horizon} days ({mamba_row['rmse']:.2f} vs. {patch_row['rmse']:.2f})"
        )
    if details:
        lines.append(
            "The remaining gap to PatchTST is concentrated at "
            + ", ".join(details)
            + "."
        )
    lines.append(
        f"The corresponding relative RMSE gap between {display_model(promoted_name)} and PatchTST on the promoted four-horizon summary is {abs(relative_gap):.2f}\\%."
    )
    lines.append("")
    return "\n".join(lines)


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(build_tex() + "\n")
    print(f"wrote {OUT_PATH.relative_to(MANUSCRIPT_ROOT)}")


if __name__ == "__main__":
    main()
