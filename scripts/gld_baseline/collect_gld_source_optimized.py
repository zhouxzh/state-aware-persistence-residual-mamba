#!/usr/bin/env python
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results"
OUT_ALL = RESULTS_DIR / "gld_source_optimized_all.csv"
OUT_BEST = RESULTS_DIR / "gld_source_optimized_best.csv"

DATASET = "GLD"
TARGET = "close"
MODELS = [
    "Autoformer",
    "Transformer",
    "DLinear",
    "NLinear",
    "PatchTST",
    "TimesNet",
    "Nonstationary_Transformer",
]
HORIZONS = [1, 3, 5, 7, 14, 30, 60, 90, 120, 180, 270, 360]
SEQ_LENS = [16, 32, 64, 96, 128, 192, 256, 320, 384]

RUN_RE = re.compile(
    r"^GLD_OPT_(?P<model>.+?)_sl(?P<seq_len>\d+)_ll(?P<label_len>\d+)_pl(?P<horizon>\d+)_"
)


def term_for_horizon(horizon):
    if horizon <= 7:
        return "short"
    if horizon <= 120:
        return "middle"
    return "long"


def parse_result_dir(path):
    match = RUN_RE.match(path.name)
    if not match:
        return None
    return {
        "model": match.group("model"),
        "seq_len": int(match.group("seq_len")),
        "label_len": int(match.group("label_len")),
        "horizon": int(match.group("horizon")),
    }


def load_completed():
    completed = {}
    for metrics_path in RESULTS_DIR.glob("GLD_OPT_*/metrics.npy"):
        parsed = parse_result_dir(metrics_path.parent)
        if parsed is None:
            continue
        if parsed["model"] not in MODELS:
            continue
        metrics = np.load(metrics_path)
        mae, mse, rmse, mape, mspe = [float(x) for x in metrics[:5]]

        meta_path = metrics_path.parent / "meta.json"
        inverse = None
        if meta_path.exists():
            with meta_path.open() as f:
                inverse = bool(json.load(f).get("inverse", False))

        key = (parsed["model"], parsed["horizon"], parsed["seq_len"])
        completed[key] = {
            **parsed,
            "mse": mse,
            "mae": mae,
            "rmse": rmse,
            "mape": mape,
            "mspe": mspe,
            "inverse": inverse,
            "run": metrics_path.parent.name,
        }
    return completed


def base_row(model, horizon, seq_len):
    return {
        "dataset": DATASET,
        "target": TARGET,
        "model": model,
        "horizon": horizon,
        "term": term_for_horizon(horizon),
        "seq_len": seq_len,
        "label_len": seq_len // 2,
        "pred_len": horizon,
        "mse": "",
        "mae": "",
        "rmse": "",
        "mape": "",
        "mspe": "",
        "metric_scale": "price" ,
        "status": "pending",
        "run": "",
        "notes": "",
    }


def write_csv(path, rows):
    path.parent.mkdir(exist_ok=True)
    fieldnames = [
        "dataset",
        "target",
        "model",
        "horizon",
        "term",
        "seq_len",
        "label_len",
        "pred_len",
        "mse",
        "mae",
        "rmse",
        "mape",
        "mspe",
        "metric_scale",
        "status",
        "run",
        "notes",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    completed = load_completed()
    rows = []
    for model in MODELS:
        for horizon in HORIZONS:
            for seq_len in SEQ_LENS:
                row = base_row(model, horizon, seq_len)
                result = completed.get((model, horizon, seq_len))
                if result is not None:
                    if result["inverse"] is False:
                        row["status"] = "legacy_scaled"
                        row["metric_scale"] = "scaled"
                        row["notes"] = "inverse=False; not comparable to price-scale runs"
                    elif result["inverse"] is None:
                        row["status"] = "legacy_unknown"
                        row["metric_scale"] = "unknown"
                        row["notes"] = "missing meta.json"
                    else:
                        row.update(
                            {
                                "mse": result["mse"],
                                "mae": result["mae"],
                                "rmse": result["rmse"],
                                "mape": result["mape"],
                                "mspe": result["mspe"],
                                "status": "complete",
                                "run": result["run"],
                            }
                        )
                rows.append(row)

    best_rows = []
    grouped = defaultdict(list)
    for row in rows:
        if row["status"] == "complete":
            grouped[(row["model"], row["horizon"])].append(row)
    for key in sorted(grouped, key=lambda item: (MODELS.index(item[0]), item[1])):
        best_rows.append(min(grouped[key], key=lambda row: float(row["mse"])))

    write_csv(OUT_ALL, rows)
    write_csv(OUT_BEST, best_rows)

    complete = sum(row["status"] == "complete" for row in rows)
    print(f"wrote {OUT_ALL.relative_to(REPO_ROOT)}")
    print(f"wrote {OUT_BEST.relative_to(REPO_ROOT)}")
    print(f"complete rows: {complete}/{len(rows)}")
    print(f"best rows: {len(best_rows)}")


if __name__ == "__main__":
    main()
