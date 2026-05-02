#!/usr/bin/env python
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results"
OUT_ALL = RESULTS_DIR / "gld_mamba_hpo_all.csv"
OUT_BEST = RESULTS_DIR / "gld_mamba_hpo_best.csv"

DATASET = "GLD"
TARGET = "close"

RUN_RE = re.compile(
    r"^GLD_MAMBAHPO_"
    r"(?P<variant>.+?)_"
    r"cfg(?P<config_id>[^_]+)_"
    r"sl(?P<seq_len>\d+)_"
    r"ll(?P<label_len>\d+)_"
    r"pl(?P<horizon>\d+)_"
    r"dm(?P<d_model>\d+)_"
    r"df(?P<d_ff>\d+)_"
    r"ds(?P<d_state>\d+)_"
    r"el(?P<e_layers>\d+)_"
    r"bs(?P<batch_size>\d+)_"
    r"lr(?P<learning_rate>[0-9p]+)_"
    r"ma(?P<moving_avg>\d+)_"
    r"sc(?P<ms_scales>[0-9-]+|na)_"
    r"fu(?P<ms_fusion>[A-Za-z]+|na)_"
    r"dc(?P<ms_use_decomp>[01]|na)_"
    r"ls(?P<ms_use_linear_skip>[01]|na)_"
    r"p(?P<patch_len>\d+|na)_"
    r"st(?P<stride>\d+|na)_"
)


def term_for_horizon(horizon):
    if horizon <= 7:
        return "short"
    if horizon <= 120:
        return "middle"
    return "long"


def model_for_variant(variant):
    if variant == "S_Mamba":
        return "S_Mamba"
    if variant.startswith("NS_Mamba-"):
        return "NS_Mamba"
    if variant.startswith("MS_Mamba-"):
        return "MS_Mamba"
    if variant.startswith("PMS_Mamba-"):
        return "PMS_Mamba"
    return variant


def parse_float_tag(value):
    return float(value.replace("p", "."))


def parse_optional_int(value):
    return "" if value == "na" else int(value)


def parse_optional_str(value):
    return "" if value == "na" else value


def parse_result_dir(path):
    match = RUN_RE.match(path.name)
    if match is None:
        return None

    horizon = int(match.group("horizon"))
    variant = match.group("variant")
    return {
        "dataset": DATASET,
        "target": TARGET,
        "model": model_for_variant(variant),
        "variant": variant,
        "config_id": match.group("config_id"),
        "horizon": horizon,
        "term": term_for_horizon(horizon),
        "seq_len": int(match.group("seq_len")),
        "label_len": int(match.group("label_len")),
        "pred_len": horizon,
        "d_model": int(match.group("d_model")),
        "d_ff": int(match.group("d_ff")),
        "d_state": int(match.group("d_state")),
        "e_layers": int(match.group("e_layers")),
        "batch_size": int(match.group("batch_size")),
        "learning_rate": parse_float_tag(match.group("learning_rate")),
        "moving_avg": int(match.group("moving_avg")),
        "ms_scales": parse_optional_str(match.group("ms_scales")),
        "ms_fusion": parse_optional_str(match.group("ms_fusion")),
        "ms_use_decomp": parse_optional_int(match.group("ms_use_decomp")),
        "ms_use_linear_skip": parse_optional_int(match.group("ms_use_linear_skip")),
        "patch_len": parse_optional_int(match.group("patch_len")),
        "stride": parse_optional_int(match.group("stride")),
    }


def load_metrics(metrics_path):
    metrics = np.load(metrics_path)
    mae, mse, rmse, mape, mspe = [float(x) for x in metrics[:5]]

    meta_path = metrics_path.parent / "meta.json"
    inverse = None
    if meta_path.exists():
        with meta_path.open() as f:
            inverse = bool(json.load(f).get("inverse", False))

    if inverse is False:
        return {
            "mse": "",
            "mae": "",
            "rmse": "",
            "mape": "",
            "mspe": "",
            "metric_scale": "scaled",
            "status": "legacy_scaled",
            "notes": "inverse=False; not comparable to price-scale results",
        }
    if inverse is None:
        return {
            "mse": "",
            "mae": "",
            "rmse": "",
            "mape": "",
            "mspe": "",
            "metric_scale": "unknown",
            "status": "legacy_unknown",
            "notes": "missing meta.json",
        }

    return {
        "mse": mse,
        "mae": mae,
        "rmse": rmse,
        "mape": mape,
        "mspe": mspe,
        "metric_scale": "price",
        "status": "complete",
        "notes": "",
    }


def discover_rows():
    rows_by_key = {}
    for metrics_path in RESULTS_DIR.glob("GLD_MAMBAHPO_*/metrics.npy"):
        parsed = parse_result_dir(metrics_path.parent)
        if parsed is None:
            continue

        row = {
            **parsed,
            **load_metrics(metrics_path),
            "run": metrics_path.parent.name,
            "mtime": metrics_path.stat().st_mtime,
        }
        key = (
            row["variant"],
            row["config_id"],
            row["horizon"],
            row["seq_len"],
            row["d_model"],
            row["d_ff"],
            row["d_state"],
            row["moving_avg"],
            row["ms_scales"],
            row["ms_fusion"],
            row["ms_use_decomp"],
            row["ms_use_linear_skip"],
            row["patch_len"],
            row["stride"],
        )
        current = rows_by_key.get(key)
        if current is None or row["mtime"] > current["mtime"]:
            rows_by_key[key] = row
    return list(rows_by_key.values())


def write_csv(path, rows):
    path.parent.mkdir(exist_ok=True)
    fieldnames = [
        "dataset",
        "target",
        "model",
        "variant",
        "config_id",
        "horizon",
        "term",
        "seq_len",
        "label_len",
        "pred_len",
        "d_model",
        "d_ff",
        "d_state",
        "e_layers",
        "batch_size",
        "learning_rate",
        "moving_avg",
        "ms_scales",
        "ms_fusion",
        "ms_use_decomp",
        "ms_use_linear_skip",
        "patch_len",
        "stride",
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


def sort_key(row):
    return (
        row["variant"],
        int(row["horizon"]),
        str(row["config_id"]),
        int(row["seq_len"]),
        int(row["d_model"]),
        int(row["d_ff"]),
        int(row["d_state"]),
        int(row["moving_avg"]),
        str(row["ms_scales"]),
        str(row["ms_fusion"]),
        str(row["patch_len"]),
        str(row["stride"]),
    )


def main():
    rows = sorted(discover_rows(), key=sort_key)

    grouped = defaultdict(list)
    for row in rows:
        if row["status"] == "complete":
            grouped[(row["variant"], row["horizon"])].append(row)

    best_rows = []
    for key in sorted(grouped, key=lambda item: (item[0], item[1])):
        best_rows.append(min(grouped[key], key=lambda row: float(row["rmse"])))

    for row in rows:
        row.pop("mtime", None)
    for row in best_rows:
        row.pop("mtime", None)

    write_csv(OUT_ALL, rows)
    write_csv(OUT_BEST, best_rows)

    complete = sum(row["status"] == "complete" for row in rows)
    print(f"wrote {OUT_ALL.relative_to(REPO_ROOT)}")
    print(f"wrote {OUT_BEST.relative_to(REPO_ROOT)}")
    print(f"complete rows: {complete}/{len(rows)}")
    print(f"best rows: {len(best_rows)}")


if __name__ == "__main__":
    main()
