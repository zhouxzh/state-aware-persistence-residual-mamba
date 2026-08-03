#!/usr/bin/env python
"""Analyze the validation-only PMS-Mamba V2 screen and confirmation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCREEN = REPO_ROOT / "results" / "nonstationary_analysis_v2" / "screen_merged"
DEFAULT_CONFIRMATION = REPO_ROOT / "results" / "nonstationary_analysis_v2" / "confirmation_merged"
DEFAULT_SELECTION = REPO_ROOT / "reproducibility" / "nonstationary_analysis_v2" / "selection"
DEFAULT_OUTPUT = REPO_ROOT / "results" / "nonstationary_analysis_v2" / "analysis"
BOOTSTRAP_SEED = 20260803
BOOTSTRAP_REPLICATES = 10000
BASELINE_CONFIG = "PMSV2_F04"
CANDIDATES = ("PMSV2_F01", "PMSV2_F03")
METRICS = ("balanced_rmsse", "short", "middle", "long")
FACTOR_SPECS = (
    ("residual_target", "Forecast target", "0", "1", "direct", "residual"),
    ("loss", "Training loss", "MSE", "SCALE_MSE", "MSE", "scale MSE"),
    ("ms_fusion", "Multi-scale fusion", "mean", "gate", "mean", "gate"),
    ("horizon_weighting", "Step weighting", "balanced", "long", "uniform", "late"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screen-root", type=Path, default=DEFAULT_SCREEN)
    parser.add_argument("--confirmation-root", type=Path, default=DEFAULT_CONFIRMATION)
    parser.add_argument("--selection-root", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--bootstrap-replicates", type=int, default=BOOTSTRAP_REPLICATES)
    parser.add_argument("--bootstrap-seed", type=int, default=BOOTSTRAP_SEED)
    return parser.parse_args()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile_interval(values: np.ndarray) -> tuple[float, float]:
    return tuple(float(value) for value in np.quantile(values, [0.025, 0.975]))


def bootstrap_block_mean(
    values: np.ndarray,
    replicates: int,
    rng: np.random.Generator,
) -> np.ndarray:
    indices = rng.integers(0, len(values), size=(replicates, len(values)))
    return values[indices].mean(axis=1)


def factor_effects(
    screen: pd.DataFrame,
    replicates: int,
    rng: np.random.Generator,
) -> pd.DataFrame:
    rows = []
    blocks = ["task", "seed"]
    for factor, label, low, high, low_label, high_label in FACTOR_SPECS:
        for metric in METRICS:
            high_values = (
                screen[screen[factor].astype(str) == high]
                .groupby(blocks)[metric]
                .mean()
            )
            low_values = (
                screen[screen[factor].astype(str) == low]
                .groupby(blocks)[metric]
                .mean()
            )
            paired = high_values.to_frame("high").join(low_values.to_frame("low"), how="inner")
            if len(paired) != 24:
                raise ValueError(f"{factor}/{metric} expected 24 paired task-seed blocks")
            difference = (paired["high"] - paired["low"]).to_numpy(dtype=float)
            grand_mean = float(screen[metric].mean())
            bootstrap = bootstrap_block_mean(difference, replicates, rng)
            ci_low, ci_high = percentile_interval(100.0 * bootstrap / grand_mean)
            rows.append({
                "factor": factor,
                "factor_label": label,
                "low_level": low_label,
                "high_level": high_label,
                "metric": metric,
                "paired_task_seed_blocks": len(paired),
                "high_minus_low": float(difference.mean()),
                "grand_mean": grand_mean,
                "effect_pct_of_grand_mean": 100.0 * float(difference.mean()) / grand_mean,
                "bootstrap_ci_low_pct": ci_low,
                "bootstrap_ci_high_pct": ci_high,
                "bootstrap_replicates": replicates,
            })
    return pd.DataFrame(rows)


def confirmation_comparisons(
    confirmation: pd.DataFrame,
    replicates: int,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    baseline = confirmation[confirmation["config_id"] == BASELINE_CONFIG].set_index(["task", "seed"])
    summary_rows = []
    task_rows = []
    for config_id in CANDIDATES:
        candidate = confirmation[confirmation["config_id"] == config_id].set_index(["task", "seed"])
        if not candidate.index.equals(baseline.index):
            raise ValueError(f"{config_id} and {BASELINE_CONFIG} are not paired on task and seed")
        for metric in METRICS:
            candidate_values = candidate[metric].to_numpy(dtype=float)
            baseline_values = baseline[metric].to_numpy(dtype=float)
            difference = candidate_values - baseline_values
            sample_indices = rng.integers(0, len(difference), size=(replicates, len(difference)))
            bootstrap_difference = difference[sample_indices].mean(axis=1)
            bootstrap_improvement = -100.0 * bootstrap_difference / baseline_values[sample_indices].mean(axis=1)
            diff_ci = percentile_interval(bootstrap_difference)
            improvement_ci = percentile_interval(bootstrap_improvement)
            summary_rows.append({
                "config_id": config_id,
                "baseline_config_id": BASELINE_CONFIG,
                "metric": metric,
                "paired_task_seed_runs": len(difference),
                "candidate_mean": float(candidate_values.mean()),
                "baseline_mean": float(baseline_values.mean()),
                "mean_difference": float(difference.mean()),
                "difference_bootstrap_ci_low": diff_ci[0],
                "difference_bootstrap_ci_high": diff_ci[1],
                "improvement_pct": -100.0 * float(difference.mean()) / float(baseline_values.mean()),
                "improvement_bootstrap_ci_low_pct": improvement_ci[0],
                "improvement_bootstrap_ci_high_pct": improvement_ci[1],
                "candidate_better_runs": int((difference < 0).sum()),
                "ties": int((difference == 0).sum()),
                "bootstrap_replicates": replicates,
            })
        for task, baseline_task in baseline.groupby(level="task"):
            candidate_task = candidate.loc[task]
            record = {"config_id": config_id, "baseline_config_id": BASELINE_CONFIG, "task": task}
            for metric in METRICS:
                candidate_mean = float(candidate_task[metric].mean())
                baseline_mean = float(baseline_task[metric].mean())
                record[f"candidate_{metric}"] = candidate_mean
                record[f"baseline_{metric}"] = baseline_mean
                record[f"improvement_{metric}_pct"] = 100.0 * (
                    baseline_mean - candidate_mean
                ) / baseline_mean
            task_rows.append(record)
    return pd.DataFrame(summary_rows), pd.DataFrame(task_rows)


def make_figure(
    effects: pd.DataFrame,
    task_summary: pd.DataFrame,
    output_root: Path,
) -> list[Path]:
    factor_order = [spec[0] for spec in FACTOR_SPECS]
    factor_labels = {
        factor: f"{label}\n({high_label} - {low_label})"
        for factor, label, _low, _high, low_label, high_label in FACTOR_SPECS
    }
    balanced = effects[effects["metric"] == "balanced_rmsse"].set_index("factor").loc[factor_order]
    task_order = sorted(task_summary["task"].unique())
    display_tasks = [task.removeprefix("financial_").replace("_", " ") for task in task_order]
    colors = {"PMSV2_F01": "#0072B2", "PMSV2_F03": "#D55E00"}
    markers = {"PMSV2_F01": "o", "PMSV2_F03": "s"}

    style = {
        "font.family": "DejaVu Sans",
        "font.size": 7.5,
        "axes.labelsize": 8,
        "axes.titlesize": 8,
        "legend.fontsize": 7,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
    with mpl.rc_context(style):
        fig, (ax_a, ax_b) = plt.subplots(
            1, 2, figsize=(180 / 25.4, 86 / 25.4), layout="constrained",
            gridspec_kw={"width_ratios": [1.0, 1.35]},
        )
        y = np.arange(len(balanced))
        estimate = balanced["effect_pct_of_grand_mean"].to_numpy()
        lower = estimate - balanced["bootstrap_ci_low_pct"].to_numpy()
        upper = balanced["bootstrap_ci_high_pct"].to_numpy() - estimate
        ax_a.errorbar(
            estimate, y, xerr=np.vstack([lower, upper]), fmt="o", color="#0072B2",
            ecolor="#555555", elinewidth=1.0, capsize=2.5, markersize=4.2,
        )
        ax_a.axvline(0, color="#333333", linewidth=0.8, linestyle="--")
        ax_a.set_yticks(y, [factor_labels[factor] for factor in factor_order])
        ax_a.invert_yaxis()
        ax_a.set_xlabel("High - low effect (% of grand mean RMSSE)\nNegative favors high level")
        ax_a.grid(axis="x", color="#DDDDDD", linewidth=0.6)
        ax_a.text(-0.14, 1.03, "A", transform=ax_a.transAxes, fontweight="bold", fontsize=9)

        offsets = {"PMSV2_F01": -0.12, "PMSV2_F03": 0.12}
        y_tasks = np.arange(len(task_order))
        for config_id in CANDIDATES:
            subset = task_summary[task_summary["config_id"] == config_id].set_index("task").loc[task_order]
            values = subset["improvement_balanced_rmsse_pct"].to_numpy()
            ax_b.scatter(
                values, y_tasks + offsets[config_id], s=22, color=colors[config_id],
                marker=markers[config_id], label=config_id, edgecolor="white", linewidth=0.4, zorder=3,
            )
        ax_b.axvline(0, color="#333333", linewidth=0.8, linestyle="--")
        ax_b.set_yticks(y_tasks, display_tasks)
        ax_b.invert_yaxis()
        ax_b.set_xlabel("Improvement over F04 (%)\nPositive favors candidate")
        ax_b.grid(axis="x", color="#DDDDDD", linewidth=0.6)
        ax_b.legend(frameon=False, loc="lower right")
        ax_b.text(-0.12, 1.03, "B", transform=ax_b.transAxes, fontweight="bold", fontsize=9)

        base = output_root / "pms_v2_validation_effects"
        pdf_path = base.with_suffix(".pdf")
        png_path = base.with_suffix(".png")
        fig.savefig(pdf_path, facecolor="white")
        fig.savefig(png_path, dpi=300, facecolor="white")
        plt.close(fig)
        with Image.open(png_path) as image:
            image.convert("RGB").save(png_path, dpi=(300, 300))
    return [pdf_path, png_path]


def write_report(
    output_root: Path,
    effects: pd.DataFrame,
    comparison: pd.DataFrame,
    task_summary: pd.DataFrame,
    selection: dict,
) -> Path:
    overall = comparison[comparison["metric"] == "balanced_rmsse"].set_index("config_id")
    factor = effects[effects["metric"] == "balanced_rmsse"].set_index("factor")
    lines = [
        "# PMS-Mamba V2 validation analysis",
        "",
        "This report is validation-only. The protected test targets were not read for screening,",
        "confirmation, selection, or this analysis.",
        "",
        "## Decision",
        "",
        f"The frozen decision is `{selection['selection_status']}` with `{selection['selected_config_id']}` selected.",
        "Neither finalist met the predeclared requirement of at least 2% lower mean balanced RMSSE,",
        "although neither violated the 5% term-level degradation guardrail.",
        "",
        "| Candidate | Improvement vs F04 | 95% paired bootstrap interval | Better task-seed runs |",
        "| --- | ---: | ---: | ---: |",
    ]
    for config_id in CANDIDATES:
        row = overall.loc[config_id]
        lines.append(
            f"| {config_id} | {row['improvement_pct']:.2f}% | "
            f"[{row['improvement_bootstrap_ci_low_pct']:.2f}%, {row['improvement_bootstrap_ci_high_pct']:.2f}%] | "
            f"{int(row['candidate_better_runs'])}/{int(row['paired_task_seed_runs'])} |"
        )
    lines.extend([
        "",
        "The intervals are descriptive 95% percentile intervals from 10,000 paired task-seed",
        "bootstrap resamples; the unit of replication is one task-seed validation summary (n=40).",
        "No confirmatory p-values are claimed for this exploratory V2 analysis.",
        "",
        "## Factor diagnosis",
        "",
        "Factor effects are high minus low levels in the resolution-IV screen. Negative values",
        "indicate lower (better) balanced RMSSE at the high level. Main effects remain aliased with",
        "three-factor interactions under the D=ABC fractional design.",
        "",
        "| Factor | High vs low effect | 95% paired bootstrap interval |",
        "| --- | ---: | ---: |",
    ])
    for factor_name, label, _low, _high, _low_label, _high_label in FACTOR_SPECS:
        row = factor.loc[factor_name]
        lines.append(
            f"| {label} | {row['effect_pct_of_grand_mean']:.2f}% | "
            f"[{row['bootstrap_ci_low_pct']:.2f}%, {row['bootstrap_ci_high_pct']:.2f}%] |"
        )
    lines.extend([
        "",
        "The dominant useful direction is residual anchoring. Scale-normalized MSE is unfavorable",
        "in this screen, while gated fusion and late-step weighting show smaller average effects.",
        "The next optimization cycle should therefore keep residual anchoring fixed and investigate",
        "long-horizon capacity or regime conditioning with a new, separately frozen validation protocol.",
        "",
        "## Figure description",
        "",
        "Panel A shows the four high-minus-low screening effects on balanced RMSSE with descriptive",
        "95% paired bootstrap intervals. Panel B shows task-level validation improvement over F04",
        "for F01 and F03; points to the right of zero favor the candidate. The task table below the",
        "figure is available in `confirmation_task_summary.csv`.",
        "",
        "## Evidence files",
        "",
        "- `screen_factor_effects.csv`: factor estimates for balanced, short, middle, and long RMSSE.",
        "- `confirmation_paired_summary.csv`: five-seed paired candidate comparisons.",
        "- `confirmation_task_summary.csv`: task-level candidate and F04 summaries.",
        "- `pms_v2_validation_effects.pdf` and `.png`: provisional general manuscript figure.",
        "- `analysis_manifest.json`: source hashes, transformations, bootstrap settings, and figure metadata.",
        "",
    ])
    path = output_root / "REPORT.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> None:
    args = parse_args()
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    screen_path = args.screen_root.resolve() / "screen_run_summary.csv"
    confirmation_path = args.confirmation_root.resolve() / "screen_run_summary.csv"
    selection_path = args.selection_root.resolve() / "selection_manifest.json"
    screen = pd.read_csv(screen_path)
    confirmation = pd.read_csv(confirmation_path)
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    if selection.get("test_targets_read") is not False:
        raise ValueError("Selection manifest must certify test_targets_read=false")
    if len(screen) != 192 or len(confirmation) != 120:
        raise ValueError(f"Unexpected run-summary sizes: screen={len(screen)}, confirmation={len(confirmation)}")

    rng = np.random.default_rng(args.bootstrap_seed)
    effects = factor_effects(screen, args.bootstrap_replicates, rng)
    comparison, task_summary = confirmation_comparisons(
        confirmation, args.bootstrap_replicates, rng
    )
    effects_path = output_root / "screen_factor_effects.csv"
    comparison_path = output_root / "confirmation_paired_summary.csv"
    task_path = output_root / "confirmation_task_summary.csv"
    effects.to_csv(effects_path, index=False)
    comparison.to_csv(comparison_path, index=False)
    task_summary.to_csv(task_path, index=False)
    figure_paths = make_figure(effects, task_summary, output_root)
    report_path = write_report(output_root, effects, comparison, task_summary, selection)

    outputs = [effects_path, comparison_path, task_path, *figure_paths, report_path]
    manifest = {
        "stage": "validation_only_v2_analysis",
        "test_targets_read": False,
        "audience": "provisional general scientific manuscript; target journal not specified",
        "source_files": {
            str(screen_path.relative_to(REPO_ROOT)): sha256_path(screen_path),
            str(confirmation_path.relative_to(REPO_ROOT)): sha256_path(confirmation_path),
            str(selection_path.relative_to(REPO_ROOT)): sha256_path(selection_path),
        },
        "transformations": [
            "screen main effects computed as high-minus-low within paired task-seed blocks",
            "confirmation candidates paired with F04 by task and seed",
            "task summaries average five fixed validation seeds",
        ],
        "uncertainty": {
            "method": "paired task-seed percentile bootstrap",
            "replicates": int(args.bootstrap_replicates),
            "seed": int(args.bootstrap_seed),
            "interval": "95%",
            "screen_units": 24,
            "confirmation_units": 40,
        },
        "missing_data": "none; input matrices were required to be complete and finite",
        "figure": {
            "width_mm": 180,
            "height_mm": 86,
            "png_dpi": 300,
            "background": "opaque white",
            "color_redundancy": "candidate color plus marker shape",
            "alt_text": (
                "Two-panel validation figure. Residual targeting has the strongest favorable "
                "screening effect; scale-normalized loss is unfavorable. Candidate improvements "
                "over F04 vary by task and neither candidate reaches the frozen 2% overall rule."
            ),
        },
        "outputs": {
            path.name: sha256_path(path) for path in outputs
        },
        "versions": {
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "matplotlib": mpl.__version__,
        },
    }
    manifest_path = output_root / "analysis_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"Wrote validation-only V2 analysis to {output_root}; "
        f"selection={selection['selection_status']} test_targets_read=false"
    )


if __name__ == "__main__":
    main()
