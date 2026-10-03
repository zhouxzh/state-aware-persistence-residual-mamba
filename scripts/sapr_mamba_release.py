#!/usr/bin/env python
"""Build compact SAPR-Mamba v1 evidence from completed v1.7 artifacts."""

from __future__ import annotations

import csv
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from utils.sapr_mamba.io import REPO_ROOT, STUDY_SLUG, atomic_write_json, sha256_path, utc_now


RESULT_ROOT = REPO_ROOT / "results" / STUDY_SLUG
RELEASE_ROOT = REPO_ROOT / "reproducibility" / STUDY_SLUG
REAL_ROOT = RESULT_ROOT / "real"
COMPACT_REAL = RELEASE_ROOT / "real"


def copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def checksum_tree(root: Path) -> dict:
    files = [path for path in sorted(root.rglob("*")) if path.is_file() and path.name != "SHA256SUMS.json"]
    return {
        "root": str(root),
        "created_at": utc_now(),
        "file_count": len(files),
        "total_bytes": sum(path.stat().st_size for path in files),
        "files": [
            {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha256_path(path)}
            for path in files
        ],
    }


def main() -> None:
    if not (REAL_ROOT / "metrics_all.csv").is_file():
        raise SystemExit("real metrics_all.csv is missing")
    summary = json.loads((REAL_ROOT / "campaign_manifest.json").read_text(encoding="utf-8"))
    task_manifests = sorted(REAL_ROOT.glob("*/*_seed*/task_manifest.json"))
    statuses = Counter(json.loads(path.read_text(encoding="utf-8")).get("status") for path in task_manifests)
    expected = {
        "sources": ["electricity", "beijing_air_quality", "ett_ETTh1", "ett_ETTh2", "ett_ETTm1", "ett_ETTm2"],
        "learned_random_models": ["M1", "M2", "M3", "M3-shuffle", "DLinear"],
        "deterministic_models": ["M0", "SeasonalNaive", "Drift", "ETS", "ARIMA"],
        "random_seeds": [20261011, 20261012, 20261013, 20261014, 20261015],
        "deterministic_seed": 20261011,
    }
    compact_files = [
        REPO_ROOT / "configs" / STUDY_SLUG / "protocol.lock.json",
        RELEASE_ROOT / "runtime_environment.json",
        REAL_ROOT / "metrics_all.csv",
        REAL_ROOT / "campaign_manifest.json",
        REAL_ROOT / "failures.csv",
        REPO_ROOT / "data" / STUDY_SLUG / "real" / "data_manifest.json",
        REPO_ROOT / "data" / STUDY_SLUG / "real" / "processed" / "prepared_manifest.json",
    ]
    for path in compact_files:
        if path.is_file():
            copy(path, COMPACT_REAL / path.name)
    for path in sorted(REAL_ROOT.glob("*/*_seed*/selected_candidates.csv")):
        copy(path, COMPACT_REAL / "selections" / path.relative_to(REAL_ROOT))
    candidate_counts = Counter()
    for path in sorted(REAL_ROOT.glob("*/*_seed*/selected_candidates.csv")):
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                candidate_counts[(path.parent.parent.name, path.parent.name.split("_seed")[0], row["candidate"])] += 1
    with (COMPACT_REAL / "candidate_counts.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("panel", "model", "candidate", "rows"))
        writer.writerows((panel, model, candidate, count) for (panel, model, candidate), count in sorted(candidate_counts.items()))
    manifest = {
        "created_at": utc_now(),
        "expected": expected,
        "observed_task_manifests": len(task_manifests),
        "observed_statuses": dict(statuses),
        "campaign_summary": summary,
        "metrics_sha256": sha256_path(REAL_ROOT / "metrics_all.csv"),
        "failures_csv_sha256": sha256_path(REAL_ROOT / "failures.csv"),
        "warnings_policy": "statsmodels warnings are retained in task logs; failed fits are represented in per-model failures.csv and persistence fallback rows",
    }
    atomic_write_json(COMPACT_REAL / "real_release_manifest.json", manifest)
    atomic_write_json(COMPACT_REAL / "SHA256SUMS.json", checksum_tree(COMPACT_REAL))
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
