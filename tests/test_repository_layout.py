"""Regression checks for the historical and current public repository layouts."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_scripts_are_flat_and_complete() -> None:
    scripts = ROOT / "scripts"
    required = {
        "analyze.py",
        "data.py",
        "evaluate.py",
        "reproduce.py",
    }
    assert required <= {path.name for path in scripts.glob("*.py")}
    assert all(path.name.startswith("sapr_mamba_") for path in scripts.glob("sapr_mamba_*.py"))
    assert not (scripts / "financial").exists()
    assert not (scripts / "evaluation").exists()
    assert not (scripts / "publication").exists()


def test_active_financial_workflow_has_no_parallel_legacy_entrypoint() -> None:
    assert (ROOT / "experiments" / "financial" / "s_only.py").is_file()
    assert (ROOT / "experiments" / "financial" / "deterministic.py").is_file()
    assert not (ROOT / "experiments" / "financial" / "reference.py").exists()
    assert not (ROOT / "experiments" / "financial" / "reproduce.py").exists()
    assert not (ROOT / "reproducibility" / "financial_reference_evaluation_v1").exists()


def test_active_data_scope_is_financial_only() -> None:
    active_directories = {path.name for path in (ROOT / "data").iterdir() if path.is_dir()}
    assert "sapr_mamba_v3" in active_directories
    assert active_directories <= {"financial", "sapr_mamba_v1", "sapr_mamba_v2", "sapr_mamba_v3", "sapr_mamba_v7", "sapr_mamba_v8", "sapr_mamba_sim_v1", "sapr_mamba_sim_v2", "sapr_mamba_sim_v3", "sapr_mamba_sim_v4", "sapr_mamba_sim_v5", "sapr_mamba_canonical_v1", "sapr_mamba_canonical_v2", "sapr_mamba_bocpd_e1", "sapr_mamba_bocpd_e2", "sapr_mamba_bocpd_e3", "sapr_mamba_bocpd_e4", "sapr_mamba_bocpd_e5", "sapr_mamba_bocpd_confirm_v1"}
