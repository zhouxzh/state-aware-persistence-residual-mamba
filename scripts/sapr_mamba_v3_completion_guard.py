#!/usr/bin/env python
"""Wait for the frozen V3/V3.1 real matrix, then run final evidence checks."""

from __future__ import annotations

import json
import os
import subprocess
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_ROOT = REPO_ROOT / "results" / "sapr_mamba_v3" / "real"
LOG_PATH = REPO_ROOT / "docs" / "current" / "zhong3_runlog" / "sapr_mamba_v3" / "external_completion_guard.log"


def stamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def counts() -> Counter[str]:
    result = Counter()
    if not RESULT_ROOT.is_dir():
        return result
    for path in RESULT_ROOT.rglob("task_manifest.json"):
        try:
            result[str(json.loads(path.read_text(encoding="utf-8")).get("status", "invalid"))] += 1
        except (OSError, json.JSONDecodeError):
            result["invalid"] += 1
    return result


def log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{stamp()} {message}\n")


def run(command: list[str]) -> int:
    log("start " + " ".join(command))
    completed = subprocess.run(
        ["conda", "run", "--no-capture-output", "-n", "sci-agent", *command],
        cwd=REPO_ROOT,
        env={**os.environ, "SAPR_MAMBA_VERSION": "v3"},
        check=False,
        text=True,
    )
    log(f"finish rc={completed.returncode} {' '.join(command)}")
    return int(completed.returncode)


def main() -> int:
    log("guard_started")
    while True:
        current = counts()
        log(f"complete={current.get('complete', 0)} failed={current.get('failed', 0)} invalid={current.get('invalid', 0)}")
        if current.get("complete", 0) >= 950 and not any(current.get(key, 0) for key in ("failed", "invalid")):
            break
        time.sleep(60)
    commands = (
        ["python", "scripts/sapr_mamba_v3_pipeline.py", "--stage", "real_extended", "--max-rounds", "3"],
        ["python", "scripts/sapr_mamba_real_analysis.py", "--stage", "analyze"],
        ["python", "scripts/sapr_mamba_v3_manuscript.py"],
        ["python", "scripts/sapr_mamba_real_analysis.py", "--stage", "verify"],
        ["python", "scripts/sapr_mamba_v3_release.py", "--stage", "build"],
        ["python", "scripts/sapr_mamba_v3_release.py", "--stage", "verify"],
        ["python", "-m", "pytest", "-q"],
    )
    return_codes = [run(command) for command in commands]
    log(f"guard_finished return_codes={return_codes}")
    return 0 if all(code == 0 for code in return_codes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
