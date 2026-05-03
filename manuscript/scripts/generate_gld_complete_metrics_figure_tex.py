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
        r"Panel A shows the current cross-model frontier across the strongest optimized baseline, imported, and Mamba-family rows, while Panel B shows the currently completed Mamba-HPO variants on the diagnostic horizons 30, 120, 180, and 360 days."
    )
    lines.append(
        r"All curves are plotted on the original GLD price scale using RMSE. Because the imported optimized and Mamba-HPO tracks are still incomplete, the figure should be read as a current-status summary rather than a final global leaderboard. The detailed imported optimized tables are reported in Appendix~A."
    )
    lines.append("")
    lines.append(r"\begin{figure}[t]")
    lines.append(r"\centering")
    lines.append(r"\includegraphics[width=0.94\linewidth]{figures/gld_result_overview.pdf}")
    lines.append(
        r"\caption{Compact GLD RMSE comparison across the currently completed optimized evaluation tracks. Panel A shows the current cross-model frontier across all completed horizons, including the strongest optimized baselines, imported optimized baselines, and the promoted Mamba-HPO row. Panel B shows the currently completed Mamba-HPO variants on the diagnostic horizons 30, 120, 180, and 360 days.}"
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
