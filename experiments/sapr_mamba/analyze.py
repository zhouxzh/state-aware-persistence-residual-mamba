#!/usr/bin/env python
"""Recompute SAPR-Mamba synthetic evidence from retained task artifacts."""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import spearmanr

from utils.sapr_mamba.analysis import holm_adjust, paired_percentile_bootstrap, write_checksum_manifest, write_csv
from utils.sapr_mamba.io import CONFIG_ROOT, RESULT_ROOT, STUDY_SLUG, STUDY_VERSION, atomic_write_json, load_configs, sha256_path, utc_now


ANALYSIS_ROOT = REPO_ROOT / "docs" / "analysis" / STUDY_SLUG
FIGURE_ROOT = REPO_ROOT / "docs" / "figures" / STUDY_SLUG
RELEASE_ROOT = REPO_ROOT / "reproducibility" / STUDY_SLUG


def _read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _as_float(row: dict, field: str) -> float:
    return float(row[field])


def _per_seed_metrics(rows: list[dict]) -> dict[tuple, dict[str, float]]:
    values: dict[tuple, dict[str, float]] = {}
    for row in rows:
        key = (row["model"], row["seed"], row["series_id"], row["mechanism"], row["strength"], row["horizon"], row["state"])
        values[key] = {field: _as_float(row, field) for field in ("mae", "rmse", "smae", "srmse")}
    return values


def _seed_averaged(values: dict[tuple, dict[str, float]]) -> dict[tuple, dict[str, float]]:
    grouped: dict[tuple, list[dict[str, float]]] = defaultdict(list)
    for (model, _seed, series_id, mechanism, strength, horizon, state), metric in values.items():
        grouped[(model, series_id, mechanism, strength, horizon, state)].append(metric)
    return {
        key: {field: float(np.mean([entry[field] for entry in entries])) for field in ("mae", "rmse", "smae", "srmse")}
        for key, entries in grouped.items()
    }


def _paired_deltas(averaged: dict[tuple, dict[str, float]], left: str, right: str, horizon: int, state: str, mechanisms: set[str] | None, relative: bool = False) -> np.ndarray:
    deltas = []
    for (model, series_id, mechanism, strength, current_horizon, current_state), left_values in averaged.items():
        if model != left or int(current_horizon) != int(horizon) or current_state != state:
            continue
        if mechanisms is not None and mechanism not in mechanisms:
            continue
        right_key = (right, series_id, mechanism, strength, current_horizon, current_state)
        if right_key not in averaged:
            continue
        left_loss = left_values["rmse"]
        right_loss = averaged[right_key]["rmse"]
        deltas.append(left_loss / right_loss - 1.0 if relative else left_loss - right_loss)
    return np.asarray(deltas, dtype=np.float64)


def _aggregate_rows(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    fields = ("mae", "rmse", "smae", "srmse", "gate_mean", "gate_median", "residual_norm_mean", "change_score_mean")
    for row in rows:
        key = tuple(row[field] for field in ("dataset", "mechanism", "strength", "model", "horizon", "state"))
        grouped[key].append(row)
    result = []
    for key, entries in sorted(grouped.items()):
        row = dict(zip(("dataset", "mechanism", "strength", "model", "horizon", "state"), key))
        row.update(series_seed_rows=len(entries), unique_series=len({entry["series_id"] for entry in entries}), unique_seeds=len({entry["seed"] for entry in entries}))
        row.update({field: float(np.mean([_as_float(entry, field) for entry in entries])) for field in fields})
        result.append(row)
    return result


def _completion_matrix(root: Path, config: dict) -> list[dict]:
    rows = []
    for model in config["protocol"]["models"]:
        for seed in config["protocol"]["seeds"]:
            manifest = root / f"{model}_seed{seed}" / "task_manifest.json"
            status, detail = "missing", ""
            if manifest.is_file():
                payload = json.loads(manifest.read_text(encoding="utf-8"))
                status = payload.get("status", "unknown")
                detail = payload.get("error", "")
            rows.append({"model": model, "seed": int(seed), "status": status, "detail": detail, "manifest": str(manifest.relative_to(REPO_ROOT))})
    return rows


def _gate_audit(root: Path) -> list[dict]:
    rows = []
    for archive in sorted(root.glob("M3_seed*/predictions.npz")):
        seed = int(archive.parent.name.removeprefix("M3_seed"))
        with np.load(archive) as arrays:
            gates = arrays["gate"][:, 0]
            residual_norm = np.linalg.norm(arrays["residual"], axis=1)
            scores = arrays["change_score"]
            states = arrays["state"]
            series = arrays["series_index"]
        for series_index in np.unique(series):
            selected = series == series_index
            score_correlation = spearmanr(gates[selected], scores[selected]).statistic if selected.sum() >= 3 else np.nan
            residual_correlation = spearmanr(gates[selected], residual_norm[selected]).statistic if selected.sum() >= 3 else np.nan
            for state_value, state_name in ((0, "stable"), (1, "change")):
                state_selected = selected & (states == state_value)
                if not state_selected.any():
                    continue
                rows.append({
                    "seed": seed, "series_index": int(series_index), "state": state_name, "origins": int(state_selected.sum()),
                    "gate_mean": float(np.mean(gates[state_selected])), "gate_median": float(np.median(gates[state_selected])),
                    "gate_score_spearman": float(score_correlation), "gate_residual_norm_spearman": float(residual_correlation),
                })
    return rows


def _plot_primary(rows: list[dict]) -> list[Path]:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    labels = [f"{row['comparison']} h{row['horizon']}" for row in rows]
    estimates = [float(row["estimate"]) for row in rows]
    lower = [estimate - float(row["ci_low"]) for estimate, row in zip(estimates, rows)]
    upper = [float(row["ci_high"]) - estimate for estimate, row in zip(estimates, rows)]
    figure, axis = plt.subplots(figsize=(11, 4.5))
    axis.axhline(0.0, color="black", linewidth=0.8)
    axis.errorbar(np.arange(len(rows)), estimates, yerr=[lower, upper], fmt="o", capsize=3, color="#1f77b4")
    axis.set_xticks(np.arange(len(rows)), labels, rotation=45, ha="right")
    axis.set_ylabel("Paired RMSE delta (negative favours left model)")
    axis.set_title("SAPR-Mamba synthetic primary paired comparisons")
    figure.tight_layout()
    outputs = [FIGURE_ROOT / "synthetic_primary_deltas.png", FIGURE_ROOT / "synthetic_primary_deltas.pdf"]
    for output in outputs:
        figure.savefig(output, dpi=180)
    plt.close(figure)
    return outputs


def analyze_synthetic() -> dict:
    config = load_configs()
    root = RESULT_ROOT / "synthetic"
    metrics_path = root / "metrics_all.csv"
    if not metrics_path.is_file():
        raise FileNotFoundError("Synthetic metrics are absent; run synthetic-run first")
    rows = _read_rows(metrics_path)
    completion = _completion_matrix(root, config)
    incomplete = [row for row in completion if row["status"] != "complete"]
    ANALYSIS_ROOT.mkdir(parents=True, exist_ok=True)
    write_csv(ANALYSIS_ROOT / "synthetic_metrics_aggregate.csv", _aggregate_rows(rows), (
        "dataset", "mechanism", "strength", "model", "horizon", "state", "series_seed_rows", "unique_series", "unique_seeds",
        "mae", "rmse", "smae", "srmse", "gate_mean", "gate_median", "residual_norm_mean", "change_score_mean",
    ))
    write_csv(ANALYSIS_ROOT / "synthetic_completion_matrix.csv", completion, ("model", "seed", "status", "detail", "manifest"))
    values = _per_seed_metrics(rows)
    averaged = _seed_averaged(values)
    nonstable = {name for name in config["synthetic"]["mechanisms"] if name != "stable"}
    primary = []
    for comparison, left, right, state, mechanisms, relative in (
        ("H1_M2_minus_M1", "M2", "M1", "all", nonstable, False),
        ("H2_M3_minus_M2", "M3", "M2", "all", nonstable, False),
        ("stable_safety_M3_over_M0_minus_1", "M3", "M0", "all", {"stable"}, True),
    ):
        for horizon in config["synthetic"]["horizons"]:
            result = paired_percentile_bootstrap(
                _paired_deltas(averaged, left, right, int(horizon), state, mechanisms, relative),
                int(config["protocol"]["evaluation"]["bootstrap_replicates"]),
                91000 + int(horizon),
            )
            primary.append({"comparison": comparison, "left_model": left, "right_model": right, "horizon": int(horizon), "state": state, "metric": "relative_rmse" if relative else "rmse", **result})
    adjusted = holm_adjust([float(row["p_two_sided"]) for row in primary])
    for row, p_adjusted in zip(primary, adjusted):
        row["p_holm"] = p_adjusted
        row["complete_matrix"] = not incomplete
    primary_path = ANALYSIS_ROOT / "synthetic_primary_comparisons.csv"
    write_csv(primary_path, primary, ("comparison", "left_model", "right_model", "horizon", "state", "metric", "n", "estimate", "ci_low", "ci_high", "p_two_sided", "p_holm", "complete_matrix"))
    secondary = []
    for horizon in config["synthetic"]["horizons"]:
        result = paired_percentile_bootstrap(_paired_deltas(averaged, "M3", "M3-shuffle", int(horizon), "all", nonstable), int(config["protocol"]["evaluation"]["bootstrap_replicates"]), 92000 + int(horizon))
        secondary.append({"comparison": "M3_minus_M3_shuffle", "horizon": int(horizon), "metric": "rmse", **result})
    write_csv(ANALYSIS_ROOT / "synthetic_secondary_comparisons.csv", secondary, ("comparison", "horizon", "metric", "n", "estimate", "ci_low", "ci_high", "p_two_sided"))
    gate_rows = _gate_audit(root)
    write_csv(ANALYSIS_ROOT / "synthetic_gate_audit.csv", gate_rows, ("seed", "series_index", "state", "origins", "gate_mean", "gate_median", "gate_score_spearman", "gate_residual_norm_spearman"))
    figure_paths = _plot_primary(primary)
    claims = [
        {"claim_id": "H1", "artifact": str(primary_path.relative_to(REPO_ROOT)), "filter": "comparison=H1_M2_minus_M1", "interpretation": "Synthetic nonstable primary paired RMSE comparison only."},
        {"claim_id": "H2", "artifact": str(primary_path.relative_to(REPO_ROOT)), "filter": "comparison=H2_M3_minus_M2", "interpretation": "Synthetic nonstable complete-path comparison only."},
        {"claim_id": "H3", "artifact": str((ANALYSIS_ROOT / 'synthetic_gate_audit.csv').relative_to(REPO_ROOT)), "filter": "all rows", "interpretation": "Descriptive gate association, not causal evidence."},
    ]
    write_csv(RELEASE_ROOT / "claim_evidence_map.csv", claims, ("claim_id", "artifact", "filter", "interpretation"))
    summary = {
        "analyzed_at": utc_now(), "metrics_source": {"path": str(metrics_path.relative_to(REPO_ROOT)), "sha256": sha256_path(metrics_path)},
        "completion_incomplete": incomplete, "primary_rows": len(primary), "gate_rows": len(gate_rows), "figures": [str(path.relative_to(REPO_ROOT)) for path in figure_paths],
    }
    atomic_write_json(ANALYSIS_ROOT / "synthetic_analysis_manifest.json", summary)
    return summary


def export_release() -> dict:
    """Copy compact immutable evidence, then checksum it without raw arrays/checkpoints."""
    import shutil

    files = [
        CONFIG_ROOT / "protocol.lock.json", RELEASE_ROOT / "runtime_environment.json", RELEASE_ROOT / "claim_evidence_map.csv",
        ANALYSIS_ROOT / "synthetic_metrics_aggregate.csv", ANALYSIS_ROOT / "synthetic_completion_matrix.csv", ANALYSIS_ROOT / "synthetic_primary_comparisons.csv",
        ANALYSIS_ROOT / "synthetic_secondary_comparisons.csv", ANALYSIS_ROOT / "synthetic_gate_audit.csv", ANALYSIS_ROOT / "synthetic_analysis_manifest.json",
        RESULT_ROOT / "synthetic" / "metrics_all.csv", RESULT_ROOT / "synthetic" / "campaign_manifest.json", RESULT_ROOT / "synthetic" / "failures.csv",
        REPO_ROOT / "data" / STUDY_SLUG / "synthetic" / "data_manifest.json",
    ]
    compact = RELEASE_ROOT / "synthetic"
    compact.mkdir(parents=True, exist_ok=True)
    copied = []
    for source in files:
        if source.is_file():
            destination = compact / source.name
            shutil.copy2(source, destination)
            copied.append(destination)
    for source in FIGURE_ROOT.glob("synthetic_primary_deltas.*"):
        destination = compact / source.name
        shutil.copy2(source, destination)
        copied.append(destination)
    checksums = write_checksum_manifest(RELEASE_ROOT, RELEASE_ROOT / "SHA256SUMS.json")
    return {"copied": len(copied), "checksums": checksums}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, choices=("synthetic", "export"))
    args = parser.parse_args()
    outcome = analyze_synthetic() if args.stage == "synthetic" else export_release()
    print(json.dumps(outcome, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
