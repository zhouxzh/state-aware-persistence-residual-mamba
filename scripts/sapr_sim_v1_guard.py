#!/usr/bin/env python
"""Wait for the SAPR Sim V1 trainer, then run its immutable post-training checks."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("SAPR_MAMBA_VERSION", "sim_v1")

from utils.sapr_mamba.io import RESULT_ROOT, RUNLOG_ROOT, atomic_write_json, utc_now


STUDY_VERSION = os.environ["SAPR_MAMBA_VERSION"]
if STUDY_VERSION not in {"sim_v1", "sim_v2", "sim_v3", "sim_v5", "canonical_v1", "canonical_v2", "bocpd_confirm_v1"} and not (STUDY_VERSION.startswith("bocpd_e") and STUDY_VERSION[7:].isdigit()):
    raise ValueError("sapr_sim guard requires a configured simulation namespace")
ROOT = RESULT_ROOT / "synthetic"
STATE = RESULT_ROOT / "autocontinue_state.json"


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def snapshot(trainer_pid: int, stage: str) -> dict:
    statuses: Counter[str] = Counter()
    current: list[dict] = []
    for path in sorted(ROOT.glob("*_seed*/task_manifest.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        statuses[str(payload.get("status", "unknown"))] += 1
        if payload.get("status") == "running":
            current.append({"task": path.parent.name, "started_at": payload.get("started_at")})
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader"], text=True, capture_output=True, check=False).stdout.strip()
    payload = {"timestamp": utc_now(), "stage": stage, "trainer_pid": trainer_pid, "trainer_alive": alive(trainer_pid), "task_statuses": dict(statuses), "current_tasks": current, "gpu": gpu}
    RUNLOG_ROOT.mkdir(parents=True, exist_ok=True)
    atomic_write_json(RUNLOG_ROOT / f"progress_{time.strftime('%Y%m%dT%H%M%S%z')}.json", payload)
    atomic_write_json(STATE, payload)
    return payload


def run_command(command: list[str], stage: str) -> None:
    log = RUNLOG_ROOT / f"{stage}_{time.strftime('%Y%m%dT%H%M%S%z')}.log"
    RUNLOG_ROOT.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(command, cwd=REPO_ROOT, env={**os.environ, "SAPR_MAMBA_VERSION": STUDY_VERSION}, stdout=handle, stderr=subprocess.STDOUT, check=False)
    if completed.returncode:
        raise RuntimeError(f"{stage}_failed: see {log}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trainer-pid", type=int, required=True)
    parser.add_argument("--interval-seconds", type=int, default=1800)
    args = parser.parse_args()
    try:
        while alive(args.trainer_pid):
            snapshot(args.trainer_pid, "waiting_for_training")
            time.sleep(max(30, args.interval_seconds))
        final = snapshot(args.trainer_pid, "training_exited")
        protocol = json.loads((REPO_ROOT / "configs" / f"sapr_mamba_{STUDY_VERSION}" / "protocol.json").read_text(encoding="utf-8"))
        expected_tasks = len(protocol["models"]) * len(protocol["seeds"])
        if final["task_statuses"].get("complete", 0) != expected_tasks or final["task_statuses"].get("failed", 0):
            raise RuntimeError(f"training_matrix_invalid:{final['task_statuses']}")
        run_command(["conda", "run", "--no-capture-output", "-n", "sci-agent", "python", "scripts/sapr_sim_v1_analyze.py", "--stage", "analyze"], "analysis")
        run_command(["conda", "run", "--no-capture-output", "-n", "sci-agent", "python", "scripts/sapr_sim_v1_analyze.py", "--stage", "verify"], "verification")
        run_command(["conda", "run", "--no-capture-output", "-n", "sci-agent", "pytest", "-q", "tests/test_sapr_sim_v1.py", "tests/test_sapr_sim_v1_analysis.py"], "sim_tests")
        # Strip the simulation selector at process creation so historical V3
        # tests resolve their own frozen configuration namespace.
        run_command(["env", "-u", "SAPR_MAMBA_VERSION", "conda", "run", "--no-capture-output", "-n", "sci-agent", "pytest", "-q"], "tests")
        atomic_write_json(STATE, {"timestamp": utc_now(), "stage": "complete", "trainer_pid": args.trainer_pid, "analysis": "complete", "verification": "complete", "tests": "complete"})
    except Exception as exc:
        atomic_write_json(STATE, {"timestamp": utc_now(), "stage": "failed", "trainer_pid": args.trainer_pid, "error": repr(exc)})
        raise


if __name__ == "__main__":
    main()
