#!/usr/bin/env python
"""Resume the V3 pipeline after a live real-data run and keep it unattended.

The supervisor is intentionally separate from the training process. It waits
for the exact V3 ``real`` controller to exit, then runs the additive external
panel, analysis, verification, release, and test stages in order. Each stage
is resumable and failures are recorded without preventing later diagnostics.
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

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_ROOT = REPO_ROOT / "results" / "sapr_mamba_v3"
RUNLOG_ROOT = REPO_ROOT / "docs" / "current" / "zhong3_runlog" / "sapr_mamba_v3"
LOCK_PATH = RESULT_ROOT / "autocontinue.lock"
STATE_PATH = RESULT_ROOT / "autocontinue_state.json"
LOG_PATH = RUNLOG_ROOT / "autocontinue.jsonl"


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def write_event(event: str, **fields: object) -> None:
    RUNLOG_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": now(), "event": event, **fields}
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True), flush=True)


def save_state(**fields: object) -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    existing = {}
    if STATE_PATH.is_file():
        try:
            existing = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    existing.update(fields)
    existing["updated_at"] = now()
    temporary = STATE_PATH.with_name(f".{STATE_PATH.name}.tmp")
    temporary.write_text(json.dumps(existing, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, STATE_PATH)


def process_cmdline(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except (FileNotFoundError, PermissionError):
        return ""
    return raw.replace(b"\0", b" ").decode(errors="replace").strip()


def live_real_controller() -> list[tuple[int, str]]:
    matches = []
    for entry in Path("/proc").glob("[0-9]*"):
        try:
            pid = int(entry.name)
        except ValueError:
            continue
        command = process_cmdline(pid)
        if (
            "scripts/sapr_mamba_v3_pipeline.py" in command
            and "--stage real" in command
            and "--stage real_extended" not in command
        ):
            matches.append((pid, command))
    return matches


def task_counts() -> dict[str, int]:
    counts = {"real_complete": 0, "real_failed": 0, "external_complete": 0, "external_failed": 0}
    for path in (RESULT_ROOT / "real").rglob("task_manifest.json") if (RESULT_ROOT / "real").exists() else ():
        try:
            status = json.loads(path.read_text(encoding="utf-8")).get("status")
        except (OSError, json.JSONDecodeError):
            continue
        if path.parent.parent.name in {"solar_10min", "tourism_monthly", "nn5_daily", "m4_monthly"}:
            counts["external_complete" if status == "complete" else "external_failed"] += 1
        else:
            counts["real_complete" if status == "complete" else "real_failed"] += 1
    return counts


def run_stage(stage: str, poll_seconds: int = 30) -> int:
    command = [
        "conda", "run", "--no-capture-output", "-n", "sci-agent",
        "python", "scripts/sapr_mamba_v3_pipeline.py", "--stage", stage, "--max-rounds", "3",
    ]
    stage_log = RUNLOG_ROOT / f"autocontinue_{stage}.log"
    stage_log.parent.mkdir(parents=True, exist_ok=True)
    write_event("stage_started", stage=stage, command=command)
    save_state(current_stage=stage, stage_started_at=now())
    with stage_log.open("a", encoding="utf-8") as output:
        process = subprocess.Popen(command, cwd=REPO_ROOT, env={**os.environ, "SAPR_MAMBA_VERSION": "v3"}, stdout=output, stderr=subprocess.STDOUT, text=True)
        last_report = 0.0
        while process.poll() is None:
            current = time.monotonic()
            if current - last_report >= 1800 or last_report == 0.0:
                counts = task_counts()
                write_event("progress", stage=stage, pid=process.pid, **counts)
                save_state(current_stage=stage, last_progress_at=now(), **counts)
                last_report = current
            time.sleep(poll_seconds)
        returncode = int(process.returncode)
    pipeline_status = "unknown"
    try:
        pipeline = json.loads((RESULT_ROOT / "pipeline_state.json").read_text(encoding="utf-8"))
        pipeline_status = str(pipeline.get("stages", {}).get(stage, {}).get("status", pipeline.get("status", "unknown")))
    except (OSError, json.JSONDecodeError):
        pass
    write_event("stage_finished", stage=stage, returncode=returncode, pipeline_status=pipeline_status, **task_counts())
    save_state(current_stage=None, last_stage=stage, last_returncode=returncode, last_pipeline_status=pipeline_status, last_finished_at=now())
    return returncode


def run_direct(command: list[str]) -> int:
    write_event("direct_command_started", command=command)
    completed = subprocess.run(
        ["conda", "run", "--no-capture-output", "-n", "sci-agent", *command],
        cwd=REPO_ROOT, env={**os.environ, "SAPR_MAMBA_VERSION": "v3"}, check=False,
        text=True,
    )
    write_event("direct_command_finished", command=command, returncode=completed.returncode)
    return int(completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--no-wait", action="store_true", help="run follow-on stages immediately")
    args = parser.parse_args()
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("w", encoding="utf-8") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            write_event("already_running")
            return 0
        write_event("supervisor_started", pid=os.getpid(), **task_counts())
        save_state(status="waiting_for_real", supervisor_pid=os.getpid(), started_at=now(), **task_counts())
        if not args.no_wait:
            last_report = 0.0
            while live_real_controller():
                current = time.monotonic()
                if current - last_report >= 1800 or last_report == 0.0:
                    live = live_real_controller()
                    write_event("waiting", live_pids=[pid for pid, _ in live], **task_counts())
                    save_state(status="waiting_for_real", last_progress_at=now(), **task_counts())
                    last_report = current
                time.sleep(max(5, int(args.poll_seconds)))
        write_event("real_controller_finished", **task_counts())
        save_state(status="running_follow_on", real_finished_at=now(), **task_counts())

        # Continue even when a stage reports limitations; each later stage
        # provides independent diagnostics and may repair missing artifacts.
        for stage in ("real_extended", "analysis", "verify", "release"):
            run_stage(stage, max(5, int(args.poll_seconds)))
            if stage == "analysis":
                # The manuscript renderer is deliberately idempotent and is
                # useful even when an optional analysis command is limited.
                run_direct(["python", "scripts/sapr_mamba_v3_manuscript.py"])
        run_direct(["python", "-m", "pytest", "-q"])
        save_state(status="finished", finished_at=now(), **task_counts())
        write_event("supervisor_finished", **task_counts())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
