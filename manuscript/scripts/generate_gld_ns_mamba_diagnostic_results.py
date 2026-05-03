#!/usr/bin/env python
import csv
from pathlib import Path


MANUSCRIPT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = MANUSCRIPT_ROOT / "data" / "gld_ns_mamba_ablation.csv"
OUT_PATH = MANUSCRIPT_ROOT / "sections" / "results_ns_mamba_diagnostic.tex"

HORIZONS = [30, 120, 180, 360]
LONG_HORIZONS = [120, 180, 360]
ORDER = ["S_Mamba", "iTransformer", "NS_Mamba-A", "NS_Mamba-D", "NS_Mamba-AD", "NS_Mamba-ADG"]


def avg(values):
    return sum(values) / len(values)


def load_rows():
    rows = {}
    with CSV_PATH.open() as f:
        for row in csv.DictReader(f):
            if row["status"] != "complete":
                continue
            variant = row["variant"]
            horizon = int(row["horizon"])
            rows.setdefault(variant, {})[horizon] = {
                "rmse": float(row["rmse"]),
                "mae": float(row["mae"]),
            }
    return rows


def baseline_rows():
    return {
        "S_Mamba": {30: 11.12, 120: 20.31, 180: 26.91, 360: 39.48},
        "iTransformer": {30: 11.45, 120: 19.89, 180: 26.71, 360: 39.45},
    }


def build_tex():
    rows = load_rows()
    baselines = baseline_rows()

    lines = []
    lines.append(r"\subsection{NS-Mamba Diagnostic Ablation}")
    lines.append("")
    lines.append(
        r"The first NS-Mamba diagnostic sweep is complete for horizons 30, 120, 180, and 360 days."
    )
    lines.append(
        r"This is a partial ablation rather than the final 12-horizon result table."
    )
    lines.append(
        r"The completed diagnostic stage contains 16 finished runs, corresponding to four NS-Mamba variants evaluated on four horizons under the same locked Setting A used by the GLD baselines."
    )
    lines.append("")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(
        r"\caption{Diagnostic GLD RMSE results for NS-Mamba variants. The long average is computed over 120, 180, and 360 days.}"
    )
    lines.append(r"\label{tab:ns-mamba-diagnostic}")
    lines.append(r"\small")
    lines.append(r"\resizebox{\linewidth}{!}{%")
    lines.append(r"\begin{tabular}{lccc rrrrr}")
    lines.append(r"\toprule")
    lines.append(r"Model & Adaptive Norm & Decomp. & Gate & 30 & 120 & 180 & 360 & Long Avg. \\")
    lines.append(r"\midrule")
    lines.append(r"S-Mamba & No & No & No & 11.12 & 20.31 & 26.91 & 39.48 & 28.90 \\")
    lines.append(r"iTransformer & Yes & No & No & 11.45 & 19.89 & 26.71 & 39.45 & 28.69 \\")
    lines.append(r"\midrule")

    flags = {
        "NS_Mamba-A": ("Yes", "No", "No"),
        "NS_Mamba-D": ("No", "Yes", "No"),
        "NS_Mamba-AD": ("Yes", "Yes", "No"),
        "NS_Mamba-ADG": ("Yes", "Yes", "Yes"),
    }
    for name in ["NS_Mamba-A", "NS_Mamba-D", "NS_Mamba-AD", "NS_Mamba-ADG"]:
        row = rows[name]
        long_avg = avg([row[h]["rmse"] for h in LONG_HORIZONS])
        prefix = r"\textbf{" if name == "NS_Mamba-D" else ""
        suffix = "}" if name == "NS_Mamba-D" else ""
        a, d, g = flags[name]
        values = " & ".join(f"{prefix}{row[h]['rmse']:.2f}{suffix}" for h in HORIZONS)
        lines.append(f"{name.replace('_', '-')} & {a} & {d} & {g} & {values} & {prefix}{long_avg:.2f}{suffix} \\\\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"}")
    lines.append(r"\end{table}")
    lines.append("")

    best = rows["NS_Mamba-D"]
    improvements = []
    for horizon in HORIZONS:
        ref = min(baselines["S_Mamba"][horizon], baselines["iTransformer"][horizon])
        improvements.append((ref - best[horizon]["rmse"]) / ref * 100)
    long_best = avg([best[h]["rmse"] for h in LONG_HORIZONS])
    long_sm = avg([baselines["S_Mamba"][h] for h in LONG_HORIZONS])
    long_it = avg([baselines["iTransformer"][h] for h in LONG_HORIZONS])

    lines.append(
        r"Among the four completed diagnostic variants, NS-Mamba-D is strongest at every completed horizon and on the diagnostic long-horizon average."
    )
    lines.append(
        f"Relative to the better of S-Mamba and iTransformer at each diagnostic horizon, NS-Mamba-D reduces RMSE by {improvements[0]:.2f}\\% at 30 days, {improvements[1]:.2f}\\% at 120 days, {improvements[2]:.2f}\\% at 180 days, and {improvements[3]:.2f}\\% at 360 days."
    )
    lines.append(
        f"Its long-horizon average RMSE is {long_best:.2f}, compared with {long_sm:.2f} for S-Mamba and {long_it:.2f} for iTransformer."
    )
    lines.append(
        "The completed diagnostic ablation is also informative about module choice."
    )
    lines.append(
        "Adaptive normalization alone is weaker than both reference baselines on the long diagnostic horizons."
    )
    lines.append(
        "Adding adaptive normalization to the decomposition branch weakens the decomposition-only result, and the shift-aware gate does not improve the decomposition variant in this first fixed-setting sweep."
    )
    lines.append(
        "Within the completed diagnostic study, explicit decomposition is therefore the only modification that consistently improves over both reference models."
    )
    lines.append("")
    return "\n".join(lines)


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(build_tex() + "\n")
    print(f"wrote {OUT_PATH.relative_to(MANUSCRIPT_ROOT)}")


if __name__ == "__main__":
    main()
