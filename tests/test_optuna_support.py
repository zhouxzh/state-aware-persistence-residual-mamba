import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from utils.optuna_support import (
    load_dataset_manifest,
    require_term_coverage,
    summarize_horizon_metrics,
    term_for_horizon,
)


def write_dataset(tmp_path):
    data_dir = tmp_path / "data" / "Demo"
    data_dir.mkdir(parents=True)
    csv_path = data_dir / "demo.csv"
    csv_path.write_text(
        "date,target\n"
        "2024-01-01,1.0\n"
        "2024-01-02,2.0\n"
        "2024-01-03,3.0\n"
    )
    manifest_path = tmp_path / "optuna_datasets.json"
    manifest_path.write_text(
        json.dumps(
            {
                "demo": {
                    "root_path": "data/Demo",
                    "data_path": "demo.csv",
                    "target": "target",
                    "freq": "d",
                    "features": "S",
                    "horizons": [1, 3, 5, 7, 14, 30, 60, 90, 120, 180, 270, 360],
                    "term_groups": {
                        "short": [1, 3, 5, 7],
                        "middle": [14, 30, 60, 90],
                        "long": [120, 180, 270, 360],
                    },
                }
            }
        )
    )
    return manifest_path


def test_load_dataset_manifest(tmp_path):
    manifest_path = write_dataset(tmp_path)
    manifest = load_dataset_manifest(manifest_path, "demo", tmp_path)
    assert manifest["slug"] == "demo"
    assert manifest["target"] == "target"
    assert manifest["features"] == "S"
    assert Path(manifest["data_file"]).exists()
    assert manifest["horizons"][-1] == 360


def test_term_helpers_and_balanced_rmsse(tmp_path):
    manifest_path = write_dataset(tmp_path)
    manifest = load_dataset_manifest(manifest_path, "demo", tmp_path)

    assert term_for_horizon(7, manifest["term_groups"]) == "short"
    assert term_for_horizon(60, manifest["term_groups"]) == "middle"
    assert term_for_horizon(270, manifest["term_groups"]) == "long"

    require_term_coverage([7, 90, 360], manifest["term_groups"], "Calibration horizons")

    horizon_metrics = {
        7: {"mae": 1.0, "mse": 1.0, "rmse": 1.0, "mape": 0.1, "mspe": 0.01, "rmsse": 2.0},
        90: {"mae": 2.0, "mse": 4.0, "rmse": 2.0, "mape": 0.2, "mspe": 0.04, "rmsse": 4.0},
        360: {"mae": 3.0, "mse": 9.0, "rmse": 3.0, "mape": 0.3, "mspe": 0.09, "rmsse": 8.0},
    }
    summary = summarize_horizon_metrics(horizon_metrics, manifest["term_groups"])

    assert summary["grouped_metrics"]["rmse"]["short"] == pytest.approx(1.0)
    assert summary["grouped_metrics"]["rmse"]["middle"] == pytest.approx(2.0)
    assert summary["grouped_metrics"]["rmse"]["long"] == pytest.approx(3.0)
    assert summary["balanced_rmsse"] == pytest.approx((2.0 + 4.0 + 8.0) / 3.0)


def test_require_term_coverage_raises_on_missing_term(tmp_path):
    manifest_path = write_dataset(tmp_path)
    manifest = load_dataset_manifest(manifest_path, "demo", tmp_path)

    with pytest.raises(ValueError):
        require_term_coverage([7, 90], manifest["term_groups"], "Calibration horizons")
