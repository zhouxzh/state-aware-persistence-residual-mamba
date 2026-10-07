#!/usr/bin/env python
"""Analyze and independently verify retained SAPR-Mamba V2 real-panel evidence.

This script reads completed prediction archives only. It neither trains a model nor
downloads data. The primary unit is a series after averaging repeated random seeds;
the four ETT files remain one source cluster rather than four independent domains.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("SAPR_MAMBA_VERSION", "v2")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import spearmanr

from utils.sapr_mamba.analysis import (
    METRIC_COLUMNS,
    holm_adjust,
    paired_percentile_bootstrap,
    summarize_predictions,
    write_csv,
)
from utils.sapr_mamba.io import (
    DATA_ROOT,
    RESULT_ROOT,
    STUDY_SLUG,
    atomic_write_json,
    config_hashes,
    sha256_path,
    utc_now,
)


ANALYSIS_ROOT = REPO_ROOT / "docs" / "analysis" / STUDY_SLUG
FIGURE_ROOT = REPO_ROOT / "docs" / "figures" / STUDY_SLUG
REAL_ROOT = RESULT_ROOT / "real"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@lru_cache(maxsize=1)
def prepared_panel_index() -> dict[str, dict]:
    """Read the active panel manifest once, including additive amendments."""
    path = DATA_ROOT / "real" / "processed" / "prepared_manifest.json"
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(item["panel_id"]): item for item in payload.get("panels", [])}


def panel_source(dataset: str) -> str:
    """Use the frozen source cluster, grouping the four ETT files together."""
    item = prepared_panel_index().get(dataset)
    if item is not None and item.get("source_cluster"):
        return str(item["source_cluster"])
    return "ett" if dataset.startswith("ett_") else dataset


def panel_horizons(configs: dict, panel: str) -> list[int]:
    manifest_item = prepared_panel_index().get(panel)
    if manifest_item is not None and manifest_item.get("horizons"):
        return [int(value) for value in manifest_item["horizons"]]
    panels = configs["real_panels"]["panels"]
    if panel in {"electricity", "beijing_air_quality"}:
        return [int(value) for value in panels[panel]["horizons"]]
    if panel.startswith("ett_"):
        period = int(panels["ett"]["period_by_file"][panel.removeprefix("ett_")])
        return [period // 8, period // 4, period // 2, period]
    raise ValueError(f"Unknown real panel: {panel}")


def expected_tasks(protocol: dict, prepared_manifest: dict) -> list[dict[str, object]]:
    """Reconstruct the frozen 180-task V2 real matrix from configuration."""
    panels = [str(entry["panel_id"]) for entry in prepared_manifest["panels"]]
    random_models = set(protocol["real_seed_policy"]["five_seeds_for"])
    deterministic_seed = int(protocol["real_seed_policy"]["single_deterministic_seed"])
    models = [
        *protocol["models"],
        "SeasonalNaive",
        "Drift",
        "DLinear",
        "ETS",
        "ARIMA",
    ]
    rows = []
    for panel in panels:
        for model in models:
            seeds = protocol["seeds"] if model in random_models else [deterministic_seed]
            for seed in seeds:
                rows.append({"dataset": panel, "source": panel_source(panel), "model": model, "seed": int(seed)})
    return rows


def expected_seed_set(protocol: dict, model: str) -> frozenset[int]:
    if model in set(protocol["real_seed_policy"]["five_seeds_for"]):
        return frozenset(int(seed) for seed in protocol["seeds"])
    return frozenset({int(protocol["real_seed_policy"]["single_deterministic_seed"])})


def manifest_artifact_problems(payload: dict) -> list[str]:
    problems = []
    for name, entry in payload.get("artifacts", {}).items():
        if not isinstance(entry, dict) or "path" not in entry or "sha256" not in entry:
            continue
        candidate = Path(entry["path"])
        if not candidate.is_file():
            problems.append(f"missing:{name}")
        elif sha256_path(candidate) != entry["sha256"]:
            problems.append(f"checksum_mismatch:{name}")
    return problems


def metric_counter(rows: list[dict[str, str]]) -> Counter[tuple[str, ...]]:
    return Counter(tuple(row.get(field, "") for field in METRIC_COLUMNS) for row in rows)


def task_metric_matrix_matches(metrics_rows: list[dict[str, str]], tasks: list[dict[str, object]]) -> bool:
    recombined = []
    for task in tasks:
        path = REAL_ROOT / str(task["dataset"]) / f"{task['model']}_seed{task['seed']}" / "metrics.csv"
        if not path.is_file():
            return False
        recombined.extend(read_rows(path))
    return metric_counter(recombined) == metric_counter(metrics_rows)


def completion_matrix(tasks: list[dict[str, object]], metrics_rows: list[dict[str, str]]) -> tuple[list[dict], dict]:
    """Check all frozen task manifests, retained artifacts, and combined metrics."""
    current_config_hashes = config_hashes()
    rows = []
    expected_keys = set()
    for task in tasks:
        dataset, model, seed = str(task["dataset"]), str(task["model"]), int(task["seed"])
        key = (dataset, model, seed)
        expected_keys.add(key)
        manifest = REAL_ROOT / dataset / f"{model}_seed{seed}" / "task_manifest.json"
        metrics_count = sum(
            row["dataset"] == dataset and row["model"] == model and int(row["seed"]) == seed
            for row in metrics_rows
        )
        status, artifact_problems, hash_match = "missing", ["missing_manifest"], False
        if manifest.is_file():
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            status = str(payload.get("status", "unknown"))
            artifact_problems = manifest_artifact_problems(payload)
            hash_match = payload.get("config_hashes") == current_config_hashes
        rows.append({
            **task,
            "status": status,
            "metrics_rows": metrics_count,
            "config_hashes_match": hash_match,
            "artifact_problems": ";".join(artifact_problems),
            "manifest": str(manifest.relative_to(REPO_ROOT)),
        })
    observed = set()
    for manifest in REAL_ROOT.glob("*/*_seed*/task_manifest.json"):
        dataset = manifest.parents[1].name
        model, seed_text = manifest.parent.name.rsplit("_seed", 1)
        observed.add((dataset, model, int(seed_text)))
    summary = {
        "expected_task_count": len(tasks),
        "observed_task_manifest_count": len(observed),
        "unexpected_task_manifests": [list(item) for item in sorted(observed - expected_keys)],
        "missing_task_manifests": [list(item) for item in sorted(expected_keys - observed)],
        "incomplete_tasks": sum(row["status"] != "complete" for row in rows),
        "artifact_problem_tasks": sum(bool(row["artifact_problems"]) for row in rows),
        "config_hash_mismatch_tasks": sum(not row["config_hashes_match"] for row in rows),
        "metrics_matrix_matches_task_files": task_metric_matrix_matches(metrics_rows, tasks),
    }
    summary["complete"] = (
        not summary["unexpected_task_manifests"]
        and not summary["missing_task_manifests"]
        and summary["incomplete_tasks"] == 0
        and summary["artifact_problem_tasks"] == 0
        and summary["config_hash_mismatch_tasks"] == 0
        and summary["metrics_matrix_matches_task_files"]
    )
    return rows, summary


def average_seed_metrics(rows: list[dict[str, str]]) -> dict[tuple[str, str, str, int, str], dict[str, object]]:
    grouped: dict[tuple[str, str, str, int, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["dataset"], row["series_id"], row["model"], int(row["horizon"]), row["state"])].append(row)
    output = {}
    fields = ("mae", "rmse", "smae", "srmse", "gate_mean", "gate_median", "residual_norm_mean", "change_score_mean")
    for key, entries in grouped.items():
        output[key] = {field: float(np.mean([float(entry[field]) for entry in entries])) for field in fields}
        output[key]["seeds"] = frozenset(int(entry["seed"]) for entry in entries)
        output[key]["source"] = panel_source(key[0])
    return output


def series_aggregates(seed_means: dict[tuple[str, str, str, int, str], dict[str, object]]) -> list[dict]:
    fields = ("mae", "rmse", "smae", "srmse", "gate_mean", "gate_median", "residual_norm_mean", "change_score_mean")
    rows = []
    for (dataset, series_id, model, horizon, state), values in sorted(seed_means.items()):
        rows.append({
            "source": values["source"], "dataset": dataset, "series_id": series_id,
            "model": model, "horizon": horizon, "state": state,
            "unique_seeds": len(values["seeds"]),
            **{field: values[field] for field in fields},
        })
    return rows


def aggregate_by(rows: list[dict], group_fields: tuple[str, ...]) -> list[dict]:
    fields = ("mae", "rmse", "smae", "srmse", "gate_mean", "gate_median", "residual_norm_mean", "change_score_mean")
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[field] for field in group_fields)].append(row)
    output = []
    for key, entries in sorted(grouped.items()):
        output.append({
            **dict(zip(group_fields, key)),
            "unique_series": len({(entry["dataset"], entry["series_id"]) for entry in entries}),
            "panels": ";".join(sorted({entry["dataset"] for entry in entries})),
            **{field: float(np.mean([float(entry[field]) for entry in entries])) for field in fields},
        })
    return output


def expected_all_units(configs: dict, prepared_manifest: dict) -> dict[tuple[str, int], set[tuple[str, str]]]:
    """Return frozen source/panel/series units for each available horizon."""
    output: dict[tuple[str, int], set[tuple[str, str]]] = defaultdict(set)
    for panel in prepared_manifest["panels"]:
        panel_id = str(panel["panel_id"])
        roster = json.loads((DATA_ROOT / "real" / "processed" / f"{panel_id}_roster.json").read_text(encoding="utf-8"))
        for horizon in panel_horizons(configs, panel_id):
            output[(panel_source(panel_id), horizon)].update((panel_id, record["series_id"]) for record in roster["records"])
    return output


def paired_deltas(
    seed_means: dict[tuple[str, str, str, int, str], dict[str, object]],
    protocol: dict,
    units: set[tuple[str, str]],
    left: str,
    right: str,
    horizon: int,
    state: str,
    relative: bool,
) -> tuple[np.ndarray, int]:
    deltas, missing = [], 0
    left_seeds, right_seeds = expected_seed_set(protocol, left), expected_seed_set(protocol, right)
    for dataset, series_id in sorted(units):
        left_values = seed_means.get((dataset, series_id, left, horizon, state))
        right_values = seed_means.get((dataset, series_id, right, horizon, state))
        if (
            left_values is None
            or right_values is None
            or left_values["seeds"] != left_seeds
            or right_values["seeds"] != right_seeds
        ):
            missing += 1
            continue
        left_rmse, right_rmse = float(left_values["rmse"]), float(right_values["rmse"])
        if relative:
            if right_rmse == 0.0:
                missing += 1
                continue
            deltas.append(left_rmse / right_rmse - 1.0)
        else:
            deltas.append(left_rmse - right_rmse)
    return np.asarray(deltas, dtype=np.float64), missing


def primary_comparisons(
    seed_means: dict[tuple[str, str, str, int, str], dict[str, object]],
    protocol: dict,
    units_by_source_horizon: dict[tuple[str, int], set[tuple[str, str]]],
    technical_matrix_complete: bool,
) -> list[dict]:
    definitions = (
        ("H1_M2_minus_M1", "M2", "M1", "all", False),
        ("H2_M3_minus_M2", "M3", "M2", "all", False),
        ("stable_safety_M3_over_M0_minus_1", "M3", "M0", "stable", True),
    )
    rows = []
    for source, horizon in sorted(units_by_source_horizon):
        units = units_by_source_horizon[(source, horizon)]
        for comparison, left, right, state, relative in definitions:
            values, missing_units = paired_deltas(seed_means, protocol, units, left, right, horizon, state, relative)
            result = paired_percentile_bootstrap(values, int(protocol["evaluation"]["bootstrap_replicates"]), 93000 + horizon + len(rows))
            state_coverage = int(result["n"]) / len(units) if units else float("nan")
            if result["n"] == 0:
                evidence_status = "no_eligible_state_units" if state == "stable" else "missing_pair_data"
            elif state == "stable" and state_coverage < 1.0:
                evidence_status = "limited_stable_state_coverage"
            elif missing_units:
                evidence_status = "incomplete_pair_matrix"
            else:
                evidence_status = "complete"
            rows.append({
                "comparison": comparison, "left_model": left, "right_model": right,
                "source": source, "horizon": horizon, "state": state,
                "metric": "relative_rmse" if relative else "raw_rmse",
                "source_sequence_units": len(units), "missing_pair_units": missing_units,
                "state_coverage": state_coverage, "evidence_status": evidence_status,
                "technical_matrix_complete": technical_matrix_complete,
                **result,
            })
    adjusted = holm_adjust([float(row["p_two_sided"]) for row in rows])
    for row, adjusted_value in zip(rows, adjusted):
        row["p_holm"] = adjusted_value
    return rows


def statistical_audit(root: Path) -> list[dict]:
    rows = []
    for path in sorted(root.glob("*/*_seed*/failures.csv")):
        records = read_rows(path)
        rows.append({
            "dataset": path.parents[1].name,
            "source": panel_source(path.parents[1].name),
            "model": path.parent.name.split("_seed")[0],
            "failure_rows": len(records),
            "path": str(path.relative_to(REPO_ROOT)),
            "sha256": sha256_path(path),
        })
    return rows


def gate_audit() -> tuple[list[dict], list[dict]]:
    details = []
    for archive in sorted(REAL_ROOT.glob("*/M3_seed*/predictions.npz")):
        dataset = archive.parents[1].name
        seed = int(archive.parent.name.removeprefix("M3_seed"))
        roster = json.loads((DATA_ROOT / "real" / "processed" / f"{dataset}_roster.json").read_text(encoding="utf-8"))
        series_ids = [record["series_id"] for record in roster["records"]]
        with np.load(archive) as arrays:
            gates = arrays["gate"][:, 0]
            residual_norm = np.linalg.norm(arrays["residual"], axis=1)
            scores, states, series = arrays["change_score"], arrays["state"], arrays["series_index"]
        for series_index in np.unique(series):
            selected = series == series_index
            score_corr = spearmanr(gates[selected], scores[selected]).statistic if selected.sum() >= 3 else np.nan
            residual_corr = spearmanr(gates[selected], residual_norm[selected]).statistic if selected.sum() >= 3 else np.nan
            for state_value, state_name in ((0, "stable"), (1, "change")):
                state_selected = selected & (states == state_value)
                if not state_selected.any():
                    continue
                details.append({
                    "source": panel_source(dataset), "dataset": dataset, "seed": seed,
                    "series_index": int(series_index), "series_id": series_ids[int(series_index)],
                    "state": state_name, "origins": int(state_selected.sum()),
                    "gate_mean": float(np.mean(gates[state_selected])), "gate_median": float(np.median(gates[state_selected])),
                    "gate_score_spearman": float(score_corr), "gate_residual_norm_spearman": float(residual_corr),
                })
    summary = []
    grouped: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in details:
        grouped[(row["source"], row["dataset"], row["state"])].append(row)
    for (source, dataset, state), entries in sorted(grouped.items()):
        summary.append({
            "source": source, "dataset": dataset, "state": state,
            "series_seed_units": len(entries), "origins": sum(int(entry["origins"]) for entry in entries),
            "gate_mean": float(np.mean([entry["gate_mean"] for entry in entries])),
            "gate_median": float(np.mean([entry["gate_median"] for entry in entries])),
            "gate_score_spearman": float(np.nanmean([entry["gate_score_spearman"] for entry in entries])),
            "gate_residual_norm_spearman": float(np.nanmean([entry["gate_residual_norm_spearman"] for entry in entries])),
        })
    return details, summary


def plot_primary(rows: list[dict]) -> list[Path]:
    primary = [row for row in rows if row["comparison"] in {"H1_M2_minus_M1", "H2_M3_minus_M2"}]
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    colors = {"H1_M2_minus_M1": "#0072B2", "H2_M3_minus_M2": "#D55E00"}
    for axis, comparison in zip(axes, ("H1_M2_minus_M1", "H2_M3_minus_M2")):
        subset = [row for row in primary if row["comparison"] == comparison]
        labels = [f"{row['source']}\nh={row['horizon']}" for row in subset]
        estimates = np.asarray([float(row["estimate"]) for row in subset])
        lower = estimates - np.asarray([float(row["ci_low"]) for row in subset])
        upper = np.asarray([float(row["ci_high"]) for row in subset]) - estimates
        axis.axhline(0.0, color="black", linewidth=0.8)
        axis.errorbar(np.arange(len(subset)), estimates, yerr=np.vstack((lower, upper)), fmt="o", capsize=3, color=colors[comparison])
        axis.set_ylabel("Paired RMSE delta")
        axis.set_title(f"{comparison}: negative favours the left model")
        axis.grid(axis="y", color="#d9d9d9", linewidth=0.6)
        axis.set_xticks(np.arange(len(subset)), labels)
    axes[-1].tick_params(axis="x", labelrotation=45)
    figure.tight_layout()
    outputs = [FIGURE_ROOT / "real_primary_deltas.png", FIGURE_ROOT / "real_primary_deltas.pdf"]
    for output in outputs:
        figure.savefig(output, dpi=300, facecolor="white")
    plt.close(figure)
    return outputs


def write_figure_manifest(source: Path, outputs: list[Path]) -> Path:
    manifest = FIGURE_ROOT / "real_figure_manifest.json"
    payload = {
        "study": STUDY_SLUG,
        "created_at": utc_now(),
        "source_files": [{"path": str(source.relative_to(REPO_ROOT)), "sha256": sha256_path(source)}],
        "output_files": [{"path": str(path.relative_to(REPO_ROOT)), "sha256": sha256_path(path)} for path in outputs],
        "description": "Source-stratified real-panel primary paired RMSE deltas with 95% paired percentile bootstrap intervals.",
    }
    atomic_write_json(manifest, payload)
    return manifest


def analyze() -> dict:
    metrics_path = REAL_ROOT / "metrics_all.csv"
    prepared_path = DATA_ROOT / "real" / "processed" / "prepared_manifest.json"
    if not metrics_path.is_file() or not prepared_path.is_file():
        raise SystemExit("V3 real metrics or prepared manifest is unavailable")
    from utils.sapr_mamba.io import load_configs

    configs = load_configs()
    protocol = configs["protocol"]
    metrics_rows = read_rows(metrics_path)
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    tasks = expected_tasks(protocol, prepared)
    completion, completion_summary = completion_matrix(tasks, metrics_rows)
    seed_means = average_seed_metrics(metrics_rows)
    per_series = series_aggregates(seed_means)
    panel_aggregate = aggregate_by(per_series, ("source", "dataset", "model", "horizon", "state"))
    source_aggregate = aggregate_by(per_series, ("source", "model", "horizon", "state"))
    units = expected_all_units(configs, prepared)
    primary = primary_comparisons(seed_means, protocol, units, bool(completion_summary["complete"]))
    state_coverage = [
        {
            "source": row["source"], "horizon": row["horizon"],
            "source_sequence_units": row["source_sequence_units"], "stable_sequence_units": row["n"],
            "stable_state_coverage": row["state_coverage"], "evidence_status": row["evidence_status"],
        }
        for row in primary if row["comparison"] == "stable_safety_M3_over_M0_minus_1"
    ]
    audit = statistical_audit(REAL_ROOT)
    gate_details, gate_summary = gate_audit()
    ANALYSIS_ROOT.mkdir(parents=True, exist_ok=True)
    write_csv(ANALYSIS_ROOT / "real_completion_matrix.csv", completion, (
        "source", "dataset", "model", "seed", "status", "metrics_rows", "config_hashes_match", "artifact_problems", "manifest",
    ))
    write_csv(ANALYSIS_ROOT / "real_series_seed_averages.csv", per_series, (
        "source", "dataset", "series_id", "model", "horizon", "state", "unique_seeds",
        "mae", "rmse", "smae", "srmse", "gate_mean", "gate_median", "residual_norm_mean", "change_score_mean",
    ))
    write_csv(ANALYSIS_ROOT / "real_panel_metrics_aggregate.csv", panel_aggregate, (
        "source", "dataset", "model", "horizon", "state", "unique_series", "panels",
        "mae", "rmse", "smae", "srmse", "gate_mean", "gate_median", "residual_norm_mean", "change_score_mean",
    ))
    write_csv(ANALYSIS_ROOT / "real_source_metrics_aggregate.csv", source_aggregate, (
        "source", "model", "horizon", "state", "unique_series", "panels",
        "mae", "rmse", "smae", "srmse", "gate_mean", "gate_median", "residual_norm_mean", "change_score_mean",
    ))
    primary_path = ANALYSIS_ROOT / "real_primary_comparisons.csv"
    write_csv(primary_path, primary, (
        "comparison", "left_model", "right_model", "source", "horizon", "state", "metric",
        "source_sequence_units", "missing_pair_units", "state_coverage", "evidence_status", "technical_matrix_complete",
        "n", "estimate", "ci_low", "ci_high", "p_two_sided", "p_holm",
    ))
    # V3.1 declares the solar and tourism source clusters as external
    # holdouts. Keep their paired estimates in a separate table so the
    # manuscript cannot accidentally present them as ordinary development
    # panels or silently pool them with the base V3 sources.
    external_clusters = {
        str(item.get("source_cluster"))
        for item in prepared.get("panels", [])
        if bool(item.get("external_holdout", False)) and item.get("source_cluster")
    }
    external_primary = [row for row in primary if row.get("source") in external_clusters]
    external_primary_path = ANALYSIS_ROOT / "external_holdout_primary_comparisons.csv"
    write_csv(external_primary_path, external_primary, (
        "comparison", "left_model", "right_model", "source", "horizon", "state", "metric",
        "source_sequence_units", "missing_pair_units", "state_coverage", "evidence_status", "technical_matrix_complete",
        "n", "estimate", "ci_low", "ci_high", "p_two_sided", "p_holm",
    ))
    write_csv(ANALYSIS_ROOT / "real_stable_state_coverage.csv", state_coverage, (
        "source", "horizon", "source_sequence_units", "stable_sequence_units", "stable_state_coverage", "evidence_status",
    ))
    write_csv(ANALYSIS_ROOT / "real_statistical_audit.csv", audit, ("dataset", "source", "model", "failure_rows", "path", "sha256"))
    write_csv(ANALYSIS_ROOT / "real_gate_audit.csv", gate_details, (
        "source", "dataset", "seed", "series_index", "series_id", "state", "origins",
        "gate_mean", "gate_median", "gate_score_spearman", "gate_residual_norm_spearman",
    ))
    write_csv(ANALYSIS_ROOT / "real_gate_summary.csv", gate_summary, (
        "source", "dataset", "state", "series_seed_units", "origins", "gate_mean", "gate_median",
        "gate_score_spearman", "gate_residual_norm_spearman",
    ))
    figure_paths = plot_primary(primary)
    figure_manifest = write_figure_manifest(primary_path, figure_paths)
    claim_path = REPO_ROOT / "reproducibility" / STUDY_SLUG / "claim_evidence_map.csv"
    previous_claims = read_rows(claim_path) if claim_path.is_file() else []
    retained_claims = [row for row in previous_claims if not row["claim_id"].startswith("real_")]
    retained_claims.extend([
        {"claim_id": "real_H1", "artifact": str(primary_path.relative_to(REPO_ROOT)), "filter": "comparison=H1_M2_minus_M1; state=all", "interpretation": "Source-stratified real-panel paired comparison; no cross-source universal inference.", "sha256": sha256_path(primary_path)},
        {"claim_id": "real_H2", "artifact": str(primary_path.relative_to(REPO_ROOT)), "filter": "comparison=H2_M3_minus_M2; state=all", "interpretation": "Source-stratified complete-path comparison; not an isolated gate causal effect.", "sha256": sha256_path(primary_path)},
        {"claim_id": "real_stable_safety", "artifact": str((ANALYSIS_ROOT / 'real_stable_state_coverage.csv').relative_to(REPO_ROOT)), "filter": "all rows", "interpretation": "Stable-state safety evidence is limited to available state-labelled sequence units.", "sha256": sha256_path(ANALYSIS_ROOT / 'real_stable_state_coverage.csv')},
        {"claim_id": "real_H3", "artifact": str((ANALYSIS_ROOT / 'real_gate_audit.csv').relative_to(REPO_ROOT)), "filter": "all rows", "interpretation": "Descriptive gate association only, not causal mechanism evidence.", "sha256": sha256_path(ANALYSIS_ROOT / 'real_gate_audit.csv')},
    ])
    write_csv(claim_path, retained_claims, ("claim_id", "artifact", "filter", "interpretation", "sha256"))
    summary = {
        "analyzed_at": utc_now(), "study": STUDY_SLUG,
        "metrics_source": {"path": str(metrics_path.relative_to(REPO_ROOT)), "sha256": sha256_path(metrics_path), "rows": len(metrics_rows)},
        "completion": completion_summary,
        "primary_rows": len(primary),
        "external_holdout_clusters": sorted(external_clusters),
        "external_holdout_primary_rows": len(external_primary),
        "primary_rows_with_finite_p": int(sum(np.isfinite(float(row["p_two_sided"])) for row in primary)),
        "stable_safety_limited_rows": sum(row["evidence_status"] != "complete" for row in state_coverage),
        "statistical_failure_rows": sum(row["failure_rows"] for row in audit),
        "gate_audit_rows": len(gate_details),
        "figures": [str(path.relative_to(REPO_ROOT)) for path in figure_paths],
        "figure_manifest": str(figure_manifest.relative_to(REPO_ROOT)),
    }
    atomic_write_json(ANALYSIS_ROOT / "real_analysis_manifest.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def panel_metadata(panel: str) -> list[dict]:
    roster = json.loads((DATA_ROOT / "real" / "processed" / f"{panel}_roster.json").read_text(encoding="utf-8"))
    quality = {item["series_id"]: item for item in roster["quality"] if item["included"]}
    metadata = []
    for record in roster["records"]:
        item = dict(record)
        item["strength"] = float("nan") if item.get("strength") is None else item["strength"]
        item["training_std"] = max(float(quality[item["series_id"]]["training_std"]), 1e-6)
        item["training_mean"] = float(quality[item["series_id"]]["training_mean"])
        metadata.append(item)
    return metadata


def metric_rows_match(expected: list[dict], observed: list[dict[str, str]]) -> tuple[bool, str]:
    expected_by_key = {tuple(str(row[field]) for field in METRIC_COLUMNS[:8]): row for row in expected}
    observed_by_key = {tuple(row[field] for field in METRIC_COLUMNS[:8]): row for row in observed}
    if expected_by_key.keys() != observed_by_key.keys():
        return False, "metric_keys_mismatch"
    for key, expected_row in expected_by_key.items():
        observed_row = observed_by_key[key]
        for field in METRIC_COLUMNS[8:]:
            if field in {"origins", "points"}:
                if int(expected_row[field]) != int(observed_row[field]):
                    return False, f"integer_mismatch:{field}"
            elif not np.isclose(float(expected_row[field]), float(observed_row[field]), rtol=1e-6, atol=1e-6, equal_nan=True):
                return False, f"value_mismatch:{field}"
    return True, ""


def verify() -> dict:
    """Recompute every retained real task's metrics from prediction archives."""
    from utils.sapr_mamba.io import load_configs

    configs = load_configs()
    prepared = json.loads((DATA_ROOT / "real" / "processed" / "prepared_manifest.json").read_text(encoding="utf-8"))
    tasks = expected_tasks(configs["protocol"], prepared)
    results = []
    for task in tasks:
        dataset, model, seed = str(task["dataset"]), str(task["model"]), int(task["seed"])
        task_root = REAL_ROOT / dataset / f"{model}_seed{seed}"
        archive, metrics = task_root / "predictions.npz", task_root / "metrics.csv"
        passed, detail = False, "missing_archive_or_metrics"
        if archive.is_file() and metrics.is_file():
            with np.load(archive) as arrays:
                recomputed = summarize_predictions(
                    prediction=arrays["prediction"], target=arrays["target"], state=arrays["state"], gate=arrays["gate"],
                    residual=arrays["residual"], change_scores=arrays["change_score"], series_indices=arrays["series_index"],
                    series_metadata=panel_metadata(dataset), model=model, seed=seed,
                    horizons=panel_horizons(configs, dataset), dataset=dataset,
                )
            passed, detail = metric_rows_match(recomputed, read_rows(metrics))
        results.append({**task, "metrics_recomputed": passed, "detail": detail, "archive": str(archive.relative_to(REPO_ROOT))})
    ANALYSIS_ROOT.mkdir(parents=True, exist_ok=True)
    write_csv(ANALYSIS_ROOT / "real_recompute_matrix.csv", results, (
        "source", "dataset", "model", "seed", "metrics_recomputed", "detail", "archive",
    ))
    summary = {
        "verified_at": utc_now(), "study": STUDY_SLUG,
        "python_executable": sys.executable,
        "conda_prefix": os.environ.get("CONDA_PREFIX", ""),
        "tasks": len(results), "metric_recompute_failures": [row for row in results if not row["metrics_recomputed"]],
        "status": "verified" if all(row["metrics_recomputed"] for row in results) else "failed",
    }
    atomic_write_json(ANALYSIS_ROOT / "real_verification_manifest.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("analyze", "verify"), default="analyze")
    args = parser.parse_args()
    (analyze if args.stage == "analyze" else verify)()


if __name__ == "__main__":
    main()
