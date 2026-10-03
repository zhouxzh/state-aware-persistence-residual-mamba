from __future__ import annotations

import numpy as np

from utils.sapr_mamba.synthetic import generate_sequence


def test_variance_shift_changes_post_change_innovations_not_pre_change_history() -> None:
    config = {
        "length": 128,
        "seasonal_period": 12,
        "base_process": {
            "ar_coefficient_range": [0.5, 0.5],
            "innovation_std": 1.0,
            "trend_slope_range": [0.0, 0.0],
            "seasonal_amplitude_range": [0.0, 0.0],
            "change_point_range": [64, 64],
        },
    }
    stable, stable_meta = generate_sequence(config, "stable", 0.0, np.random.default_rng(7))
    shifted, shifted_meta = generate_sequence(config, "variance_shift", 3.0, np.random.default_rng(7))
    assert stable_meta["change_point"] == shifted_meta["change_point"] == 64
    assert np.array_equal(stable[:64], shifted[:64])
    assert not np.array_equal(stable[64:], shifted[64:])
