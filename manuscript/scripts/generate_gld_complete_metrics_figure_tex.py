#!/usr/bin/env python
from pathlib import Path


MANUSCRIPT_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = MANUSCRIPT_ROOT / "sections" / "results_overview_figure.tex"


def build_tex():
    lines = []
    lines.append(r"\subsection{Completed Result Overview}")
    lines.append("")
    lines.append(
        r"Figure~\ref{fig:gld-result-overview} replaces the oversized full-results table with a compact visual summary of the completed GLD comparisons."
    )
    lines.append(
        r"Panel A shows the main cross-model frontier, and Panel B shows the completed Mamba-family comparisons."
    )
    lines.append(
        r"All curves are plotted on the original GLD price scale using RMSE. The local data snapshots used by this figure are bundled in the submission package under \texttt{figures/}."
    )
    lines.append("")
    lines.append(r"\begin{figure}[t]")
    lines.append(r"\centering")
    lines.append(r"\includegraphics[width=0.94\linewidth]{figures/gld_result_overview.pdf}")
    lines.append(
        r"\caption{Compact GLD RMSE comparison for publication. Panel A shows the main cross-model frontier across all completed horizons, including the strongest shared baselines, tuned imported baselines, and the promoted Mamba-HPO result. Panel B compares the completed Mamba-family variants on the diagnostic horizons 30, 120, 180, and 360 days. This figure preserves the ranking structure without the space cost of the full result table.}"
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
