#!/usr/bin/env python
"""Resumable canonical T0-T8 and validation-only BOCPD research controller."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from utils.sapr_mamba.io import atomic_write_json, utc_now

CANONICAL = "canonical_v2"
EXPLORATIONS = tuple(f"bocpd_e{index}" for index in range(1, 6))
STATE = REPO_ROOT / "results" / "sapr_sim_research_controller" / "state.json"


def command(study: str, *arguments: str) -> None:
    environment = {**os.environ, "SAPR_MAMBA_VERSION": study}
    completed = subprocess.run([sys.executable, *arguments], cwd=REPO_ROOT, env=environment, check=False)
    if completed.returncode:
        raise RuntimeError(f"command_failed:{study}:{' '.join(arguments)}")


def payload() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.is_file() else {"created_at": utc_now(), "studies": {}}


def save(value: dict) -> None:
    value["updated_at"] = utc_now()
    atomic_write_json(STATE, value)


def coverage_passed(study: str) -> bool:
    path = REPO_ROOT / "docs" / "current" / f"sapr_{study}_coverage.json"
    return path.is_file() and bool(json.loads(path.read_text(encoding="utf-8")).get("passed"))


def campaign_ok(study: str) -> bool:
    path = REPO_ROOT / "results" / f"sapr_mamba_{study}" / "synthetic" / "campaign_manifest.json"
    return path.is_file() and not json.loads(path.read_text(encoding="utf-8")).get("failures")


def run_study(study: str, exploratory: bool, state: dict) -> bool:
    item = state["studies"].setdefault(study, {"role": "exploratory" if exploratory else "canonical"})
    if item.get("complete"):
        return True
    command(study, "scripts/sapr_sim_v1.py", "--stage", "preflight")
    coverage_path = REPO_ROOT / "docs" / "current" / f"sapr_{study}_coverage.json"
    if coverage_path.is_file() and not coverage_passed(study):
        item.update({"coverage": "failed", "complete": False, "finished_at": utc_now()})
        save(state)
        return False
    if not coverage_passed(study):
        try:
            command(study, "scripts/sapr_sim_v1.py", "--stage", "generate")
        except RuntimeError:
            item.update({"coverage": "failed", "complete": False, "finished_at": utc_now()})
            save(state)
            return False
    if not coverage_passed(study):
        item.update({"coverage": "failed", "complete": False, "finished_at": utc_now()})
        save(state)
        return False
    item["coverage"] = "passed"
    save(state)
    if exploratory:
        command(study, "scripts/sapr_sim_v1.py", "--stage", "validation_detector")
    for attempt in range(1, 3):
        command(study, "scripts/sapr_sim_v1.py", "--stage", "train")
        if campaign_ok(study):
            break
        item["training_retry"] = attempt
        save(state)
    if not campaign_ok(study):
        item.update({"training": "failed", "complete": False, "finished_at": utc_now()})
        save(state)
        return False
    command(study, "scripts/sapr_sim_v1_analyze.py", "--stage", "analyze")
    command(study, "scripts/sapr_sim_v1_analyze.py", "--stage", "verify")
    item.update({"training": "complete", "analysis": "complete", "complete": True, "finished_at": utc_now()})
    save(state)
    return True


def create_confirmation(selected: str) -> None:
    source = REPO_ROOT / "configs" / f"sapr_mamba_{selected}"
    target = REPO_ROOT / "configs" / "sapr_mamba_bocpd_confirm_v1"
    if target.exists():
        return
    target.mkdir(parents=True)
    for name in ("model_spec.json", "protocol.json", "synthetic.json"):
        shutil.copy2(source / name, target / name)
    protocol = json.loads((target / "protocol.json").read_text(encoding="utf-8"))
    protocol.update({"protocol_version": "sapr_sim_bocpd_confirm_v1.0", "status": "frozen_before_generation", "study_role": "independent confirmation selected exclusively from exploration validation diagnostics", "selected_from": selected, "seeds": [20264101, 20264102, 20264103, 20264104, 20264105]})
    synthetic = json.loads((target / "synthetic.json").read_text(encoding="utf-8"))
    synthetic.update({"generator_version": "sapr_sim_bocpd_confirm_v1.0", "generator_seed": 20264100})
    atomic_write_json(target / "protocol.json", protocol)
    atomic_write_json(target / "synthetic.json", synthetic)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-canonical", action="store_true")
    parser.add_argument("--stop-after", choices=("canonical", "exploration", "confirmation"), default="confirmation")
    args = parser.parse_args()
    state = payload()
    if not args.skip_canonical:
        if not run_study(CANONICAL, False, state):
            raise SystemExit("canonical_coverage_or_training_failed")
    if args.stop_after == "canonical":
        return
    for study in EXPLORATIONS:
        run_study(study, True, state)
    available = [study for study in EXPLORATIONS if state["studies"].get(study, {}).get("complete")]
    if not available:
        selection = {
            "status": "no_eligible_candidate",
            "selection_split": "not_run",
            "uses_test_results": False,
            "reason": "All exploration versions stopped before training at their frozen coverage or detector-discrimination gate.",
            "confirmation_started": False,
        }
        output = REPO_ROOT / "reproducibility" / "sapr_bocpd_selection" / "selection_lock.json"
        atomic_write_json(output, selection)
        state.update({"selection": selection, "stage": "complete_no_bocpd_candidate"})
        save(state)
        return
    command("bocpd_e1", "scripts/sapr_sim_bocpd_select.py")
    selection = json.loads((REPO_ROOT / "reproducibility" / "sapr_bocpd_selection" / "selection_lock.json").read_text(encoding="utf-8"))
    if selection["selected_study"] not in available:
        raise SystemExit("selected_study_not_completed")
    state["selection"] = selection
    save(state)
    if args.stop_after == "exploration":
        return
    create_confirmation(str(selection["selected_study"]))
    if not run_study("bocpd_confirm_v1", True, state):
        raise SystemExit("confirmation_coverage_or_training_failed")
    command("bocpd_confirm_v1", "-m", "pytest", "-q", "tests/test_sapr_sim_v1.py", "tests/test_sapr_sim_v1_analysis.py", "tests/test_sapr_mamba_features.py")
    subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=REPO_ROOT, env={key: value for key, value in os.environ.items() if key != "SAPR_MAMBA_VERSION"}, check=True)
    state["stage"] = "complete"
    save(state)


if __name__ == "__main__":
    main()
