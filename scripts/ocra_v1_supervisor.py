#!/usr/bin/env python
"""Continue one sealed OCRA protocol without bypassing its test gate.

The supervisor only advances after every registered train/validation bundle is
complete.  E2 is always run before test evaluation; an E2 failure is terminal
for this protocol version and is recorded without materializing test data.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def cmdline(pid: int) -> str:
    try:
        return Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
    except (FileNotFoundError, PermissionError):
        return ""


def environment(pid: int) -> dict[str, str]:
    try:
        raw = Path(f"/proc/{pid}/environ").read_bytes()
    except (FileNotFoundError, PermissionError):
        return {}
    result = {}
    for item in raw.split(b"\0"):
        if b"=" in item:
            key, value = item.split(b"=", 1)
            result[key.decode(errors="replace")] = value.decode(errors="replace")
    return result


def training_processes(run_id: str) -> list[int]:
    pids = []
    for entry in Path("/proc").glob("[0-9]*"):
        try:
            pid = int(entry.name)
        except ValueError:
            continue
        if "scripts/ocra_v1.py train-bundle" in cmdline(pid) and environment(pid).get("OCRA_RUN_ID") == run_id:
            pids.append(pid)
    return pids


def bundle_statuses(root: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for manifest in root.glob("bundles/h*-s*/bundle_manifest.json"):
        try:
            status = str(json.loads(manifest.read_text(encoding="utf-8")).get("status", "unknown"))
        except (OSError, json.JSONDecodeError):
            status = "invalid"
        counts[status] = counts.get(status, 0) + 1
    return counts


def run_stage(config_dir: str, run_id: str, root: Path, stage: str) -> int:
    log = root / "supervisor" / f"{stage}.log"
    command = ["conda", "run", "--no-capture-output", "-n", "sci-agent", "python", "scripts/ocra_v1.py", stage]
    with log.open("a", encoding="utf-8") as handle:
        completed = subprocess.run(command, cwd=ROOT, env={**os.environ, "OCRA_CONFIG_DIR": config_dir, "OCRA_RUN_ID": run_id}, stdout=handle, stderr=subprocess.STDOUT, check=False)
    return int(completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--poll-seconds", type=int, default=30)
    args = parser.parse_args()
    root = (ROOT / args.run_root).resolve()
    state_path, lock_path = root / "supervisor" / "state.json", root / "supervisor" / "lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        atomic_json(state_path, {"status": "waiting_for_training", "started_at": now(), "run_id": args.run_id})
        while training_processes(args.run_id):
            atomic_json(state_path, {"status": "waiting_for_training", "updated_at": now(), "run_id": args.run_id, "training_pids": training_processes(args.run_id), "bundle_statuses": bundle_statuses(root)})
            time.sleep(max(15, args.poll_seconds))
        statuses = bundle_statuses(root)
        if statuses.get("complete", 0) != 20 or any(key != "complete" for key in statuses):
            atomic_json(state_path, {"status": "stopped_training_matrix_invalid", "updated_at": now(), "run_id": args.run_id, "bundle_statuses": statuses, "test_loaded": (root / "data" / "test.npz").exists()})
            return 1
        atomic_json(state_path, {"status": "running_e2", "updated_at": now(), "run_id": args.run_id, "bundle_statuses": statuses})
        if run_stage(args.config_dir, args.run_id, root, "fit-certificate"):
            atomic_json(state_path, {"status": "stopped_e2_failed", "updated_at": now(), "run_id": args.run_id, "test_loaded": (root / "data" / "test.npz").exists()})
            return 1
        e2 = json.loads((root / "protocol" / "e2_status.json").read_text(encoding="utf-8"))
        if e2.get("status") != "passed":
            atomic_json(state_path, {"status": "stopped_e2_not_passed", "updated_at": now(), "run_id": args.run_id, "e2": e2, "test_loaded": (root / "data" / "test.npz").exists()})
            return 1
        atomic_json(state_path, {"status": "running_test_once", "updated_at": now(), "run_id": args.run_id})
        if run_stage(args.config_dir, args.run_id, root, "evaluate-once"):
            atomic_json(state_path, {"status": "stopped_test_failed", "updated_at": now(), "run_id": args.run_id})
            return 1
        atomic_json(state_path, {"status": "running_analysis", "updated_at": now(), "run_id": args.run_id})
        analysis_returncode = run_stage(args.config_dir, args.run_id, root, "analyze")
        atomic_json(state_path, {"status": "complete" if analysis_returncode == 0 else "stopped_analysis_failed", "updated_at": now(), "run_id": args.run_id, "test_loaded": True})
        return analysis_returncode


if __name__ == "__main__":
    raise SystemExit(main())
