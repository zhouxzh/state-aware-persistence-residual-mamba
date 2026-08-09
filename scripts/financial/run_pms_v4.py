#!/usr/bin/env python
"""Run the V4 regime-conditioned PMS-Mamba accuracy gate."""

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
    load_hpo_params,
    strongest_non_pms,
)


V3_PROTOCOL = REPO_ROOT / "configs" / "pms_mamba_v3.json"
MANIFEST = REPO_ROOT / "data" / "financial" / "manifests" / "training_datasets.json"
GATE_ROOT = REPO_ROOT / "results" / "nonstationary_analysis_v4" / "gate"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unlock-gate", action="store_true")
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--seeds", nargs="+", type=int, default=[2023, 2024, 2025, 2026, 2027])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.unlock_gate:
        raise RuntimeError("V4 gate requires --unlock-gate")
    protocol = json.loads(V3_PROTOCOL.read_text(encoding="utf-8"))
    tasks = list(protocol["tasks"])
    strongest = strongest_non_pms(protocol, tasks)
    candidate = {
        "config_id": "PMSV4_R2",
        "parent_config": "PMSV4_R1",
        "model": "PMS_Mamba-PD",
        "parameter_overrides": {
            "pms_branch_mode": "regime_linear",
            "d_model": 64,
            "d_ff": 128,
            "d_state": 8,
            "e_layers": 1,
            "ms_use_decomp": 0,
            "ms_fusion": "mean",
            "forecast_head": "persistence_change",
            "change_gate_regularization": 0.0,
            "pms_change_scale": 1.0,
            "pms_regime_channel_gate": 1,
        },
    }
    configs = [
        candidate,
        {
            "config_id": "PMSV3_B0",
            "parent_config": "",
            **protocol["screen"]["configs"]["PMSV3_B0"],
        },
        {"config_id": f"RETUNED_{strongest}", "model": strongest, "parent_config": ""},
    ]
    cli = argparse.Namespace(
        gpu=args.gpu,
        num_workers=args.num_workers,
        max_runs=0,
        dry_run=False,
    )
    execute_matrix(
        cli,
        protocol,
        tasks,
        MANIFEST,
        configs,
        args.seeds,
        GATE_ROOT,
        "val",
        fixed_train_epochs=True,
    )
    frame = pd.read_csv(GATE_ROOT / "results.csv")
    complete = frame[frame.status == "complete"].copy()
    complete["term"] = complete.horizon.map(
        {h: term for term, horizons in protocol["term_groups"].items() for h in horizons}
    )
    summary = (
        complete.groupby(["config_id", "task", "seed"], as_index=False)
        .agg(
            balanced_rmsse=("rmsse", "mean"),
            short=("rmsse", lambda x: float(x[complete.loc[x.index, "term"] == "short"].mean())),
            middle=("rmsse", lambda x: float(x[complete.loc[x.index, "term"] == "middle"].mean())),
            long=("rmsse", lambda x: float(x[complete.loc[x.index, "term"] == "long"].mean())),
        )
    )
    summary.to_csv(GATE_ROOT / "run_summary.csv", index=False)
    aggregate = summary.groupby("config_id").mean(numeric_only=True)
    candidate_id = "PMSV4_R2"
    references = ["PMSV3_B0", f"RETUNED_{strongest}"]
    task_means = summary.groupby(["config_id", "task"]).balanced_rmsse.mean()
    payload = {
        "candidate_id": candidate_id,
        "reference_ids": references,
        "mean_balanced_rmsse": {k: float(v) for k, v in aggregate.balanced_rmsse.items()},
        "improvement_fraction": {
            ref: float((aggregate.loc[ref, "balanced_rmsse"] - aggregate.loc[candidate_id, "balanced_rmsse"]) / aggregate.loc[ref, "balanced_rmsse"])
            for ref in references
        },
        "improved_tasks": {
            ref: int(sum(task_means.loc[(candidate_id, task)] < task_means.loc[(ref, task)] for task in tasks))
            for ref in references
        },
        "term_means": {
            config_id: {
                term: float(aggregate.loc[config_id, term])
                for term in ("short", "middle", "long")
            }
            for config_id in aggregate.index
        },
        "complete_rows": int(len(complete)),
        "merge_gate_targets_read": True,
        "financial_2023_2026_targets_read": False,
    }
    payload["accuracy_pass"] = bool(
        all(value >= 0.02 for value in payload["improvement_fraction"].values())
        and all(value >= 5 for value in payload["improved_tasks"].values())
    )
    (GATE_ROOT / "promotion_decision.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
