#!/usr/bin/env python
import csv
import json
import re
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results"
OUT_PATH = RESULTS_DIR / "gld_pms_mamba_ablation.csv"

DATASET = "GLD"
TARGET = "close"
MODEL = "PMS_Mamba"
SETTING_ID = "PMS"
VARIANTS = ["PMS_Mamba-P", "PMS_Mamba-PG", "PMS_Mamba-PD", "PMS_Mamba-PDG"]
HORIZONS = [1, 3, 5, 7, 14, 30, 60, 90, 120, 180, 270, 360]
DEFAULT_MOVING_AVG = 25
DEFAULT_SCALES = "1-2-4"
DEFAULT_PATCH_LEN = 16
DEFAULT_STRIDE = 8

RUN_PATTERN = re.compile(
    r"^GLD_PMS_"
    r"(?P<variant>PMS_Mamba-(?:PDG|PG|PD|P))_"
    r"pl(?P<horizon>\d+)_"
    r"s(?P<scales>[0-9-]+)_"
    r"f(?P<fusion>[A-Za-z]+)_"
    r"dc(?P<use_decomp>[01])_"
    r"ma(?P<moving_avg>\d+)_"
    r"p(?P<patch_len>\d+)_"
    r"st(?P<stride>\d+)_"
)


def term_for_horizon(horizon):
    if horizon <= 7:
        return "short"
    if horizon <= 120:
        return "middle"
    return "long"


def variant_config(variant):
    configs = {
        "PMS_Mamba-P": (0, "mean"),
        "PMS_Mamba-PG": (0, "gate"),
        "PMS_Mamba-PD": (1, "mean"),
        "PMS_Mamba-PDG": (1, "gate"),
    }
    return configs[variant]


def parse_result_dir(path):
    match = RUN_PATTERN.match(path.name)
    if match is None:
        return None

    return {
        "variant": match.group("variant"),
        "horizon": int(match.group("horizon")),
        "ms_scales": match.group("scales"),
        "ms_fusion": match.group("fusion"),
        "ms_use_decomp": int(match.group("use_decomp")),
        "moving_avg": int(match.group("moving_avg")),
        "patch_len": int(match.group("patch_len")),
        "stride": int(match.group("stride")),
    }


def load_metrics(metrics_path):
    metrics = np.load(metrics_path)
    mae, mse, rmse, mape, mspe = [float(x) for x in metrics[:5]]
    meta_path = metrics_path.parent / "meta.json"

    if not meta_path.exists():
        return {
            "status": "legacy_unknown",
            "notes": "missing meta.json; metric scale is unknown",
        }

    with meta_path.open() as f:
        meta = json.load(f)

    if not bool(meta.get("inverse", False)):
        return {
            "status": "legacy_scaled",
            "notes": "inverse=False; not mixed with price-scale results",
        }

    return {
        "mse": mse,
        "mae": mae,
        "rmse": rmse,
        "mape": mape,
        "mspe": mspe,
        "status": "complete",
        "notes": "",
    }


def discover_results():
    discovered = {}
    for metrics_path in RESULTS_DIR.glob("GLD_PMS_PMS_Mamba-*/metrics.npy"):
        parsed = parse_result_dir(metrics_path.parent)
        if parsed is None:
            continue

        key = (
            parsed["variant"],
            parsed["horizon"],
            parsed["ms_scales"],
            parsed["ms_fusion"],
            parsed["ms_use_decomp"],
            parsed["moving_avg"],
            parsed["patch_len"],
            parsed["stride"],
        )
        candidate = {
            **parsed,
            **load_metrics(metrics_path),
            "run": metrics_path.parent.name,
            "mtime": metrics_path.stat().st_mtime,
        }

        current = discovered.get(key)
        if current is None or candidate["mtime"] > current["mtime"]:
            discovered[key] = candidate

    return discovered


def empty_row(variant, horizon, scales, fusion, use_decomp, moving_avg, patch_len, stride):
    return {
        "dataset": DATASET,
        "target": TARGET,
        "variant": variant,
        "model": MODEL,
        "horizon": horizon,
        "term": term_for_horizon(horizon),
        "mse": "",
        "mae": "",
        "rmse": "",
        "mape": "",
        "mspe": "",
        "setting_id": SETTING_ID,
        "moving_avg": moving_avg,
        "ms_scales": scales,
        "ms_fusion": fusion,
        "ms_use_decomp": use_decomp,
        "patch_len": patch_len,
        "stride": stride,
        "status": "pending",
        "run": "",
        "notes": "",
    }


def main():
    discovered = discover_results()
    planned_keys = set()
    for variant in VARIANTS:
        use_decomp, fusion = variant_config(variant)
        for horizon in HORIZONS:
            planned_keys.add(
                (
                    variant,
                    horizon,
                    DEFAULT_SCALES,
                    fusion,
                    use_decomp,
                    DEFAULT_MOVING_AVG,
                    DEFAULT_PATCH_LEN,
                    DEFAULT_STRIDE,
                )
            )

    variant_order = {variant: index for index, variant in enumerate(VARIANTS)}
    keys = sorted(
        planned_keys | set(discovered.keys()),
        key=lambda item: (
            variant_order.get(item[0], len(VARIANTS)),
            item[1],
            item[2],
            item[3],
            item[4],
            item[5],
            item[6],
            item[7],
        ),
    )

    rows = []
    for variant, horizon, scales, fusion, use_decomp, moving_avg, patch_len, stride in keys:
        row = empty_row(
            variant,
            horizon,
            scales,
            fusion,
            use_decomp,
            moving_avg,
            patch_len,
            stride,
        )
        result = discovered.get(
            (variant, horizon, scales, fusion, use_decomp, moving_avg, patch_len, stride)
        )
        if result is not None:
            if result["status"] == "complete":
                row.update(
                    {
                        "mse": result["mse"],
                        "mae": result["mae"],
                        "rmse": result["rmse"],
                        "mape": result["mape"],
                        "mspe": result["mspe"],
                    }
                )
            row["status"] = result["status"]
            row["run"] = result["run"]
            row["notes"] = result["notes"]
        rows.append(row)

    OUT_PATH.parent.mkdir(exist_ok=True)
    fieldnames = [
        "dataset",
        "target",
        "variant",
        "model",
        "horizon",
        "term",
        "mse",
        "mae",
        "rmse",
        "mape",
        "mspe",
        "setting_id",
        "moving_avg",
        "ms_scales",
        "ms_fusion",
        "ms_use_decomp",
        "patch_len",
        "stride",
        "status",
        "run",
        "notes",
    ]
    with OUT_PATH.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    complete = sum(row["status"] == "complete" for row in rows)
    print(f"wrote {OUT_PATH.relative_to(REPO_ROOT)}")
    print(f"complete rows: {complete}/{len(rows)}")


if __name__ == "__main__":
    main()
