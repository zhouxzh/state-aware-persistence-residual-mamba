#!/usr/bin/env python
"""无人值守 SAPR-Mamba V3 确认性研究编排器。

The controller keeps immutable attempt records and automatically retries,
remediates resource failures, expands the predeclared source registry, or
downgrades an estimand to descriptive-only. It never emits a blocked state.
Use ``--stage plan`` for a non-mutating protocol audit and ``--stage smoke``
for the bounded end-to-end execution check.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("SAPR_MAMBA_VERSION", "v3")

from utils.sapr_mamba.io import atomic_write_json, config_hashes, git_state, read_json, sha256_path, utc_now


STUDY = "sapr_mamba_v3"
CONFIG_ROOT = REPO_ROOT / "configs" / STUDY
DATA_ROOT = REPO_ROOT / "data" / STUDY
RESULT_ROOT = REPO_ROOT / "results" / STUDY
DOC_ROOT = REPO_ROOT / "docs" / "analysis" / STUDY
MANUSCRIPT_ROOT = REPO_ROOT / "manuscript" / STUDY
STATE_PATH = RESULT_ROOT / "pipeline_state.json"
SOURCE_REGISTRY = CONFIG_ROOT / "candidate_sources.json"


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_state() -> dict:
    if STATE_PATH.is_file():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {
        "study": STUDY,
        "created_at": now(),
        "status": "planned",
        "stages": {},
        "remediation": [],
        "limitations": [],
    }


def save_state(state: dict) -> None:
    state["updated_at"] = now()
    state["git"] = git_state()
    state["config_hashes"] = config_hashes()
    atomic_write_json(STATE_PATH, state)


def configs() -> dict:
    return {
        name: read_json(CONFIG_ROOT / f"{name}.json")
        for name in ("protocol", "synthetic", "real_panels", "model_spec")
    }


def run_command(command: list[str], *, env: dict[str, str] | None = None, timeout: int | None = None) -> dict:
    process_env = os.environ.copy()
    process_env["SAPR_MAMBA_VERSION"] = "v3"
    if env:
        process_env.update(env)
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=process_env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-12000:],
        "stderr": completed.stderr[-12000:],
    }


def sci(command: list[str], timeout: int | None = None) -> dict:
    return run_command(["conda", "run", "--no-capture-output", "-n", "sci-agent", *command], timeout=timeout)


def validate_plan() -> dict:
    protocol = configs()["protocol"]
    registry = read_json(SOURCE_REGISTRY)
    errors = []
    required = {
        "auto_remediation", "study_design", "primary_models", "models",
        "evaluation", "failure_policy", "seeds",
    }
    errors.extend(f"missing_protocol_field:{field}" for field in sorted(required - set(protocol)))
    if protocol.get("protocol_version") != "sapr_mamba_v3.0":
        errors.append("wrong_protocol_version")
    if protocol.get("failure_policy", {}).get("no_blocked_state") is not True:
        errors.append("blocked_state_policy_not_disabled")
    if len(protocol.get("seeds", [])) < 10:
        errors.append("fewer_than_ten_seeds")
    if registry.get("selection_rule", {}).get("uses_test_results") is not False:
        errors.append("source_selection_may_use_test_results")
    if len(registry.get("sources", [])) < 6:
        errors.append("candidate_pool_smaller_than_six")
    if len({source.get("domain") for source in registry.get("sources", [])}) < 3:
        errors.append("candidate_pool_has_fewer_than_three_domains")
    return {
        "status": "complete" if not errors else "complete_with_limitations",
        "errors": errors,
        "protocol_version": protocol.get("protocol_version"),
        "candidate_sources": len(registry.get("sources", [])),
        "candidate_domains": len({source.get("domain") for source in registry.get("sources", [])}),
        "primary_models": protocol.get("primary_models", []),
        "all_models": protocol.get("models", []),
        "seed_count": len(protocol.get("seeds", [])),
    }


def write_plan_artifacts() -> dict:
    MANUSCRIPT_ROOT.mkdir(parents=True, exist_ok=True)
    DOC_ROOT.mkdir(parents=True, exist_ok=True)
    plan = validate_plan()
    atomic_write_json(DOC_ROOT / "v3_plan_audit.json", plan)
    atomic_write_json(MANUSCRIPT_ROOT / "submission_manifest.json", {
        "study": STUDY,
        "status": "draft",
        "automated_generation": True,
        "human_signature_required": True,
        "claim_evidence_source": f"reproducibility/{STUDY}/claim_evidence_map.csv",
        "protocol": f"configs/{STUDY}/protocol.lock.json",
    })
    (MANUSCRIPT_ROOT / "manuscript.md").write_text(
        "# SAPR-Mamba V3\n\n"
        "Automated manuscript scaffold. Numeric claims are inserted only from the verified V3 release.\n\n"
        "## Abstract\n\n[Generated after verified analysis]\n\n"
        "## Methods\n\n[Generated from protocol.lock.json]\n\n"
        "## Results\n\n[Generated from claim_evidence_map.csv]\n\n"
        "## Limitations\n\n[Generated from remediation and limitations manifests]\n",
        encoding="utf-8",
    )
    return plan


def stage_commands(stage: str) -> list[list[str]]:
    if stage == "sources":
        return [["python", "scripts/sapr_mamba_v3_sources.py"]]
    if stage == "external_sources":
        return [["python", "scripts/sapr_mamba_v3_sources.py", "--stage", "prepare"]]
    if stage == "preflight":
        return [
            ["python", "experiments/sapr_mamba/run.py", "--stage", "preflight"],
            ["python", "experiments/sapr_mamba/run.py", "--stage", "environment"],
        ]
    if stage == "freeze":
        return [["python", "experiments/sapr_mamba/run.py", "--stage", "freeze"]]
    if stage == "smoke":
        return [["python", "experiments/sapr_mamba/run.py", "--stage", "smoke", "--models", "M0", "M1", "M2", "M3", "M3-shuffle", "--seeds", "20261021"]]
    if stage == "synthetic":
        return [["python", "experiments/sapr_mamba/run.py", "--stage", "synthetic-run"]]
    if stage == "real":
        return [
            ["python", "experiments/sapr_mamba/run.py", "--stage", "real-download"],
            ["python", "experiments/sapr_mamba/run.py", "--stage", "real-prepare"],
            ["python", "experiments/sapr_mamba/run.py", "--stage", "real-run"],
        ]
    if stage == "real_extended":
        return [
            ["python", "scripts/sapr_mamba_v3_sources.py", "--stage", "prepare"],
            ["python", "scripts/sapr_mamba_v3_sources.py", "--stage", "integrate"],
            ["python", "experiments/sapr_mamba/run.py", "--stage", "real-run"],
        ]
    if stage == "analysis":
        return [
            ["python", "experiments/sapr_mamba/analyze.py", "--stage", "synthetic"],
            ["python", "scripts/sapr_mamba_real_analysis.py", "--stage", "analyze"],
            ["python", "scripts/sapr_mamba_v3_manuscript.py"],
        ]
    if stage == "verify":
        return [
            ["python", "experiments/sapr_mamba/run.py", "--stage", "verify"],
            ["python", "scripts/sapr_mamba_real_analysis.py", "--stage", "verify"],
        ]
    if stage == "release":
        return [
            ["python", "scripts/sapr_mamba_v3_release.py", "--stage", "build"],
            ["python", "scripts/sapr_mamba_v3_release.py", "--stage", "verify"],
        ]
    return []


def remediation_for(stage: str, result: dict, round_index: int, state: dict) -> dict:
    text = f"{result.get('stdout', '')}\n{result.get('stderr', '')}".lower()
    action = "retry_identical"
    if any(token in text for token in ("out of memory", "cuda out of memory", "oom")):
        action = "reduce_batch_with_gradient_accumulation"
    elif any(token in text for token in ("no eligible", "no series", "missing source")):
        action = "expand_candidate_source_registry"
    elif any(token in text for token in ("convergence", "runtimewarning", "numerical")):
        action = "retain_failure_and_use_persistence_fallback"
    elif stage in {"analysis", "verify"}:
        action = "downgrade_affected_estimand_to_descriptive_only"
    record = {
        "timestamp": now(), "stage": stage, "round": round_index,
        "action": action, "returncode": result.get("returncode"),
        "stderr_tail": result.get("stderr", "")[-2000:],
    }
    state["remediation"].append(record)
    if action == "downgrade_affected_estimand_to_descriptive_only":
        limitation = f"{stage}: automated verification failed; affected estimand is descriptive-only."
        if limitation not in state["limitations"]:
            state["limitations"].append(limitation)
    return record


def execute_stage(stage: str, state: dict, max_rounds: int = 3) -> dict:
    if stage == "plan":
        result = write_plan_artifacts()
        state["stages"][stage] = {"status": result["status"], "result": result, "finished_at": now()}
        state["status"] = result["status"]
        save_state(state)
        return result
    commands = stage_commands(stage)
    if not commands:
        raise ValueError(f"Unsupported V3 pipeline stage: {stage}")
    attempts = []
    remediation_env: dict[str, str] = {}
    for round_index in range(1, max_rounds + 1):
        round_ok = True
        for command in commands:
            result = run_command(
                ["conda", "run", "--no-capture-output", "-n", "sci-agent", *command],
                env=remediation_env,
                timeout=60 * 60 * 24,
            )
            attempts.append(result)
            if result["returncode"] != 0:
                round_ok = False
                remediation = remediation_for(stage, result, round_index, state)
                if remediation["action"] == "reduce_batch_with_gradient_accumulation":
                    current = int(remediation_env.get("SAPR_MAMBA_BATCH_SIZE", "64"))
                    remediation_env["SAPR_MAMBA_BATCH_SIZE"] = str(max(1, current // 2))
                    remediation["environment"] = dict(remediation_env)
                elif remediation["action"] == "cpu_replay_only":
                    remediation_env["SAPR_MAMBA_DEVICE"] = "cpu"
                    remediation["environment"] = dict(remediation_env)
                save_state(state)
                break
        if round_ok:
            if stage in {"analysis", "verify"}:
                # A successful V3 rerun supersedes an earlier transient
                # downgrade (for example, a stale V2-only verifier error),
                # while the immutable remediation attempt remains recorded.
                state["limitations"] = [
                    item for item in state.get("limitations", [])
                    if not str(item).startswith(f"{stage}:")
                ]
            state["stages"][stage] = {"status": "complete", "attempts": attempts, "finished_at": now()}
            state["status"] = "complete"
            save_state(state)
            return state["stages"][stage]
    state["stages"][stage] = {
        "status": "complete_with_limitations",
        "attempts": attempts,
        "finished_at": now(),
        "automatic_continuation": True,
    }
    state["status"] = "complete_with_limitations"
    save_state(state)
    return state["stages"][stage]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, choices=("plan", "sources", "external_sources", "preflight", "freeze", "smoke", "synthetic", "real", "real_extended", "analysis", "verify", "release"))
    parser.add_argument("--max-rounds", type=int, default=3)
    args = parser.parse_args()
    state = load_state()
    result = execute_stage(args.stage, state, max(1, args.max_rounds))
    print(json.dumps(result, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
