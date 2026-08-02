#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FINAL_ROOT = REPO_ROOT / "reproducibility" / "nonstationary_analysis_v1" / "final"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "results" / "nonstationary_metric_suite"

PMS_MODEL = "PMS_Mamba-PD"
S_MAMBA = "S_Mamba"
MAMBA_MODELS = {"S_Mamba", "NS_Mamba-D", "MS_Mamba-MD", "PMS_Mamba-PD"}
STAT_OR_NAIVE_MODELS = {"Last-value", "Random-walk-drift", "ARIMA", "VAR-difference"}
TERM_BY_HORIZON = {
    1: "short",
    5: "short",
    20: "middle",
    60: "middle",
    120: "long",
    252: "long",
}

LOWER_IS_BETTER_METRICS = [
    "path_mae_mean",
    "path_mse_mean",
    "path_rmse_mean",
    "path_rmsse_mean",
    "terminal_mae_mean",
    "terminal_mse_mean",
    "terminal_rmse_mean",
    "terminal_rmsse_mean",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build common-metric model comparison tables and PMS-Mamba diagnostics."
    )
    parser.add_argument("--final-root", type=Path, default=DEFAULT_FINAL_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def model_category(model: str) -> str:
    if model in MAMBA_MODELS:
        return "mamba"
    if model in STAT_OR_NAIVE_MODELS:
        return "statistical_or_naive"
    return "non_mamba_learned"


def term_for_horizon(horizon: int) -> str:
    try:
        return TERM_BY_HORIZON[int(horizon)]
    except KeyError as exc:
        raise ValueError(f"Unsupported horizon: {horizon}") from exc


def require_columns(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{name} is missing required columns: {missing}")


def load_inputs(final_root: Path) -> dict[str, pd.DataFrame]:
    tables = {
        "aggregate": "aggregate_metrics.csv",
        "bootstrap": "bootstrap_contrasts.csv",
        "regime": "regime_metrics.csv",
        "seed_stability": "seed_stability.csv",
        "runtime": "runtime_summary.csv",
        "s_ms": "s_ms_comparison.csv",
        "proposal_summary": "proposal_contrast_summary.csv",
        "winners": "task_horizon_winners.csv",
    }
    output: dict[str, pd.DataFrame] = {}
    for key, filename in tables.items():
        path = final_root / filename
        if not path.is_file():
            raise FileNotFoundError(f"Missing required final analysis file: {path}")
        output[key] = pd.read_csv(path)
    return output


def add_metric_ranks(aggregate: pd.DataFrame) -> pd.DataFrame:
    require_columns(aggregate, ["dataset", "model", "horizon", *LOWER_IS_BETTER_METRICS], "aggregate")
    table = aggregate.copy()
    table["term"] = table["horizon"].map(term_for_horizon)
    table["model_category"] = table["model"].map(model_category)
    for metric in LOWER_IS_BETTER_METRICS:
        rank_col = metric.replace("_mean", "_rank")
        table[rank_col] = table.groupby(["dataset", "horizon"])[metric].rank(method="min")
    return table.sort_values(["dataset", "horizon", "path_rmsse_rank", "model"]).reset_index(drop=True)


def model_summary(ranked: pd.DataFrame, seed_stability: pd.DataFrame, runtime: pd.DataFrame) -> pd.DataFrame:
    summary = ranked.groupby("model", as_index=False).agg(
        model_category=("model_category", "first"),
        evaluated_task_horizons=("path_rmsse_mean", "size"),
        mean_path_mae=("path_mae_mean", "mean"),
        mean_path_mse=("path_mse_mean", "mean"),
        mean_path_rmse=("path_rmse_mean", "mean"),
        mean_path_rmsse=("path_rmsse_mean", "mean"),
        median_path_rmsse=("path_rmsse_mean", "median"),
        mean_terminal_mae=("terminal_mae_mean", "mean"),
        mean_terminal_rmse=("terminal_rmse_mean", "mean"),
        mean_terminal_rmsse=("terminal_rmsse_mean", "mean"),
        mean_skill_vs_last_value=("skill_vs_last_value", "mean"),
        positive_skill_cells=("skill_vs_last_value", lambda values: int((values > 0).sum())),
        path_rmsse_wins=("path_rmsse_rank", lambda values: int((values == 1).sum())),
        path_rmsse_top3=("path_rmsse_rank", lambda values: int((values <= 3).sum())),
        average_path_rmsse_rank=("path_rmsse_rank", "mean"),
    )
    if not seed_stability.empty:
        summary = summary.merge(seed_stability, on="model", how="left")
    if not runtime.empty:
        runtime_cols = [
            "model",
            "horizon_run_count",
            "total_runtime_seconds",
            "median_runtime_seconds",
            "median_peak_gpu_memory_mb",
        ]
        summary = summary.merge(runtime[runtime_cols], on="model", how="left")
    return summary.sort_values(
        ["path_rmsse_wins", "mean_path_rmsse", "average_path_rmsse_rank"],
        ascending=[False, True, True],
    ).reset_index(drop=True)


def horizon_summary(ranked: pd.DataFrame) -> pd.DataFrame:
    return (
        ranked.groupby(["horizon", "term", "model"], as_index=False)
        .agg(
            model_category=("model_category", "first"),
            evaluated_cells=("path_rmsse_mean", "size"),
            mean_path_mae=("path_mae_mean", "mean"),
            mean_path_mse=("path_mse_mean", "mean"),
            mean_path_rmse=("path_rmse_mean", "mean"),
            mean_path_rmsse=("path_rmsse_mean", "mean"),
            median_path_rmsse=("path_rmsse_mean", "median"),
            mean_terminal_rmse=("terminal_rmse_mean", "mean"),
            mean_terminal_rmsse=("terminal_rmsse_mean", "mean"),
            mean_skill_vs_last_value=("skill_vs_last_value", "mean"),
            path_rmsse_wins=("path_rmsse_rank", lambda values: int((values == 1).sum())),
            path_rmsse_top3=("path_rmsse_rank", lambda values: int((values <= 3).sum())),
            average_path_rmsse_rank=("path_rmsse_rank", "mean"),
        )
        .sort_values(["horizon", "mean_path_rmsse", "average_path_rmsse_rank", "model"])
        .reset_index(drop=True)
    )


def dataset_balanced_summary(ranked: pd.DataFrame) -> pd.DataFrame:
    by_term = (
        ranked.groupby(["dataset", "model", "model_category", "term"], as_index=False)
        .agg(
            path_rmsse_term_mean=("path_rmsse_mean", "mean"),
            path_rmse_term_mean=("path_rmse_mean", "mean"),
            path_mae_term_mean=("path_mae_mean", "mean"),
            terminal_rmsse_term_mean=("terminal_rmsse_mean", "mean"),
        )
    )
    summary = (
        by_term.groupby(["dataset", "model", "model_category"], as_index=False)
        .agg(
            balanced_path_rmsse=("path_rmsse_term_mean", "mean"),
            balanced_path_rmse=("path_rmse_term_mean", "mean"),
            balanced_path_mae=("path_mae_term_mean", "mean"),
            balanced_terminal_rmsse=("terminal_rmsse_term_mean", "mean"),
        )
    )
    summary["balanced_path_rmsse_rank"] = summary.groupby("dataset")["balanced_path_rmsse"].rank(method="min")
    return summary.sort_values(["dataset", "balanced_path_rmsse_rank", "model"]).reset_index(drop=True)


def metric_winner_counts(ranked: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for metric in LOWER_IS_BETTER_METRICS:
        winner = ranked.loc[ranked.groupby(["dataset", "horizon"])[metric].idxmin()]
        counts = winner["model"].value_counts().rename_axis("model").reset_index(name="wins")
        counts["metric"] = metric
        rows.append(counts)
    return pd.concat(rows, ignore_index=True)[["metric", "model", "wins"]].sort_values(
        ["metric", "wins", "model"], ascending=[True, False, True]
    )


def comparator_row(group: pd.DataFrame, models: set[str]) -> pd.Series:
    subset = group[group["model"].isin(models)]
    if subset.empty:
        raise ValueError("No comparator model found in group")
    return subset.loc[subset["path_rmsse_mean"].idxmin()]


def bootstrap_status(row: pd.Series | None) -> str:
    if row is None or pd.isna(row.get("holm_p_value", math.nan)):
        return "not_available"
    significant = float(row["holm_p_value"]) < 0.05
    if not significant:
        return "not_significant"
    if float(row["mean_loss_difference"]) < 0:
        return "favorable_significant"
    return "unfavorable_significant"


def pms_diagnostics(ranked: pd.DataFrame, bootstrap: pd.DataFrame) -> pd.DataFrame:
    rows = []
    non_mamba_learned = {
        model for model in ranked["model"].unique()
        if model_category(model) == "non_mamba_learned"
    }

    pms_boot = bootstrap[bootstrap["proposal"] == PMS_MODEL].copy()

    for (dataset, horizon), group in ranked.groupby(["dataset", "horizon"]):
        pms = group[group["model"] == PMS_MODEL]
        if pms.empty:
            raise ValueError(f"Missing {PMS_MODEL} for {dataset}/h{horizon}")
        pms = pms.iloc[0]
        winner = group.loc[group["path_rmsse_mean"].idxmin()]
        s_mamba = group[group["model"] == S_MAMBA].iloc[0]
        best_stat = comparator_row(group, STAT_OR_NAIVE_MODELS)
        best_non_mamba = comparator_row(group, non_mamba_learned)

        boot_s = pms_boot[
            (pms_boot["dataset"] == dataset)
            & (pms_boot["horizon"] == horizon)
            & (pms_boot["comparator"] == S_MAMBA)
        ]
        boot_selected = pms_boot[
            (pms_boot["dataset"] == dataset)
            & (pms_boot["horizon"] == horizon)
            & (pms_boot["comparator"] != S_MAMBA)
        ]
        boot_s_row = None if boot_s.empty else boot_s.iloc[0]
        boot_selected_row = None if boot_selected.empty else boot_selected.iloc[0]

        def rel_pct(value: float, baseline: float) -> float:
            return (value / baseline - 1.0) * 100.0

        rows.append(
            {
                "dataset": dataset,
                "horizon": int(horizon),
                "term": term_for_horizon(int(horizon)),
                "winner": winner["model"],
                "winner_category": model_category(winner["model"]),
                "winner_path_rmsse": winner["path_rmsse_mean"],
                "pms_path_mae": pms["path_mae_mean"],
                "pms_path_mse": pms["path_mse_mean"],
                "pms_path_rmse": pms["path_rmse_mean"],
                "pms_path_rmsse": pms["path_rmsse_mean"],
                "pms_terminal_rmse": pms["terminal_rmse_mean"],
                "pms_terminal_rmsse": pms["terminal_rmsse_mean"],
                "pms_skill_vs_last_value": pms["skill_vs_last_value"],
                "pms_path_rmsse_rank": int(pms["path_rmsse_rank"]),
                "pms_top3_path_rmsse": bool(pms["path_rmsse_rank"] <= 3),
                "pms_minus_winner_path_rmsse": pms["path_rmsse_mean"] - winner["path_rmsse_mean"],
                "pms_vs_winner_pct": rel_pct(pms["path_rmsse_mean"], winner["path_rmsse_mean"]),
                "s_mamba_path_rmsse": s_mamba["path_rmsse_mean"],
                "pms_minus_s_mamba_path_rmsse": pms["path_rmsse_mean"] - s_mamba["path_rmsse_mean"],
                "pms_vs_s_mamba_pct": rel_pct(pms["path_rmsse_mean"], s_mamba["path_rmsse_mean"]),
                "best_stat_or_naive": best_stat["model"],
                "best_stat_or_naive_path_rmsse": best_stat["path_rmsse_mean"],
                "pms_vs_best_stat_or_naive_pct": rel_pct(pms["path_rmsse_mean"], best_stat["path_rmsse_mean"]),
                "best_non_mamba_learned": best_non_mamba["model"],
                "best_non_mamba_learned_path_rmsse": best_non_mamba["path_rmsse_mean"],
                "pms_vs_best_non_mamba_learned_pct": rel_pct(
                    pms["path_rmsse_mean"], best_non_mamba["path_rmsse_mean"]
                ),
                "bootstrap_vs_s_mamba_mean_loss_difference": (
                    float(boot_s_row["mean_loss_difference"]) if boot_s_row is not None else math.nan
                ),
                "bootstrap_vs_s_mamba_holm_p": (
                    float(boot_s_row["holm_p_value"]) if boot_s_row is not None else math.nan
                ),
                "bootstrap_vs_s_mamba_status": bootstrap_status(boot_s_row),
                "selected_learned_comparator": (
                    str(boot_selected_row["comparator"]) if boot_selected_row is not None else ""
                ),
                "bootstrap_vs_selected_learned_mean_loss_difference": (
                    float(boot_selected_row["mean_loss_difference"]) if boot_selected_row is not None else math.nan
                ),
                "bootstrap_vs_selected_learned_holm_p": (
                    float(boot_selected_row["holm_p_value"]) if boot_selected_row is not None else math.nan
                ),
                "bootstrap_vs_selected_learned_status": bootstrap_status(boot_selected_row),
            }
        )
    return pd.DataFrame(rows).sort_values(["dataset", "horizon"]).reset_index(drop=True)


def pms_regime_summary(regime: pd.DataFrame) -> pd.DataFrame:
    pms = regime[regime["model"] == PMS_MODEL].copy()
    pms["term"] = pms["horizon"].map(term_for_horizon)
    pms["estimable"] = pms["origin_count"] > 0
    return (
        pms.groupby(["term", "regime"], as_index=False)
        .agg(
            rows=("dataset", "size"),
            estimable_rows=("estimable", lambda values: int(values.sum())),
            mean_origin_mse=("origin_mse_mean", "mean"),
            median_origin_mse=("origin_mse_mean", "median"),
            mean_skill_vs_last_value=("skill_vs_last_value", "mean"),
            positive_skill_rows=("skill_vs_last_value", lambda values: int((values > 0).sum())),
            not_estimable_rows=("estimable", lambda values: int((~values).sum())),
        )
        .sort_values(["term", "regime"])
    )


def pms_term_summary(diagnostics: pd.DataFrame) -> pd.DataFrame:
    def count_status(values: pd.Series, status: str) -> int:
        return int((values == status).sum())

    return (
        diagnostics.groupby("term", as_index=False)
        .agg(
            cells=("dataset", "size"),
            mean_gap_to_winner_pct=("pms_vs_winner_pct", "mean"),
            median_gap_to_winner_pct=("pms_vs_winner_pct", "median"),
            within_5pct_of_winner=("pms_vs_winner_pct", lambda values: int((values <= 5).sum())),
            pms_top3_cells=("pms_top3_path_rmsse", lambda values: int(values.sum())),
            pms_better_than_s_mamba=("pms_minus_s_mamba_path_rmsse", lambda values: int((values < 0).sum())),
            pms_better_than_best_non_mamba_learned=(
                "pms_vs_best_non_mamba_learned_pct",
                lambda values: int((values < 0).sum()),
            ),
            pms_better_than_best_stat_or_naive=(
                "pms_vs_best_stat_or_naive_pct",
                lambda values: int((values < 0).sum()),
            ),
            sig_favorable_vs_s_mamba=(
                "bootstrap_vs_s_mamba_status",
                lambda values: count_status(values, "favorable_significant"),
            ),
            sig_unfavorable_vs_s_mamba=(
                "bootstrap_vs_s_mamba_status",
                lambda values: count_status(values, "unfavorable_significant"),
            ),
            sig_favorable_vs_selected_learned=(
                "bootstrap_vs_selected_learned_status",
                lambda values: count_status(values, "favorable_significant"),
            ),
            sig_unfavorable_vs_selected_learned=(
                "bootstrap_vs_selected_learned_status",
                lambda values: count_status(values, "unfavorable_significant"),
            ),
        )
        .sort_values("term", key=lambda col: col.map({"short": 0, "middle": 1, "long": 2}))
    )


def pms_selected_params() -> pd.DataFrame:
    rows = []
    for path in sorted((REPO_ROOT / "results" / "optuna").glob("financial_*/mamba_best_params.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        model_payload = payload.get("models", {}).get(PMS_MODEL)
        if not model_payload:
            continue
        params = model_payload["params"]
        rows.append(
            {
                "dataset": payload["dataset"],
                "objective_metric": payload.get("objective_metric", ""),
                "calibration_horizons": ",".join(map(str, payload.get("calibration_horizons", []))),
                "full_horizons": ",".join(map(str, payload.get("full_horizons", []))),
                "validation_balanced_rmsse": model_payload.get("best_validation_replay_balanced_rmsse"),
                "best_calibration_objective": model_payload.get("best_calibration_objective"),
                "seq_len": params.get("seq_len"),
                "patch_len": params.get("patch_len"),
                "stride": params.get("stride"),
                "d_model": params.get("d_model"),
                "d_ff": params.get("d_ff"),
                "d_state": params.get("d_state"),
                "batch_size": params.get("batch_size"),
                "learning_rate": params.get("learning_rate"),
                "moving_avg": params.get("moving_avg"),
                "ms_scales": ",".join(map(str, params.get("ms_scales", []))),
                "ms_fusion": params.get("ms_fusion"),
                "ms_use_decomp": params.get("ms_use_decomp"),
                "use_norm": params.get("use_norm"),
            }
        )
    return pd.DataFrame(rows).sort_values("dataset").reset_index(drop=True)


def pms_strengths(diagnostics: pd.DataFrame) -> pd.DataFrame:
    mask = (
        (diagnostics["pms_top3_path_rmsse"])
        | (diagnostics["pms_vs_winner_pct"] <= 5)
        | (diagnostics["pms_minus_s_mamba_path_rmsse"] < 0)
        | (diagnostics["bootstrap_vs_selected_learned_status"] == "favorable_significant")
    )
    columns = [
        "dataset",
        "horizon",
        "term",
        "winner",
        "pms_path_rmsse_rank",
        "pms_vs_winner_pct",
        "pms_vs_s_mamba_pct",
        "best_non_mamba_learned",
        "pms_vs_best_non_mamba_learned_pct",
        "bootstrap_vs_selected_learned_status",
    ]
    return diagnostics.loc[mask, columns].sort_values(
        ["term", "pms_vs_winner_pct", "dataset", "horizon"],
        key=lambda col: col.map({"short": 0, "middle": 1, "long": 2}) if col.name == "term" else col,
    )


def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 20) -> str:
    if frame.empty:
        return "_No rows._"
    view = frame.loc[:, columns].head(max_rows).copy()
    for column in view.columns:
        if pd.api.types.is_float_dtype(view[column]):
            view[column] = view[column].map(lambda value: "" if pd.isna(value) else f"{value:.4g}")
    header = "| " + " | ".join(view.columns) + " |"
    divider = "| " + " | ".join(["---"] * len(view.columns)) + " |"
    rows = [
        "| " + " | ".join(str(value) for value in row) + " |"
        for row in view.to_numpy()
    ]
    return "\n".join([header, divider, *rows])


def write_report(
    output_root: Path,
    ranked: pd.DataFrame,
    model_view: pd.DataFrame,
    horizon_view: pd.DataFrame,
    balanced_view: pd.DataFrame,
    pms_view: pd.DataFrame,
    pms_terms: pd.DataFrame,
    pms_params: pd.DataFrame,
    proposal_summary: pd.DataFrame,
) -> None:
    winner_counts = (
        ranked[ranked["path_rmsse_rank"] == 1]["model"]
        .value_counts()
        .rename_axis("model")
        .reset_index(name="path_rmsse_wins")
    )
    balanced_winners = (
        balanced_view[balanced_view["balanced_path_rmsse_rank"] == 1]["model"]
        .value_counts()
        .rename_axis("model")
        .reset_index(name="balanced_dataset_wins")
    )
    pms_row = model_view[model_view["model"] == PMS_MODEL].iloc[0]
    learned = model_view[model_view["model_category"].isin(["mamba", "non_mamba_learned"])].copy()
    pms_learned_rank = int(
        learned["mean_path_rmsse"].rank(method="min").loc[pms_row.name]
    )

    pms_proposal = proposal_summary[proposal_summary["proposal"] == PMS_MODEL].copy()

    report = f"""# Common-Metric Model Comparison and PMS-Mamba Diagnosis

## Evidence boundary

This report uses the frozen final analysis snapshot in `reproducibility/nonstationary_analysis_v1/final`.
It does not retrain models, alter predictions, or reopen model selection. Lower values are better for
MAE, MSE, RMSE, and RMSSE. The primary confirmatory ranking remains horizon-specific test path RMSSE.

## Data checked

- Task-horizon model rows: {len(ranked)}
- Datasets/tasks: {ranked['dataset'].nunique()}
- Models: {ranked['model'].nunique()}
- Horizons: {', '.join(map(str, sorted(ranked['horizon'].unique())))}

## Path-RMSSE winners

{markdown_table(winner_counts, ['model', 'path_rmsse_wins'])}

Balanced by short/middle/long term at the dataset level, the winners are:

{markdown_table(balanced_winners, ['model', 'balanced_dataset_wins'])}

## Overall common-metric model summary

These pooled means are descriptive because they mix datasets and horizons. Use them to
understand broad tendencies, not as a replacement for paired task-horizon comparisons.

{markdown_table(model_view, ['model', 'model_category', 'evaluated_task_horizons', 'mean_path_mae', 'mean_path_rmse', 'mean_path_rmsse', 'mean_terminal_rmse', 'mean_terminal_rmsse', 'mean_skill_vs_last_value', 'path_rmsse_wins', 'path_rmsse_top3', 'average_path_rmsse_rank'], max_rows=20)}

PMS-Mamba-PD has mean path RMSSE {pms_row['mean_path_rmsse']:.4g}, {int(pms_row['path_rmsse_wins'])}
task-horizon wins, {int(pms_row['path_rmsse_top3'])} top-3 task-horizon placements, and descriptive
rank {pms_learned_rank}/{len(learned)} among learned models by pooled mean path RMSSE.

## Horizon-level comparison

{markdown_table(horizon_view[horizon_view['model'].isin([PMS_MODEL, S_MAMBA, 'NLinear', 'PatchTST', 'DLinear', 'Last-value', 'ARIMA'])], ['horizon', 'term', 'model', 'mean_path_rmse', 'mean_path_rmsse', 'path_rmsse_wins', 'path_rmsse_top3', 'average_path_rmsse_rank'], max_rows=60)}

## PMS-Mamba-PD diagnostic summary

{markdown_table(pms_terms, ['term', 'cells', 'mean_gap_to_winner_pct', 'median_gap_to_winner_pct', 'within_5pct_of_winner', 'pms_top3_cells', 'pms_better_than_s_mamba', 'pms_better_than_best_non_mamba_learned', 'pms_better_than_best_stat_or_naive', 'sig_favorable_vs_selected_learned', 'sig_unfavorable_vs_selected_learned'])}

Prespecified bootstrap summary for PMS-Mamba-PD:

{markdown_table(pms_proposal, ['proposal', 'comparator_group', 'contrast_count', 'favorable_mean_count', 'favorable_holm_count', 'unfavorable_holm_count', 'non_significant_count'])}

## PMS-Mamba-PD selected hyperparameters

{markdown_table(pms_params, ['dataset', 'validation_balanced_rmsse', 'seq_len', 'patch_len', 'stride', 'd_model', 'd_ff', 'd_state', 'learning_rate', 'moving_avg', 'ms_scales', 'ms_fusion', 'ms_use_decomp', 'use_norm'], max_rows=20)}

## Defensible paper angle

The current data do not support a claim that PMS-Mamba-PD is the all-model winner. Naive
and statistical references remain very strong. The positive, defensible result is narrower:
PMS-Mamba-PD is competitive among learned models, has the strongest PMS-vs-selected-learned
baseline profile in several long-horizon comparisons, and provides a useful nonstationary
multi-scale ablation story. Phrase this as a mixed result under a strict reference benchmark,
not as state-of-the-art dominance.

## Optimization directions for the next PMS-Mamba run

1. Align training with evaluation. Training currently uses MSE, selection uses balanced RMSSE,
   and reporting uses path RMSSE. This does not invalidate the current data, but PMS-Mamba
   may improve if the training loss is scale-normalized or baseline-relative, e.g. target-scale
   weighted MSE, RMSSE-like loss, or residual-to-last-value loss.
2. Make PMS explicitly baseline anchored. Many cells are won by Last-value or ARIMA. Predicting
   a residual around the last observed value can reduce the penalty for over-moving in weak-signal
   financial panels.
3. Separate short/middle/long model selection. The current validation selection is balanced across
   terms. A paper focused on long-term nonstationary forecasting should run a prespecified long-horizon
   PMS selection/ablation, not reuse a globally balanced configuration and then over-interpret long
   horizons post hoc.
4. Replace mean multi-scale fusion with learnable or gated fusion. The selected PMS runs frequently
   use fixed multi-scale settings. A dataset-conditioned or volatility-conditioned fusion gate is a
   direct architectural improvement consistent with the nonstationary thesis.
5. Add a small factorial ablation: residual target vs level target, MSE vs scale-normalized MSE,
   mean vs gated fusion, and current vs long-horizon calibration. Keep the test split locked and use
   validation-only decisions.
6. Treat cross-asset 252-day and FX/yields persistence failures as separate failure modes. Cross-asset
   long horizons need better patch/scale memory against PatchTST; FX/yields need stronger no-change
   anchoring against Last-value.

## Files written

- `task_horizon_metric_matrix.csv`: all model/task/horizon metrics and metric ranks.
- `model_common_metric_summary.csv`: overall model-level MAE/MSE/RMSE/RMSSE summary.
- `horizon_model_common_metric_summary.csv`: horizon-level model comparison.
- `dataset_balanced_metric_summary.csv`: dataset-level short/middle/long balanced summary.
- `common_metric_winner_counts.csv`: winner counts for each common metric.
- `pms_mamba_diagnostics.csv`: PMS-Mamba-PD cell-level gaps and bootstrap statuses.
- `pms_mamba_term_summary.csv`: PMS-Mamba-PD short/middle/long summary.
- `pms_mamba_strengths.csv`: cells where PMS-Mamba-PD is close, top-3, or favorable in bootstrap.
- `pms_mamba_regime_summary.csv`: PMS-Mamba-PD volatility-regime summary.
- `pms_mamba_selected_params.csv`: selected validation hyperparameters for PMS-Mamba-PD.
"""
    (output_root / "PMS_MAMBA_OPTIMIZATION_REPORT.md").write_text(report, encoding="utf-8")


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def main() -> None:
    args = parse_args()
    tables = load_inputs(args.final_root)
    ranked = add_metric_ranks(tables["aggregate"])
    model_view = model_summary(ranked, tables["seed_stability"], tables["runtime"])
    horizon_view = horizon_summary(ranked)
    balanced_view = dataset_balanced_summary(ranked)
    winners = metric_winner_counts(ranked)
    pms_view = pms_diagnostics(ranked, tables["bootstrap"])
    pms_terms = pms_term_summary(pms_view)
    pms_regimes = pms_regime_summary(tables["regime"])
    params = pms_selected_params()
    strengths = pms_strengths(pms_view)

    args.output_root.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_root / "task_horizon_metric_matrix.csv", ranked)
    write_csv(args.output_root / "model_common_metric_summary.csv", model_view)
    write_csv(args.output_root / "horizon_model_common_metric_summary.csv", horizon_view)
    write_csv(args.output_root / "dataset_balanced_metric_summary.csv", balanced_view)
    write_csv(args.output_root / "common_metric_winner_counts.csv", winners)
    write_csv(args.output_root / "pms_mamba_diagnostics.csv", pms_view)
    write_csv(args.output_root / "pms_mamba_term_summary.csv", pms_terms)
    write_csv(args.output_root / "pms_mamba_strengths.csv", strengths)
    write_csv(args.output_root / "pms_mamba_regime_summary.csv", pms_regimes)
    write_csv(args.output_root / "pms_mamba_selected_params.csv", params)
    write_report(
        args.output_root,
        ranked,
        model_view,
        horizon_view,
        balanced_view,
        pms_view,
        pms_terms,
        params,
        tables["proposal_summary"],
    )

    manifest = {
        "final_root": str(args.final_root),
        "output_root": str(args.output_root),
        "task_horizon_metric_rows": int(len(ranked)),
        "model_count": int(ranked["model"].nunique()),
        "dataset_count": int(ranked["dataset"].nunique()),
        "horizons": [int(value) for value in sorted(ranked["horizon"].unique())],
        "pms_diagnostic_rows": int(len(pms_view)),
        "primary_metric": "path_rmsse_mean",
        "common_metrics": LOWER_IS_BETTER_METRICS,
    }
    (args.output_root / "analysis_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote common metric suite and PMS-Mamba report to {args.output_root}")


if __name__ == "__main__":
    main()
