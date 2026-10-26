from __future__ import annotations

import numpy as np

from utils.sapr_mamba.calibration import select_residual_shrinkage, select_validation_candidate


def test_validation_shrinkage_selects_without_test_inputs() -> None:
    baseline = np.array([[0.0], [0.0], [1.0], [1.0]], dtype=float)
    forecast = np.array([[2.0], [2.0], [3.0], [3.0]], dtype=float)
    target = np.array([[0.0], [0.0], [3.0], [3.0]], dtype=float)
    alphas, audit = select_residual_shrinkage(baseline, forecast, target, np.array([0, 0, 1, 1]))
    assert alphas == {0: 0.0, 1: 1.0}
    assert [row["validation_origins"] for row in audit] == [2, 2]


def test_validation_shrinkage_resolves_ties_conservatively() -> None:
    baseline = np.array([[0.0]], dtype=float)
    forecast = np.array([[2.0]], dtype=float)
    target = np.array([[1.0]], dtype=float)
    alphas, _ = select_residual_shrinkage(baseline, forecast, target, np.array([0]), candidates=(0.0, 1.0))
    assert alphas[0] == 0.0


def test_validation_candidate_selection_obeys_predeclared_tie_order() -> None:
    forecasts = {"M0": np.array([[0.0], [0.0]]), "M1": np.array([[2.0], [3.0]])}
    selected, audit = select_validation_candidate(forecasts, np.array([[1.0], [1.0]]), np.array([0, 1]), ("M0", "M1"))
    assert selected == {0: "M0", 1: "M0"}
    assert all(row["selected_model"] == "M0" for row in audit)
