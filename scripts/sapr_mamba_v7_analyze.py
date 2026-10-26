#!/usr/bin/env python
"""Analyze the locked V7 Traffic external confirmation experiment."""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("SAPR_MAMBA_VERSION", "v7")

from utils.sapr_mamba.analysis import holm_adjust, paired_percentile_bootstrap, summarize_predictions, write_csv
from utils.sapr_mamba.io import atomic_write_json, sha256_path, utc_now


ROOT = REPO_ROOT / "results" / "sapr_mamba_v7" / "confirmation" / "traffic_hourly"
OUT = REPO_ROOT / "docs" / "analysis" / "sapr_mamba_v7"
MODELS = ("M0", "M1", "M2", "M3", "DLinear", "SeasonalNaive", "Drift", "M7-validation-selection")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def combine() -> Path:
    rows = []
    for path in sorted(ROOT.glob("*_seed*/metrics.csv")):
        rows.extend(read_rows(path))
    output = ROOT / "metrics_all.csv"
    if rows:
        write_csv(output, rows)
    return output


def mean_rmse(rows: list[dict[str, str]], model: str) -> dict[tuple[str, int, str], float]:
    grouped: dict[tuple[str, int, str], list[float]] = defaultdict(list)
    for row in rows:
        if row["model"] == model:
            grouped[(row["series_id"], int(row["horizon"]), row["state"])].append(float(row["rmse"]))
    return {key: float(np.mean(value)) for key, value in grouped.items()}


def artifact_failures() -> list[str]:
    failures = []
    for manifest in sorted(ROOT.glob("*_seed*/task_manifest.json")):
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        if payload.get("status") != "complete":
            failures.append(str(manifest.relative_to(REPO_ROOT)))
            continue
        for artifact in payload.get("artifacts", {}).values():
            if not isinstance(artifact, dict) or "path" not in artifact:
                continue
            path = Path(artifact["path"])
            if not path.is_file() or sha256_path(path) != artifact.get("sha256"):
                failures.append(str(path.relative_to(REPO_ROOT)) if path.exists() else str(path))
    return failures


def analyze() -> dict:
    metrics = combine()
    if not metrics.is_file():
        raise SystemExit("V7 metrics are absent")
    rows = read_rows(metrics)
    m3 = mean_rmse(rows, "M3")
    m7 = mean_rmse(rows, "M7-validation-selection")
    comparisons = []
    for index, (horizon, state) in enumerate(sorted({(key[1], key[2]) for key in m7})):
        deltas = [value - m3[(series, horizon, state)] for (series, h, s), value in m7.items() if h == horizon and s == state and (series, h, s) in m3]
        result = paired_percentile_bootstrap(np.asarray(deltas, dtype=np.float64), 10000, 170000 + index)
        comparisons.append({"comparison": "M7_validation_selection_minus_M3", "source": "zenodo_traffic_hourly", "horizon": horizon, "state": state, "metric": "raw_rmse", **result})
    for row, adjusted in zip(comparisons, holm_adjust([float(row["p_two_sided"]) for row in comparisons])):
        row["p_holm"] = adjusted
    selection_counts: Counter[str] = Counter()
    for path in sorted(ROOT.glob("M7-validation-selection_seed*/validation_model_selection.csv")):
        selection_counts.update(row["selected_model"] for row in read_rows(path))
    OUT.mkdir(parents=True, exist_ok=True)
    comparison_path = OUT / "traffic_m7_vs_m3_confirmation.csv"
    write_csv(comparison_path, comparisons, ("comparison", "source", "horizon", "state", "metric", "n", "estimate", "ci_low", "ci_high", "p_two_sided", "p_holm"))
    selection_path = OUT / "traffic_validation_selection_counts.csv"
    write_csv(selection_path, [{"model": key, "series_seed_units": value} for key, value in sorted(selection_counts.items())], ("model", "series_seed_units"))
    failures = artifact_failures()
    manifest = {
        "study": "sapr_mamba_v7",
        "status": "verified" if not failures else "complete_with_limitations",
        "created_at": utc_now(),
        "task_manifests": len(list(ROOT.glob("*_seed*/task_manifest.json"))),
        "artifact_failures": failures,
        "metrics": {"path": str(metrics.relative_to(REPO_ROOT)), "sha256": sha256_path(metrics)},
        "comparison": {"path": str(comparison_path.relative_to(REPO_ROOT)), "sha256": sha256_path(comparison_path)},
        "test_targets_used_for_selection": False,
    }
    atomic_write_json(OUT / "confirmation_manifest.json", manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


if __name__ == "__main__":
    analyze()
