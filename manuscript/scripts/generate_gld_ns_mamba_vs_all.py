#!/usr/bin/env python
import csv
from pathlib import Path
from statistics import mean


MANUSCRIPT_ROOT = Path(__file__).resolve().parents[1]
BASELINE_CSV = MANUSCRIPT_ROOT / "data" / "gld_baselines.csv"
NS_CSV = MANUSCRIPT_ROOT / "data" / "gld_ns_mamba_ablation.csv"
OPT_CSV = MANUSCRIPT_ROOT / "data" / "gld_source_optimized_best.csv"
HPO_CSV = MANUSCRIPT_ROOT / "data" / "gld_mamba_hpo_best.csv"
OUT_PATH = MANUSCRIPT_ROOT / "sections" / "results_ns_mamba_vs_all.tex"

HORIZONS = [30, 120, 180, 360]
LONG_HORIZONS = [120, 180, 360]


def ordinal(value):
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def display_model(name):
    mapping = {
        "S_Mamba": "S-Mamba",
        "iTransformer": "iTransformer",
        "Autoformer": "Autoformer",
        "Transformer": "Transformer",
        "Informer": "Informer",
        "Reformer": "Reformer",
        "NS_Mamba-A": "NS-Mamba-A",
        "NS_Mamba-D": "NS-Mamba-D",
        "NS_Mamba-AD": "NS-Mamba-AD",
        "NS_Mamba-ADG": "NS-Mamba-ADG",
        "PatchTST": "PatchTST",
        "TimesNet": "TimesNet",
        "NLinear": "NLinear",
        "DLinear": "DLinear",
        "Nonstationary_Transformer": "Non-stationary Transformer",
        "MS_Mamba-MD": "MS-Mamba-MD",
        "MS_Mamba-MDG": "MS-Mamba-MDG",
        "MS_Mamba-MDS": "MS-Mamba-MDS",
        "PMS_Mamba-PD": "PMS-Mamba-PD",
    }
    return mapping.get(name, name.replace("_", r"\_"))


def collect_track(path, track, name_key):
    grouped = {}
    with path.open() as f:
        for row in csv.DictReader(f):
            if row["status"] != "complete":
                continue
            h = int(row["horizon"])
            if h not in HORIZONS:
                continue
            name = row[name_key]
            key = (track, name)
            grouped.setdefault(key, {"track": track, "name": name, "horizons": {}})
            grouped[key]["horizons"][h] = {"rmse": float(row["rmse"]), "mae": float(row["mae"])}

    rows = []
    for payload in grouped.values():
        if all(h in payload["horizons"] for h in HORIZONS):
            rows.append(
                {
                    "track": payload["track"],
                    "name": payload["name"],
                    "key": (payload["track"], payload["name"]),
                    "horizons": payload["horizons"],
                    "long_rmse": mean(payload["horizons"][h]["rmse"] for h in LONG_HORIZONS),
                    "long_mae": mean(payload["horizons"][h]["mae"] for h in LONG_HORIZONS),
                }
            )
    return rows


def collect_rows():
    rows = []
    rows.extend(collect_track(BASELINE_CSV, "Shared", "model"))
    rows.extend(collect_track(NS_CSV, "NS-Diag", "variant"))
    rows.extend(collect_track(OPT_CSV, "Opt", "model"))
    rows.extend(collect_track(HPO_CSV, "Mamba-HPO", "variant"))
    return rows


def rank_map(rows, horizon):
    ranked = sorted(rows, key=lambda row: row["horizons"][horizon]["rmse"])
    return {row["key"]: idx + 1 for idx, row in enumerate(ranked)}


def build_tex(rows):
    rows = sorted(rows, key=lambda row: row["long_rmse"])
    long_rank = {row["key"]: idx + 1 for idx, row in enumerate(rows)}
    ranks = {h: rank_map(rows, h) for h in HORIZONS}

    nsd = next(row for row in rows if row["track"] == "NS-Diag" and row["name"] == "NS_Mamba-D")

    lines = []
    lines.append(r"\subsection{NS-Mamba-D in the Current Completed Comparison Set}")
    lines.append("")
    lines.append(
        r"Table~\ref{tab:ns-mamba-vs-all} places the fixed-setting NS-Mamba-D diagnostic row against every currently completed result on the overlapping horizons 30, 120, 180, and 360 days."
    )
    lines.append(
        r"This comparison now includes four tracks: the shared locked-setting baselines, the NS-Mamba diagnostic ablation, the currently completed source-optimized imported runs, and the currently completed Mamba-HPO rows."
    )
    lines.append("")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(
        r"\caption{Direct RMSE and MAE comparison of the fixed-setting NS-Mamba-D row against all currently completed GLD results on the overlapping horizons 30, 120, 180, and 360 days. Long Avg. is computed over 120, 180, and 360 days.}"
    )
    lines.append(r"\label{tab:ns-mamba-vs-all}")
    lines.append(r"\small")
    lines.append(r"\resizebox{\linewidth}{!}{%")
    lines.append(r"\begin{tabular}{llrrrrrr}")
    lines.append(r"\toprule")
    lines.append(r"Track & Model & 30 & 120 & 180 & 360 & Long Avg. RMSE & Long Avg. MAE \\")
    lines.append(r"\midrule")
    for row in rows:
        name = display_model(row["name"])
        if row["track"] == "NS-Diag" and row["name"] == "NS_Mamba-D":
            name = r"\textbf{" + name + "}"
        lines.append(
            f"{row['track']} & {name} & "
            f"{row['horizons'][30]['rmse']:.2f} & "
            f"{row['horizons'][120]['rmse']:.2f} & "
            f"{row['horizons'][180]['rmse']:.2f} & "
            f"{row['horizons'][360]['rmse']:.2f} & "
            f"{row['long_rmse']:.2f} & {row['long_mae']:.2f} \\\\"
        )
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"}")
    lines.append(r"\end{table}")
    lines.append("")
    lines.append(
        f"Within this current completed comparison set, the fixed-setting NS-Mamba-D row ranks {ordinal(ranks[30][('NS-Diag', 'NS_Mamba-D')])} at 30 days, {ordinal(ranks[120][('NS-Diag', 'NS_Mamba-D')])} at 120 days, {ordinal(ranks[180][('NS-Diag', 'NS_Mamba-D')])} at 180 days, and {ordinal(ranks[360][('NS-Diag', 'NS_Mamba-D')])} at 360 days among {len(rows)} completed entries."
    )
    lines.append(
        f"On the 120/180/360 long-horizon average, it ranks {ordinal(long_rank[('NS-Diag', 'NS_Mamba-D')])} overall with RMSE {nsd['long_rmse']:.2f} and MAE {nsd['long_mae']:.2f}."
    )
    lines.append(
        r"It remains stronger than the shared locked-setting baselines and the other completed NS-Mamba diagnostic variants, but it is now clearly outperformed by the stronger completed Mamba-HPO rows as well as the best completed imported optimized baselines."
    )
    lines.append(
        r"This comparison clarifies the role of the diagnostic ablation: the fixed-setting decomposition-only result is a useful proof of concept, but the strongest current Mamba-family performance comes after additional tuning of lookback length, moving-average window, and multi-scale structure."
    )
    return "\n".join(lines) + "\n"


def main():
    rows = collect_rows()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(build_tex(rows))
    print(f"wrote {OUT_PATH.relative_to(MANUSCRIPT_ROOT)}")


if __name__ == "__main__":
    main()
