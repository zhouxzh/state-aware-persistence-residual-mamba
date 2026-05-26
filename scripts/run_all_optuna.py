#!/usr/bin/env python
"""
Batch Optuna HPO runner for all non-stationary benchmark datasets.

Runs baseline and mamba phases sequentially for each dataset.
Supports pause/resume — skipped if study already has enough trials.

Usage:
    python scripts/run_all_optuna.py                              # all datasets, baseline + mamba
    python scripts/run_all_optuna.py --datasets exchange,ili      # specific datasets
    python scripts/run_all_optuna.py --phase baseline             # baseline only
    python scripts/run_all_optuna.py --phase mamba                # mamba only
    python scripts/run_all_optuna.py --datasets etth1 --phase mamba --trials 30
    python scripts/run_all_optuna.py --dry-run                    # print plan only
    python scripts/run_all_optuna.py --gpu 1 --trials 24
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "configs" / "optuna_datasets.json"
OPTUNA_SCRIPT = REPO_ROOT / "scripts" / "optuna" / "run_dataset_optuna.py"

ALL_DATASETS = [
    "gld",
    "exchange",
    "etth1",
    "etth2",
    "ettm1",
    "ettm2",
    "electricity",
    "traffic",
    "weather",
    "ili",
]

CALIBRATION_HORIZONS = {
    "gld":         [7, 90, 360],
    "exchange":    [7, 90, 360],
    "etth1":       [48, 168, 720],
    "etth2":       [48, 168, 720],
    "ettm1":       [48, 192, 720],
    "ettm2":       [48, 192, 720],
    "electricity": [48, 168, 720],
    "traffic":     [48, 168, 720],
    "weather":     [96, 336, 720],
    "ili":         [24, 48, 60],
}

DEFAULT_TRIALS = {"baseline": 20, "mamba": 24}


def parse_args():
    parser = argparse.ArgumentParser(description="Batch Optuna HPO for all benchmark datasets")
    parser.add_argument(
        "--datasets",
        type=str,
        default=",".join(ALL_DATASETS),
        help=f"Comma-separated dataset slugs. Available: {ALL_DATASETS}",
    )
    parser.add_argument(
        "--phase",
        choices=["baseline", "mamba", "both"],
        default="both",
        help="Which phase(s) to run",
    )
    parser.add_argument("--trials", type=int, default=0, help="Trials per model per dataset (0 = use defaults)")
    parser.add_argument("--top-k-replays", type=int, default=5)
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--cpu", action="store_true")
    parser.add_argument("--train-epochs", type=int, default=10)
    parser.add_argument("--patience", type=int, default=3)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true", help="Print plan without executing")
    parser.add_argument("--no-save-final-artifacts", action="store_true")
    return parser.parse_args()


def resolve_phases(arg_phase):
    if arg_phase == "both":
        return ["baseline", "mamba"]
    return [arg_phase]


def run_optuna(dataset, phase, args):
    trials = args.trials if args.trials > 0 else DEFAULT_TRIALS[phase]
    calib = CALIBRATION_HORIZONS[dataset]

    cmd = [
        sys.executable,
        str(OPTUNA_SCRIPT),
        "--dataset", dataset,
        "--manifest", str(MANIFEST),
        "--phase", phase,
        "--trials", str(trials),
        "--top-k-replays", str(args.top_k_replays),
        "--calibration-horizons",
    ] + [str(h) for h in calib] + [
        "--gpu", str(args.gpu),
        "--train-epochs", str(args.train_epochs),
        "--patience", str(args.patience),
        "--num-workers", str(args.num_workers),
    ]

    if args.cpu:
        cmd.append("--cpu")
    if args.no_save_final_artifacts:
        cmd.append("--no-save-final-artifacts")

    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}]  START  {dataset:12s}  {phase:8s}  trials={trials}")
    t0 = time.time()

    result = subprocess.run(cmd, cwd=str(REPO_ROOT))

    elapsed = time.time() - t0
    status = "OK" if result.returncode == 0 else f"FAIL(rc={result.returncode})"
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}]  {status:6s}  {dataset:12s}  {phase:8s}  elapsed={elapsed/60:.1f}min")

    return result.returncode == 0


def main():
    args = parse_args()
    selected = [s.strip() for s in args.datasets.split(",") if s.strip()]
    invalid = [s for s in selected if s not in ALL_DATASETS]
    if invalid:
        print(f"Unknown datasets: {invalid}. Available: {ALL_DATASETS}")
        sys.exit(1)

    phases = resolve_phases(args.phase)

    # Print plan
    print("=" * 72)
    print(f"Datasets: {selected}")
    print(f"Phases:   {phases}")
    for ds in selected:
        calib = CALIBRATION_HORIZONS[ds]
        bt = args.trials if args.trials > 0 else DEFAULT_TRIALS["baseline"]
        mt = args.trials if args.trials > 0 else DEFAULT_TRIALS["mamba"]
        print(f"  {ds:12s}  calib={calib}  baseline_trials={bt}  mamba_trials={mt}")
    print(f"GPU:      {args.gpu}")
    if args.dry_run:
        print("(dry-run, no experiments will run)")
    print("=" * 72)

    if args.dry_run:
        return

    total = len(selected) * len(phases)
    success = 0
    fail = 0

    for idx, dataset in enumerate(selected, start=1):
        for phase in phases:
            print(f"\n{'─'*60}")
            print(f"[{idx}/{total}] {dataset} / {phase}")
            print(f"{'─'*60}")
            ok = run_optuna(dataset, phase, args)
            if ok:
                success += 1
            else:
                fail += 1
                print(f"  WARNING: {dataset}/{phase} failed. Continuing with next task.")

    print(f"\n{'='*72}")
    print(f"Done.  success={success}  failed={fail}  total={success+fail}")
    print(f"{'='*72}")


if __name__ == "__main__":
    main()
