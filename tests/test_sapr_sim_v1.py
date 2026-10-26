from __future__ import annotations

import os
import json
from pathlib import Path

import pytest

SIMULATION_VERSION = os.environ.get("SAPR_MAMBA_VERSION")
pytestmark = pytest.mark.skipif(SIMULATION_VERSION not in {"sim_v1", "sim_v2", "sim_v3", "sim_v5", "canonical_v1", "canonical_v2", "bocpd_e1", "bocpd_confirm_v1"}, reason="SAPR simulation tests require an isolated simulation namespace")

if SIMULATION_VERSION in {"sim_v1", "sim_v2", "sim_v3", "sim_v5", "canonical_v1", "canonical_v2", "bocpd_e1", "bocpd_confirm_v1"}:
    import numpy as np
    import torch

    from scripts.sapr_sim_v1 import REPO_ROOT, TYPES, collect, cfg, dataset, generate_one, true_label
    from model.StateAwarePersistenceResidualMamba import PersistenceModel


def test_sim_v1_config_covers_all_frozen_types_and_oversamples_stable_controls() -> None:
    settings = cfg("synthetic")
    mechanisms = tuple(settings["mechanisms"])
    assert mechanisms[:len(TYPES)] == TYPES
    assert set(mechanisms[len(TYPES):]) <= {"gradual_drift", "weak_change"}
    for mechanism in ("stable", "stable_season"):
        assert settings["mechanism_split_overrides"][mechanism] == {"train": 300, "validation": 100, "test": 200}


def test_sim_v1_true_labels_keep_future_events_unseen_and_trend_visible() -> None:
    delay = 12
    future = {"mechanism": "future_jump", "change_point": 100}
    trend = {"mechanism": "continuing_trend", "change_point": 0}
    level = {"mechanism": "visible_level_shift", "change_point": 100}
    assert true_label(future, 52, 48, delay) == "stable"
    assert true_label(future, 53, 48, delay) == "unseen_change"
    assert true_label(future, 100, 48, delay) == "unseen_change"
    assert true_label(future, 101, 48, delay) == "stable"
    assert true_label(trend, 48, 96, delay) == "visible_change"
    assert true_label(level, 111, 96, delay) == "stable"
    assert true_label(level, 112, 96, delay) == "visible_change"


def test_sim_v1_prediction_collection_retains_recomputable_label_and_detector_arrays() -> None:
    if not (REPO_ROOT / "data" / f"sapr_mamba_{SIMULATION_VERSION}" / "synthetic" / "test.npz").is_file():
        pytest.skip("simulation data have not been generated for this isolated namespace")
    settings = cfg("synthetic")
    threshold = 3.0
    ds, _, labels = dataset("test", threshold, settings)
    subset = torch.utils.data.Subset(ds, range(3))
    arrays = collect(PersistenceModel(int(settings["maximum_horizon"])), subset, torch.device("cpu"), 1, labels[:3])
    required = {"prediction", "target", "gate", "residual", "state", "change_score", "series_index", "origin", "phi", "true_label"}
    assert required <= set(arrays)
    assert arrays["prediction"].shape == arrays["target"].shape == (3, int(settings["maximum_horizon"]))
    assert arrays["phi"].shape[0] == arrays["true_label"].shape[0] == 3
    assert np.all(np.isfinite(arrays["prediction"]))


def test_sim_v2_balances_future_jump_direction_independently_of_history() -> None:
    settings = json.loads((REPO_ROOT / "configs" / "sapr_mamba_sim_v2" / "synthetic.json").read_text(encoding="utf-8"))
    directions = []
    for index in range(10):
        _, record = generate_one("future_jump", index, "test", settings, np.random.default_rng(100 + index))
        directions.append(record["future_jump_direction"])
    assert directions.count(-1.0) == directions.count(1.0) == 5


def test_sim_v3_future_jump_uses_random_walk_baseline() -> None:
    settings = json.loads((REPO_ROOT / "configs" / "sapr_mamba_sim_v3" / "synthetic.json").read_text(encoding="utf-8"))
    values, record = generate_one("future_jump", 1, "test", settings, np.random.default_rng(9))
    cp = int(record["change_point"])
    # Before its unseen jump, T2 has independent random-walk increments rather than an exploitable AR mean-reversion path.
    increments = np.diff(values[:cp])
    assert abs(float(np.corrcoef(increments[:-1], increments[1:])[0, 1])) < 0.2


def test_sim_v5_freezes_a_causal_prefix_before_evaluation_origins() -> None:
    settings = json.loads((REPO_ROOT / "configs" / "sapr_mamba_sim_v5" / "synthetic.json").read_text(encoding="utf-8"))
    protocol = json.loads((REPO_ROOT / "configs" / "sapr_mamba_sim_v5" / "protocol.json").read_text(encoding="utf-8"))
    policy = protocol["state_threshold"]
    assert settings["state_score_mode"] == "ar_residual"
    assert int(policy["calibration_end"]) < int(settings["evaluation_origin_start"])


def test_canonical_configuration_retains_all_question_types_and_diagnostics() -> None:
    settings = json.loads((REPO_ROOT / "configs" / "sapr_mamba_canonical_v1" / "synthetic.json").read_text(encoding="utf-8"))
    assert set(TYPES) <= set(settings["mechanisms"])
    assert {"gradual_drift", "weak_change"} == set(settings["diagnostic_mechanisms"])
