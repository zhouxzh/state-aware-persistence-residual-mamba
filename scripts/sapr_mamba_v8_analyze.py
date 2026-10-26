#!/usr/bin/env python
"""Analyze frozen V8 KDD original-path external confirmation comparisons."""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("SAPR_MAMBA_VERSION", "v8")

from utils.sapr_mamba.analysis import holm_adjust, paired_percentile_bootstrap, write_csv
from utils.sapr_mamba.io import atomic_write_json, sha256_path, utc_now


ROOT = REPO_ROOT / "results" / "sapr_mamba_v8" / "confirmation" / "kdd_cup_2018"
OUT = REPO_ROOT / "docs" / "analysis" / "sapr_mamba_v8"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def means(rows: list[dict[str, str]], model: str) -> dict[tuple[str, int, str], float]:
    grouped: dict[tuple[str, int, str], list[float]] = defaultdict(list)
    for row in rows:
        if row["model"] == model:
            grouped[(row["series_id"], int(row["horizon"]), row["state"])].append(float(row["rmse"]))
    return {key: float(np.mean(value)) for key, value in grouped.items()}


def analyze() -> dict:
    rows = []
    manifests = sorted(ROOT.glob("*_seed*/task_manifest.json"))
    failures = []
    for manifest in manifests:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        if payload.get("status") != "complete":
            failures.append(str(manifest.relative_to(REPO_ROOT)))
        metrics = manifest.parent / "metrics.csv"
        if not metrics.is_file():
            failures.append(str(metrics.relative_to(REPO_ROOT)))
        elif payload.get("status") == "complete":
            rows.extend(read_rows(metrics))
    if failures:
        raise RuntimeError(f"incomplete V8 candidate matrix: {failures[:5]}")
    metrics_path = ROOT / "metrics_all.csv"
    write_csv(metrics_path, rows)
    model_rows = {name: means(rows, name) for name in ("M1", "M2", "M3")}
    comparisons = []
    definitions = (("H1_M2_minus_M1", "M2", "M1"), ("H2_M3_minus_M2", "M3", "M2"))
    index = 0
    for name, left, right in definitions:
        for horizon, state in sorted({(key[1], key[2]) for key in model_rows[left]}):
            delta = [value - model_rows[right][key] for key, value in model_rows[left].items() if key[1:] == (horizon, state) and key in model_rows[right]]
            result = paired_percentile_bootstrap(np.asarray(delta, dtype=np.float64), 10000, 180000 + index)
            comparisons.append({"comparison": name, "left_model": left, "right_model": right, "source": "zenodo_kdd_cup_2018", "horizon": horizon, "state": state, "metric": "raw_rmse", **result})
            index += 1
    for row, adjusted in zip(comparisons, holm_adjust([float(row["p_two_sided"]) for row in comparisons])):
        row["p_holm"] = adjusted
    OUT.mkdir(parents=True, exist_ok=True)
    comparison_path = OUT / "kdd_original_path_confirmation.csv"
    write_csv(comparison_path, comparisons, ("comparison", "left_model", "right_model", "source", "horizon", "state", "metric", "n", "estimate", "ci_low", "ci_high", "p_two_sided", "p_holm"))
    manifest = {"study": "sapr_mamba_v8", "status": "verified", "created_at": utc_now(), "task_manifests": len(manifests), "metrics": {"path": str(metrics_path.relative_to(REPO_ROOT)), "sha256": sha256_path(metrics_path)}, "comparison": {"path": str(comparison_path.relative_to(REPO_ROOT)), "sha256": sha256_path(comparison_path)}, "test_targets_used_for_selection": False}
    atomic_write_json(OUT / "confirmation_manifest.json", manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    analyze()
