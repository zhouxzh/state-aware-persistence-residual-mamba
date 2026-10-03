from __future__ import annotations

import numpy as np

from utils.sapr_mamba.analysis import summarize_predictions


def test_summary_retains_all_and_each_state_rows() -> None:
    rows = summarize_predictions(
        prediction=np.array([[1.0, 2.0], [4.0, 4.0]]),
        target=np.array([[2.0, 2.0], [2.0, 2.0]]),
        state=np.array([0, 1]),
        gate=np.ones((2, 2)),
        residual=np.ones((2, 2)),
        change_scores=np.array([0.1, 3.0]),
        series_indices=np.array([0, 0]),
        series_metadata=[{"series_id": "a", "mechanism": "stable", "strength": 0.0, "training_std": 2.0}],
        model="M0", seed=1, horizons=[2], dataset="synthetic",
    )
    assert {row["state"] for row in rows} == {"all", "stable", "change"}
    overall = next(row for row in rows if row["state"] == "all")
    assert overall["origins"] == 2
    assert overall["mae"] == 1.25
