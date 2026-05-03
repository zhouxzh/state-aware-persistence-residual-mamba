#!/usr/bin/env python
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from utils.metrics import RMSSE


RESULTS_DIR = REPO_ROOT / "results"
MANUSCRIPT_DATA_DIR = REPO_ROOT / "manuscript" / "data"
GLD_PATH = REPO_ROOT / "data" / "GLD" / "GLD.csv"
TARGET = "close"
TRAIN_RATIO = 0.7

CSV_OUTPUTS = [
    "gld_baselines.csv",
    "gld_source_optimized_all.csv",
    "gld_source_optimized_best.csv",
    "gld_rmse_optimized_all.csv",
    "gld_rmse_optimized_best.csv",
    "gld_ns_mamba_ablation.csv",
    "gld_mamba_hpo_all.csv",
    "gld_mamba_hpo_best.csv",
]

COLLECTOR_SCRIPTS = [
    "scripts/gld_baseline/collect_gld_baselines.py",
    "scripts/gld_baseline/collect_gld_source_optimized.py",
    "scripts/gld_baseline/collect_gld_rmse_optimized.py",
    "scripts/gld_ns_mamba/collect_ns_mamba_results.py",
    "scripts/gld_ns_mamba/collect_gld_mamba_hpo.py",
]


def load_gld_train_insample():
    df = pd.read_csv(GLD_PATH)
    train_end = int(len(df) * TRAIN_RATIO)
    return df[[TARGET]].values[:train_end]


def backfill_result_dir(result_dir, insample):
    meta_path = result_dir / "meta.json"
    pred_path = result_dir / "pred.npy"
    true_path = result_dir / "true.npy"
    metrics_path = result_dir / "metrics.npy"

    if not (meta_path.exists() and pred_path.exists() and true_path.exists() and metrics_path.exists()):
        return "skipped_missing"

    with meta_path.open() as f:
        meta = json.load(f)

    if meta.get("features") != "S" or meta.get("target") != TARGET:
        return "skipped_non_target"
    if not bool(meta.get("inverse", False)):
        return "skipped_scaled"

    pred = np.load(pred_path)
    true = np.load(true_path)
    metrics = np.load(metrics_path)
    rmsse = float(RMSSE(pred, true, insample))

    if metrics.shape[0] >= 6:
        metrics[5] = rmsse
    else:
        metrics = np.concatenate([metrics[:5], np.array([rmsse], dtype=metrics.dtype)])
    np.save(metrics_path, metrics)

    meta["metric_names"] = ["mae", "mse", "rmse", "mape", "mspe", "rmsse"]
    meta["rmsse_seasonality"] = 1
    with meta_path.open("w") as f:
        json.dump(meta, f, indent=2)

    return "updated"


def run_collectors():
    for script in COLLECTOR_SCRIPTS:
        subprocess.run([sys.executable, script], check=True, cwd=REPO_ROOT)


def copy_csvs_to_manuscript():
    MANUSCRIPT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name in CSV_OUTPUTS:
        shutil.copy2(RESULTS_DIR / name, MANUSCRIPT_DATA_DIR / name)


def main():
    insample = load_gld_train_insample()
    counts = {}
    for result_dir in sorted(RESULTS_DIR.glob("GLD*/")):
        status = backfill_result_dir(result_dir, insample)
        counts[status] = counts.get(status, 0) + 1

    run_collectors()
    copy_csvs_to_manuscript()

    for key in sorted(counts):
        print(f"{key}: {counts[key]}")
    print(f"copied {len(CSV_OUTPUTS)} CSV files to {MANUSCRIPT_DATA_DIR.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
