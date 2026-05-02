#!/usr/bin/env python
import csv
import json
import re
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results"
OUT_PATH = RESULTS_DIR / "gld_ms_mamba_ablation.csv"

DATASET = "GLD"
TARGET = "close"
MODEL = "MS_Mamba"
SETTING_ID = "MS"
VARIANTS = [
    "MS_Mamba-M",
    "MS_Mamba-MG",
    "MS_Mamba-MD",
    "MS_Mamba-MDG",
    "MS_Mamba-MDS",
    "MS_Mamba-MDGS",
]
HORIZONS = [1, 3, 5, 7, 14, 30, 60, 90, 120, 180, 270, 360]
DEFAULT_MOVING_AVG = 25
DEFAULT_SCALES = "1-2-4"

RUN_PATTERN = re.compile(
    r"^GLD_MS_"
    r"(?P<variant>MS_Mamba-(?:MDGS|MDS|MDG|MG|MD|M))_"
    r"pl(?P<horizon>\d+)_"
    r"s(?P<scales>[0-9-]+)_"
    r"f(?P<fusion>[A-Za-z]+)_"
    r"dc(?P<use_decomp>[01])_"
    r"(?:ls(?P<linear_skip>[01])_)?"
    r"ma(?P<moving_avg>\d+)_"
)


def term_for_horizon(horizon):
    if horizon <= 7:
        return "short"
    if horizon <= 120:
        return "middle"
    return "long"


def variant_config(variant):
    configs = {
        "MS_Mamba-M": (0, "mean"),
        "MS_Mamba-MG": (0, "gate"),
        "MS_Mamba-MD": (1, "mean"),
        "MS_Mamba-MDG": (1, "gate"),
        "MS_Mamba-MDS": (1, "mean"),
        "MS_Mamba-MDGS": (1, "gate"),
    }
    return configs[variant]


def variant_linear_skip(variant):
    return 1 if variant.endswith("S") else 0


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
        "ms_use_linear_skip": int(match.group("linear_skip") or 0),
        "moving_avg": int(match.group("moving_avg")),
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
    for metrics_path in RESULTS_DIR.glob("GLD_MS_MS_Mamba-*/metrics.npy"):
        parsed = parse_result_dir(metrics_path.parent)
        if parsed is None:
            continue

        key = (
            parsed["variant"],
            parsed["horizon"],
            parsed["ms_scales"],
            parsed["ms_fusion"],
            parsed["ms_use_decomp"],
            parsed["ms_use_linear_skip"],
            parsed["moving_avg"],
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


def empty_row(variant, horizon, scales, fusion, use_decomp, linear_skip, moving_avg):
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
        "ms_use_linear_skip": linear_skip,
        "status": "pending",
        "run": "",
        "notes": "",
    }


def main():
    discovered = discover_results()
    planned_keys = set()
    for variant in VARIANTS:
        use_decomp, fusion = variant_config(variant)
        linear_skip = variant_linear_skip(variant)
        for horizon in HORIZONS:
            planned_keys.add(
                (
                    variant,
                    horizon,
                    DEFAULT_SCALES,
                    fusion,
                    use_decomp,
                    linear_skip,
                    DEFAULT_MOVING_AVG,
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
        ),
    )

    rows = []
    for variant, horizon, scales, fusion, use_decomp, linear_skip, moving_avg in keys:
        row = empty_row(
            variant,
            horizon,
            scales,
            fusion,
            use_decomp,
            linear_skip,
            moving_avg,
        )
        result = discovered.get(
            (variant, horizon, scales, fusion, use_decomp, linear_skip, moving_avg)
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
        "ms_use_linear_skip",
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
