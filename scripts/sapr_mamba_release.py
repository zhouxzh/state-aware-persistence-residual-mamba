#!/usr/bin/env python
"""Build or verify the compact, evidence-only SAPR-Mamba V2 release."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
STUDY_SLUG = "sapr_mamba_v2"
RELEASE_ROOT = REPO_ROOT / "reproducibility" / STUDY_SLUG
RESULT_ROOT = REPO_ROOT / "results" / STUDY_SLUG
ANALYSIS_ROOT = REPO_ROOT / "docs" / "analysis" / STUDY_SLUG
FIGURE_ROOT = REPO_ROOT / "docs" / "figures" / STUDY_SLUG
DATA_ROOT = REPO_ROOT / "data" / STUDY_SLUG


def require_v2_environment() -> None:
    if os.environ.get("SAPR_MAMBA_VERSION") != "v2":
        raise SystemExit("Set SAPR_MAMBA_VERSION=v2 explicitly before building or verifying a SAPR-Mamba release.")


def artifact_entry(path: Path) -> dict:
    from utils.sapr_mamba.io import sha256_path

    return {"path": str(path.relative_to(REPO_ROOT)), "bytes": path.stat().st_size, "sha256": sha256_path(path)}


def copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_gzip(source: Path, destination: Path) -> None:
    """Store a complete large CSV in the compact release below GitHub's file cap."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    with source.open("rb") as input_handle, temporary.open("wb") as output_handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=output_handle, mtime=0) as compressed:
            shutil.copyfileobj(input_handle, compressed)
    os.replace(temporary, destination)


def checksum_tree(root: Path) -> dict:
    from utils.sapr_mamba.io import sha256_path, utc_now

    output = root / "SHA256SUMS.json"
    files = [path for path in sorted(root.rglob("*")) if path.is_file() and path != output]
    return {
        "root": str(root.relative_to(REPO_ROOT)),
        "created_at": utc_now(),
        "file_count": len(files),
        "total_bytes": sum(path.stat().st_size for path in files),
        "files": [
            {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha256_path(path)}
            for path in files
        ],
    }


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def require_complete_evidence() -> dict:
    real_analysis = read_json(ANALYSIS_ROOT / "real_analysis_manifest.json")
    real_verification = read_json(ANALYSIS_ROOT / "real_verification_manifest.json")
    synthetic_analysis = read_json(ANALYSIS_ROOT / "synthetic_analysis_manifest.json")
    confirmation = read_json(ANALYSIS_ROOT / "confirmation_verification_manifest.json")
    blockers = []
    if not real_analysis["completion"]["complete"]:
        blockers.append("real_completion_matrix_incomplete")
    if real_verification["status"] != "verified":
        blockers.append("real_prediction_metric_recompute_failed")
    if synthetic_analysis["completion_incomplete"]:
        blockers.append("synthetic_completion_matrix_incomplete")
    if confirmation["status"] != "verified":
        blockers.append("independent_confirmation_verification_failed")
    if blockers:
        raise SystemExit(f"Refusing compact release: {', '.join(blockers)}")
    return {
        "real_analysis": real_analysis,
        "real_verification": real_verification,
        "synthetic_analysis": synthetic_analysis,
        "confirmation": confirmation,
    }


def copy_confirmation_evidence() -> list[Path]:
    compact = RELEASE_ROOT / "verification"
    files = [
        ANALYSIS_ROOT / "synthetic_recompute_matrix.csv",
        ANALYSIS_ROOT / "forward_replay_matrix.csv",
        ANALYSIS_ROOT / "confirmation_verification_manifest.json",
    ]
    missing = [str(path.relative_to(REPO_ROOT)) for path in files if not path.is_file()]
    if missing:
        raise SystemExit(f"Missing independent confirmation artifacts: {missing}")
    copied = []
    for source in files:
        destination = compact / source.name
        copy(source, destination)
        copied.append(destination)
    return copied


def copy_synthetic_evidence() -> list[Path]:
    compact = RELEASE_ROOT / "synthetic"
    files = [
        REPO_ROOT / "configs" / STUDY_SLUG / "protocol.lock.json",
        RELEASE_ROOT / "runtime_environment.json",
        RESULT_ROOT / "synthetic" / "campaign_manifest.json",
        RESULT_ROOT / "synthetic" / "failures.csv",
        DATA_ROOT / "synthetic" / "data_manifest.json",
        ANALYSIS_ROOT / "synthetic_metrics_aggregate.csv",
        ANALYSIS_ROOT / "synthetic_completion_matrix.csv",
        ANALYSIS_ROOT / "synthetic_primary_comparisons.csv",
        ANALYSIS_ROOT / "synthetic_secondary_comparisons.csv",
        ANALYSIS_ROOT / "synthetic_gate_audit.csv",
        ANALYSIS_ROOT / "synthetic_analysis_manifest.json",
        FIGURE_ROOT / "synthetic_primary_deltas.png",
        FIGURE_ROOT / "synthetic_primary_deltas.pdf",
    ]
    source_metrics = RESULT_ROOT / "synthetic" / "metrics_all.csv"
    missing = [str(path.relative_to(REPO_ROOT)) for path in [*files, source_metrics] if not path.is_file()]
    if missing:
        raise SystemExit(f"Missing synthetic release artifacts: {missing}")
    copied = []
    for source in files:
        destination = compact / source.name
        copy(source, destination)
        copied.append(destination)
    compressed_metrics = compact / "metrics_all.csv.gz"
    stale_metrics = compact / "metrics_all.csv"
    if stale_metrics.exists():
        stale_metrics.unlink()
    copy_gzip(source_metrics, compressed_metrics)
    copied.append(compressed_metrics)
    return copied


def copy_real_evidence() -> tuple[list[Path], Path]:
    compact = RELEASE_ROOT / "real"
    source_files = [
        REPO_ROOT / "configs" / STUDY_SLUG / "protocol.lock.json",
        RELEASE_ROOT / "runtime_environment.json",
        RESULT_ROOT / "real" / "metrics_all.csv",
        RESULT_ROOT / "real" / "campaign_manifest.json",
        RESULT_ROOT / "real" / "failures.csv",
        DATA_ROOT / "real" / "data_manifest.json",
        DATA_ROOT / "real" / "processed" / "prepared_manifest.json",
    ]
    analysis_files = [
        "real_completion_matrix.csv",
        "real_series_seed_averages.csv",
        "real_panel_metrics_aggregate.csv",
        "real_source_metrics_aggregate.csv",
        "real_primary_comparisons.csv",
        "real_stable_state_coverage.csv",
        "real_statistical_audit.csv",
        "real_gate_audit.csv",
        "real_gate_summary.csv",
        "real_recompute_matrix.csv",
        "real_analysis_manifest.json",
        "real_verification_manifest.json",
    ]
    figure_files = ["real_primary_deltas.png", "real_primary_deltas.pdf", "real_figure_manifest.json"]
    missing = [str(path.relative_to(REPO_ROOT)) for path in source_files if not path.is_file()]
    missing.extend(str((ANALYSIS_ROOT / name).relative_to(REPO_ROOT)) for name in analysis_files if not (ANALYSIS_ROOT / name).is_file())
    missing.extend(str((FIGURE_ROOT / name).relative_to(REPO_ROOT)) for name in figure_files if not (FIGURE_ROOT / name).is_file())
    if missing:
        raise SystemExit(f"Missing real release artifacts: {missing}")
    copied = []
    for source in source_files:
        destination = compact / source.name
        copy(source, destination)
        copied.append(destination)
    for name in analysis_files:
        source = ANALYSIS_ROOT / name
        destination = compact / "analysis" / name
        copy(source, destination)
        copied.append(destination)
    for name in figure_files:
        source = FIGURE_ROOT / name
        destination = compact / "figures" / name
        copy(source, destination)
        copied.append(destination)
    candidate_counts = Counter()
    for source in sorted((RESULT_ROOT / "real").glob("*/*_seed*/selected_candidates.csv")):
        for row in read_rows(source):
            candidate_counts[(source.parents[1].name, source.parent.name.split("_seed")[0], row["candidate"])] += 1
        destination = compact / "selections" / source.relative_to(RESULT_ROOT / "real")
        copy(source, destination)
        copied.append(destination)
    candidate_path = compact / "candidate_counts.csv"
    with candidate_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("panel", "model", "candidate", "rows"))
        writer.writerows((*key, value) for key, value in sorted(candidate_counts.items()))
    copied.append(candidate_path)
    return copied, candidate_path


def build_release() -> dict:
    require_v2_environment()
    from utils.sapr_mamba.io import atomic_write_json, sha256_path, utc_now

    evidence = require_complete_evidence()
    claim_path = RELEASE_ROOT / "claim_evidence_map.csv"
    if not claim_path.is_file():
        raise SystemExit("claim_evidence_map.csv is required before release")
    synthetic_files = copy_synthetic_evidence()
    real_files, candidate_path = copy_real_evidence()
    confirmation_files = copy_confirmation_evidence()
    manifest = {
        "study": STUDY_SLUG,
        "created_at": utc_now(),
        "release_contract": "compact evidence only; raw data, predictions, checkpoints, and feature caches remain ignored local artifacts",
        "synthetic": {"copied_files": len(synthetic_files), "analysis": evidence["synthetic_analysis"]},
        "real": {
            "copied_files": len(real_files),
            "analysis": evidence["real_analysis"],
            "verification": evidence["real_verification"],
            "candidate_counts": artifact_entry(candidate_path),
        },
        "independent_confirmation": {"copied_files": len(confirmation_files), "summary": evidence["confirmation"]},
        "claim_evidence_map": artifact_entry(claim_path),
        "source_metrics": {
            "synthetic": artifact_entry(RESULT_ROOT / "synthetic" / "metrics_all.csv"),
            "real": artifact_entry(RESULT_ROOT / "real" / "metrics_all.csv"),
        },
    }
    atomic_write_json(RELEASE_ROOT / "release_manifest.json", manifest)
    checksum = checksum_tree(RELEASE_ROOT)
    atomic_write_json(RELEASE_ROOT / "SHA256SUMS.json", checksum)
    result = {"release_manifest": artifact_entry(RELEASE_ROOT / "release_manifest.json"), "checksums": checksum}
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def checksum_problems(root: Path) -> list[str]:
    from utils.sapr_mamba.io import sha256_path

    manifest_path = root / "SHA256SUMS.json"
    if not manifest_path.is_file():
        return ["missing_checksum_manifest"]
    payload = read_json(manifest_path)
    recorded = {item["path"]: item for item in payload.get("files", [])}
    actual = {
        str(path.relative_to(root)): path
        for path in root.rglob("*")
        if path.is_file() and path != manifest_path
    }
    problems = []
    for relative, entry in recorded.items():
        path = root / relative
        if not path.is_file():
            problems.append(f"missing:{relative}")
        elif path.stat().st_size != int(entry["bytes"]):
            problems.append(f"size_mismatch:{relative}")
        elif sha256_path(path) != entry["sha256"]:
            problems.append(f"checksum_mismatch:{relative}")
    for relative in sorted(set(actual) - set(recorded)):
        problems.append(f"untracked_release_file:{relative}")
    return problems


def verify_release() -> dict:
    require_v2_environment()
    problems = checksum_problems(RELEASE_ROOT)
    result = {"study": STUDY_SLUG, "status": "verified" if not problems else "failed", "problems": problems}
    print(json.dumps(result, indent=2, sort_keys=True))
    if problems:
        raise SystemExit("Release checksum verification failed")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("build", "verify"), default="build")
    args = parser.parse_args()
    (build_release if args.stage == "build" else verify_release)()


if __name__ == "__main__":
    main()
