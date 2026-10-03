#!/usr/bin/env python
"""Analyze completed SAPR-Mamba V2 real-panel evidence without touching training code."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("SAPR_MAMBA_VERSION", "v2")

import numpy as np

from utils.sapr_mamba.analysis import paired_percentile_bootstrap, write_csv
from utils.sapr_mamba.io import RESULT_ROOT, STUDY_SLUG, atomic_write_json, load_configs, sha256_path, utc_now


ANALYSIS_ROOT = REPO_ROOT / "docs" / "analysis" / STUDY_SLUG
RELEASE_ROOT = REPO_ROOT / "reproducibility" / STUDY_SLUG


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def average_seed_metrics(rows: list[dict]) -> dict[tuple, dict[str, float]]:
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["dataset"], row["series_id"], row["model"], row["horizon"], row["state"])].append(row)
    metrics: dict[tuple, dict[str, float]] = {}
    for key, entries in grouped.items():
        metrics[key] = {
            field: float(np.mean([float(entry[field]) for entry in entries]))
            for field in ("mae", "rmse", "smae", "srmse")
        }
        metrics[key]["seeds"] = len({entry["seed"] for entry in entries})
    return metrics


def aggregate_real(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["dataset"], row["model"], row["horizon"], row["state"])].append(row)
    output = []
    for key, entries in sorted(grouped.items()):
        row = dict(zip(("dataset", "model", "horizon", "state"), key))
        row.update(
            series_seed_rows=len(entries),
            unique_series=len({entry["series_id"] for entry in entries}),
            unique_seeds=len({entry["seed"] for entry in entries}),
        )
        for field in ("mae", "rmse", "smae", "srmse", "gate_mean", "gate_median", "residual_norm_mean", "change_score_mean"):
            row[field] = float(np.mean([float(entry[field]) for entry in entries]))
        output.append(row)
    return output


def paired_comparisons(seed_means: dict[tuple, dict[str, float]], protocol: dict) -> list[dict]:
    output = []
    for left, right, label in (("M2", "M1", "H1_M2_minus_M1"), ("M3", "M2", "H2_M3_minus_M2")):
        sources = sorted({key[0] for key in seed_means})
        for source in sources:
            horizons = sorted({int(key[3]) for key in seed_means if key[0] == source})
            for horizon in horizons:
                deltas = []
                for key, values in seed_means.items():
                    dataset, series_id, model, row_horizon, state = key
                    if dataset != source or model != left or int(row_horizon) != horizon or state != "all":
                        continue
                    paired = (dataset, series_id, right, row_horizon, state)
                    if paired in seed_means:
                        deltas.append(values["rmse"] - seed_means[paired]["rmse"])
                result = paired_percentile_bootstrap(
                    np.asarray(deltas), int(protocol["evaluation"]["bootstrap_replicates"]), 93000 + horizon
                )
                output.append({"comparison": label, "dataset": source, "horizon": horizon, "metric": "raw_rmse", **result})
    return output


def statistical_audit(root: Path) -> list[dict]:
    rows = []
    for path in sorted(root.glob("*/*_seed*/failures.csv")):
        records = read_rows(path)
        rows.append({
            "dataset": path.parents[1].name,
            "model": path.parent.name.split("_seed")[0],
            "failure_rows": len(records),
            "path": str(path.relative_to(REPO_ROOT)),
            "sha256": sha256_path(path),
        })
    return rows


def analyze() -> dict:
    root = RESULT_ROOT / "real"
    metrics_path = root / "metrics_all.csv"
    if not metrics_path.is_file():
        raise SystemExit("V2 real metrics matrix is not available")
    config = load_configs()["protocol"]
    rows = read_rows(metrics_path)
    manifests = sorted(root.glob("*/*_seed*/task_manifest.json"))
    incomplete = [
        str(path.relative_to(REPO_ROOT))
        for path in manifests
        if json.loads(path.read_text(encoding="utf-8")).get("status") != "complete"
    ]
    seed_means = average_seed_metrics(rows)
    aggregate = aggregate_real(rows)
    comparisons = paired_comparisons(seed_means, config)
    audit = statistical_audit(root)
    ANALYSIS_ROOT.mkdir(parents=True, exist_ok=True)
    write_csv(
        ANALYSIS_ROOT / "real_metrics_aggregate.csv", aggregate,
        ("dataset", "model", "horizon", "state", "series_seed_rows", "unique_series", "unique_seeds", "mae", "rmse", "smae", "srmse", "gate_mean", "gate_median", "residual_norm_mean", "change_score_mean"),
    )
    write_csv(
        ANALYSIS_ROOT / "real_paired_comparisons.csv", comparisons,
        ("comparison", "dataset", "horizon", "metric", "n", "estimate", "ci_low", "ci_high", "p_two_sided"),
    )
    write_csv(
        ANALYSIS_ROOT / "real_statistical_audit.csv", audit,
        ("dataset", "model", "failure_rows", "path", "sha256"),
    )
    summary = {
        "analyzed_at": utc_now(),
        "study": STUDY_SLUG,
        "metrics_source": {"path": str(metrics_path.relative_to(REPO_ROOT)), "sha256": sha256_path(metrics_path)},
        "task_manifests": len(manifests),
        "incomplete": incomplete,
        "metric_rows": len(rows),
        "statistical_failure_rows": sum(row["failure_rows"] for row in audit),
    }
    atomic_write_json(ANALYSIS_ROOT / "real_analysis_manifest.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("analyze",), default="analyze")
    parser.parse_args()
    analyze()
