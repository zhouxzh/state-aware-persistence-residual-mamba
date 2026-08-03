#!/usr/bin/env python
"""Merge and validate sharded PMS-Mamba V2 validation results."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = REPO_ROOT / "results" / "nonstationary_analysis_v2"
DEFAULT_INPUTS = (
    DEFAULT_ROOT / "screen",
    DEFAULT_ROOT / "screen_f02_f03",
    DEFAULT_ROOT / "screen_f04_f05",
    DEFAULT_ROOT / "screen_f06_f07_f08",
)
DEFAULT_OUTPUT = DEFAULT_ROOT / "screen_merged"
NUMERIC_METRICS = ("mae", "mse", "rmse", "mape", "mspe", "rmsse", "runtime_seconds")
KEY_FIELDS = ("config_id", "task", "seed", "horizon")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_pms_v2_screen import (  # noqa: E402
    HORIZONS,
    RESULT_FIELDS,
    TASKS,
    build_design,
    sha256_path,
    summarize,
    write_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-roots", nargs="+", type=Path, default=list(DEFAULT_INPUTS))
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--config-ids", nargs="+", default=None)
    parser.add_argument("--seeds", nargs="+", type=int, default=[2023, 2024, 2025])
    parser.add_argument("--stage", default="validation_screen")
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_complete_rows(input_roots: list[Path]) -> tuple[pd.DataFrame, list[dict]]:
    frames = []
    sources = []
    for root in input_roots:
        path = root.resolve() / "screen_results.csv"
        if not path.is_file():
            raise FileNotFoundError(path)
        frame = pd.read_csv(path)
        missing = sorted(set(RESULT_FIELDS) - set(frame.columns))
        if missing:
            raise ValueError(f"{path} is missing columns: {missing}")
        frames.append(frame[frame["status"] == "complete"].copy())
        sources.append({
            "path": str(path.relative_to(REPO_ROOT)),
            "sha256": file_sha256(path),
            "complete_rows": int((frame["status"] == "complete").sum()),
            "discarded_rows": int((frame["status"] != "complete").sum()),
        })
    return pd.concat(frames, ignore_index=True), sources


def validate_and_deduplicate(
    frame: pd.DataFrame,
    design: list[dict],
    seeds: list[int],
) -> pd.DataFrame:
    config_ids = [row["config_id"] for row in design]
    frame = frame[frame["config_id"].isin(config_ids)].copy()
    for field in ("seed", "horizon", *NUMERIC_METRICS):
        frame[field] = pd.to_numeric(frame[field], errors="raise")
    metric_values = frame[list(NUMERIC_METRICS)].to_numpy(dtype=float)
    if not np.isfinite(metric_values).all():
        raise ValueError("Complete rows contain non-finite metrics")

    factor_fields = ("residual_target", "loss", "ms_fusion", "horizon_weighting")
    expected_factors = {row["config_id"]: row for row in design}
    for config_id, group in frame.groupby("config_id"):
        expected = expected_factors[config_id]
        for field in factor_fields:
            observed = {str(value) for value in group[field].unique()}
            wanted = str(expected[field])
            if observed != {wanted}:
                raise ValueError(f"{config_id} has invalid {field}: {sorted(observed)} != {wanted}")

    duplicates = frame[frame.duplicated(list(KEY_FIELDS), keep=False)]
    if not duplicates.empty:
        for key, group in duplicates.groupby(list(KEY_FIELDS), sort=False):
            comparable = group[list(RESULT_FIELDS)].drop(columns=["runtime_seconds", "error"])
            if len(comparable.drop_duplicates()) != 1:
                raise ValueError(f"Conflicting duplicate result for {key}")
    frame = frame.drop_duplicates(list(KEY_FIELDS), keep="first")

    expected_keys = set(itertools.product(config_ids, TASKS, seeds, HORIZONS))
    observed_keys = {
        (row.config_id, row.task, int(row.seed), int(row.horizon))
        for row in frame.itertuples(index=False)
    }
    missing = sorted(expected_keys - observed_keys)
    unexpected = sorted(observed_keys - expected_keys)
    if missing or unexpected:
        raise ValueError(
            f"Incomplete design: missing={len(missing)}, unexpected={len(unexpected)}; "
            f"first_missing={missing[:3]}, first_unexpected={unexpected[:3]}"
        )
    expected_rows = len(config_ids) * len(TASKS) * len(seeds) * len(HORIZONS)
    if len(frame) != expected_rows:
        raise ValueError(f"Expected {expected_rows} rows, found {len(frame)}")
    return frame.sort_values(list(KEY_FIELDS)).reset_index(drop=True)


def main() -> None:
    args = parse_args()
    full_design = build_design()
    all_ids = {row["config_id"] for row in full_design}
    requested_ids = args.config_ids or [row["config_id"] for row in full_design]
    unknown = sorted(set(requested_ids) - all_ids)
    if unknown:
        raise ValueError(f"Unknown config IDs: {unknown}")
    design = [row for row in full_design if row["config_id"] in set(requested_ids)]
    seeds = sorted(set(int(seed) for seed in args.seeds))
    frame, sources = read_complete_rows(args.input_roots)
    frame = validate_and_deduplicate(frame, design, seeds)

    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    results_path = output_root / "screen_results.csv"
    frame[list(RESULT_FIELDS)].to_csv(results_path, index=False, quoting=csv.QUOTE_MINIMAL)
    write_csv(output_root / "screen_design.csv", design, tuple(design[0].keys()))
    summarize(results_path, output_root)

    summary = pd.read_csv(output_root / "screen_config_summary.csv")
    manifest = {
        "stage": args.stage,
        "selection_eval_flag": "val",
        "objective_metric": "mean_balanced_rmsse",
        "config_ids": [row["config_id"] for row in design],
        "tasks": list(TASKS),
        "seeds": seeds,
        "horizons": list(HORIZONS),
        "expected_rows": int(len(frame)),
        "complete_rows": int(len(frame)),
        "test_targets_read": False,
        "source_results": sources,
        "results_sha256": sha256_path(results_path),
        "design_sha256": sha256_path(output_root / "screen_design.csv"),
        "ranked_config_ids": summary["config_id"].tolist(),
    }
    (output_root / "validation_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"Merged {len(frame)} complete validation rows for {len(design)} configs; "
        f"best={summary.iloc[0]['config_id']} "
        f"mean_balanced_rmsse={summary.iloc[0]['mean_balanced_rmsse']:.6f}"
    )


if __name__ == "__main__":
    main()
