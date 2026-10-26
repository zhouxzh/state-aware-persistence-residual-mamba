#!/usr/bin/env python
"""Analyze the post-V3 validation-shrinkage diagnostic without mixing V3 claims."""

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
os.environ.setdefault("SAPR_MAMBA_VERSION", "v3")

from utils.sapr_mamba.analysis import holm_adjust, paired_percentile_bootstrap, write_csv
from utils.sapr_mamba.io import atomic_write_json, sha256_path, utc_now


V3 = REPO_ROOT / "results" / "sapr_mamba_v3" / "real" / "metrics_all.csv"
V4 = REPO_ROOT / "results" / "sapr_mamba_v4" / "real" / "metrics_all.csv"
V4_ROOT = REPO_ROOT / "results" / "sapr_mamba_v4" / "real"
OUT = REPO_ROOT / "docs" / "analysis" / "sapr_mamba_v4"
PREPARED = REPO_ROOT / "data" / "sapr_mamba_v3" / "real" / "processed" / "prepared_manifest.json"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def source_map() -> dict[str, str]:
    payload = json.loads(PREPARED.read_text(encoding="utf-8"))
    return {str(row["panel_id"]): str(row.get("source_cluster") or ("ett" if str(row["panel_id"]).startswith("ett_") else row["panel_id"])) for row in payload["panels"]}


def seed_means(rows: list[dict[str, str]], model: str) -> dict[tuple[str, str, int, str], float]:
    grouped: dict[tuple[str, str, int, str], list[float]] = defaultdict(list)
    for row in rows:
        if row["model"] == model:
            grouped[(row["dataset"], row["series_id"], int(row["horizon"]), row["state"])].append(float(row["rmse"]))
    return {key: float(np.mean(value)) for key, value in grouped.items()}


def alpha_summary() -> list[dict]:
    rows = []
    for path in sorted(V4_ROOT.glob("*/M4-validation-shrinkage_seed*/validation_shrinkage.csv")):
        panel, seed = path.parents[1].name, int(path.parent.name.rsplit("seed", 1)[1])
        for row in read_rows(path):
            rows.append({"panel": panel, "seed": seed, "alpha": float(row["selected_alpha"])})
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        grouped[row["panel"]].append(row["alpha"])
    return [
        {"panel": panel, "series_seed_units": len(values), "alpha_mean": float(np.mean(values)), "alpha_zero_fraction": float(np.mean(np.asarray(values) == 0.0)), "alpha_one_fraction": float(np.mean(np.asarray(values) == 1.0))}
        for panel, values in sorted(grouped.items())
    ]


def analyze() -> dict:
    if not V3.is_file() or not V4.is_file():
        raise SystemExit("V3 and V4 combined metrics are required")
    source = source_map()
    m3 = seed_means(read_rows(V3), "M3")
    m4 = seed_means(read_rows(V4), "M4-validation-shrinkage")
    grouped: dict[tuple[str, int, str], list[float]] = defaultdict(list)
    missing: Counter[tuple[str, int, str]] = Counter()
    for key, value in m4.items():
        dataset, _series, horizon, state = key
        target = m3.get(key)
        group = (source[dataset], horizon, state)
        if target is None:
            missing[group] += 1
        else:
            grouped[group].append(value - target)
    rows = []
    for index, ((cluster, horizon, state), values) in enumerate(sorted(grouped.items())):
        result = paired_percentile_bootstrap(np.asarray(values, dtype=np.float64), 10000, 140000 + index)
        rows.append({
            "comparison": "M4_validation_shrinkage_minus_M3", "source": cluster, "horizon": horizon, "state": state,
            "metric": "raw_rmse", "post_v3_diagnostic": True, "missing_pair_units": missing[(cluster, horizon, state)], **result,
        })
    adjusted = holm_adjust([float(row["p_two_sided"]) for row in rows])
    for row, value in zip(rows, adjusted):
        row["p_holm"] = value
    OUT.mkdir(parents=True, exist_ok=True)
    comparison_path = OUT / "m4_vs_m3_post_v3_diagnostic.csv"
    write_csv(comparison_path, rows, ("comparison", "source", "horizon", "state", "metric", "post_v3_diagnostic", "missing_pair_units", "n", "estimate", "ci_low", "ci_high", "p_two_sided", "p_holm"))
    alpha_path = OUT / "m4_validation_alpha_summary.csv"
    write_csv(alpha_path, alpha_summary(), ("panel", "series_seed_units", "alpha_mean", "alpha_zero_fraction", "alpha_one_fraction"))
    manifest = {
        "study": "sapr_mamba_v4", "status": "complete", "interpretation": "post-V3 diagnostic; V3 claims remain unchanged",
        "created_at": utc_now(), "v3_metrics": {"path": str(V3.relative_to(REPO_ROOT)), "sha256": sha256_path(V3)},
        "v4_metrics": {"path": str(V4.relative_to(REPO_ROOT)), "sha256": sha256_path(V4)},
        "comparison_rows": len(rows), "alpha_summary": str(alpha_path.relative_to(REPO_ROOT)),
    }
    atomic_write_json(OUT / "analysis_manifest.json", manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


if __name__ == "__main__":
    analyze()
