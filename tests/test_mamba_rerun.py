"""Contract tests for the active S-only learned-model workflow."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from experiments.financial.evaluation import build_base_args, format_setting
from experiments.financial.mamba_rerun import (
    campaign_plan,
    load_config,
    resolve_scope,
    selection_params,
    stage_tag,
    storage_model_label,
)


ROOT = Path(__file__).resolve().parents[1]


def config_path(release: str) -> Path:
    return ROOT / "configs" / f"financial_s_only_{release}.json"


def scope_args(**overrides) -> Namespace:
    values = {
        "tasks": ["ALL"],
        "models": ["ALL"],
        "horizons": None,
        "seeds": [2023, 2024, 2025, 2026, 2027],
    }
    values.update(overrides)
    return Namespace(**values)


def test_v1_and_v2_have_the_prespecified_s_only_learned_matrix() -> None:
    expected_rows = {"v1": 1320, "v2": 5940}
    for release, expected in expected_rows.items():
        config = load_config(config_path(release))
        manifest = json.loads((ROOT / config["base_protocol"]["training_manifest"]).read_text())
        plan = campaign_plan(
            config,
            sorted(manifest),
            list(config["models"]),
            config["base_protocol"]["horizons"],
            config["base_protocol"]["seeds"],
            manifest,
        )
        assert len(config["models"]) == 11
        assert "RegimeGatedMamba" in config["models"]
        assert "UngatedRegimeLinearMamba" in config["models"]
        assert plan["planned_horizon_runs"] == expected
        assert all(task.endswith("_s") and row["features"] == "S" for task, row in manifest.items())


def test_every_active_model_uses_a_frozen_selection_and_mse_training() -> None:
    for release in ("v1", "v2"):
        config = load_config(config_path(release))
        manifest = json.loads((ROOT / config["base_protocol"]["training_manifest"]).read_text())
        for task in manifest:
            for model_id in config["models"]:
                params, path = selection_params(config, task, model_id)
                assert path.is_file()
                assert params["loss"] == "MSE"
                assert params["horizon_weighting"] == "balanced"
                assert params["seq_len"] > 0


def test_scope_rejects_non_s_task_even_when_a_manifest_is_tampered() -> None:
    config = load_config(config_path("v1"))
    manifest_path = ROOT / config["base_protocol"]["training_manifest"]
    manifest = json.loads(manifest_path.read_text())
    assert all(task.endswith("_s") for task in manifest)
    with pytest.raises(ValueError, match="Unknown task IDs"):
        resolve_scope(config, scope_args(tasks=["financial_cross_asset_ms"]))


def test_compact_storage_labels_cover_the_new_ablation() -> None:
    assert storage_model_label("RegimeGatedMamba") == "rgm"
    assert storage_model_label("UngatedRegimeLinearMamba") == "urgm"
    assert stage_tag("UngatedRegimeLinearMamba", 2027) == "rerun_urgm_s2027"
    args = Namespace(
        require_cuda=False, cpu=True, phase="mamba_rerun",
        storage_model_label=storage_model_label("UngatedRegimeLinearMamba"),
        checkpoints="checkpoints", results_root="results", num_workers=0, seed=2023,
        train_epochs=1, patience=1, tensorboard_dir="tensorboard", gpu=0,
    )
    dataset = {
        "slug": "financial_cross_asset_s", "data": "custom", "root_path": "./data/financial",
        "data_path": "x.csv", "features": "S", "target": "target", "freq": "d",
        "enc_in": 1, "dec_in": 1, "c_out": 1,
    }
    run_args = build_base_args(
        args, dataset, "RegimeGatedMamba",
        {"seq_len": 32, "d_model": 8, "d_ff": 32, "pms_regime_disable_gate": 1},
        252, "rerun_urgm_s2023",
    )
    assert "_urgm_pl252_" in run_args.model_id
    assert len(format_setting(run_args)) < 255
