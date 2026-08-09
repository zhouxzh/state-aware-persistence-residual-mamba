#!/usr/bin/env python
"""Run the held-out gate for the efficient PMS-Mamba V5 R6 candidate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.financial.run_pms_v3 import (
    execute_matrix,
    stage_manifest,
    strongest_non_pms,
)


PROTOCOL_PATH = REPO_ROOT / "configs" / "pms_mamba_v3.json"
BASE_MANIFEST = REPO_ROOT / "data" / "financial" / "manifests" / "training_datasets.json"
GATE_ROOT = REPO_ROOT / "results" / "nonstationary_analysis_v5" / "gate"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unlock-gate", action="store_true")
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--seeds", nargs="+", type=int, default=[2023, 2024, 2025, 2026, 2027])
    return parser.parse_args()


def r6_candidate(protocol: dict) -> dict:
    recipe = protocol["v5_candidates"]["PMSV5_R6"]
    return {
        "config_id": "PMSV5_R6",
        "parent_config": "PMSV4_R5",
        "model": "PMS_Mamba-PD",
        "parameter_overrides": dict(recipe["parameter_overrides"]),
    }


def summarize_gate(protocol: dict, candidate_id: str, strongest: str) -> dict:
    frame = pd.read_csv(GATE_ROOT / "results.csv")
    complete = frame[frame.status == "complete"].copy()
    expected = len(protocol["tasks"]) * len(protocol["promotion"]["seeds"]) * len(protocol["selection_horizons"]) * 3
    if len(complete) != expected:
        raise RuntimeError(f"Gate incomplete: expected {expected} rows, found {len(complete)}")
    term_map = {
        horizon: term
        for term, horizons in protocol["term_groups"].items()
        for horizon in horizons
    }
    complete["term"] = complete.horizon.map(term_map)
    per_task_seed = (
        complete.groupby(["config_id", "task", "seed", "term"], as_index=False)
        .rmsse.mean()
        .pivot(index=["config_id", "task", "seed"], columns="term", values="rmsse")
        .reset_index()
    )
    for term in ("short", "middle", "long"):
        if term not in per_task_seed:
            per_task_seed[term] = float("nan")
    per_task_seed["balanced_rmsse"] = per_task_seed[["short", "middle", "long"]].mean(axis=1)
    per_task_seed.to_csv(GATE_ROOT / "run_summary.csv", index=False)
    aggregate = per_task_seed.groupby("config_id").mean(numeric_only=True)
    references = ["PMSV3_B0", f"RETUNED_{strongest}"]
    task_means = per_task_seed.groupby(["config_id", "task"]).balanced_rmsse.mean()
    improvements = {
        ref: float((aggregate.loc[ref, "balanced_rmsse"] - aggregate.loc[candidate_id, "balanced_rmsse"]) / aggregate.loc[ref, "balanced_rmsse"])
        for ref in references
    }
    improved_tasks = {
        ref: int(sum(task_means.loc[(candidate_id, task)] < task_means.loc[(ref, task)] for task in protocol["tasks"]))
        for ref in references
    }
    term_degradation = {
        ref: {
            term: float((aggregate.loc[candidate_id, term] - aggregate.loc[ref, term]) / aggregate.loc[ref, term])
            for term in ("short", "middle", "long")
        }
        for ref in references
    }
    accuracy_pass = (
        all(value >= protocol["promotion"]["minimum_balanced_rmsse_improvement_fraction"] for value in improvements.values())
        and all(value >= protocol["promotion"]["minimum_improved_tasks"] for value in improved_tasks.values())
        and all(value <= protocol["promotion"]["maximum_term_degradation_fraction"] for item in term_degradation.values() for value in item.values())
    )
    payload = {
        "candidate_id": candidate_id,
        "reference_ids": references,
        "mean_balanced_rmsse": {key: float(value) for key, value in aggregate.balanced_rmsse.items()},
        "improvement_fraction": improvements,
        "improved_tasks": improved_tasks,
        "term_degradation_fraction": term_degradation,
        "accuracy_pass": bool(accuracy_pass),
        "complete_rows": int(len(complete)),
        "merge_gate_targets_read": True,
        "financial_2023_2026_targets_read": False,
    }
    (GATE_ROOT / "promotion_decision.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def main() -> None:
    args = parse_args()
    if not args.unlock_gate:
        raise RuntimeError("V5 gate requires --unlock-gate")
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    tasks = list(protocol["tasks"])
    strongest = strongest_non_pms(protocol, tasks)
    candidate = r6_candidate(protocol)
    configs = [
        candidate,
        {"config_id": "PMSV3_B0", "parent_config": "", **protocol["screen"]["configs"]["PMSV3_B0"]},
        {"config_id": f"RETUNED_{strongest}", "model": strongest, "parent_config": ""},
    ]
    cli = argparse.Namespace(gpu=args.gpu, num_workers=args.num_workers, max_runs=0, dry_run=False)
    manifest = stage_manifest(protocol, PROTOCOL_PATH, BASE_MANIFEST, "merge_gate")
    execute_matrix(
        cli, protocol, tasks, manifest, configs, args.seeds, GATE_ROOT, "val", fixed_train_epochs=True
    )
    print(json.dumps(summarize_gate(protocol, candidate["config_id"], strongest), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
