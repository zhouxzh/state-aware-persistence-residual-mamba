#!/usr/bin/env python
"""Thermal and resource monitor scoped to the Study 3 process namespace."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import signal
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = ROOT / os.environ.get("STUDY3_MONITOR_RUN_ROOT", os.environ.get("STUDY3_RUN_ROOT", "results/study3_v1"))
RUN_ID = os.environ.get("STUDY3_RUN_ID", RUN_ROOT.name)
RUNNER = os.environ.get("STUDY3_RUNNER", "scripts/study3_v1.py")
MONITOR = RUN_ROOT / "monitor"


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def process_environment(pid: int) -> dict[str, str]:
    try:
        payload = Path(f"/proc/{pid}/environ").read_bytes()
    except (FileNotFoundError, PermissionError):
        return {}
    return {key.decode(errors="replace"): value.decode(errors="replace") for item in payload.split(b"\0") if b"=" in item for key, value in (item.split(b"=", 1),)}


def process_command(pid: int) -> str:
    try:
        return Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
    except (FileNotFoundError, PermissionError):
        return ""


def study_processes() -> list[dict]:
    output = []
    for entry in Path("/proc").glob("[0-9]*"):
        pid = int(entry.name)
        command = process_command(pid)
        if RUNNER in command and process_environment(pid).get("STUDY3_RUN_ID") == RUN_ID:
            output.append({"pid": pid, "command": command})
    return output


def gpu_snapshot() -> list[dict]:
    fields = "index,name,temperature.gpu,power.draw,power.limit,memory.used,memory.total,utilization.gpu,utilization.memory,fan.speed"
    result = subprocess.run(["nvidia-smi", f"--query-gpu={fields}", "--format=csv,noheader,nounits"], text=True, capture_output=True, check=False)
    if result.returncode:
        return [{"unavailable": result.stderr.strip() or result.stdout.strip()}]
    names = ("index", "name", "temperature_c", "power_w", "power_limit_w", "memory_used_mib", "memory_total_mib", "utilization_gpu_pct", "utilization_memory_pct", "fan_pct")
    return [dict(zip(names, (value.strip() for value in line.split(",")), strict=True)) for line in result.stdout.splitlines()]


def host_snapshot() -> dict:
    memory = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        key, value = line.split(":", 1)
        memory[key] = int(value.strip().split()[0]) * 1024
    disk = shutil.disk_usage(ROOT)
    return {"load_average": list(os.getloadavg()), "memory": {"total_bytes": memory["MemTotal"], "available_bytes": memory["MemAvailable"], "swap_free_bytes": memory.get("SwapFree", 0)}, "disk": {"total_bytes": disk.total, "used_bytes": disk.used, "free_bytes": disk.free}}


def protocol_snapshot() -> dict:
    protocol, gate, ledger = RUN_ROOT / "protocol" / "protocol.json", RUN_ROOT / "protocol" / "release_gate.json", RUN_ROOT / "protocol" / "test_access_ledger.json"
    if not protocol.is_file():
        return {"status": "not_sealed", "test_numeric_materialized": False}
    payload = json.loads(protocol.read_text(encoding="utf-8"))
    return {"status": payload.get("status"), "release_gate": json.loads(gate.read_text(encoding="utf-8")).get("status") if gate.is_file() else "not_run", "test_access": json.loads(ledger.read_text(encoding="utf-8")).get("status") if ledger.is_file() else "locked", "test_numeric_materialized": (RUN_ROOT / "data" / "test.npz").exists()}


def experiment_snapshot() -> dict:
    statuses, invalid = Counter(), []
    for path in (RUN_ROOT / "bundles").glob("*/manifest.json"):
        try:
            statuses[str(json.loads(path.read_text(encoding="utf-8")).get("status", "unknown"))] += 1
        except (OSError, json.JSONDecodeError):
            invalid.append(str(path.relative_to(RUN_ROOT)))
    failures = sorted(str(path.relative_to(RUN_ROOT)) for path in (RUN_ROOT / "failures").glob("*.json"))
    return {"bundle_statuses": dict(statuses), "failure_files": failures, "invalid_manifests": invalid}


def emit(event: str, payload: dict) -> None:
    MONITOR.mkdir(parents=True, exist_ok=True)
    entry = {"timestamp": now(), "event": event, **payload}
    with (MONITOR / "events.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(entry, ensure_ascii=True, sort_keys=True) + "\n")
    write_json(MONITOR / "state.json", entry)
    print(json.dumps(entry, ensure_ascii=True, sort_keys=True), flush=True)


def temperatures(gpus: list[dict]) -> list[float]:
    values = []
    for gpu in gpus:
        try:
            values.append(float(gpu["temperature_c"]))
        except (KeyError, TypeError, ValueError):
            pass
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval-seconds", type=int, default=1800)
    parser.add_argument("--active-poll-seconds", type=int, default=60)
    parser.add_argument("--warning-temperature-c", type=float, default=80.0)
    parser.add_argument("--critical-temperature-c", type=float, default=85.0)
    parser.add_argument("--critical-samples", type=int, default=3)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.interval_seconds < 60 or args.active_poll_seconds < 15 or args.critical_samples < 1:
        raise ValueError("unsafe monitor interval")
    MONITOR.mkdir(parents=True, exist_ok=True)
    with (MONITOR / "monitor.lock").open("w", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        emit("monitor_started", {"run_id": RUN_ID, "interval_seconds": args.interval_seconds, "active_poll_seconds": args.active_poll_seconds, "warning_temperature_c": args.warning_temperature_c, "critical_temperature_c": args.critical_temperature_c})
        last_full, critical = 0.0, 0
        while True:
            gpus = gpu_snapshot()
            thermal = temperatures(gpus)
            critical = critical + 1 if thermal and max(thermal) >= args.critical_temperature_c else 0
            payload = {"run_id": RUN_ID, "study_processes": study_processes(), "gpu": gpus, "host": host_snapshot(), "protocol": protocol_snapshot(), "experiment": experiment_snapshot(), "critical_temperature_samples": critical}
            if thermal and max(thermal) >= args.warning_temperature_c:
                event = "temperature_warning"
            elif str(payload["protocol"]["status"]).startswith("stopped_"):
                event = "protocol_stopped"
            else:
                event = "health_snapshot"
            emit(event, payload)
            if critical >= args.critical_samples and payload["study_processes"]:
                stopped = []
                for process in payload["study_processes"]:
                    try:
                        os.kill(int(process["pid"]), signal.SIGTERM); stopped.append(int(process["pid"]))
                    except ProcessLookupError:
                        pass
                emit("critical_temperature_stop", {"run_id": RUN_ID, "stopped_pids": stopped, "critical_temperature_c": args.critical_temperature_c, "consecutive_samples": critical})
                critical = 0
            if args.once:
                return
            if time.monotonic() - last_full >= args.interval_seconds:
                write_json(MONITOR / f"snapshot_{time.strftime('%Y%m%dT%H%M%S%z')}.json", {"timestamp": now(), **payload})
                last_full = time.monotonic()
            time.sleep(max(15, args.active_poll_seconds))


if __name__ == "__main__":
    main()
