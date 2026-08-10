"""Regression checks for the compact public repository layout."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_scripts_are_flat_and_complete() -> None:
    scripts = ROOT / "scripts"
    assert {path.name for path in scripts.glob("*.py")} == {
        "analyze.py",
        "data.py",
        "evaluate.py",
        "reproduce.py",
    }
    assert not (scripts / "financial").exists()
    assert not (scripts / "evaluation").exists()
    assert not (scripts / "publication").exists()


def test_financial_workflow_uses_existing_source_roots() -> None:
    assert (ROOT / "experiments" / "financial" / "reference.py").is_file()
    assert (ROOT / "experiments" / "financial" / "reproduce.py").is_file()
    assert (ROOT / "utils" / "financial" / "metrics.py").is_file()
    assert not (ROOT / "pms_mamba").exists()


def test_active_data_scope_is_financial_only() -> None:
    active_directories = {
        path.name for path in (ROOT / "data").iterdir() if path.is_dir()
    }
    assert active_directories == {"financial"}
