#!/usr/bin/env python
"""Advance Study 3 only through its sealed train, release, test, and analysis gates."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def write_state(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def command(pid: int) -> str:
    try:
        return Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
    except (FileNotFoundError, PermissionError):
        return ""


def environment(pid: int) -> dict[str, str]:
    try:
        raw = Path(f"/proc/{pid}/environ").read_bytes()
    except (FileNotFoundError, PermissionError):
        return {}
    return {key.decode(errors="replace"): value.decode(errors="replace") for item in raw.split(b"\0") if b"=" in item for key, value in (item.split(b"=", 1),)}


def training_pids(run_id: str, runner: str) -> list[int]:
    marker = f"{runner} train"
    return [int(path.name) for path in Path("/proc").glob("[0-9]*") if marker in command(int(path.name)) and environment(int(path.name)).get("STUDY3_RUN_ID") == run_id]


def complete_count(root: Path) -> tuple[int, int]:
    complete, invalid = 0, 0
    for path in root.glob("bundles/*/manifest.json"):
        try:
            complete += json.loads(path.read_text(encoding="utf-8")).get("status") == "complete"
        except (OSError, json.JSONDecodeError):
            invalid += 1
    return complete, invalid


def stage(config: str, run_root: str, run_id: str, root: Path, name: str) -> int:
    log = root / "supervisor" / f"{name}.log"
    runner = os.environ.get("STUDY3_RUNNER", "scripts/study3_v1.py")
    with log.open("a", encoding="utf-8") as stream:
        return subprocess.run(["conda", "run", "--no-capture-output", "-n", "sci-agent", "python", runner, name], cwd=ROOT, env={**os.environ, "STUDY3_CONFIG_DIR": config, "STUDY3_RUN_ROOT": run_root, "STUDY3_RUN_ID": run_id}, stdout=stream, stderr=subprocess.STDOUT, check=False).returncode


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", default="configs/study3_v1")
    parser.add_argument("--run-root", default="results/study3_v1")
    parser.add_argument("--run-id", default="study3_v1")
    parser.add_argument("--poll-seconds", type=int, default=30)
    args = parser.parse_args()
    runner = os.environ.get("STUDY3_RUNNER", "scripts/study3_v1.py")
    root = ROOT / args.run_root
    state, lock_path = root / "supervisor" / "state.json", root / "supervisor" / "lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        while training_pids(args.run_id, runner):
            complete, invalid = complete_count(root)
            write_state(state, {"status": "waiting_for_training", "updated_at": now(), "run_id": args.run_id, "training_pids": training_pids(args.run_id, runner), "complete_cells": complete, "invalid_manifests": invalid})
            time.sleep(max(15, args.poll_seconds))
        complete, invalid = complete_count(root)
        failures = list((root / "failures").glob("*.json"))
        if complete != 40 or invalid or failures:
            write_state(state, {"status": "stopped_training_matrix_invalid", "updated_at": now(), "run_id": args.run_id, "complete_cells": complete, "invalid_manifests": invalid, "failure_files": [str(path.name) for path in failures], "test_loaded": (root / "data" / "test.npz").exists()})
            return
        write_state(state, {"status": "running_release_gate", "updated_at": now(), "run_id": args.run_id})
        if stage(args.config_dir, args.run_root, args.run_id, root, "release-gate"):
            write_state(state, {"status": "stopped_release_gate_failed", "updated_at": now(), "run_id": args.run_id, "test_loaded": False})
            return
        write_state(state, {"status": "running_test_once", "updated_at": now(), "run_id": args.run_id})
        if stage(args.config_dir, args.run_root, args.run_id, root, "evaluate-once"):
            write_state(state, {"status": "stopped_test_failed", "updated_at": now(), "run_id": args.run_id})
            return
        write_state(state, {"status": "running_analysis", "updated_at": now(), "run_id": args.run_id})
        result = stage(args.config_dir, args.run_root, args.run_id, root, "analyze")
        write_state(state, {"status": "complete" if result == 0 else "stopped_analysis_failed", "updated_at": now(), "run_id": args.run_id, "test_loaded": True})


if __name__ == "__main__":
    main()
