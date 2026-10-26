#!/usr/bin/env python
"""Wait for V7 candidate completion, then run the locked selector and audit."""

from __future__ import annotations

import json
import os
import subprocess
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT = REPO_ROOT / "results" / "sapr_mamba_v7" / "confirmation" / "traffic_hourly"
LOG = REPO_ROOT / "docs" / "current" / "zhong3_runlog" / "sapr_mamba_v7" / "confirmation_guard.log"
EXPECTED_CANDIDATES = 70
CANDIDATES = {"M0", "M1", "M2", "M3", "DLinear", "SeasonalNaive", "Drift"}


def log(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"{datetime.now().astimezone().isoformat(timespec='seconds')} {message}\n")


def counts() -> Counter[str]:
    outcome: Counter[str] = Counter()
    for path in ROOT.glob("*_seed*/task_manifest.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("model") in CANDIDATES:
                outcome[payload.get("status", "invalid")] += 1
        except (OSError, json.JSONDecodeError): outcome["invalid"] += 1
    return outcome


def run(args: list[str]) -> int:
    log("start " + " ".join(args))
    result = subprocess.run(["conda", "run", "--no-capture-output", "-n", "sci-agent", "python", *args], cwd=REPO_ROOT, env={**os.environ, "SAPR_MAMBA_VERSION": "v7"}, check=False)
    log(f"finish rc={result.returncode} {' '.join(args)}")
    return int(result.returncode)


def main() -> int:
    log("guard_started")
    while True:
        current = counts()
        log(f"complete={current['complete']} failed={current['failed']} invalid={current['invalid']}")
        if current["complete"] >= EXPECTED_CANDIDATES and not current["failed"] and not current["invalid"]:
            break
        time.sleep(60)
    codes = [run(["scripts/sapr_mamba_v7.py", "--stage", "select"]), run(["scripts/sapr_mamba_v7_analyze.py"])]
    log(f"guard_finished codes={codes}")
    return 0 if all(code == 0 for code in codes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
