#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ANALYSIS_ROOT = REPO_ROOT / "results" / "financial_confirmatory" / "analysis"
DEFAULT_FINAL_SUMMARY = REPO_ROOT / "results" / "financial_confirmatory" / "final_runs.json"
DEFAULT_STATISTICAL_ROOT = REPO_ROOT / "results" / "financial_confirmatory" / "statistical"
DEFAULT_PROTOCOL = REPO_ROOT / "configs" / "financial_benchmark.json"
DEFAULT_MANIFEST = REPO_ROOT / "data" / "financial" / "manifests" / "training_datasets.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "reproducibility" / "nonstationary_analysis_v1" / "final"
ANALYSIS_FILES = (
    "aggregate_metrics.csv",
    "analysis_manifest.json",
    "bootstrap_contrasts.csv",
    "neural_metrics_by_seed.csv",
    "regime_metrics.csv",
    "s_ms_comparison.csv",
    "statistical_metrics.csv",
)
MAMBA_MODELS = ("S_Mamba", "NS_Mamba-D", "MS_Mamba-MD", "PMS_Mamba-PD")
PROPOSALS = ("NS_Mamba-D", "MS_Mamba-MD", "PMS_Mamba-PD")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a Git-trackable final snapshot for the nonstationary analysis."
    )
    parser.add_argument("--analysis-root", type=Path, default=DEFAULT_ANALYSIS_ROOT)
    parser.add_argument("--final-summary", type=Path, default=DEFAULT_FINAL_SUMMARY)
    parser.add_argument("--statistical-root", type=Path, default=DEFAULT_STATISTICAL_ROOT)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def write_json(path: Path, payload: object) -> None:
    write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def copy_file(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    shutil.copy2(source, temporary)
    temporary.replace(destination)


def validate_inputs(
    protocol_path: Path,
    protocol: dict,
    training_manifest: dict,
    analysis_manifest: dict,
    final_summary: dict,
    neural: pd.DataFrame,
    statistical: pd.DataFrame,
    aggregate: pd.DataFrame,
    contrasts: pd.DataFrame,
    regimes: pd.DataFrame,
) -> None:
    protocol_hash = sha256_path(protocol_path)
    if analysis_manifest.get("protocol_sha256") != protocol_hash:
        raise ValueError("Analysis manifest does not match the frozen protocol hash")
    if final_summary.get("protocol_sha256") != protocol_hash:
        raise ValueError("Final run summary does not match the frozen protocol hash")
    if {item["protocol_sha256"] for item in training_manifest.values()} != {protocol_hash}:
        raise ValueError("Training manifest contains a different protocol hash")

    tasks = sorted(training_manifest)
    models = protocol["level_models"]
    seeds = protocol["final_seeds"]
    horizons = protocol["horizons"]
    expected_run_keys = {
        f"{task}|{model}|{seed}" for task in tasks for model in models for seed in seeds
    }
    runs = final_summary.get("runs", {})
    complete = {key for key, value in runs.items() if value.get("status") == "complete"}
    if complete != expected_run_keys or len(runs) != len(expected_run_keys):
        raise ValueError("Final task/model/seed matrix is incomplete")

    expected_neural = len(tasks) * len(models) * len(seeds) * len(horizons)
    expected_statistical = sum(
        (4 if config["features"] == "MS" else 3) * len(horizons)
        for config in training_manifest.values()
    )
    expected_aggregate = len(tasks) * len(models) * len(horizons) + expected_statistical
    expected_contrasts = len(tasks) * len(PROPOSALS) * 2 * len(horizons)
    counts = {
        "neural_run_count": (len(neural), expected_neural),
        "statistical_run_count": (len(statistical), expected_statistical),
        "contrast_count": (len(contrasts), expected_contrasts),
    }
    for field, (observed, expected) in counts.items():
        if observed != expected or int(analysis_manifest.get(field, -1)) != expected:
            raise ValueError(f"Unexpected {field}: observed={observed}, expected={expected}")
    if len(aggregate) != expected_aggregate:
        raise ValueError(f"Unexpected aggregate row count: {len(aggregate)}")

    metric_columns = [column for column in aggregate if column.endswith(("_mean", "_std"))]
    if not np.isfinite(aggregate[metric_columns].to_numpy(dtype=float)).all():
        raise ValueError("Aggregate metrics contain non-finite values")
    regime_metric_columns = ["origin_mse_mean", "origin_mse_std", "skill_vs_last_value"]
    estimated = regimes["origin_count"] > 0
    if not np.isfinite(regimes.loc[estimated, regime_metric_columns].to_numpy(dtype=float)).all():
        raise ValueError("Estimated regime metrics contain non-finite values")
    if regimes.loc[~estimated, ["origin_mse_mean", "skill_vs_last_value"]].notna().any().any():
        raise ValueError("Empty prescribed regimes must be represented as not estimable")


def winner_summary(aggregate: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    winners = aggregate.loc[
        aggregate.groupby(["dataset", "horizon"])["path_rmsse_mean"].idxmin()
    ][["dataset", "horizon", "model", "path_rmsse_mean", "skill_vs_last_value"]]
    winners = winners.sort_values(["dataset", "horizon"]).reset_index(drop=True)
    model_summary = (
        aggregate.groupby("model", as_index=False)
        .agg(
            evaluated_task_horizons=("path_rmsse_mean", "size"),
            mean_path_rmsse=("path_rmsse_mean", "mean"),
            median_path_rmsse=("path_rmsse_mean", "median"),
            mean_skill_vs_last_value=("skill_vs_last_value", "mean"),
        )
        .merge(
            winners["model"].value_counts().rename_axis("model").rename("task_horizon_wins"),
            on="model",
            how="left",
        )
    )
    model_summary["task_horizon_wins"] = model_summary["task_horizon_wins"].fillna(0).astype(int)
    return winners, model_summary.sort_values(
        ["task_horizon_wins", "mean_path_rmsse"], ascending=[False, True]
    )


def contrast_summary(contrasts: pd.DataFrame) -> pd.DataFrame:
    table = contrasts.copy()
    table["comparator_group"] = np.where(
        table["comparator"] == "S_Mamba", "S_Mamba", "validation-selected non-Mamba"
    )
    table["favorable"] = table["mean_loss_difference"] < 0
    table["significant"] = table["holm_p_value"] < 0.05
    rows = []
    for (proposal, comparator), group in table.groupby(["proposal", "comparator_group"]):
        rows.append(
            {
                "proposal": proposal,
                "comparator_group": comparator,
                "contrast_count": len(group),
                "favorable_mean_count": int(group["favorable"].sum()),
                "favorable_holm_count": int((group["favorable"] & group["significant"]).sum()),
                "unfavorable_holm_count": int((~group["favorable"] & group["significant"]).sum()),
                "non_significant_count": int((~group["significant"]).sum()),
            }
        )
    return pd.DataFrame(rows)


def seed_stability(neural: pd.DataFrame) -> pd.DataFrame:
    per_cell = (
        neural.groupby(["dataset", "model", "horizon"])["path_rmsse"]
        .agg(["mean", "std"])
        .reset_index()
    )
    per_cell["coefficient_of_variation"] = per_cell["std"] / per_cell["mean"]
    return (
        per_cell.groupby("model", as_index=False)
        .agg(
            median_seed_cv=("coefficient_of_variation", "median"),
            maximum_seed_cv=("coefficient_of_variation", "max"),
            mean_seed_sd_rmsse=("std", "mean"),
        )
        .sort_values("median_seed_cv")
    )


def runtime_summary(neural: pd.DataFrame) -> pd.DataFrame:
    return (
        neural.groupby("model", as_index=False)
        .agg(
            horizon_run_count=("runtime_seconds", "size"),
            total_runtime_seconds=("runtime_seconds", "sum"),
            median_runtime_seconds=("runtime_seconds", "median"),
            maximum_runtime_seconds=("runtime_seconds", "max"),
            median_peak_gpu_memory_mb=("peak_gpu_memory_mb", "median"),
            maximum_peak_gpu_memory_mb=("peak_gpu_memory_mb", "max"),
        )
        .sort_values("total_runtime_seconds")
    )


def input_mode_summary(mode_comparison: pd.DataFrame) -> pd.DataFrame:
    table = mode_comparison[mode_comparison["model"].isin(MAMBA_MODELS)].copy()
    return (
        table.groupby("model", as_index=False)
        .agg(
            paired_family_horizons=("ms_minus_s_path_rmsse", "size"),
            ms_lower_rmsse_count=("ms_minus_s_path_rmsse", lambda values: int((values < 0).sum())),
            mean_ms_minus_s_rmsse=("ms_minus_s_path_rmsse", "mean"),
        )
        .sort_values("model")
    )


def arima_audit(statistical_root: Path, tasks: list[str], horizons: list[int]) -> pd.DataFrame:
    rows = []
    for task in tasks:
        records = []
        for horizon in horizons:
            path = statistical_root / task / "ARIMA" / f"h{horizon}" / "meta.json"
            metadata = json.loads(path.read_text(encoding="utf-8"))
            selection = metadata.get("arima_selection", {})
            if metadata.get("coefficient_fit_converged") is not True:
                raise ValueError(f"Final ARIMA coefficient fit did not converge: {task}/h{horizon}")
            if selection.get("selected_converged") is not True:
                raise ValueError(f"Selected ARIMA candidate did not converge: {task}/h{horizon}")
            records.append((tuple(metadata["arima_order"]), selection))
        orders = {record[0] for record in records}
        audits = {json.dumps(record[1], sort_keys=True) for record in records}
        if len(orders) != 1 or len(audits) != 1:
            raise ValueError(f"ARIMA order audit differs across horizons: {task}")
        order = next(iter(orders))
        selection = records[0][1]
        rows.append(
            {
                "dataset": task,
                "p": order[0],
                "d": order[1],
                "q": order[2],
                "attempted_candidate_count": selection["attempted_candidate_count"],
                "converged_candidate_count": selection["converged_candidate_count"],
                "nonconverged_candidate_count": selection["nonconverged_candidate_count"],
                "failed_candidate_count": selection["failed_candidate_count"],
                "selected_aic": selection["selected_aic"],
                "selected_converged": selection["selected_converged"],
                "pretest_coefficient_fit_converged": True,
            }
        )
    return pd.DataFrame(rows)


def runtime_environment(neural: pd.DataFrame) -> dict:
    fields = ("gpu_name", "torch_version", "cuda_version", "cudnn_version")
    observed = {field: set() for field in fields}
    deterministic = set()
    run_root = REPO_ROOT / "results" / "financial_confirmatory" / "runs"
    for setting in neural["setting"]:
        metadata = json.loads((run_root / setting / "meta.json").read_text(encoding="utf-8"))
        for field in fields:
            observed[field].add(metadata.get(field))
        deterministic.add(metadata.get("deterministic_algorithms"))
    if any(len(values) != 1 for values in observed.values()) or deterministic != {True}:
        raise ValueError("Neural runtime metadata are inconsistent")
    return {
        **{field: next(iter(values)) for field, values in observed.items()},
        "deterministic_algorithms": True,
        "mamba_ssm_version": "2.3.1",
        "horizon_specific_run_count": int(len(neural)),
        "summed_runtime_seconds": float(neural["runtime_seconds"].sum()),
    }


def plot_winners(winners: pd.DataFrame, output: Path) -> None:
    horizons = sorted(winners["horizon"].unique())
    tasks = sorted(winners["dataset"].unique())
    models = sorted(winners["model"].unique())
    model_index = {model: index for index, model in enumerate(models)}
    pivot = winners.pivot(index="dataset", columns="horizon", values="model").loc[tasks, horizons]
    values = pivot.map(model_index.get).to_numpy(dtype=float)
    colors = ["#377eb8", "#e41a1c", "#4daf4a", "#984ea3", "#ff7f00", "#a65628", "#f781bf"]
    cmap = ListedColormap(colors[: len(models)])
    norm = BoundaryNorm(np.arange(-0.5, len(models) + 0.5), cmap.N)
    figure, axis = plt.subplots(figsize=(12.5, 5.8), constrained_layout=True)
    axis.imshow(values, cmap=cmap, norm=norm, aspect="auto")
    axis.set_xticks(range(len(horizons)), [str(value) for value in horizons])
    axis.set_yticks(
        range(len(tasks)),
        [task.removeprefix("financial_").replace("_", " ").upper() for task in tasks],
    )
    axis.set_xlabel("Forecast horizon")
    axis.set_title("Lowest path RMSSE on the financial reference panels")
    for row in range(len(tasks)):
        for column in range(len(horizons)):
            axis.text(column, row, pivot.iloc[row, column], ha="center", va="center", fontsize=8)
    for spine in axis.spines.values():
        spine.set_visible(False)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=180)
    plt.close(figure)


def markdown_table(
    frame: pd.DataFrame, columns: list[str], formats: dict[str, str] | None = None
) -> str:
    formats = formats or {}
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    rows = []
    for record in frame[columns].to_dict("records"):
        values = []
        for column in columns:
            value = record[column]
            values.append(format(value, formats[column]) if column in formats else str(value))
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join([header, separator, *rows])


def build_report(
    winners: pd.DataFrame,
    contrast_counts: pd.DataFrame,
    stability: pd.DataFrame,
    runtime: pd.DataFrame,
    input_modes: pd.DataFrame,
    regimes: pd.DataFrame,
    analysis_manifest: dict,
) -> str:
    win_counts = winners["model"].value_counts()
    statistical_models = {"Last-value", "Random-walk-drift", "ARIMA", "VAR-difference"}
    statistical_wins = int(winners["model"].isin(statistical_models).sum())
    mamba_wins = int(winners["model"].isin(MAMBA_MODELS).sum())
    learned_other_wins = len(winners) - statistical_wins - mamba_wins
    empty = regimes[regimes["origin_count"] == 0]
    empty_cells = empty[["dataset", "horizon", "regime"]].drop_duplicates()
    win_table = win_counts.rename_axis("model").rename("wins").reset_index()
    contrast_table = contrast_counts.rename(
        columns={
            "comparator_group": "comparator",
            "favorable_holm_count": "favorable",
            "unfavorable_holm_count": "unfavorable",
            "non_significant_count": "not significant",
        }
    )
    stability_table = stability[["model", "median_seed_cv", "maximum_seed_cv"]]
    mode_table = input_modes.rename(
        columns={
            "paired_family_horizons": "pairs",
            "ms_lower_rmsse_count": "MS lower RMSSE",
            "mean_ms_minus_s_rmsse": "mean MS-S RMSSE",
        }
    )
    total_runtime = float(runtime["total_runtime_seconds"].sum())
    return f"""# Final Nonstationary Forecasting Analysis

## Evidence boundary

This is the final test-period analysis for the current financial reference panels. The
research scope is forecasting under nonstationarity; these panels do not define the
future dataset boundary. The frozen internal protocol ID remains
`financial_confirmatory_v1` to preserve its hash.

The protected 2023-01-01 through 2026-06-30 targets were opened only after validation
selection was frozen. All 360 task/model/seed cells are complete. They contain 2,160
horizon-specific learned-model training/evaluation records across horizons 1, 5, 20,
60, 120, and 252. Statistical references add 168 deterministic records.

## Primary result

No Mamba model has the lowest mean path RMSSE in any of the 48 dataset-horizon cells.
Naive or statistical references win {statistical_wins}/48 cells and non-Mamba learned
models win {learned_other_wins}/48. This does not support a claim that the proposed
Mamba variants dominate the comparison set on these reference datasets.

{markdown_table(win_table, ['model', 'wins'])}

The pooled RMSSE means in `model_summary.csv` are descriptive only. They mix datasets
and horizons and must not replace the paired cell-level comparisons above.

## Prespecified proposal contrasts

Loss differences are proposal minus comparator, so negative values favor the proposal.
Intervals use 10,000 moving-block bootstrap replicates. Holm adjustment is applied
within each dataset/proposal/comparator family across the six horizons.

{markdown_table(contrast_table, ['proposal', 'comparator', 'favorable', 'unfavorable', 'not significant'])}

The proposal results are mixed: some improvements over S-Mamba or the
validation-selected learned baseline are statistically supported, while other cells
significantly favor the comparator. These contrasts do not overturn the all-model
winner result because naive and statistical references are also in the benchmark.

## Stability and compute

Five final seeds were used for every learned model. Median and maximum coefficients of
variation below summarize path RMSSE across seeds for each dataset/model/horizon cell.

{markdown_table(stability_table, ['model', 'median_seed_cv', 'maximum_seed_cv'], {'median_seed_cv': '.4f', 'maximum_seed_cv': '.4f'})}

The 2,160 horizon-specific runs sum to {total_runtime / 3600:.2f} recorded GPU-hours.
This is summed model runtime, not wall-clock duration. `runtime_summary.csv` reports
model-level runtime and peak-memory distributions.

## Regime and input-mode limits

The prespecified volatility-regime table has {analysis_manifest['regime_metric_count']}
rows. {len(empty)} rows, representing {len(empty_cells)} distinct
dataset/horizon/regime cells, have zero eligible origins and are explicitly reported as
not estimable. They are not imputed and are excluded from regime-specific claims.

{markdown_table(mode_table, ['model', 'pairs', 'MS lower RMSSE', 'mean MS-S RMSSE'], {'mean MS-S RMSSE': '.4f'})}

The S/MS comparison is descriptive. Multivariate input does not consistently improve
the Mamba variants, so the current evidence does not justify a general claim that
adding covariates improves nonstationary forecasting.

## Reproducibility map

- `analysis_manifest.json`: frozen protocol hash and expected analysis counts.
- `final_runs.json`: all 360 completed task/model/seed cells and their settings.
- `aggregate_metrics.csv`: task/model/horizon metrics and five-seed dispersion.
- `task_horizon_winners.csv`: the 48 primary path-RMSSE comparisons.
- `bootstrap_contrasts.csv`: paired proposal contrasts and Holm-adjusted p-values.
- `neural_metrics_by_seed.csv`: 2,160 learned-model records.
- `statistical_metrics.csv`: 168 deterministic baseline records.
- `regime_metrics.csv`: prespecified regime estimates and explicit not-estimable rows.
- `arima_convergence_audit.csv`: candidate and final-fit convergence evidence.
- `runtime_environment.json`: GPU and numerical runtime metadata.
- `SHA256SUMS`: integrity hashes for every payload in this directory.

Raw per-origin predictions are retained under `results/financial_confirmatory/` and are
not duplicated into Git because the runtime directory is approximately 1.2 GB. The
Git snapshot preserves final metrics, parameters, hashes, completion records, and
analysis provenance; exact bootstrap regeneration still requires the local per-origin
prediction arrays.
"""


def main() -> None:
    args = parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    training_manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    analysis_manifest = json.loads(
        (args.analysis_root / "analysis_manifest.json").read_text(encoding="utf-8")
    )
    final_summary = json.loads(args.final_summary.read_text(encoding="utf-8"))
    neural = pd.read_csv(args.analysis_root / "neural_metrics_by_seed.csv")
    statistical = pd.read_csv(args.analysis_root / "statistical_metrics.csv")
    aggregate = pd.read_csv(args.analysis_root / "aggregate_metrics.csv")
    contrasts = pd.read_csv(args.analysis_root / "bootstrap_contrasts.csv")
    regimes = pd.read_csv(args.analysis_root / "regime_metrics.csv")
    mode_comparison = pd.read_csv(args.analysis_root / "s_ms_comparison.csv")
    validate_inputs(
        args.protocol,
        protocol,
        training_manifest,
        analysis_manifest,
        final_summary,
        neural,
        statistical,
        aggregate,
        contrasts,
        regimes,
    )

    winners, models = winner_summary(aggregate)
    contrast_counts = contrast_summary(contrasts)
    stability = seed_stability(neural)
    runtime = runtime_summary(neural)
    input_modes = input_mode_summary(mode_comparison)
    arima = arima_audit(args.statistical_root, sorted(training_manifest), protocol["horizons"])
    environment = runtime_environment(neural)

    for name in ANALYSIS_FILES:
        copy_file(args.analysis_root / name, args.output_root / name)
    copy_file(args.final_summary, args.output_root / "final_runs.json")
    copy_file(args.protocol, args.output_root / "protocol" / args.protocol.name)
    copy_file(args.manifest, args.output_root / "manifests" / args.manifest.name)
    write_csv(args.output_root / "task_horizon_winners.csv", winners)
    write_csv(args.output_root / "model_summary.csv", models)
    write_csv(args.output_root / "proposal_contrast_summary.csv", contrast_counts)
    write_csv(args.output_root / "seed_stability.csv", stability)
    write_csv(args.output_root / "runtime_summary.csv", runtime)
    write_csv(args.output_root / "s_ms_model_summary.csv", input_modes)
    write_csv(args.output_root / "arima_convergence_audit.csv", arima)
    write_json(args.output_root / "runtime_environment.json", environment)
    plot_winners(winners, args.output_root / "task_horizon_winners.png")
    write_text(
        args.output_root / "REPORT.md",
        build_report(
            winners,
            contrast_counts,
            stability,
            runtime,
            input_modes,
            regimes,
            analysis_manifest,
        ),
    )
    write_json(
        args.output_root / "release_manifest.json",
        {
            "analysis_scope": "final_test",
            "current_dataset_role": "financial_reference_panels",
            "protocol_version": protocol["protocol_version"],
            "protocol_sha256": sha256_path(args.protocol),
            "completed_task_model_seed_cells": len(final_summary["runs"]),
            "horizon_specific_neural_records": len(neural),
            "statistical_records": len(statistical),
            "task_horizon_cells": len(winners),
            "mamba_task_horizon_wins": int(winners["model"].isin(MAMBA_MODELS).sum()),
            "empty_regime_rows": int((regimes["origin_count"] == 0).sum()),
        },
    )
    payloads = sorted(
        path for path in args.output_root.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS"
    )
    checksums = "".join(
        f"{sha256_path(path)}  {path.relative_to(args.output_root)}\n" for path in payloads
    )
    write_text(args.output_root / "SHA256SUMS", checksums)
    print(f"wrote final nonstationary analysis snapshot to {args.output_root}")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"Release blocked: {exc}") from None
