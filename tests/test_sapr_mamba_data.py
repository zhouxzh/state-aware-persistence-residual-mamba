from __future__ import annotations

import numpy as np

from utils.sapr_mamba.data import SeriesInfo, WindowDataset, cap_origins_per_series, causal_forward_fill, make_origins


def _info() -> list[SeriesInfo]:
    return [SeriesInfo("example", period=4, train_end=12, valid_end=16, source="test")]


def test_targets_do_not_cross_chronological_split_boundary() -> None:
    values = np.arange(20, dtype=np.float32).reshape(1, -1)
    origins = make_origins(values, _info(), input_length=4, horizon=3, split="validation", stride=1)
    assert origins[:, 1].min() >= 12
    assert origins[:, 1].max() + 3 <= 16


def test_long_missing_gap_remains_ineligible_and_short_gap_is_causal() -> None:
    values = np.array([1.0, np.nan, np.nan, 4.0, np.nan, np.nan, np.nan, 8.0])
    filled, eligible = causal_forward_fill(values, maximum_gap=2)
    assert np.allclose(filled[:4], [1.0, 1.0, 1.0, 4.0])
    assert eligible[:4].all()
    assert not eligible[4:7].any()


def test_shuffle_changes_only_model_feature_pairing_not_state_audit() -> None:
    values = np.stack((np.arange(24), np.arange(24) ** 2)).astype(np.float32)
    infos = [SeriesInfo("a", 4, 12, 18, "test"), SeriesInfo("b", 4, 12, 18, "test")]
    origins = make_origins(values, infos, input_length=4, horizon=2, split="all", stride=2)
    original = WindowDataset(values, infos, origins, 4, 2, 1e-6, 2.5)
    shuffled = WindowDataset(values, infos, origins, 4, 2, 1e-6, 2.5, feature_permutation_seed=9001)
    assert original[0]["state"] == shuffled[0]["state"]
    assert not np.array_equal(original[0]["phi"], shuffled[0]["phi"])


def test_state_shuffle_preserves_audit_state_and_changes_only_gate_input() -> None:
    values = np.stack((np.arange(24), np.arange(24) ** 2)).astype(np.float32)
    infos = [SeriesInfo("a", 4, 12, 18, "test"), SeriesInfo("b", 4, 12, 18, "test")]
    origins = make_origins(values, infos, input_length=4, horizon=2, split="all", stride=2)
    dataset = WindowDataset(values, infos, origins, 4, 2, 1e-6, 2.5, state_permutation_seed=5)
    dataset.audit_state = (np.arange(len(dataset)) % 2).astype(np.int8)
    assert dataset[0]["state"] == dataset.audit_state[0]
    assert any(dataset[index]["gate_state"] != dataset[index]["state"] for index in range(len(dataset)))


def test_cached_features_are_reused_without_changing_audit_values() -> None:
    values = np.arange(24, dtype=np.float32).reshape(1, -1)
    info = [SeriesInfo("a", 4, 12, 18, "test")]
    origins = make_origins(values, info, input_length=4, horizon=2, split="all", stride=2)
    dataset = WindowDataset(values, info, origins, 4, 2, 1e-6, 2.5)
    first, second = dataset[0], dataset[0]
    assert np.array_equal(first["phi"], second["phi"])
    assert first["state"] == second["state"]
    assert first["change_score"] == second["change_score"]


def test_capped_test_origins_remain_within_each_series() -> None:
    origins = np.array([[0, 1], [0, 3], [0, 5], [0, 7], [1, 2], [1, 4], [1, 6]])
    capped = cap_origins_per_series(origins, 2)
    assert list(capped[:, 0]).count(0) == 2
    assert list(capped[:, 0]).count(1) == 2
    assert set(capped[:, 1]).issubset(set(origins[:, 1]))
