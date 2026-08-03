#!/usr/bin/env python
"""Build the Git-tracked PMS-Mamba V2 validation release snapshot."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import mamba_ssm
import numpy as np
import pandas as pd
import torch


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = REPO_ROOT / "results" / "nonstationary_analysis_v2"
RELEASE_ROOT = REPO_ROOT / "reproducibility" / "nonstationary_analysis_v2"

COPIES = {
    RESULTS_ROOT / "screen_merged" / "screen_design.csv": RELEASE_ROOT / "validation" / "screen_design.csv",
    RESULTS_ROOT / "screen_merged" / "screen_results.csv": RELEASE_ROOT / "validation" / "screen_results.csv",
    RESULTS_ROOT / "screen_merged" / "screen_run_summary.csv": RELEASE_ROOT / "validation" / "screen_run_summary.csv",
    RESULTS_ROOT / "screen_merged" / "screen_config_summary.csv": RELEASE_ROOT / "validation" / "screen_config_summary.csv",
    RESULTS_ROOT / "screen_merged" / "validation_manifest.json": RELEASE_ROOT / "validation" / "screen_manifest.json",
    RESULTS_ROOT / "confirmation_merged" / "screen_results.csv": RELEASE_ROOT / "validation" / "confirmation_results.csv",
    RESULTS_ROOT / "confirmation_merged" / "screen_run_summary.csv": RELEASE_ROOT / "validation" / "confirmation_run_summary.csv",
    RESULTS_ROOT / "confirmation_merged" / "screen_config_summary.csv": RELEASE_ROOT / "validation" / "confirmation_config_summary.csv",
    RESULTS_ROOT / "confirmation_merged" / "validation_manifest.json": RELEASE_ROOT / "validation" / "confirmation_manifest.json",
    RESULTS_ROOT / "analysis" / "REPORT.md": RELEASE_ROOT / "analysis" / "REPORT.md",
    RESULTS_ROOT / "analysis" / "screen_factor_effects.csv": RELEASE_ROOT / "analysis" / "screen_factor_effects.csv",
    RESULTS_ROOT / "analysis" / "confirmation_paired_summary.csv": RELEASE_ROOT / "analysis" / "confirmation_paired_summary.csv",
    RESULTS_ROOT / "analysis" / "confirmation_task_summary.csv": RELEASE_ROOT / "analysis" / "confirmation_task_summary.csv",
    RESULTS_ROOT / "analysis" / "pms_v2_validation_effects.pdf": RELEASE_ROOT / "analysis" / "pms_v2_validation_effects.pdf",
    RESULTS_ROOT / "analysis" / "pms_v2_validation_effects.png": RELEASE_ROOT / "analysis" / "pms_v2_validation_effects.png",
    RESULTS_ROOT / "analysis" / "analysis_manifest.json": RELEASE_ROOT / "analysis" / "analysis_manifest.json",
}

SOURCE_FILES = (
    "run.py",
    "experiments/exp_long_term_forecasting.py",
    "model/PMS_Mamba.py",
    "scripts/optuna/run_dataset_optuna.py",
    "scripts/financial/run_pms_v2_screen.py",
    "scripts/financial/merge_pms_v2_validation.py",
    "scripts/financial/freeze_pms_v2_selection.py",
    "scripts/financial/analyze_pms_v2_validation.py",
    "scripts/financial/build_pms_v2_release.py",
    "docs/pms_mamba_optimization_plan.md",
    "configs/financial_benchmark.json",
    "data/financial/manifests/training_datasets.json",
)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_output(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def validate_inputs() -> None:
    for source in COPIES:
        if not source.is_file():
            raise FileNotFoundError(source)
    screen = pd.read_csv(RESULTS_ROOT / "screen_merged" / "screen_results.csv")
    confirmation = pd.read_csv(RESULTS_ROOT / "confirmation_merged" / "screen_results.csv")
    if len(screen) != 1152 or len(confirmation) != 720:
        raise ValueError(f"Unexpected validation row counts: screen={len(screen)}, confirmation={len(confirmation)}")
    for name, frame in (("screen", screen), ("confirmation", confirmation)):
        if set(frame["status"]) != {"complete"}:
            raise ValueError(f"{name} contains non-complete rows")
        metrics = frame[["mae", "mse", "rmse", "mape", "mspe", "rmsse"]].to_numpy(dtype=float)
        if not np.isfinite(metrics).all():
            raise ValueError(f"{name} contains non-finite metrics")
    selection = json.loads(
        (RELEASE_ROOT / "selection" / "selection_manifest.json").read_text(encoding="utf-8")
    )
    if selection.get("test_targets_read") is not False:
        raise ValueError("Selection manifest does not certify test_targets_read=false")


def write_readme() -> Path:
    content = """# PMS-Mamba V2 validation release

This snapshot records a validation-only optimization study for forecasting under
nonstationarity. Financial panels are reference datasets, not the scope label of the
method. The protected test targets were not read during V2 screening, confirmation,
selection, or analysis.

## Result

The resolution-IV screen compared eight configurations on eight S/MS tasks, three
seeds, and six horizons (1,152 horizon-level rows). F01 and F03 were then compared
with the current PMS configuration F04 using five seeds (720 rows). F01 improved
mean validation balanced RMSSE by 1.79% and F03 by 1.68%; neither reached the frozen
2% practical threshold, so F04 was retained and no new locked-test run was opened.

## Contents

- `validation/`: exact design, horizon metrics, task-seed summaries, and manifests.
- `selection/`: frozen decision, selected per-task parameters, and checksums.
- `analysis/`: factor effects, paired diagnostics, report, figure, and provenance.
- `analysis/pms_v2_results.tex`: evidence-bound LaTeX results fragment for later inclusion.
- `release_manifest.json`: source-code hashes and runtime versions.
- `SHA256SUMS`: checksums for every release file except the checksum file itself.

## Replay

Run commands from the repository root in the `mamba` conda environment:

```bash
conda run -n mamba python scripts/financial/merge_pms_v2_validation.py
conda run -n mamba python scripts/financial/freeze_pms_v2_selection.py
conda run -n mamba python scripts/financial/analyze_pms_v2_validation.py
conda run -n mamba python scripts/financial/build_pms_v2_release.py
```

Training replay uses `scripts/financial/run_pms_v2_screen.py`; exact configuration,
task, seed, horizon, protocol, and data hashes are recorded in the manifests. No
checkpoint is required to reproduce the reported aggregate metrics from the frozen
tables; retraining requires the tracked source and the documented `mamba` conda
environment.
"""
    path = RELEASE_ROOT / "README.md"
    path.write_text(content, encoding="utf-8")
    return path


def write_manuscript_fragment() -> tuple[Path, Path]:
    fragment = r"""% Generated by scripts/financial/build_pms_v2_release.py.
% Validation-only evidence. Do not describe these results as locked-test performance.
% Requires the graphicx and booktabs packages.
\subsection{Validation-only PMS-Mamba optimization}
\label{sec:pms-v2-validation}

We evaluated eight prespecified PMS-Mamba configurations in a resolution-IV
fractional-factorial screen across eight forecasting tasks, three training seeds,
and six horizons. The two leading configurations were then evaluated with five
seeds and compared with the current PMS-Mamba configuration (F04) on the same
validation splits. F01 reduced mean balanced RMSSE by 1.79\% relative to F04
(descriptive 95\% paired bootstrap interval, 1.51\% to 2.02\%), whereas F03 reduced
it by 1.68\% (1.20\% to 2.13\%). These improvements did not meet the prespecified
2\% practical-effect threshold; therefore, F04 was retained and no new locked-test
evaluation was opened.

\begin{table}[t]
  \centering
  \caption{Five-seed validation confirmation of the two screened finalists. RMSSE
  is lower-is-better. Intervals are descriptive 95\% percentile intervals from
  10,000 paired bootstrap resamples of 40 task--seed validation summaries. The
  frozen success rule required at least 2\% overall improvement and no term-level
  degradation greater than 5\%.}
  \label{tab:pms-v2-validation}
  \begin{tabular}{lrrrr}
    \toprule
    Configuration & Mean RMSSE & Improvement & 95\% interval & Better runs \\
    \midrule
    F01 & 9.849 & 1.79\% & [1.51\%, 2.02\%] & 38/40 \\
    F03 & 9.859 & 1.68\% & [1.20\%, 2.13\%] & 28/40 \\
    F04 (reference) & 10.028 & 0.00\% & -- & -- \\
    \bottomrule
  \end{tabular}
\end{table}

The exploratory screen identified residual anchoring as the strongest favorable
factor. Its high-minus-low effect was $-1.77\%$ of the grand mean balanced RMSSE
(descriptive 95\% paired bootstrap interval, $-2.76\%$ to $-0.89\%$). Scale-normalized MSE was
unfavorable (6.11\%; 1.99\% to 10.96\%), while gated fusion and late-step weighting
had smaller average effects. Because the fractional design aliases main effects with
three-factor interactions, these estimates are diagnostic rather than confirmatory.

\begin{figure}[t]
  \centering
  % Add reproducibility/nonstationary_analysis_v2/analysis/ to \graphicspath.
  \includegraphics[width=\linewidth]{pms_v2_validation_effects.pdf}
  \caption{Validation-only PMS-Mamba V2 analysis. (A) High-minus-low factor effects
  on balanced RMSSE in 24 paired task--seed screening blocks; negative values favor
  the high factor level. Error bars are descriptive 95\% percentile intervals from
  10,000 paired bootstrap resamples. (B) Five-seed task-level improvement of F01 and
  F03 over F04; positive values favor the candidate. Color and marker shape jointly
  encode configuration. No protected test targets were used.}
  \label{fig:pms-v2-validation}
\end{figure}

Taken together, the validation study supports retaining residual anchoring as a
future design direction, but it does not support replacing the current PMS-Mamba
configuration under the frozen decision rule. A subsequent protocol should examine
long-horizon capacity or regime conditioning without reusing the protected test period
for model selection.
"""
    fragment_path = RELEASE_ROOT / "analysis" / "pms_v2_results.tex"
    fragment_path.write_text(fragment, encoding="utf-8")
    evidence = {
        "document": "analysis/pms_v2_results.tex",
        "manuscript_integration_status": "fragment_only_no_manuscript_source_present",
        "claims": [
            {
                "claim_id": "PMSV2-C001",
                "scope": "validation confirmation",
                "claim": "F01 improves mean balanced RMSSE by 1.79% versus F04 but does not meet 2%",
                "evidence": "analysis/confirmation_paired_summary.csv",
                "locator": "config_id=PMSV2_F01, metric=balanced_rmsse",
            },
            {
                "claim_id": "PMSV2-C002",
                "scope": "validation confirmation",
                "claim": "F03 improves mean balanced RMSSE by 1.68% versus F04 but does not meet 2%",
                "evidence": "analysis/confirmation_paired_summary.csv",
                "locator": "config_id=PMSV2_F03, metric=balanced_rmsse",
            },
            {
                "claim_id": "PMSV2-C003",
                "scope": "exploratory validation screen",
                "claim": "Residual anchoring is the strongest favorable screened factor",
                "evidence": "analysis/screen_factor_effects.csv",
                "locator": "factor=residual_target, metric=balanced_rmsse",
            },
            {
                "claim_id": "PMSV2-C004",
                "scope": "validation selection",
                "claim": "F04 retained and protected test not opened for V2",
                "evidence": "selection/selection_manifest.json",
                "locator": "selection_status, selected_config_id, locked_test_action",
            },
        ],
        "human_verification_required": True,
    }
    evidence_path = RELEASE_ROOT / "analysis" / "claim_evidence.json"
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return fragment_path, evidence_path


def main() -> None:
    validate_inputs()
    for source, destination in COPIES.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    readme_path = write_readme()
    fragment_path, claim_evidence_path = write_manuscript_fragment()

    source_hashes = {
        path: sha256_path(REPO_ROOT / path)
        for path in SOURCE_FILES
    }
    selection = json.loads(
        (RELEASE_ROOT / "selection" / "selection_manifest.json").read_text(encoding="utf-8")
    )
    release_manifest = {
        "release": "nonstationary_analysis_v2_validation",
        "scope": "validation-only PMS-Mamba optimization and negative ablation",
        "selection_status": selection["selection_status"],
        "selected_config_id": selection["selected_config_id"],
        "test_targets_read": False,
        "locked_test_action": selection["locked_test_action"],
        "manuscript_integration": {
            "status": "fragment_only_no_manuscript_source_present",
            "fragment": str(fragment_path.relative_to(RELEASE_ROOT)),
            "claim_evidence": str(claim_evidence_path.relative_to(RELEASE_ROOT)),
            "human_verification_required": True,
        },
        "git_head": git_output("rev-parse", "HEAD"),
        "git_worktree_dirty": bool(git_output("status", "--porcelain")),
        "runtime": {
            "python_environment": "mamba conda environment",
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "cuda_available": torch.cuda.is_available(),
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "mamba_ssm": getattr(mamba_ssm, "__version__", "unknown"),
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "row_counts": {
            "screen_horizon_rows": 1152,
            "screen_task_seed_rows": 192,
            "confirmation_horizon_rows": 720,
            "confirmation_task_seed_rows": 120,
        },
        "source_files": source_hashes,
        "release_inputs": {
            str(destination.relative_to(RELEASE_ROOT)): sha256_path(source)
            for source, destination in COPIES.items()
        },
    }
    manifest_path = RELEASE_ROOT / "release_manifest.json"
    manifest_path.write_text(
        json.dumps(release_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    release_files = sorted(
        path for path in RELEASE_ROOT.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS"
    )
    checksum_path = RELEASE_ROOT / "SHA256SUMS"
    checksum_path.write_text(
        "".join(
            f"{sha256_path(path)}  {path.relative_to(RELEASE_ROOT)}\n"
            for path in release_files
        ),
        encoding="utf-8",
    )
    print(
        f"Built {RELEASE_ROOT} with {len(release_files)} files; "
        "selection=baseline_retained test_targets_read=false"
    )


if __name__ == "__main__":
    main()
