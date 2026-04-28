#!/usr/bin/env python
import csv
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_CSV = REPO_ROOT / "results" / "gld_baselines.csv"
NS_CSV = REPO_ROOT / "results" / "gld_ns_mamba_ablation.csv"
OPT_CSV = REPO_ROOT / "results" / "gld_source_optimized_best.csv"
OUT_PATH = REPO_ROOT / "manuscript" / "generated" / "gld_complete_metrics_table.tex"


def latex_escape(text):
    return text.replace("_", r"\_")


def display_model(name):
    mapping = {
        "S_Mamba": r"S\_Mamba",
        "NS_Mamba-A": "NS-Mamba-A",
        "NS_Mamba-D": "NS-Mamba-D",
        "NS_Mamba-AD": "NS-Mamba-AD",
        "NS_Mamba-ADG": "NS-Mamba-ADG",
        "Nonstationary_Transformer": "Non-stationary Transformer",
    }
    return mapping.get(name, latex_escape(name))


def load_rows():
    rows = []

    with BASELINE_CSV.open() as f:
        for row in csv.DictReader(f):
            if row["status"] != "complete":
                continue
            rows.append(
                {
                    "track": "Shared",
                    "model": row["model"],
                    "horizon": int(row["horizon"]),
                    "seq_len": int(row["seq_len"]),
                    "rmse": float(row["rmse"]),
                    "mae": float(row["mae"]),
                }
            )

    with NS_CSV.open() as f:
        for row in csv.DictReader(f):
            if row["status"] != "complete":
                continue
            rows.append(
                {
                    "track": "NS-Diag",
                    "model": row["variant"],
                    "horizon": int(row["horizon"]),
                    "seq_len": 360,
                    "rmse": float(row["rmse"]),
                    "mae": float(row["mae"]),
                }
            )

    with OPT_CSV.open() as f:
        for row in csv.DictReader(f):
            if row["status"] != "complete":
                continue
            rows.append(
                {
                    "track": "Opt",
                    "model": row["model"],
                    "horizon": int(row["horizon"]),
                    "seq_len": int(row["seq_len"]),
                    "rmse": float(row["rmse"]),
                    "mae": float(row["mae"]),
                }
            )

    return rows


def build_table(rows):
    track_order = {"Shared": 0, "NS-Diag": 1, "Opt": 2}
    rows = sorted(rows, key=lambda row: (track_order[row["track"]], row["model"], row["horizon"]))

    lines = []
    lines.append(r"\subsection{Complete RMSE and MAE Record}")
    lines.append("")
    lines.append(
        r"Table~\ref{tab:gld-complete-metrics} lists every completed GLD result currently available in the repository."
    )
    lines.append(
        r"It combines the locked shared-setting baselines, the NS-Mamba diagnostic ablations, and the best completed source-optimized imported baselines."
    )
    lines.append(
        r"Only completed results are shown. The current table includes the finished source-optimized imported results for Non-stationary Transformer, TimesNet, PatchTST, DLinear, and NLinear."
    )
    lines.append("")
    lines.append(r"{\small")
    lines.append(r"\setlength{\LTleft}{0pt}")
    lines.append(r"\setlength{\LTright}{0pt}")
    lines.append(r"\begin{longtable}{llrrrr}")
    lines.append(
        r"\caption{Current completed GLD RMSE and MAE results across all experiment tracks. For source-optimized imported baselines, the reported sequence length is the best completed \texttt{seq\_len} for that horizon.}\label{tab:gld-complete-metrics}\\"
    )
    lines.append(r"\toprule")
    lines.append(r"Track & Model & Horizon & Seq. Len & RMSE & MAE \\")
    lines.append(r"\midrule")
    lines.append(r"\endfirsthead")
    lines.append(
        r"\caption[]{Current completed GLD RMSE and MAE results across all experiment tracks (continued).}\\"
    )
    lines.append(r"\toprule")
    lines.append(r"Track & Model & Horizon & Seq. Len & RMSE & MAE \\")
    lines.append(r"\midrule")
    lines.append(r"\endhead")
    lines.append(r"\bottomrule")
    lines.append(r"\endfoot")
    for row in rows:
        lines.append(
            f"{row['track']} & {display_model(row['model'])} & {row['horizon']} & "
            f"{row['seq_len']} & {row['rmse']:.2f} & {row['mae']:.2f} \\\\"
        )
    lines.append(r"\end{longtable}")
    lines.append(r"}")
    lines.append("")
    return "\n".join(lines)


def main():
    rows = load_rows()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(build_table(rows) + "\n")
    print(f"wrote {OUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
