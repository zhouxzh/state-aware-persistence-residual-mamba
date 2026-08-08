#!/usr/bin/env python
"""Freeze S/M external benchmark tasks without reading forecast targets."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = REPO_ROOT / "configs" / "optuna_datasets.json"
DEFAULT_PROTOCOL = REPO_ROOT / "configs" / "pms_mamba_v3.json"
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "reproducibility"
    / "nonstationary_analysis_v3"
    / "protocol"
    / "external_tasks.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> None:
    args = parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8"))
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    untouched = set(protocol["evidence_boundary"]["untouched_external"])
    opened = set(protocol["evidence_boundary"]["previously_opened_robustness"])
    tasks = {}
    missing = {}
    for dataset, config in source.items():
        path = (REPO_ROOT / config["root_path"] / config["data_path"]).resolve()
        if not path.is_file():
            missing[dataset] = {
                "path": str(path.relative_to(REPO_ROOT)),
                "reason": "configured source file is unavailable",
            }
            continue
        columns = pd.read_csv(path, nrows=0).columns.tolist()
        if not columns or columns[0] != "date" or config["target"] not in columns:
            raise ValueError(f"Unexpected benchmark schema: {path}")
        variable_count = len(columns) - 1
        if dataset in untouched:
            evidence_status = "untouched_confirmatory"
        elif dataset in opened:
            evidence_status = "previously_opened_robustness"
        else:
            evidence_status = "development_only"
        split_policy = (
            "TSLib fixed ETT train/validation/test boundaries"
            if str(config.get("data", "custom")).startswith("ETT")
            else "chronological 70/10/20 row split"
        )
        for mode in ("S", "M"):
            slug = f"{dataset}_{mode.lower()}"
            dimension = 1 if mode == "S" else variable_count
            tasks[slug] = {
                **config,
                "features": mode,
                "enc_in": dimension,
                "dec_in": dimension,
                "c_out": dimension,
                "data_sha256": sha256(path),
                "protocol_version": protocol["protocol_version"],
                "protocol_sha256": sha256(args.protocol),
                "source_manifest": "data/benchmark_download_manifest.json",
                "physical_dataset": dataset,
                "input_mode": mode,
                "variable_count": variable_count,
                "split_policy": split_policy,
                "evidence_status": evidence_status,
                "test_targets_read": False,
            }
    payload = {
        "protocol_version": protocol["protocol_version"],
        "protocol_sha256": sha256(args.protocol),
        "source_config_sha256": sha256(args.source),
        "generated_without_reading_target_values": True,
        "task_count": len(tasks),
        "tasks": tasks,
        "missing_configured_datasets": missing,
    }
    atomic_write(args.output, payload)
    print(f"Wrote {len(tasks)} frozen S/M tasks to {args.output.relative_to(REPO_ROOT)}")
    if missing:
        print(f"Unavailable configured datasets: {', '.join(sorted(missing))}")


if __name__ == "__main__":
    main()
