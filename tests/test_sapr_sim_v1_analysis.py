from __future__ import annotations

import os

import pytest

SIMULATION_VERSION = os.environ.get("SAPR_MAMBA_VERSION")
pytestmark = pytest.mark.skipif(SIMULATION_VERSION not in {"sim_v1", "sim_v2", "sim_v3", "sim_v5", "canonical_v1", "canonical_v2", "bocpd_e1", "bocpd_confirm_v1"}, reason="SAPR simulation tests require an isolated simulation namespace")

if SIMULATION_VERSION in {"sim_v1", "sim_v2", "sim_v3", "sim_v5", "canonical_v1", "canonical_v2", "bocpd_e1", "bocpd_confirm_v1"}:
    from scripts.sapr_sim_v1_analyze import comparison, detector_audit


def _rows() -> list[dict]:
    rows = []
    for seed in (1, 2):
        for series_id, left, right in (("a", 1.0, 2.0), ("b", 3.0, 4.0)):
            for model, rmse in (("M2", left), ("M1", right)):
                rows.append({"group": "T3", "model": model, "seed": seed, "series_id": series_id, "horizon": 12, "rmse": rmse})
    return rows


def test_sim_v1_comparison_bootstraps_over_series_after_seed_averaging() -> None:
    row = comparison(_rows(), "C", "T3", "M2", "M1", 12, 100, relative=False)
    assert row["n"] == 2
    assert row["estimate"] == -1.0
    assert row["ci_high"] < 0.0


def test_sim_v1_detector_audit_separates_generator_labels_from_detector_states() -> None:
    signature = {"series_index": __import__("numpy").array([0, 0, 1]), "true_label": __import__("numpy").array(["stable", "stable", "visible_change"]), "state": __import__("numpy").array([0, 1, 1])}
    rows = detector_audit(signature, [{"mechanism": "stable"}, {"mechanism": "trend_break"}])
    stable = next(row for row in rows if row["mechanism"] == "stable")
    assert stable["detector_stable"] == stable["detector_change"] == 1
