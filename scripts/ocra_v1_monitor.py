#!/usr/bin/env python
"""Monitor sealed OCRA-v1 resources without changing protocol decisions.

Full health snapshots are written every 30 minutes.  While an OCRA process is
live, GPU temperature is sampled every 60 seconds.  A critical temperature must
persist for three samples before this monitor sends SIGTERM to *only* matching
OCRA processes; it never restarts jobs or changes a frozen protocol.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = ROOT / os.environ.get("OCRA_MONITOR_RUN_ROOT", "results/ocra_v1_r2")
RUN_ID = os.environ.get("OCRA_MONITOR_RUN_ID", RUN_ROOT.name)
MONITOR_ROOT = RUN_ROOT / "monitor"
LOCK_PATH = MONITOR_ROOT / "monitor.lock"
STATE_PATH = MONITOR_ROOT / "state.json"
EVENTS_PATH = MONITOR_ROOT / "events.jsonl"


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def emit(event: str, *, update_state: bool = True, **fields: object) -> dict:
    payload = {"timestamp": now(), "event": event, **fields}
    MONITOR_ROOT.mkdir(parents=True, exist_ok=True)
    with EVENTS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")
    if update_state:
        atomic_json(STATE_PATH, payload)
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True), flush=True)
    return payload


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
    result = {}
    for item in raw.split(b"\0"):
        if b"=" not in item:
            continue
        key, value = item.split(b"=", 1)
        result[key.decode(errors="replace")] = value.decode(errors="replace")
    return result


def live_ocra_processes() -> list[dict]:
    processes: list[dict] = []
    for entry in Path("/proc").glob("[0-9]*"):
        try:
            pid = int(entry.name)
        except ValueError:
            continue
        command = process_command(pid)
        environment = process_environment(pid)
        if "scripts/ocra_v1.py" in command and environment.get("OCRA_RUN_ID") == RUN_ID and pid != os.getpid():
            processes.append({"pid": pid, "command": command})
    return processes


def gpu_snapshot() -> list[dict]:
    fields = "index,name,temperature.gpu,power.draw,power.limit,memory.used,memory.total,utilization.gpu,utilization.memory,fan.speed"
    completed = subprocess.run(
        ["nvidia-smi", f"--query-gpu={fields}", "--format=csv,noheader,nounits"],
        text=True, capture_output=True, check=False,
    )
    if completed.returncode:
        return [{"unavailable": completed.stderr.strip() or completed.stdout.strip()}]
    names = ("index", "name", "temperature_c", "power_w", "power_limit_w", "memory_used_mib", "memory_total_mib", "utilization_gpu_pct", "utilization_memory_pct", "fan_pct")
    rows = []
    for line in completed.stdout.splitlines():
        values = [value.strip() for value in line.split(",")]
        rows.append(dict(zip(names, values, strict=True)))
    return rows


def host_snapshot() -> dict:
    disk = shutil.disk_usage(ROOT)
    memory = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        key, value = line.split(":", 1)
        memory[key] = int(value.strip().split()[0]) * 1024
    return {
        "disk": {"total_bytes": disk.total, "used_bytes": disk.used, "free_bytes": disk.free},
        "memory": {"total_bytes": memory.get("MemTotal", 0), "available_bytes": memory.get("MemAvailable", 0), "swap_free_bytes": memory.get("SwapFree", 0)},
        "load_average": list(os.getloadavg()),
    }


def protocol_snapshot() -> dict:
    e2 = RUN_ROOT / "protocol" / "e2_status.json"
    test = RUN_ROOT / "data" / "test.npz"
    if e2.is_file():
        payload = json.loads(e2.read_text(encoding="utf-8"))
        return {"status": payload.get("status"), "stage": payload.get("stage"), "stop_rule": payload.get("stop_rule"), "test_loaded": payload.get("test_loaded"), "test_numeric_materialized": test.exists()}

    # Expected E2 stops do not create e2_status.json, so retain the terminal
    # supervisor state instead of reporting an ambiguous missing-file status.
    supervisor = RUN_ROOT / "supervisor" / "state.json"
    try:
        supervisor_state = json.loads(supervisor.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        supervisor_state = {}
    status = str(supervisor_state.get("status", ""))
    if status.startswith("stopped_"):
        return {
            "status": status,
            "stage": "supervisor",
            "test_loaded": supervisor_state.get("test_loaded"),
            "test_numeric_materialized": test.exists(),
        }
    return {"status": "missing_e2_status", "test_numeric_materialized": test.exists()}


def experiment_snapshot() -> dict:
    """Read manifests only; never infer completion from filenames alone."""
    bundle_statuses: Counter[str] = Counter()
    model_statuses: Counter[str] = Counter()
    invalid_manifests: list[str] = []
    for manifest in sorted((RUN_ROOT / "bundles").glob("h*-s*/bundle_manifest.json")):
        try:
            bundle_statuses[str(json.loads(manifest.read_text(encoding="utf-8")).get("status", "unknown"))] += 1
        except (OSError, json.JSONDecodeError):
            invalid_manifests.append(str(manifest.relative_to(RUN_ROOT)))
    for manifest in sorted((RUN_ROOT / "bundles").glob("h*-s*/*/run_manifest.json")):
        try:
            model_statuses[str(json.loads(manifest.read_text(encoding="utf-8")).get("status", "unknown"))] += 1
        except (OSError, json.JSONDecodeError):
            invalid_manifests.append(str(manifest.relative_to(RUN_ROOT)))
    failure_files = sorted(str(path.relative_to(RUN_ROOT)) for path in (RUN_ROOT / "failures").glob("*.json"))
    return {"bundle_statuses": dict(bundle_statuses), "model_statuses": dict(model_statuses), "failure_files": failure_files, "invalid_manifests": invalid_manifests}


def temperatures(gpus: list[dict]) -> list[float]:
    output = []
    for gpu in gpus:
        try:
            output.append(float(gpu["temperature_c"]))
        except (KeyError, TypeError, ValueError):
            continue
    return output


def stop_ocra(processes: list[dict]) -> list[int]:
    stopped = []
    for process in processes:
        try:
            os.kill(int(process["pid"]), signal.SIGTERM)
            stopped.append(int(process["pid"]))
        except ProcessLookupError:
            continue
    return stopped


def snapshot(critical_samples: int, warning_temperature: float, critical_temperature: float) -> tuple[dict, int]:
    processes, gpus = live_ocra_processes(), gpu_snapshot()
    temperatures_now = temperatures(gpus)
    critical = bool(temperatures_now) and max(temperatures_now) >= float(critical_temperature)
    next_critical = critical_samples + 1 if critical else 0
    payload = {
        "run_id": RUN_ID,
        "ocra_processes": processes,
        "gpu": gpus,
        "host": host_snapshot(),
        "protocol": protocol_snapshot(),
        "experiment": experiment_snapshot(),
        "critical_temperature_samples": next_critical,
    }
    if temperatures_now and max(temperatures_now) >= float(warning_temperature):
        emit("temperature_warning", threshold_c=warning_temperature, critical_threshold_c=critical_temperature, **payload)
    elif str(payload["protocol"]["status"]).startswith("stopped_"):
        emit("protocol_stopped", **payload)
    else:
        emit("health_snapshot", **payload)
    return payload, next_critical


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval-seconds", type=int, default=1800)
    parser.add_argument("--active-poll-seconds", type=int, default=60)
    parser.add_argument("--warning-temperature-c", type=float, default=80.0)
    parser.add_argument("--critical-temperature-c", type=float, default=85.0)
    parser.add_argument("--critical-samples", type=int, default=3)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.interval_seconds < 60 or args.active_poll_seconds < 15 or args.critical_samples < 1:
        raise ValueError("monitor intervals and critical sample count are below safe minimums")
    MONITOR_ROOT.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("w", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            emit("already_running", update_state=False)
            return 0
        emit("monitor_started", pid=os.getpid(), run_id=RUN_ID, interval_seconds=args.interval_seconds, active_poll_seconds=args.active_poll_seconds, warning_temperature_c=args.warning_temperature_c, critical_temperature_c=args.critical_temperature_c, critical_samples_required=args.critical_samples)
        last_full = 0.0
        consecutive_critical = 0
        while True:
            payload, consecutive_critical = snapshot(consecutive_critical, args.warning_temperature_c, args.critical_temperature_c)
            if consecutive_critical >= args.critical_samples and payload["ocra_processes"]:
                stopped = stop_ocra(payload["ocra_processes"])
                emit("critical_temperature_stop", threshold_c=args.critical_temperature_c, consecutive_samples=consecutive_critical, stopped_pids=stopped, gpu=payload["gpu"], protocol=payload["protocol"])
                consecutive_critical = 0
            elif str(payload["protocol"].get("status", "")).startswith("stopped_") and payload["ocra_processes"]:
                stopped = stop_ocra(payload["ocra_processes"])
                emit("protocol_violation_stop", reason="OCRA protocol reached a terminal stop state", stopped_pids=stopped, protocol=payload["protocol"])
            if args.once:
                return 0
            current = time.monotonic()
            if current - last_full >= args.interval_seconds:
                atomic_json(MONITOR_ROOT / f"snapshot_{time.strftime('%Y%m%dT%H%M%S%z')}.json", {"timestamp": now(), **payload})
                last_full = current
            # Poll process identity at the active cadence even while idle, so a
            # newly started GPU job cannot wait 30 minutes for thermal checks.
            time.sleep(max(15, args.active_poll_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
