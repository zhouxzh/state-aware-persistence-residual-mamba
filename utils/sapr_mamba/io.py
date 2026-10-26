"""Filesystem, hashing, configuration, and run-manifest helpers."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
STUDY_VERSION = os.environ.get("SAPR_MAMBA_VERSION", "v1").strip()
_BASE_STUDIES = {"v1", "v2", "v3", "v7", "v8", "sim_v1", "sim_v2", "sim_v3", "sim_v4", "sim_v5", "canonical_v1", "canonical_v2", "bocpd_confirm_v1"}
if STUDY_VERSION not in _BASE_STUDIES and not (STUDY_VERSION.startswith("bocpd_e") and STUDY_VERSION[7:].isdigit()):
    raise ValueError("SAPR_MAMBA_VERSION is not a supported SAPR study namespace")
STUDY_SLUG = f"sapr_mamba_{STUDY_VERSION}"
CONFIG_ROOT = REPO_ROOT / "configs" / STUDY_SLUG
DATA_ROOT = REPO_ROOT / "data" / STUDY_SLUG
RESULT_ROOT = REPO_ROOT / "results" / STUDY_SLUG
RUNLOG_ROOT = REPO_ROOT / "docs" / "current" / "zhong3_runlog" / STUDY_SLUG


def utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        handle.write(canonical_json(payload))
        temporary = Path(handle.name)
    os.replace(temporary, path)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_configs() -> dict[str, dict[str, Any]]:
    names = ("protocol", "synthetic", "real_panels", "model_spec")
    return {name: read_json(CONFIG_ROOT / f"{name}.json") for name in names}


def config_hashes() -> dict[str, str]:
    return {
        path.name: sha256_path(path)
        for path in sorted(CONFIG_ROOT.glob("*.json"))
        if path.name != "protocol.lock.json"
    }


def code_hashes() -> dict[str, str]:
    roots = (
        REPO_ROOT / "model" / "StateAwarePersistenceResidualMamba.py",
        REPO_ROOT / "experiments" / "sapr_mamba",
        REPO_ROOT / "utils" / "sapr_mamba",
    )
    files: list[Path] = []
    for root in roots:
        files.extend([root] if root.is_file() else sorted(root.glob("*.py")))
    return {str(path.relative_to(REPO_ROOT)): sha256_path(path) for path in files}


def command_output(command: list[str]) -> str:
    try:
        return subprocess.check_output(command, cwd=REPO_ROOT, text=True, stderr=subprocess.STDOUT).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        return f"unavailable: {exc}"


def git_state() -> dict[str, str]:
    return {
        "branch": command_output(["git", "branch", "--show-current"]),
        "commit": command_output(["git", "rev-parse", "HEAD"]),
        "status": command_output(["git", "status", "--short", "--untracked-files=all"]),
    }


def write_task_manifest(path: Path, payload: dict[str, Any]) -> None:
    payload = dict(payload)
    payload.setdefault("written_at", utc_now())
    payload.setdefault("config_hashes", config_hashes())
    payload.setdefault("code_hashes", code_hashes())
    payload.setdefault("git", git_state())
    atomic_write_json(path, payload)
