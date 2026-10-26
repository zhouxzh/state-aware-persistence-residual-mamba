from __future__ import annotations

import numpy as np

from utils.sapr_mamba.ocra_v1 import (
    OCRA_FEATURE_NAMES,
    OCRA_V1_1_FEATURE_NAMES,
    action_from_probabilities,
    evaluation_set,
    ocra_features,
    ocra_v1_1_features,
    series_id_hash,
    target_action,
    target_action_v1_1,
    target_action_v1_2,
    evaluation_set_v1_1,
    true_label,
)


def test_ocra_features_are_causal_finite_and_have_the_frozen_dimension() -> None:
    history = np.sin(np.arange(384, dtype=np.float64) / 7.0) + np.arange(384, dtype=np.float64) * 0.02
    future_changed = np.concatenate((history, np.full(96, 1_000_000.0)))
    assert np.allclose(ocra_features(history), ocra_features(future_changed[:384]))
    assert ocra_features(history).shape == (len(OCRA_FEATURE_NAMES),)
    assert np.isfinite(ocra_features(history)).all()


def test_v1_1_jump_features_are_causal_and_track_only_historical_jump_recency() -> None:
    history = np.zeros(384, dtype=np.float64)
    history[-96:] = 5.0
    future = np.concatenate((history, np.full(96, -9999.0)))
    features = ocra_v1_1_features(history)
    assert features.shape == (len(OCRA_V1_1_FEATURE_NAMES),)
    assert np.allclose(features, ocra_v1_1_features(future[:384]))
    assert features[-2] > 1.0
    assert 0.0 <= features[-1] <= 1.0


def test_truth_action_mapping_never_opens_unseen_or_variance_only_origins() -> None:
    future = {"mechanism": "future_jump", "change_point": 100}
    assert true_label(future, 52, 96, 12) == "unseen_change"
    assert target_action("future_jump", "unseen_change") == "CLOSED"
    assert target_action("variance_shift", "stable") == "CLOSED"
    assert target_action("visible_level_shift", "visible_change") == "DEFER"
    assert target_action("trend_break", "visible_change") == "OPEN"
    assert evaluation_set("seasonal_change", "visible_change") == "S+"
    assert evaluation_set("random_walk", "stable") == "N8"


def test_v1_1_requires_level_shift_deferral_only_when_the_jump_is_still_visible() -> None:
    assert target_action_v1_1("visible_level_shift", "visible_change", 860, 768, 192) == "DEFER"
    assert evaluation_set_v1_1("visible_level_shift", "visible_change", 860, 768, 192) == "T1-vis"
    assert target_action_v1_1("visible_level_shift", "visible_change", 1100, 768, 192) == "CLOSED"
    assert evaluation_set_v1_1("visible_level_shift", "visible_change", 1100, 768, 192) == "T1-post-observable"


def test_v1_2_limits_level_shift_deferral_to_the_latest_96_points() -> None:
    assert target_action_v1_2("visible_level_shift", "visible_change", 863, 768, 96) == "DEFER"
    assert target_action_v1_2("visible_level_shift", "visible_change", 864, 768, 96) == "DEFER"
    assert target_action_v1_2("visible_level_shift", "visible_change", 865, 768, 96) == "CLOSED"


def test_actions_are_three_state_and_open_has_precedence() -> None:
    actions = action_from_probabilities(
        np.asarray([0.9, 0.1, 0.1]), np.asarray([0.9, 0.9, 0.1]), 0.8, 0.8
    )
    assert actions.tolist() == ["OPEN", "DEFER", "CLOSED"]


def test_series_id_hash_uses_sorted_non_trailing_newline_contract() -> None:
    assert series_id_hash(["b", "a"]) == series_id_hash(["a", "b"])
    assert series_id_hash(["a", "b"]) != series_id_hash(["a", "b", "c"])
