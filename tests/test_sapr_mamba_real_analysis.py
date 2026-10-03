from __future__ import annotations

from scripts.sapr_mamba_real_analysis import expected_tasks, metric_rows_match, panel_source
from utils.sapr_mamba.analysis import METRIC_COLUMNS


def test_real_task_matrix_reconstructs_frozen_v2_count_and_ett_cluster() -> None:
    protocol = {
        "models": ["M0", "M1", "M2", "M3", "M3-shuffle"],
        "seeds": [1, 2, 3, 4, 5],
        "real_seed_policy": {
            "five_seeds_for": ["M1", "M2", "M3", "M3-shuffle", "DLinear"],
            "single_deterministic_seed": 1,
        },
    }
    prepared = {"panels": [{"panel_id": panel} for panel in (
        "electricity", "beijing_air_quality", "ett_ETTh1", "ett_ETTh2", "ett_ETTm1", "ett_ETTm2",
    )]}
    tasks = expected_tasks(protocol, prepared)
    assert len(tasks) == 180
    assert len({(item["dataset"], item["model"], item["seed"]) for item in tasks}) == 180
    assert panel_source("ett_ETTm1") == "ett"
    assert sum(item["model"] == "M3" for item in tasks) == 30
    assert sum(item["model"] == "M0" for item in tasks) == 6


def test_metric_recompute_comparison_rejects_numeric_change() -> None:
    expected = {field: 1.0 for field in METRIC_COLUMNS}
    expected.update({
        "dataset": "example", "series_id": "one", "mechanism": "real", "strength": float("nan"),
        "model": "M0", "seed": 1, "horizon": 2, "state": "all", "origins": 3, "points": 6,
    })
    observed = {field: str(value) for field, value in expected.items()}
    observed["strength"] = "nan"
    assert metric_rows_match([expected], [observed]) == (True, "")
    observed["rmse"] = "1.5"
    assert metric_rows_match([expected], [observed]) == (False, "value_mismatch:rmse")
