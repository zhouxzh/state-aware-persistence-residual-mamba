#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROTOCOL = REPO_ROOT / "configs" / "financial_benchmark.json"
DEFAULT_MANIFEST = REPO_ROOT / "data" / "financial" / "manifests" / "training_datasets.json"
DEFAULT_QUALITY = REPO_ROOT / "data" / "financial" / "manifests" / "quality_report.json"
DEFAULT_DIAGNOSTICS = (
    REPO_ROOT
    / "data"
    / "financial"
    / "manifests"
    / "nonstationarity_diagnostics_selection_safe.json"
)
DEFAULT_SELECTION_ROOT = REPO_ROOT / "results" / "optuna"
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT
    / "results"
    / "nonstationary_analysis"
    / "financial_reference_v1"
    / "selection_safe"
)

MAMBA_MODELS = {"S_Mamba", "NS_Mamba-D", "MS_Mamba-MD", "PMS_Mamba-PD"}
PROPOSALS = ("NS_Mamba-D", "MS_Mamba-MD", "PMS_Mamba-PD")
ARCHITECTURES = {
    "DLinear": ("linear", "moving-average decomposition with linear heads"),
    "NLinear": ("linear", "last-value normalization with a linear head"),
    "PatchTST": ("transformer", "channel-independent temporal patch Transformer"),
    "TimesNet": ("convolutional", "multi-period 2D temporal representation"),
    "iTransformer": ("transformer", "inverted variable-token Transformer"),
    "S_Mamba": ("mamba baseline", "normalized inverted tokens with bidirectional Mamba"),
    "NS_Mamba-D": ("mamba proposal", "additive trend/seasonal/residual Mamba branches"),
    "MS_Mamba-MD": ("mamba proposal", "decomposed multi-scale Mamba with mean fusion"),
    "PMS_Mamba-PD": ("mamba proposal", "decomposed multi-scale temporal-patch Mamba"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze selection-safe nonstationary forecasting evidence."
    )
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--quality-report", type=Path, default=DEFAULT_QUALITY)
    parser.add_argument("--diagnostics", type=Path, default=DEFAULT_DIAGNOSTICS)
    parser.add_argument("--selection-root", type=Path, default=DEFAULT_SELECTION_ROOT)
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
    buffer = io.StringIO(newline="")
    frame.to_csv(buffer, index=False)
    write_text(path, buffer.getvalue())


def task_parts(task: str) -> tuple[str, str]:
    if not task.startswith("financial_"):
        raise ValueError(f"Unexpected task ID: {task}")
    if task.endswith("_ms"):
        return task[len("financial_") : -len("_ms")], "MS"
    if task.endswith("_s"):
        return task[len("financial_") : -len("_s")], "S"
    raise ValueError(f"Task ID has no S/MS suffix: {task}")


def expected_models(protocol: dict, phase: str) -> set[str]:
    return {
        model
        for model in protocol["level_models"]
        if (model in MAMBA_MODELS) == (phase == "mamba")
    }


def load_data_analysis(quality_path: Path, diagnostics_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    quality_payload = json.loads(quality_path.read_text(encoding="utf-8"))
    diagnostics_payload = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    if diagnostics_payload.get("scope") != "train_validation":
        raise ValueError("Diagnostics are not selection-safe train/validation records")
    if diagnostics_payload.get("test_targets_read") is not False:
        raise ValueError("Selection-safe diagnostics report that test targets were read")

    quality = pd.DataFrame(quality_payload["datasets"])
    quality["train_rows"] = quality["split_counts"].map(lambda value: int(value["train"]))
    quality["validation_rows"] = quality["split_counts"].map(
        lambda value: int(value["validation"])
    )
    quality["protected_test_rows"] = quality["split_counts"].map(
        lambda value: int(value["test"])
    )
    data_profile = quality[
        [
            "dataset",
            "target",
            "rows",
            "start",
            "end",
            "train_rows",
            "validation_rows",
            "protected_test_rows",
            "missing_cells",
            "duplicate_dates",
            "maximum_calendar_gap_days",
        ]
    ].copy()
    data_profile["variable_count"] = quality["columns"].map(len)

    diagnostics = pd.DataFrame(diagnostics_payload["records"])
    diagnostics["level_adf_reject_unit_root_5pct"] = diagnostics["train_level_adf_p_value"] < 0.05
    diagnostics["level_kpss_reject_trend_stationarity_5pct"] = (
        diagnostics["train_level_kpss_p_value"] < 0.05
    )
    diagnostics["difference_adf_reject_unit_root_5pct"] = (
        diagnostics["train_difference_adf_p_value"] < 0.05
    )
    diagnostics["difference_kpss_reject_stationarity_5pct"] = (
        diagnostics["train_difference_kpss_p_value"] < 0.05
    )
    diagnostics["level_consensus_nonstationary"] = (
        ~diagnostics["level_adf_reject_unit_root_5pct"]
        & diagnostics["level_kpss_reject_trend_stationarity_5pct"]
    )
    diagnostics["difference_consensus_stationary"] = (
        diagnostics["difference_adf_reject_unit_root_5pct"]
        & ~diagnostics["difference_kpss_reject_stationarity_5pct"]
    )
    keep = [
        "dataset",
        "target",
        "scope",
        "train_count",
        "validation_count",
        "train_level_adf_p_value",
        "train_level_kpss_p_value",
        "train_difference_adf_p_value",
        "train_difference_kpss_p_value",
        "level_consensus_nonstationary",
        "difference_consensus_stationary",
        "validation_mean_shift_train_sd",
        "validation_std_ratio",
        "validation_difference_std_ratio",
        "validation_correlation_shift_mean_abs",
        "validation_correlation_shift_max_abs",
        "train_trailing_volatility_q25",
        "train_trailing_volatility_q75",
    ]
    return data_profile.sort_values("dataset"), diagnostics[keep].sort_values("dataset")


def read_optional_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)


def collect_selection(
    protocol: dict,
    manifest: dict,
    selection_root: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[Path]]:
    score_rows: list[dict] = []
    audit_rows: list[dict] = []
    parameter_rows: list[dict] = []
    inputs: list[Path] = []
    protocol_hashes = {config["protocol_sha256"] for config in manifest.values()}
    if len(protocol_hashes) != 1:
        raise ValueError("Training manifest contains inconsistent protocol hashes")

    for task in sorted(manifest):
        panel, mode = task_parts(task)
        config = manifest[task]
        for phase in ("baseline", "mamba"):
            task_root = selection_root / task
            best_path = task_root / f"{phase}_best_params.json"
            trial_path = task_root / f"{phase}_trials.csv"
            replay_path = task_root / f"{phase}_replays.csv"
            if not best_path.is_file():
                raise FileNotFoundError(best_path)
            inputs.append(best_path)
            selection = json.loads(best_path.read_text(encoding="utf-8"))
            if selection.get("dataset") != task or selection.get("phase") != phase:
                raise ValueError(f"Selection identity mismatch: {best_path}")
            if selection.get("protocol_version") != protocol["protocol_version"]:
                raise ValueError(f"Selection protocol mismatch: {best_path}")
            if selection.get("protocol_sha256") != config["protocol_sha256"]:
                raise ValueError(f"Selection protocol hash mismatch: {best_path}")
            if selection.get("data_sha256") != config["data_sha256"]:
                raise ValueError(f"Selection data hash mismatch: {best_path}")
            if set(selection.get("models", {})) != expected_models(protocol, phase):
                raise ValueError(f"Incomplete model set: {best_path}")

            trials = read_optional_csv(trial_path)
            replays = read_optional_csv(replay_path)
            for optional_path in (trial_path, replay_path):
                if optional_path.is_file():
                    inputs.append(optional_path)

            for model, record in sorted(selection["models"].items()):
                score = float(record["best_validation_replay_balanced_rmsse"])
                if not math.isfinite(score):
                    raise ValueError(f"Non-finite validation score: {task}/{model}")
                if record.get("selection_eval_flag") != "val":
                    raise ValueError(f"Non-validation selection flag: {task}/{model}")
                if record.get("final_eval_flag") != "not_opened":
                    raise ValueError(f"Final split was opened during selection: {task}/{model}")
                family, architecture = ARCHITECTURES[model]
                score_rows.append(
                    {
                        "task": task,
                        "panel": panel,
                        "mode": mode,
                        "phase": phase,
                        "model": model,
                        "family": family,
                        "architecture": architecture,
                        "validation_balanced_rmsse": score,
                        "calibration_objective": float(record["best_calibration_objective"]),
                        "calibration_trial": int(record["best_calibration_trial"]),
                        "selected_replay_trial": int(record["best_validation_replay_trial"]),
                        "calibration_trial_matches_replay": (
                            int(record["best_calibration_trial"])
                            == int(record["best_validation_replay_trial"])
                        ),
                        "params_json": json.dumps(record["params"], sort_keys=True),
                    }
                )
                for parameter, value in sorted(record["params"].items()):
                    parameter_rows.append(
                        {
                            "model": model,
                            "parameter": parameter,
                            "value": json.dumps(value, sort_keys=True),
                            "task": task,
                            "panel": panel,
                            "mode": mode,
                        }
                    )

                model_trials = (
                    trials[trials["model"] == model].copy() if not trials.empty else pd.DataFrame()
                )
                model_replays = (
                    replays[replays["model"] == model].copy()
                    if not replays.empty
                    else pd.DataFrame()
                )
                replay_scores = (
                    pd.to_numeric(model_replays["balanced_rmsse"], errors="raise").to_numpy()
                    if not model_replays.empty
                    else np.asarray([], dtype=float)
                )
                if replay_scores.size and not np.isclose(replay_scores.min(), score, rtol=0, atol=1e-12):
                    raise ValueError(f"Best replay score mismatch: {task}/{model}")
                states = (
                    Counter(
                        value.rsplit(".", 1)[-1]
                        for value in model_trials["state"].astype(str)
                    )
                    if not model_trials.empty
                    else Counter()
                )
                audit_rows.append(
                    {
                        "task": task,
                        "panel": panel,
                        "mode": mode,
                        "phase": phase,
                        "model": model,
                        "trial_rows": int(len(model_trials)),
                        "complete_trials": int(states.get("COMPLETE", 0)),
                        "pruned_trials": int(states.get("PRUNED", 0)),
                        "failed_trials": int(states.get("FAIL", 0)),
                        "replay_rows": int(len(model_replays)),
                        "replay_distinct_parameter_sets": (
                            int(model_replays["params_json"].nunique()) if not model_replays.empty else 0
                        ),
                        "top_replay_relative_spread": (
                            float((replay_scores.max() - replay_scores.min()) / replay_scores.min())
                            if replay_scores.size
                            else float("nan")
                        ),
                        "calibration_trial_matches_replay": (
                            int(record["best_calibration_trial"])
                            == int(record["best_validation_replay_trial"])
                        ),
                    }
                )

    scores = pd.DataFrame(score_rows)
    scores["task_rank"] = scores.groupby("task")["validation_balanced_rmsse"].rank(
        method="min", ascending=True
    )
    return scores, pd.DataFrame(audit_rows), pd.DataFrame(parameter_rows), inputs


def summarize_models(scores: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    ranking = (
        scores.groupby(["model", "family"], as_index=False)
        .agg(
            task_count=("task", "nunique"),
            mean_validation_balanced_rmsse=("validation_balanced_rmsse", "mean"),
            median_validation_balanced_rmsse=("validation_balanced_rmsse", "median"),
            mean_task_rank=("task_rank", "mean"),
            median_task_rank=("task_rank", "median"),
            task_wins=("task_rank", lambda values: int((values == 1).sum())),
            task_top3=("task_rank", lambda values: int((values <= 3).sum())),
        )
        .sort_values(["mean_task_rank", "mean_validation_balanced_rmsse", "model"])
        .reset_index(drop=True)
    )
    winners = (
        scores[scores["task_rank"] == 1]
        [["task", "panel", "mode", "model", "family", "validation_balanced_rmsse"]]
        .sort_values(["task", "model"])
        .reset_index(drop=True)
    )
    return ranking, winners


def compare_modes(scores: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    pivot = scores.pivot(index=["panel", "model"], columns="mode", values="validation_balanced_rmsse")
    pivot = pivot.reset_index()
    if not {"S", "MS"}.issubset(pivot.columns):
        raise ValueError("S/MS comparison requires both modes")
    pivot["ms_minus_s"] = pivot["MS"] - pivot["S"]
    pivot["ms_relative_change"] = pivot["ms_minus_s"] / pivot["S"]
    pivot["ms_better"] = pivot["ms_minus_s"] < 0
    aggregate = (
        pivot.groupby("model", as_index=False)
        .agg(
            panels=("panel", "nunique"),
            mean_ms_minus_s=("ms_minus_s", "mean"),
            median_ms_minus_s=("ms_minus_s", "median"),
            mean_ms_relative_change=("ms_relative_change", "mean"),
            ms_better_panels=("ms_better", "sum"),
        )
        .sort_values(["mean_ms_minus_s", "model"])
    )
    return pivot.sort_values(["model", "panel"]), aggregate


def compare_proposals(scores: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    baseline = scores[scores["model"] == "S_Mamba"].set_index("task")[
        "validation_balanced_rmsse"
    ]
    rows = []
    for proposal in PROPOSALS:
        for record in scores[scores["model"] == proposal].itertuples(index=False):
            s_score = float(baseline.loc[record.task])
            rows.append(
                {
                    "task": record.task,
                    "panel": record.panel,
                    "mode": record.mode,
                    "proposal": proposal,
                    "proposal_score": float(record.validation_balanced_rmsse),
                    "s_mamba_score": s_score,
                    "proposal_minus_s_mamba": float(record.validation_balanced_rmsse) - s_score,
                    "relative_change": float(record.validation_balanced_rmsse) / s_score - 1.0,
                    "proposal_better": float(record.validation_balanced_rmsse) < s_score,
                }
            )
    comparison = pd.DataFrame(rows)
    aggregate = (
        comparison.groupby("proposal", as_index=False)
        .agg(
            tasks=("task", "nunique"),
            mean_delta=("proposal_minus_s_mamba", "mean"),
            median_delta=("proposal_minus_s_mamba", "median"),
            mean_relative_change=("relative_change", "mean"),
            better_tasks=("proposal_better", "sum"),
        )
        .sort_values(["mean_delta", "proposal"])
    )
    return comparison, aggregate


def parameter_frequencies(parameters: pd.DataFrame) -> pd.DataFrame:
    counts = (
        parameters.groupby(["model", "parameter", "value"], as_index=False)
        .agg(selection_count=("task", "count"))
    )
    totals = parameters.groupby(["model", "parameter"])["task"].count().rename("task_count")
    counts = counts.join(totals, on=["model", "parameter"])
    counts["selection_fraction"] = counts["selection_count"] / counts["task_count"]
    return counts.sort_values(
        ["model", "parameter", "selection_count", "value"],
        ascending=[True, True, False, True],
    )


def final_status(protocol: dict, manifest: dict) -> dict:
    expected_neural = len(manifest) * len(protocol["level_models"]) * len(protocol["final_seeds"])
    summary_path = REPO_ROOT / "results" / "financial_confirmatory" / "final_runs.json"
    completed = 0
    if summary_path.is_file():
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        completed = sum(
            record.get("status") == "complete" for record in payload.get("runs", {}).values()
        )
    statistical_path = (
        REPO_ROOT / "results" / "financial_confirmatory" / "statistical" / "metrics.csv"
    )
    statistical_rows = len(pd.read_csv(statistical_path)) if statistical_path.is_file() else 0
    return {
        "final_neural_completed": int(completed),
        "final_neural_expected": int(expected_neural),
        "statistical_metric_rows": int(statistical_rows),
        "final_analysis_ready": bool(completed == expected_neural and statistical_rows > 0),
    }


def markdown_table(frame: pd.DataFrame, columns: list[str], formats: dict[str, str] = None) -> str:
    formats = formats or {}
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    rows = []
    for record in frame[columns].to_dict(orient="records"):
        values = []
        for column in columns:
            value = record[column]
            if column in formats and pd.notna(value):
                value = format(value, formats[column])
            values.append(str(value).replace("|", "\\|"))
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join([header, separator, *rows])


def plot_data_shifts(diagnostics: pd.DataFrame, output: Path) -> None:
    metrics = [
        ("validation_mean_shift_train_sd", "Mean shift (train SD)"),
        ("validation_std_ratio", "Level SD ratio"),
        ("validation_difference_std_ratio", "Difference SD ratio"),
        ("validation_correlation_shift_mean_abs", "Mean correlation shift"),
    ]
    colors = ["#2f6b4f", "#b14a3b", "#3f668f", "#805b2d"]
    figure, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)
    for axis, (metric, title), color in zip(axes.flat, metrics, colors):
        axis.bar(diagnostics["dataset"], diagnostics[metric], color=color)
        axis.axhline(0 if "shift" in metric else 1, color="#333333", linewidth=0.8)
        axis.set_title(title)
        axis.tick_params(axis="x", rotation=20)
        axis.grid(axis="y", alpha=0.25)
    figure.suptitle("Train-to-validation shifts in financial reference panels")
    figure.savefig(output, dpi=180)
    plt.close(figure)


def plot_rank_heatmap(scores: pd.DataFrame, protocol: dict, output: Path) -> None:
    tasks = sorted(scores["task"].unique())
    models = list(protocol["level_models"])
    matrix = scores.pivot(index="model", columns="task", values="task_rank").loc[models, tasks]
    figure, axis = plt.subplots(figsize=(12, 5.6), constrained_layout=True)
    image = axis.imshow(matrix.to_numpy(), cmap="RdYlGn_r", vmin=1, vmax=len(models), aspect="auto")
    axis.set_xticks(range(len(tasks)), [task.replace("financial_", "") for task in tasks], rotation=35, ha="right")
    axis.set_yticks(range(len(models)), models)
    for row in range(len(models)):
        for column in range(len(tasks)):
            axis.text(column, row, f"{matrix.iloc[row, column]:.0f}", ha="center", va="center", fontsize=8)
    axis.set_title("Validation-only model ranks (1 = lowest balanced RMSSE)")
    figure.colorbar(image, ax=axis, label="Task rank")
    figure.savefig(output, dpi=180)
    plt.close(figure)


def build_report(
    protocol: dict,
    data_profile: pd.DataFrame,
    diagnostics: pd.DataFrame,
    ranking: pd.DataFrame,
    winners: pd.DataFrame,
    mode_aggregate: pd.DataFrame,
    proposal_aggregate: pd.DataFrame,
    audit: pd.DataFrame,
    status: dict,
) -> str:
    data_view = diagnostics[
        [
            "dataset",
            "level_consensus_nonstationary",
            "difference_consensus_stationary",
            "validation_mean_shift_train_sd",
            "validation_std_ratio",
            "validation_difference_std_ratio",
            "validation_correlation_shift_mean_abs",
        ]
    ].copy()
    model_view = ranking.head(9).copy()
    trial_states = {
        "complete": int(audit["complete_trials"].sum()),
        "pruned": int(audit["pruned_trials"].sum()),
        "failed": int(audit["failed_trials"].sum()),
    }
    matching = int(audit["calibration_trial_matches_replay"].sum())
    largest_mean_shift = diagnostics.loc[
        diagnostics["validation_mean_shift_train_sd"].abs().idxmax(), "dataset"
    ]
    largest_difference_shift = diagnostics.loc[
        diagnostics["validation_difference_std_ratio"].idxmax(), "dataset"
    ]
    largest_correlation_shift = diagnostics.loc[
        diagnostics["validation_correlation_shift_mean_abs"].idxmax(), "dataset"
    ]
    report = f"""# Selection-Safe Nonstationary Forecasting Analysis

Generated from frozen protocol `{protocol['protocol_version']}`. The four market panels are reference datasets for a broader study of nonstationary forecasting; they do not define the research domain.

## Evidence boundary

This report uses data quality metadata, train/validation nonstationarity diagnostics, and validation-only Optuna selection artifacts. It does not read protected test targets or present validation ranks as confirmatory model performance. Final paired bootstrap intervals, Holm-adjusted comparisons, regime results, and test-period claims remain unavailable until the formal prediction matrix is complete.

## Completion status

- Reference panels characterized: {len(data_profile)}/4.
- S/MS forecasting tasks audited: {data_profile.shape[0] * 2}/8.
- Validation model selections audited: {len(audit)}/72.
- Formal neural task/model/seed cells: {status['final_neural_completed']}/{status['final_neural_expected']}.
- Statistical-reference metric rows: {status['statistical_metric_rows']}.
- Final inferential analysis ready: {status['final_analysis_ready']}.

## Data analysis

All panels have zero missing cells and zero duplicate dates in the processed complete-case files. ADF and KPSS are reported jointly because neither test alone identifies all forms of nonstationarity. `level_consensus_nonstationary` means the level ADF test did not reject a unit root while KPSS rejected trend stationarity at 5%. `difference_consensus_stationary` means the differenced ADF rejected a unit root while KPSS did not reject stationarity at 5%.

{markdown_table(data_view, list(data_view.columns), {
        'validation_mean_shift_train_sd': '.3f',
        'validation_std_ratio': '.3f',
        'validation_difference_std_ratio': '.3f',
        'validation_correlation_shift_mean_abs': '.3f',
    })}

The raw magnitudes show that shift is heterogeneous rather than a single financial-data effect. `{largest_mean_shift}` has the largest absolute train-to-validation level shift, `{largest_difference_shift}` has the largest difference-scale ratio, and `{largest_correlation_shift}` has the largest mean change in target-feature difference correlations. These are descriptive validation-era facts, not test-period findings.

## Model architecture analysis

{markdown_table(pd.DataFrame([
        {'model': model, 'family': values[0], 'implemented mechanism': values[1]}
        for model, values in ARCHITECTURES.items()
    ]), ['model', 'family', 'implemented mechanism'])}

## Validation-only model analysis

Lower balanced RMSSE is better. Mean task rank is used for cross-panel description because RMSSE levels still vary by task. These rankings selected frozen configurations; they are exploratory and cannot establish superiority.

{markdown_table(model_view, ['model', 'mean_task_rank', 'median_task_rank', 'task_wins', 'task_top3', 'mean_validation_balanced_rmsse'], {
        'mean_task_rank': '.3f',
        'median_task_rank': '.3f',
        'mean_validation_balanced_rmsse': '.4f',
    })}

Task winners:

{markdown_table(winners, ['task', 'model', 'validation_balanced_rmsse'], {'validation_balanced_rmsse': '.4f'})}

S/MS validation comparison by model:

{markdown_table(mode_aggregate, ['model', 'mean_ms_minus_s', 'mean_ms_relative_change', 'ms_better_panels'], {
        'mean_ms_minus_s': '.4f',
        'mean_ms_relative_change': '.2%',
    })}

Proposed Mamba variants relative to S-Mamba on validation tasks:

{markdown_table(proposal_aggregate, ['proposal', 'mean_delta', 'mean_relative_change', 'better_tasks'], {
        'mean_delta': '.4f',
        'mean_relative_change': '.2%',
    })}

## HPO audit

The 72 model/task studies contain {trial_states['complete']} complete, {trial_states['pruned']} pruned, and {trial_states['failed']} failed/interrupted trial rows, plus {int(audit['replay_rows'].sum())} full-horizon validation replays. The calibration-best trial remained the full-horizon replay winner in {matching}/72 selections. Differences are expected because calibration used horizons {protocol['calibration_horizons']} while replay used all horizons {protocol['horizons']}.

No p-values are calculated from these selected validation scores. Treating task ranks or selected configurations as independent replications would understate dependence and reuse selection data for inference.

## Required final analysis

After all {status['final_neural_expected']} formal neural cells and the statistical references exist, run:

```bash
conda run --no-capture-output -n mamba python scripts/financial/run_statistical_baselines.py --unlock-test
conda run --no-capture-output -n mamba python scripts/financial/analyze_financial_results.py
```

That stage will compute per-origin path and terminal metrics, last-value skill, S/MS comparisons, prespecified volatility-regime metrics, 10,000-replicate moving-block bootstrap intervals, and Holm-adjusted p-values. Until then, model conclusions must remain labeled validation-only.
"""
    return report


def main() -> None:
    args = parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    data_profile, diagnostics = load_data_analysis(args.quality_report, args.diagnostics)
    scores, audit, parameters, selection_inputs = collect_selection(
        protocol, manifest, args.selection_root
    )
    if len(scores) != 72 or len(audit) != 72:
        raise ValueError(f"Expected 72 selected model/task cells, got {len(scores)}")
    budgeted_trials = audit["complete_trials"] + audit["pruned_trials"]
    if not (budgeted_trials == int(protocol["hpo"]["trials_per_model_task"])).all():
        raise ValueError("At least one HPO study did not complete its frozen trial budget")
    if not (audit["replay_rows"] == int(protocol["hpo"]["top_k_validation_replays"])).all():
        raise ValueError("At least one HPO study is missing a frozen validation replay")
    ranking, winners = summarize_models(scores)
    mode_comparison, mode_aggregate = compare_modes(scores)
    proposal_comparison, proposal_aggregate = compare_proposals(scores)
    frequencies = parameter_frequencies(parameters)
    status = final_status(protocol, manifest)

    args.output_root.mkdir(parents=True, exist_ok=True)
    outputs = {
        "data_profile.csv": data_profile,
        "nonstationarity_summary.csv": diagnostics,
        "selection_scores.csv": scores.sort_values(["task", "task_rank", "model"]),
        "model_ranking.csv": ranking,
        "task_winners.csv": winners,
        "s_ms_comparison.csv": mode_comparison,
        "s_ms_model_summary.csv": mode_aggregate,
        "proposal_vs_s_mamba.csv": proposal_comparison,
        "proposal_vs_s_mamba_summary.csv": proposal_aggregate,
        "hyperparameter_frequencies.csv": frequencies,
        "hpo_audit.csv": audit.sort_values(["task", "phase", "model"]),
    }
    for name, frame in outputs.items():
        write_csv(args.output_root / name, frame)

    plot_data_shifts(diagnostics, args.output_root / "data_shift_overview.png")
    plot_rank_heatmap(scores, protocol, args.output_root / "selection_rank_heatmap.png")
    report = build_report(
        protocol,
        data_profile,
        diagnostics,
        ranking,
        winners,
        mode_aggregate,
        proposal_aggregate,
        audit,
        status,
    )
    write_text(args.output_root / "REPORT.md", report)

    input_paths = [args.protocol, args.manifest, args.quality_report, args.diagnostics, *selection_inputs]
    manifest_payload = {
        "analysis_scope": "selection_safe_train_validation",
        "test_targets_read": False,
        "protocol_version": protocol["protocol_version"],
        "task_count": len(manifest),
        "model_count": len(protocol["level_models"]),
        "selection_cell_count": len(scores),
        "formal_status": status,
        "inputs": {
            str(path.relative_to(REPO_ROOT)): sha256_path(path)
            for path in sorted(set(input_paths))
        },
        "outputs": sorted([*outputs, "REPORT.md", "data_shift_overview.png", "selection_rank_heatmap.png"]),
    }
    write_json(args.output_root / "analysis_manifest.json", manifest_payload)
    print(f"wrote selection-safe analysis to {args.output_root}")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"Selection-safe analysis blocked: {exc}") from None
