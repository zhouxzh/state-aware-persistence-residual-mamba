#!/usr/bin/env python
"""Freeze the validation-only PMS-Mamba V2 selection decision."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIRMATION = REPO_ROOT / "results" / "nonstationary_analysis_v2" / "confirmation_merged"
DEFAULT_OUTPUT = REPO_ROOT / "reproducibility" / "nonstationary_analysis_v2" / "selection"
PROTOCOL_PATH = REPO_ROOT / "configs" / "financial_benchmark.json"
DATA_MANIFEST_PATH = REPO_ROOT / "data" / "financial" / "manifests" / "training_datasets.json"
BASELINE_CONFIG = "PMSV2_F04"
CANDIDATE_CONFIGS = ("PMSV2_F01", "PMSV2_F03")
MIN_OVERALL_IMPROVEMENT_PCT = 2.0
MAX_TERM_DEGRADATION_PCT = 5.0

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_pms_v2_screen import TASKS, build_design, load_pms_params  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirmation-root", type=Path, default=DEFAULT_CONFIRMATION)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluate_rule(summary: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    indexed = summary.set_index("config_id")
    required = {BASELINE_CONFIG, *CANDIDATE_CONFIGS}
    missing = sorted(required - set(indexed.index))
    if missing:
        raise ValueError(f"Confirmation summary is missing configs: {missing}")
    baseline = indexed.loc[BASELINE_CONFIG]
    rows = []
    qualified = []
    for config_id in CANDIDATE_CONFIGS:
        candidate = indexed.loc[config_id]
        improvement = 100.0 * (
            baseline["mean_balanced_rmsse"] - candidate["mean_balanced_rmsse"]
        ) / baseline["mean_balanced_rmsse"]
        changes = {
            term: 100.0 * (
                candidate[f"mean_{term}_rmsse"] - baseline[f"mean_{term}_rmsse"]
            ) / baseline[f"mean_{term}_rmsse"]
            for term in ("short", "middle", "long")
        }
        meets_overall = improvement >= MIN_OVERALL_IMPROVEMENT_PCT
        meets_terms = max(changes.values()) <= MAX_TERM_DEGRADATION_PCT
        meets_rule = meets_overall and meets_terms
        if meets_rule:
            qualified.append(config_id)
        rows.append({
            "config_id": config_id,
            "baseline_config_id": BASELINE_CONFIG,
            "mean_balanced_rmsse": candidate["mean_balanced_rmsse"],
            "baseline_mean_balanced_rmsse": baseline["mean_balanced_rmsse"],
            "overall_improvement_pct": improvement,
            "short_change_pct": changes["short"],
            "middle_change_pct": changes["middle"],
            "long_change_pct": changes["long"],
            "meets_overall_threshold": meets_overall,
            "meets_term_guardrail": meets_terms,
            "meets_practical_success_rule": meets_rule,
        })
    if qualified:
        selected = min(qualified, key=lambda config_id: indexed.loc[config_id, "mean_balanced_rmsse"])
    else:
        selected = BASELINE_CONFIG
    return pd.DataFrame(rows), selected


def main() -> None:
    args = parse_args()
    confirmation_root = args.confirmation_root.resolve()
    output_root = args.output_root.resolve()
    summary_path = confirmation_root / "screen_config_summary.csv"
    results_path = confirmation_root / "screen_results.csv"
    source_manifest_path = confirmation_root / "validation_manifest.json"
    summary = pd.read_csv(summary_path)
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    if source_manifest.get("test_targets_read") is not False:
        raise ValueError("Confirmation manifest does not certify test_targets_read=false")
    if int(source_manifest.get("complete_rows", -1)) != 720:
        raise ValueError("Confirmation matrix must contain exactly 720 complete rows")
    comparison, selected_config = evaluate_rule(summary)

    design = {row["config_id"]: row for row in build_design()}
    selected_factors = {
        key: design[selected_config][key]
        for key in ("residual_target", "loss", "ms_fusion", "horizon_weighting")
    }
    selected_params = {}
    for task in TASKS:
        params = load_pms_params(task)
        params.update(selected_factors)
        selected_params[task] = params

    output_root.mkdir(parents=True, exist_ok=True)
    comparison_path = output_root / "candidate_comparison.csv"
    comparison.to_csv(comparison_path, index=False, quoting=csv.QUOTE_MINIMAL)
    params_path = output_root / "selected_task_params.json"
    params_path.write_text(
        json.dumps(selected_params, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    frozen_summary_path = output_root / "confirmation_config_summary.csv"
    shutil.copy2(summary_path, frozen_summary_path)

    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    manifest = {
        "stage": "v2_validation_selection_frozen",
        "selection_status": (
            "candidate_selected" if selected_config != BASELINE_CONFIG else "baseline_retained"
        ),
        "selected_config_id": selected_config,
        "selected_factors": selected_factors,
        "baseline_config_id": BASELINE_CONFIG,
        "screen_finalists": list(CANDIDATE_CONFIGS),
        "practical_success_rule": {
            "minimum_overall_improvement_pct": MIN_OVERALL_IMPROVEMENT_PCT,
            "maximum_term_degradation_pct": MAX_TERM_DEGRADATION_PCT,
        },
        "selection_eval_flag": "val",
        "objective_metric": "mean_balanced_rmsse",
        "tasks": list(TASKS),
        "seeds": [2023, 2024, 2025, 2026, 2027],
        "horizons": [1, 5, 20, 60, 120, 252],
        "complete_validation_rows": 720,
        "test_targets_read": False,
        "locked_test_action": (
            "evaluate_new_candidate" if selected_config != BASELINE_CONFIG
            else "not_opened_no_candidate_met_rule"
        ),
        "protocol_version": protocol["protocol_version"],
        "protocol_sha256": sha256_path(PROTOCOL_PATH),
        "data_manifest_sha256": sha256_path(DATA_MANIFEST_PATH),
        "source_validation_manifest_sha256": sha256_path(source_manifest_path),
        "source_validation_results_sha256": sha256_path(results_path),
        "candidate_comparison_sha256": sha256_path(comparison_path),
        "confirmation_config_summary_sha256": sha256_path(frozen_summary_path),
        "selected_task_params_sha256": sha256_path(params_path),
    }
    manifest_path = output_root / "selection_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    checksum_paths = [comparison_path, frozen_summary_path, params_path, manifest_path]
    checksums = "".join(
        f"{sha256_path(path)}  {path.name}\n" for path in sorted(checksum_paths, key=lambda item: item.name)
    )
    (output_root / "SHA256SUMS").write_text(checksums, encoding="utf-8")
    print(
        f"Selection frozen: status={manifest['selection_status']} "
        f"selected={selected_config} test_targets_read=false"
    )


if __name__ == "__main__":
    main()
