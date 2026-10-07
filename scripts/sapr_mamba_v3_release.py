#!/usr/bin/env python
"""Create a checksum-covered V3 compact release and automated manuscript bundle."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("SAPR_MAMBA_VERSION", "v3")

from utils.sapr_mamba.io import atomic_write_json, sha256_path, utc_now


STUDY = "sapr_mamba_v3"
ROOT = REPO_ROOT / "reproducibility" / STUDY
RESULTS = REPO_ROOT / "results" / STUDY
ANALYSIS = REPO_ROOT / "docs" / "analysis" / STUDY
MANUSCRIPT = REPO_ROOT / "manuscript" / STUDY


def require_v3() -> None:
    if os.environ.get("SAPR_MAMBA_VERSION") != "v3":
        raise SystemExit("Set SAPR_MAMBA_VERSION=v3 explicitly")


def entry(path: Path) -> dict:
    return {"path": str(path.relative_to(REPO_ROOT)), "bytes": path.stat().st_size, "sha256": sha256_path(path)}


def copy_if_exists(source: Path, destination: Path, copied: list[Path]) -> None:
    if source.is_file():
        if source.resolve() == destination.resolve():
            copied.append(destination)
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied.append(destination)


def copy_evidence_tree(root: Path, destination_root: Path, copied: list[Path]) -> None:
    """Copy compact evidence files while excluding large binary predictions."""
    if not root.is_dir():
        return
    allowed_names = {
        "task_manifest.json", "failures.csv",
        "campaign_manifest.json", "real_analysis_manifest.json", "real_verification_manifest.json",
        "real_completion_matrix.csv", "real_recompute_matrix.csv", "real_stable_state_coverage.csv",
        "external_holdout_primary_comparisons.csv",
        "real_statistical_audit.csv", "real_gate_audit.csv", "real_gate_summary.csv",
    }
    for source in sorted(root.rglob("*")):
        if not source.is_file() or source.name not in allowed_names:
            continue
        destination = destination_root / source.relative_to(root)
        copy_if_exists(source, destination, copied)


def checksum(root: Path) -> dict:
    manifest = root / "SHA256SUMS.json"
    files = [path for path in sorted(root.rglob("*")) if path.is_file() and path != manifest]
    return {
        "root": str(root.relative_to(REPO_ROOT)),
        "created_at": utc_now(),
        "file_count": len(files),
        "total_bytes": sum(path.stat().st_size for path in files),
        "files": [{"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha256_path(path)} for path in files],
    }


def build() -> dict:
    require_v3()
    ROOT.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for source in (
        REPO_ROOT / "configs" / STUDY / "protocol.lock.json",
        REPO_ROOT / "configs" / STUDY / "candidate_sources.json",
        REPO_ROOT / "configs" / STUDY / "amendments" / "v3.1_public_multiseries_sources.json",
        REPO_ROOT / "configs" / STUDY / "amendments" / "v3.1_protocol.lock.json",
        REPO_ROOT / "reproducibility" / STUDY / "runtime_environment.json",
        REPO_ROOT / "data" / STUDY / "source_pool_audit.json",
        REPO_ROOT / "data" / STUDY / "real" / "source_extensions" / "v3.1" / "prepared_manifest.json",
        REPO_ROOT / "data" / STUDY / "real" / "source_thresholds_v3.1.json",
        REPO_ROOT / "data" / STUDY / "real" / "source_extensions" / "v3.1" / "integration_manifest.json",
        REPO_ROOT / "data" / STUDY / "real" / "source_extensions" / "v3.1" / "state_thresholds.json",
        REPO_ROOT / "configs" / STUDY / "amendments" / "v3.1_public_multiseries_sources.json",
        REPO_ROOT / "results" / STUDY / "pipeline_state.json",
        REPO_ROOT / "results" / STUDY / "autocontinue_state.json",
        REPO_ROOT / "docs" / "current" / "sapr_mamba_v3_execution_status.md",
    ):
        copy_if_exists(source, ROOT / source.name, copied)
    for source in sorted(ANALYSIS.glob("*")):
        copy_if_exists(source, ROOT / "analysis" / source.name, copied)
    for source in sorted(MANUSCRIPT.glob("*")):
        copy_if_exists(source, ROOT / "manuscript" / source.name, copied)
    copy_evidence_tree(RESULTS / "synthetic", ROOT / "results" / "synthetic", copied)
    copy_evidence_tree(RESULTS / "real", ROOT / "results" / "real", copied)
    for source in sorted((REPO_ROOT / "docs" / "figures" / STUDY).glob("*")):
        copy_if_exists(source, ROOT / "figures" / source.name, copied)
    release = {
        "study": STUDY,
        "created_at": utc_now(),
        "status": "complete_with_limitations",
        "copied_files": len(copied),
        "limitations_source": str((RESULTS / "pipeline_state.json").relative_to(REPO_ROOT)),
        "contract": "automated evidence bundle; human authors remain responsible for declarations and submission approval",
        "excluded_runtime_outputs": {
            "policy": "large checkpoints, prediction archives, per-task metrics, and merged raw metric tables remain in ignored results/ and are not copied into the Git release",
            "source_root": str(RESULTS.relative_to(REPO_ROOT)),
        },
    }
    atomic_write_json(ROOT / "release_manifest.json", release)
    atomic_write_json(ROOT / "SHA256SUMS.json", checksum(ROOT))
    print(json.dumps(release, indent=2, sort_keys=True))
    return release


def verify() -> dict:
    require_v3()
    manifest = ROOT / "SHA256SUMS.json"
    if not manifest.is_file():
        raise SystemExit("V3 SHA256SUMS.json is missing")
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    problems = []
    for item in payload["files"]:
        path = ROOT / item["path"]
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha256_path(path) != item["sha256"]:
            problems.append(item["path"])
    result = {"status": "verified" if not problems else "complete_with_limitations", "problems": problems}
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("build", "verify"), required=True)
    args = parser.parse_args()
    (build if args.stage == "build" else verify)()


if __name__ == "__main__":
    main()
