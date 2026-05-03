#!/usr/bin/env python
import csv
import json
import re
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results"
OUT_PATH = RESULTS_DIR / "gld_ns_mamba_ablation.csv"

DATASET = "GLD"
TARGET = "close"
MODEL = "NS_Mamba"
SETTING_ID = "A"
VARIANTS = ["NS_Mamba-A", "NS_Mamba-D", "NS_Mamba-AD", "NS_Mamba-ADG"]
HORIZONS = [1, 3, 5, 7, 14, 30, 60, 90, 120, 180, 270, 360]
DEFAULT_MOVING_AVG = 25
DEFAULT_ADAPTIVE_SCALE = 0.1
DEFAULT_RECENT_RATIO = 0.25

RUN_PATTERN = re.compile(
    r"^GLD_A_"
    r"(?P<variant>NS_Mamba-(?:ADG|AD|A|D))_"
    r"pl(?P<horizon>\d+)_"
    r"ma(?P<moving_avg>\d+)_"
    r"as(?P<adaptive_scale>[0-9p]+)_"
    r"rr(?P<recent_ratio>[0-9p]+)_"
)


def term_for_horizon(horizon):
    if horizon <= 7:
        return "short"
    if horizon <= 90:
        return "middle"
    return "long"


def variant_flags(variant):
    flags = {
        "NS_Mamba-A": (1, 0, 0),
        "NS_Mamba-D": (0, 1, 0),
        "NS_Mamba-AD": (1, 1, 0),
        "NS_Mamba-ADG": (1, 1, 1),
    }
    return flags[variant]


def parse_float_tag(value):
    return float(value.replace("p", "."))


def parse_result_dir(path):
    match = RUN_PATTERN.match(path.name)
    if match is None:
        return None

    return {
        "variant": match.group("variant"),
        "horizon": int(match.group("horizon")),
        "moving_avg": int(match.group("moving_avg")),
        "ns_adaptive_scale": parse_float_tag(match.group("adaptive_scale")),
        "ns_recent_ratio": parse_float_tag(match.group("recent_ratio")),
    }


def load_metrics(metrics_path):
    metrics = np.load(metrics_path)
    mae, mse, rmse, mape, mspe = [float(x) for x in metrics[:5]]
    rmsse = float(metrics[5]) if metrics.shape[0] > 5 else ""
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
        "rmsse": rmsse,
        "status": "complete",
        "notes": "",
    }


def discover_results():
    discovered = {}
    for metrics_path in RESULTS_DIR.glob("GLD_A_NS_Mamba-*/metrics.npy"):
        parsed = parse_result_dir(metrics_path.parent)
        if parsed is None:
            continue

        key = (
            parsed["variant"],
            parsed["horizon"],
            parsed["moving_avg"],
            parsed["ns_adaptive_scale"],
            parsed["ns_recent_ratio"],
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


def empty_row(variant, horizon, moving_avg, adaptive_scale, recent_ratio):
    use_adaptive_norm, use_decomp, use_shift_gate = variant_flags(variant)
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
        "rmsse": "",
        "setting_id": SETTING_ID,
        "moving_avg": moving_avg,
        "use_adaptive_norm": use_adaptive_norm,
        "use_decomp": use_decomp,
        "use_shift_gate": use_shift_gate,
        "ns_adaptive_scale": adaptive_scale,
        "ns_recent_ratio": recent_ratio,
        "status": "pending",
        "run": "",
        "notes": "",
    }


def main():
    discovered = discover_results()
    planned_keys = {
        (
            variant,
            horizon,
            DEFAULT_MOVING_AVG,
            DEFAULT_ADAPTIVE_SCALE,
            DEFAULT_RECENT_RATIO,
        )
        for variant in VARIANTS
        for horizon in HORIZONS
    }
    keys = sorted(
        planned_keys | set(discovered.keys()),
        key=lambda item: (VARIANTS.index(item[0]), item[1], item[2], item[3], item[4]),
    )

    rows = []
    for variant, horizon, moving_avg, adaptive_scale, recent_ratio in keys:
        row = empty_row(variant, horizon, moving_avg, adaptive_scale, recent_ratio)
        result = discovered.get((variant, horizon, moving_avg, adaptive_scale, recent_ratio))
        if result is not None:
            if result["status"] == "complete":
                row.update(
                    {
                        "mse": result["mse"],
                        "mae": result["mae"],
                        "rmse": result["rmse"],
                        "mape": result["mape"],
                        "mspe": result["mspe"],
                        "rmsse": result["rmsse"],
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
        "rmsse",
        "setting_id",
        "moving_avg",
        "use_adaptive_norm",
        "use_decomp",
        "use_shift_gate",
        "ns_adaptive_scale",
        "ns_recent_ratio",
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
