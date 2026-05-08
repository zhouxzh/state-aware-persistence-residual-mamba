import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.optuna.run_dataset_optuna import (
    best_params_payload,
    phase_best_rows,
    replay_rows_from_candidates,
)


def make_result():
    grouped_metrics = {
        "rmse": {"short": 1.0, "middle": 2.0, "long": 3.0, "overall": 2.0},
        "mae": {"short": 0.5, "middle": 1.0, "long": 1.5, "overall": 1.0},
        "rmsse": {"short": 10.0, "middle": 20.0, "long": 30.0, "overall": 20.0},
    }
    return {
        "study_name": "demo_baseline_Model",
        "model": "Model",
        "best_calibration_trial": 2,
        "best_calibration_objective": 7.0,
        "best_candidate": {
            "trial_number": 4,
            "candidate_rank": 1,
            "eval_flag": "val",
            "summary": {"balanced_rmsse": 9.0},
            "params": {"seq_len": 64, "learning_rate": 0.001},
        },
        "final_summary": {
            "available_horizons": [1, 30, 360],
            "balanced_rmsse": 20.0,
            "grouped_metrics": grouped_metrics,
        },
        "final_horizon_metrics": {
            1: {"mae": 0.5, "mse": 1.0, "rmse": 1.0, "mape": 0.1, "mspe": 0.01, "rmsse": 10.0},
            30: {"mae": 1.0, "mse": 4.0, "rmse": 2.0, "mape": 0.2, "mspe": 0.04, "rmsse": 20.0},
            360: {"mae": 1.5, "mse": 9.0, "rmse": 3.0, "mape": 0.3, "mspe": 0.09, "rmsse": 30.0},
        },
        "final_settings": {1: "test_h1", 30: "test_h30", 360: "test_h360"},
    }


def test_replay_rows_are_labeled_as_validation_selection():
    rows = replay_rows_from_candidates(
        "demo",
        "baseline",
        "Model",
        "demo_baseline_Model",
        [
            {
                "trial_number": 4,
                "candidate_rank": 1,
                "eval_flag": "val",
                "summary": {"balanced_rmsse": 9.0},
                "params": {"seq_len": 64},
                "horizon_metrics": {1: {"rmsse": 9.0}},
            }
        ],
    )

    assert rows[0]["eval_flag"] == "val"
    assert rows[0]["balanced_rmsse"] == pytest.approx(9.0)


def test_phase_best_rows_distinguish_validation_selection_from_test_metrics():
    dataset_cfg = {
        "slug": "demo",
        "target": "target",
        "term_groups": {"short": [1], "middle": [30], "long": [360]},
    }

    rows = phase_best_rows(dataset_cfg, "baseline", [make_result()])

    assert rows[0]["selection_eval_flag"] == "val"
    assert rows[0]["selection_balanced_rmsse"] == pytest.approx(9.0)
    assert rows[0]["final_eval_flag"] == "test"
    assert rows[0]["overall_balanced_rmsse"] == pytest.approx(20.0)


def test_best_params_payload_uses_validation_replay_and_final_test_names():
    dataset_cfg = {"slug": "demo"}

    payload = best_params_payload(dataset_cfg, "baseline", [make_result()], [1, 30, 360], [1, 30, 360])
    model_payload = payload["models"]["Model"]

    assert model_payload["selection_eval_flag"] == "val"
    assert model_payload["best_validation_replay_trial"] == 4
    assert model_payload["best_validation_replay_balanced_rmsse"] == pytest.approx(9.0)
    assert model_payload["final_eval_flag"] == "test"
    assert model_payload["final_test_balanced_rmsse"] == pytest.approx(20.0)
