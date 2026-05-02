#!/usr/bin/env python
import csv
from pathlib import Path
from statistics import mean


REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_CSV = REPO_ROOT / "results" / "gld_baselines.csv"
NS_CSV = REPO_ROOT / "results" / "gld_ns_mamba_ablation.csv"
OPT_CSV = REPO_ROOT / "results" / "gld_source_optimized_best.csv"
OUT_PATH = REPO_ROOT / "manuscript" / "generated" / "gld_ns_mamba_vs_all.tex"

HORIZONS = [30, 120, 180, 360]
LONG_HORIZONS = [120, 180, 360]


def display_model(name):
    mapping = {
        "S_Mamba": r"S\_Mamba",
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
    }
    return mapping.get(name, name.replace("_", r"\_"))


def collect_rows():
    models = {}

    with BASELINE_CSV.open() as f:
        for row in csv.DictReader(f):
            if row["status"] != "complete":
                continue
            h = int(row["horizon"])
            if h not in HORIZONS:
                continue
            model = row["model"]
            models.setdefault(model, {"track": "Shared", "horizons": {}})
            models[model]["horizons"][h] = {"rmse": float(row["rmse"]), "mae": float(row["mae"])}

    with NS_CSV.open() as f:
        for row in csv.DictReader(f):
            if row["status"] != "complete":
                continue
            h = int(row["horizon"])
            if h not in HORIZONS:
                continue
            model = row["variant"]
            models.setdefault(model, {"track": "NS-Diag", "horizons": {}})
            models[model]["horizons"][h] = {"rmse": float(row["rmse"]), "mae": float(row["mae"])}

    with OPT_CSV.open() as f:
        for row in csv.DictReader(f):
            if row["status"] != "complete":
                continue
            h = int(row["horizon"])
            if h not in HORIZONS:
                continue
            model = row["model"]
            models.setdefault(model, {"track": "Opt", "horizons": {}})
            models[model]["horizons"][h] = {"rmse": float(row["rmse"]), "mae": float(row["mae"]), "seq_len": int(row["seq_len"])}

    complete = []
    for model, payload in models.items():
        if all(h in payload["horizons"] for h in HORIZONS):
            long_rmse = mean(payload["horizons"][h]["rmse"] for h in LONG_HORIZONS)
            long_mae = mean(payload["horizons"][h]["mae"] for h in LONG_HORIZONS)
            complete.append(
                {
                    "model": model,
                    "track": payload["track"],
                    "horizons": payload["horizons"],
                    "long_rmse": long_rmse,
                    "long_mae": long_mae,
                }
            )
    return complete


def rank_map(rows, horizon):
    ranked = sorted(rows, key=lambda row: row["horizons"][horizon]["rmse"])
    return {row["model"]: idx + 1 for idx, row in enumerate(ranked)}


def build_tex(rows):
    rows = sorted(rows, key=lambda row: row["long_rmse"])
    long_rank = {row["model"]: idx + 1 for idx, row in enumerate(rows)}
    ranks = {h: rank_map(rows, h) for h in HORIZONS}

    nsd = next(row for row in rows if row["model"] == "NS_Mamba-D")

    lines = []
    lines.append(r"\subsection{NS-Mamba-D vs All Completed Models}")
    lines.append("")
    lines.append(
        r"Table~\ref{tab:ns-mamba-vs-all} compares NS-Mamba-D against every model that currently has completed GLD results on the overlapping horizons 30, 120, 180, and 360 days."
    )
    lines.append(
        r"This includes the shared locked-setting baselines, the other NS-Mamba diagnostic variants, and the tuned imported baselines."
    )
    lines.append("")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(
        r"\caption{Direct RMSE and MAE comparison of NS-Mamba-D against all completed GLD models on the overlapping horizons 30, 120, 180, and 360 days. Long Avg. is computed over 120, 180, and 360 days.}"
    )
    lines.append(r"\label{tab:ns-mamba-vs-all}")
    lines.append(r"\small")
    lines.append(r"\resizebox{\linewidth}{!}{%")
    lines.append(r"\begin{tabular}{llrrrrrr}")
    lines.append(r"\toprule")
    lines.append(r"Track & Model & 30 & 120 & 180 & 360 & Long Avg. RMSE & Long Avg. MAE \\")
    lines.append(r"\midrule")
    for row in rows:
        name = display_model(row["model"])
        if row["model"] == "NS_Mamba-D":
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
        f"NS-Mamba-D ranks {ranks[30]['NS_Mamba-D']}th at 30 days, {ranks[120]['NS_Mamba-D']}th at 120 days, {ranks[180]['NS_Mamba-D']}th at 180 days, and {ranks[360]['NS_Mamba-D']}th at 360 days among all completed models."
    )
    lines.append(
        f"On the long-horizon average over 120, 180, and 360 days, NS-Mamba-D ranks {long_rank['NS_Mamba-D']}th overall with RMSE {nsd['long_rmse']:.2f} and MAE {nsd['long_mae']:.2f}."
    )
    lines.append(
        r"It beats every shared locked-setting baseline and every other NS-Mamba diagnostic variant, but it trails the tuned imported PatchTST, NLinear, and TimesNet baselines."
    )
    lines.append(
        r"This comparison predates the later Mamba-family hyperparameter optimization; after that search, optimized MS-Mamba-MD becomes the strongest Mamba-family result."
    )
    return "\n".join(lines) + "\n"


def main():
    rows = collect_rows()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(build_tex(rows))
    print(f"wrote {OUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
