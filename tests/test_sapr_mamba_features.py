from __future__ import annotations

import numpy as np

from utils.sapr_mamba.features import FEATURE_NAMES, ar_residual_change_score, bocpd_change_posterior, causal_features, state_label, two_window_change_score


def test_future_values_do_not_change_causal_features() -> None:
    prefix = np.linspace(-2.0, 3.0, 384, dtype=np.float64)
    first = np.concatenate((prefix, np.zeros(96)))
    second = np.concatenate((prefix, np.linspace(100.0, -100.0, 96)))
    assert np.allclose(causal_features(first[:384], 96), causal_features(second[:384], 96))


def test_constant_history_has_finite_features_and_stable_label() -> None:
    phi = causal_features(np.ones(384), 96)
    label, score = state_label(phi, 2.5)
    assert phi.shape == (len(FEATURE_NAMES),)
    assert np.isfinite(phi).all()
    assert label == "stable"
    assert score == 0.0


def test_new_change_scores_are_causal_and_finite() -> None:
    prefix = np.sin(np.arange(384, dtype=np.float64) / 9.0) + np.arange(384, dtype=np.float64) * 0.01
    changed_future = np.concatenate((prefix, np.full(96, 1000.0)))
    for scorer in (two_window_change_score, ar_residual_change_score):
        first = scorer(prefix, 48)
        second = scorer(changed_future[:384], 48)
        assert np.isfinite(first)
        assert first == second


def test_bocpd_posterior_is_causal_and_bounded() -> None:
    prefix = np.sin(np.arange(96, dtype=np.float64) / 7.0)
    future = np.concatenate((prefix, np.full(96, 1_000.0)))
    first = bocpd_change_posterior(prefix, max_run_length=24, lookback=64, input_mode="difference")
    second = bocpd_change_posterior(future[:96], max_run_length=24, lookback=64, input_mode="difference")
    assert 0.0 <= first <= 1.0
    assert first == second
