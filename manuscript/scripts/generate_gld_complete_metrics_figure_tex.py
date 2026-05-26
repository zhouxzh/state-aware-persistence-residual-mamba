#!/usr/bin/env python
from pathlib import Path


MANUSCRIPT_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = MANUSCRIPT_ROOT / "sections" / "results_overview_figure.tex"


def build_tex():
    lines = []
    lines.append(r"\subsection{Completed Result Overview}")
    lines.append("")
    lines.append(
        r"Figure~\ref{fig:gld-result-overview} summarizes the currently completed GLD evidence in compact form."
    )
    lines.append(
        r"Panel A shows the Optuna-tuned non-Mamba baseline frontier using RMSSE, while Panel B shows the completed Mamba Optuna variants using the same RMSSE metric across all horizons."
    )
    lines.append(
        r"The panels use the same scale-normalized metric, so the baseline and Mamba tracks can be read on the same axis."
    )
    lines.append("")
    lines.append(r"\begin{figure}[t]")
    lines.append(r"\centering")
    lines.append(r"\includegraphics[width=0.94\linewidth]{figures/gld_result_overview.pdf}")
    lines.append(
        r"\caption{Compact GLD RMSSE summary for the currently completed optimized evaluation tracks. Panel A reports Optuna-tuned non-Mamba baseline RMSSE across all horizons. Panel B reports Mamba Optuna RMSSE across all horizons.}"
    )
    lines.append(r"\label{fig:gld-result-overview}")
    lines.append(r"\end{figure}")
    lines.append("")
    return "\n".join(lines) + "\n"


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(build_tex())
    print(f"wrote {OUT_PATH.relative_to(MANUSCRIPT_ROOT)}")


if __name__ == "__main__":
    main()
