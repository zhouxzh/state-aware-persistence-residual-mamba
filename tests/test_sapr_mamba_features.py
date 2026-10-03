from __future__ import annotations

import numpy as np

from utils.sapr_mamba.features import FEATURE_NAMES, causal_features, state_label


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
