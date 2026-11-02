#!/usr/bin/env python
"""Record resources for one risk-controlled residual run without acting on it.

The Stage A runner is CPU-only.  This monitor records host and GPU telemetry so
that an idle GPU is distinguishable from an unrecorded resource state.  Process
matching is restricted to the runner command and its explicit ``RCR_RUN_ID``.
It never signals, restarts, or otherwise changes a scientific job.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = ROOT / os.environ.get("RCR_RUN_ROOT", "results/risk_controlled_residual_v1")
RUN_ID = os.environ.get("RCR_RUN_ID", RUN_ROOT.name)
MONITOR_ROOT = RUN_ROOT / "monitor"


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def process_command(pid: int) -> str:
    try:
        return Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
    except (FileNotFoundError, PermissionError):
        return ""


def process_environment(pid: int) -> dict[str, str]:
    try:
        raw = Path(f"/proc/{pid}/environ").read_bytes()
    except (FileNotFoundError, PermissionError):
        return {}
    return {item.split(b"=", 1)[0].decode(errors="replace"): item.split(b"=", 1)[1].decode(errors="replace") for item in raw.split(b"\0") if b"=" in item}


def live_processes() -> list[dict[str, object]]:
    result = []
    for entry in Path("/proc").glob("[0-9]*"):
        pid = int(entry.name)
        if pid == os.getpid():
            continue
        command = process_command(pid)
        if "scripts/risk_controlled_residual.py" in command and process_environment(pid).get("RCR_RUN_ID") == RUN_ID:
            result.append({"pid": pid, "command": command})
    return result


def gpu_snapshot() -> list[dict[str, str]]:
    names = ("index", "name", "temperature_c", "power_w", "memory_used_mib", "memory_total_mib", "utilization_gpu_pct")
    command = ["nvidia-smi", "--query-gpu=index,name,temperature.gpu,power.draw,memory.used,memory.total,utilization.gpu", "--format=csv,noheader,nounits"]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode:
        return [{"unavailable": completed.stderr.strip() or completed.stdout.strip() or "nvidia-smi unavailable"}]
    return [dict(zip(names, (value.strip() for value in line.split(",")), strict=True)) for line in completed.stdout.splitlines()]


def host_snapshot() -> dict[str, object]:
    memory = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        key, value = line.split(":", 1)
        memory[key] = int(value.strip().split()[0]) * 1024
    disk = shutil.disk_usage(ROOT)
    return {
        "load_average": list(os.getloadavg()),
        "memory": {"available_bytes": memory.get("MemAvailable", 0), "swap_free_bytes": memory.get("SwapFree", 0)},
        "disk": {"free_bytes": disk.free, "total_bytes": disk.total},
    }


def protocol_snapshot() -> dict[str, object]:
    path = RUN_ROOT / "protocol" / "protocol.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "unsealed", "target_numeric_materialized": False}
    return {"status": payload.get("status"), "target_numeric_materialized": payload.get("target_numeric_materialized", False)}


def snapshot() -> dict[str, object]:
    return {"timestamp": now(), "run_id": RUN_ID, "processes": live_processes(), "host": host_snapshot(), "gpu": gpu_snapshot(), "protocol": protocol_snapshot()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-interval-seconds", type=int, default=1800)
    parser.add_argument("--active-poll-seconds", type=int, default=60)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.full_interval_seconds < 60 or args.active_poll_seconds < 15:
        raise ValueError("monitor intervals are below safe minimums")
    MONITOR_ROOT.mkdir(parents=True, exist_ok=True)
    with (MONITOR_ROOT / "monitor.lock").open("w", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        last_full = 0.0
        while True:
            payload = snapshot()
            atomic_json(MONITOR_ROOT / "state.json", payload)
            current = time.monotonic()
            if current - last_full >= args.full_interval_seconds:
                atomic_json(MONITOR_ROOT / f"snapshot_{time.strftime('%Y%m%dT%H%M%S%z')}.json", payload)
                last_full = current
            if args.once:
                return 0
            time.sleep(args.active_poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
