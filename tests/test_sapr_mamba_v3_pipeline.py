from __future__ import annotations

import json
import os

os.environ.setdefault("SAPR_MAMBA_VERSION", "v3")

import pytest
import torch

from model.StateAwarePersistenceResidualMamba import MambaResidualModel, build_model
from scripts.sapr_mamba_v3_pipeline import remediation_for, validate_plan
from scripts.sapr_mamba_v3_sources import _parse_tsf, _prepare_panel
from experiments.sapr_mamba.run import _real_panel_definition


def _spec() -> dict:
    return {
        "mamba": {"d_model": 16, "d_state": 4, "d_conv": 2, "expand": 2, "layers": 1, "dropout": 0.0},
        "linear_residual": {"history_projection": 8},
        "dlinear": {"moving_average_kernel": 3},
    }


def test_v3_gate_modes_have_finite_forecasts() -> None:
    if not torch.cuda.is_available():
        pytest.skip("mamba_ssm CUDA kernels require a CUDA runtime for this model test")
    torch.manual_seed(3)
    device = torch.device("cuda")
    x = torch.randn(2, 24, device=device)
    phi = torch.randn(2, 9, device=device)
    for model_id in ("M3", "M3-state-only", "M3-hidden-only", "M3-constant-gate", "M3-no-state-feature"):
        model = build_model(model_id, 6, 9, _spec(), 24, 12).to(device)
        output = model(x, phi)
        assert output["forecast"].shape == (2, 6)
        assert torch.isfinite(output["forecast"]).all()
        assert ((output["gate"] > 0) & (output["gate"] < 1)).all()


def test_v3_plan_has_automatic_remediation_and_source_pool() -> None:
    result = validate_plan()
    assert result["protocol_version"] == "sapr_mamba_v3.0"
    assert result["candidate_sources"] >= 6
    assert result["candidate_domains"] >= 3
    assert result["seed_count"] >= 10
    assert result["errors"] == []


def test_tsf_external_source_parser_preserves_series_units_and_splits(tmp_path) -> None:
    import zipfile

    archive_path = tmp_path / "toy.tsf.zip"
    rows = ["@relation toy", "@attribute series_name string", "@attribute start_timestamp date", "@frequency 1_hour", "@missing false", "@equallength false", "@data"]
    values_a = ",".join(str(i % 24) for i in range(400))
    values_b = ",".join(str((i + 1) % 24) for i in range(420))
    rows.extend([f"A:2000-01-01 00-00-00:{values_a}", f"B:2000-01-01 00-00-00:{values_b}"])
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("toy.tsf", "\n".join(rows) + "\n")

    _, records = _parse_tsf(archive_path)
    assert len(records) == 2
    assert records[0][1].size == 400
    source = {
        "period": 4,
        "input_length": 16,
        "horizons": [1, 2, 4],
        "maximum_gap": 1,
        "minimum_nonmissing_fraction": 0.9,
        "series_cap": 2,
        "minimum_source_series": 2,
        "source_cluster": "toy",
        "domain": "test",
        "external_holdout": True,
        "state_threshold_policy": {
            "source": "selected_series_train_windows_only",
            "quantile": 0.75,
            "minimum": 1.5,
            "maximum": 4.0,
            "minimum_test_series_per_state": 1,
        },
    }
    prepared = _prepare_panel("toy", source, archive_path, tmp_path / "prepared")
    assert prepared["series_count"] == 2
    assert prepared["source_cluster"] == "toy"
    assert prepared["external_holdout"] is True
    assert prepared["threshold_source"] == "selected_series_train_windows_only"
    assert 1.5 <= prepared["change_threshold"] <= 4.0


def test_remediation_never_sets_blocked_and_reduces_oom_batch() -> None:
    state = {"remediation": [], "limitations": []}
    remediation = remediation_for(
        "synthetic",
        {"returncode": 1, "stdout": "", "stderr": "CUDA out of memory"},
        1,
        state,
    )
    assert remediation["action"] == "reduce_batch_with_gradient_accumulation"
    assert all(item.get("status") != "blocked" for item in state.values() if isinstance(item, dict))


def test_v31_amendment_panel_definitions_are_resolvable() -> None:
    assert _real_panel_definition("solar_10min") == (144, 576, [18, 36, 72, 144])
    assert _real_panel_definition("tourism_monthly") == (12, 48, [3, 6, 12])
    assert _real_panel_definition("nn5_daily") == (7, 56, [1, 2, 4, 7])
    assert _real_panel_definition("m4_monthly") == (12, 48, [3, 6, 12])
