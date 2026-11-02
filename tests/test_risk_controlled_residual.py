from __future__ import annotations

import json

import numpy as np
import pytest

from scripts import risk_controlled_residual as rcr


def test_protocol_has_frozen_384_cell_grid() -> None:
    protocol = rcr.config()
    grid = protocol["grid"]
    assert len(protocol["panels"]) * len(grid["cap_sigma"]) * len(grid["candidate_counts"]) * len(grid["calibration_series_per_group"]) * len(grid["rho"]) == 384
    assert protocol["target_test"]["simultaneous_entries"] == 2048


def test_capped_loss_difference_is_bounded_by_cap() -> None:
    protocol = rcr.config()
    cap = 0.1
    values = rcr.losses(np.asarray([1.0, 0.5, 0.25, -0.125]), cap, rcr.candidate_coefficients(protocol, 16), protocol, repeats=3, n_max=17, rng=np.random.default_rng(17))
    assert np.all(values <= cap + 1e-12)
    assert np.all(values >= -cap - 1e-12)


def test_beta_matches_frozen_simultaneous_formula() -> None:
    observed = rcr.beta(0.25, 16, 4, 0.05, 2000)
    expected = 0.25 * np.sqrt(2.0 * np.log(2.0 * 16 * 4 / 0.05) / 2000.0)
    assert observed == pytest.approx(expected)


def test_all_group_rule_falls_back_and_breaks_ties_by_candidate_id() -> None:
    upper = np.asarray([
        [[-0.1, -0.1], [-0.2, -0.2], [-0.3, -0.3], [-0.4, -0.4]],
        [[0.1, -0.1], [-0.2, -0.2], [-0.3, -0.3], [-0.4, -0.4]],
        [[0.1, 0.1], [-0.2, -0.2], [-0.3, -0.3], [-0.4, -0.4]],
    ])
    selected, worst = rcr.select_candidate(upper)
    assert selected.tolist() == [0, 1, -1]
    assert worst[:2].tolist() == pytest.approx([-0.1, -0.1])
    assert np.isnan(worst[2])


def test_quadrature_production_and_validation_rules_agree() -> None:
    protocol = rcr.config()
    audit = rcr.quadrature_audit(protocol)
    assert audit["status"] == "passed"
    assert audit["maximum_absolute_difference"] <= protocol["truth"]["absolute_tolerance"]


def test_analytic_target_risk_is_cached_by_frozen_cell() -> None:
    protocol = rcr.config()
    theta = np.asarray(protocol["panels"]["BENEFICIAL"], dtype=float)
    rcr.TRUTH_CACHE.clear()
    first = rcr.truth_matrix(protocol, theta, 0.1, 4, 0.05, (32, 32))
    second = rcr.truth_matrix(protocol, theta, 0.1, 4, 0.05, (32, 32))
    assert first is second
    assert first.shape == (4, 4)


def test_target_test_cannot_materialize_before_main(tmp_path, monkeypatch) -> None:
    protocol = rcr.config()
    paths = {name: tmp_path / name for name in ("protocol", "target", "metrics", "reports", "pilot", "chunks", "failures", "monitor", "logs")}
    paths["root"] = tmp_path
    paths["protocol"].mkdir(parents=True)
    paths["target"].mkdir(parents=True)
    (paths["protocol"] / "protocol.json").write_text(json.dumps({"status": "pilot_passed"}), encoding="utf-8")
    monkeypatch.setattr(rcr, "require_sealed", lambda: (protocol, paths))
    with pytest.raises(RuntimeError, match="main grid must complete"):
        rcr.target_test()
    assert not (paths["target"] / "target_test_access.json").exists()
