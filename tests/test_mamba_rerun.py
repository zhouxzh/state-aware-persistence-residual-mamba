"""Checks for the retained five-model Mamba rerun workflow."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from data_provider.data_loader import Dataset_Custom
from experiments.financial.evaluation import build_base_args, format_setting
from experiments.financial.mamba_rerun import campaign_plan, load_config, selection_params, stage_tag, storage_model_label


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "financial_mamba_rerun_v1.json"


def test_full_rerun_configuration_has_five_trainable_mamba_models() -> None:
    config = load_config(CONFIG_PATH)
    assert set(config["models"]) == {
        "RegimeGatedMamba",
        "MultiScalePatchMamba",
        "InvertedMamba",
        "DecompositionMamba",
        "MultiScaleDecompositionMamba",
    }
    manifest = json.loads((ROOT / config["base_protocol"]["training_manifest"]).read_text())
    plan = campaign_plan(
        config,
        sorted(manifest),
        list(config["models"]),
        config["base_protocol"]["horizons"],
        config["base_protocol"]["seeds"],
        manifest,
    )
    assert plan["planned_horizon_runs"] == 1200


def test_every_model_uses_a_frozen_validation_selection() -> None:
    config = load_config(CONFIG_PATH)
    task = "financial_cross_asset_ms"
    for model_id in config["models"]:
        params, path = selection_params(config, task, model_id)
        assert path.is_file()
        assert params["loss"] == "MSE"
        assert params["horizon_weighting"] == "balanced"
        assert params["seq_len"] > 0


def test_baseline_configuration_has_all_retained_reference_models() -> None:
    config = load_config(ROOT / "configs" / "financial_baseline_rerun_v1.json")
    assert set(config["models"]) == {"DLinear", "NLinear", "PatchTST", "TimesNet", "iTransformer"}
    params, path = selection_params(config, "financial_fx_ms", "PatchTST")
    assert path.name == "baseline_best_params.json"
    assert params["patch_len"] > 0
    assert storage_model_label("TimesNet") == "timesnet"
    assert stage_tag("PatchTST", 2023) == "rerun_patchtst_s2023"


def test_compact_storage_label_avoids_long_multiscale_checkpoint_paths() -> None:
    args = Namespace(
        require_cuda=False, cpu=True, phase="mamba_rerun",
        storage_model_label=storage_model_label("MultiScaleDecompositionMamba"),
        checkpoints="checkpoints", results_root="results", num_workers=0, seed=2023,
        train_epochs=1, patience=1, tensorboard_dir="tensorboard", gpu=0,
    )
    dataset = {
        "slug": "financial_cross_asset_ms", "data": "custom", "root_path": "./data/financial",
        "data_path": "x.csv", "features": "MS", "target": "target", "freq": "d",
        "enc_in": 1, "dec_in": 1, "c_out": 1,
    }
    run_args = build_base_args(
        args, dataset, "MultiScaleDecompositionMamba",
        {"seq_len": 32, "d_model": 8, "d_ff": 256}, 252, "rerun_msd_s2023",
    )
    assert "_msd_pl252_" in run_args.model_id
    assert len(format_setting(run_args)) < 255


def test_custom_dataset_returns_exact_forecast_target_dates() -> None:
    dataset = Dataset_Custom(
        root_path=str(ROOT / "data" / "financial" / "processed"),
        data_path="cross_asset.csv",
        flag="test",
        size=[16, 8, 5],
        features="S",
        target="GLD",
        freq="d",
        split_dates={
            "train_end": "2020-12-31",
            "validation_start": "2021-01-01",
            "validation_end": "2022-12-31",
            "test_start": "2023-01-01",
            "test_end": "2026-06-30",
        },
    )
    dates = dataset.forecast_target_dates()
    assert dates.shape == (len(dataset), 5)
    assert dates[0, 0] == dataset.forecast_origin_dates()[0]
    assert dates[-1, -1] == "2026-06-30"
