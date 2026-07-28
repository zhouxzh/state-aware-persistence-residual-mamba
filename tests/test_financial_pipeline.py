from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd

from data_provider.data_loader import Dataset_Custom
from experiments.exp_long_term_forecasting import Exp_Long_Term_Forecast
from scripts.optuna.run_dataset_optuna import (
    model_params_feasibility_error,
    prepare_study_resume,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = REPO_ROOT / "configs" / "financial_benchmark.json"
DATA_ROOT = REPO_ROOT / "data" / "financial"
TRAINING_MANIFEST = DATA_ROOT / "manifests" / "training_datasets.json"
QUALITY_REPORT = DATA_ROOT / "manifests" / "quality_report.json"
DOWNLOAD_MANIFEST = DATA_ROOT / "manifests" / "download_manifest.json"
SELECTION_DIAGNOSTICS = DATA_ROOT / "manifests" / "nonstationarity_diagnostics_selection_safe.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class FinancialPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        cls.training = json.loads(TRAINING_MANIFEST.read_text(encoding="utf-8"))
        cls.quality = json.loads(QUALITY_REPORT.read_text(encoding="utf-8"))

    def test_frozen_task_matrix(self) -> None:
        expected = {
            f"financial_{dataset}_{mode}"
            for dataset in ("fx", "yields", "cross_asset", "crypto")
            for mode in ("s", "ms")
        }
        self.assertEqual(set(self.training), expected)
        self.assertEqual(self.protocol["horizons"], [1, 5, 20, 60, 120, 252])
        self.assertEqual(self.protocol["final_seeds"], [2023, 2024, 2025, 2026, 2027])
        protocol_sha256 = sha256(PROTOCOL_PATH)
        for config in self.training.values():
            self.assertEqual(config["protocol_sha256"], protocol_sha256)

    def test_download_manifest_and_binance_checksums(self) -> None:
        manifest = json.loads(DOWNLOAD_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["protocol_version"], self.protocol["protocol_version"])
        self.assertEqual(manifest["protocol_sha256"], sha256(PROTOCOL_PATH))
        self.assertEqual(manifest["path_base"], "data/financial")
        self.assertEqual(manifest["record_count"], len(manifest["records"]))
        self.assertEqual(manifest["record_count"], 846)
        source_ids = [record["source_id"] for record in manifest["records"]]
        self.assertEqual(len(source_ids), len(set(source_ids)))
        path_base = REPO_ROOT / manifest["path_base"]
        for record in manifest["records"]:
            source_path = path_base / record["path"]
            self.assertTrue(source_path.is_file(), source_path)
            self.assertEqual(source_path.stat().st_size, record["bytes"], source_path)
            self.assertEqual(sha256(source_path), record["sha256"], source_path)
        zip_records = [
            record for record in manifest["records"]
            if record["path"].endswith(".zip")
        ]
        checksum_records = [
            record for record in manifest["records"]
            if record["path"].endswith(".CHECKSUM")
        ]
        self.assertEqual(len(zip_records), 416)
        self.assertEqual(len(checksum_records), 416)

    def test_processed_files_match_manifest_hashes_and_target_order(self) -> None:
        for task_id, config in self.training.items():
            path = REPO_ROOT / config["root_path"] / config["data_path"]
            self.assertEqual(sha256(path), config["data_sha256"], task_id)
            columns = pd.read_csv(path, nrows=1).columns.tolist()
            self.assertEqual(columns[0], "date", task_id)
            self.assertEqual(columns[-1], config["target"], task_id)

    def test_quality_boundaries_and_gaps(self) -> None:
        quality = {row["dataset"]: row for row in self.quality["datasets"]}
        self.assertEqual(set(quality), {"fx", "yields", "cross_asset", "crypto"})
        self.assertEqual(quality["yields"]["start"], "2006-02-09")
        for name, record in quality.items():
            self.assertEqual(record["missing_cells"], 0, name)
            self.assertEqual(record["duplicate_dates"], 0, name)
            self.assertGreater(record["split_counts"]["test"], 252, name)
        self.assertEqual(quality["crypto"]["maximum_calendar_gap_days"], 1)

    def test_selection_diagnostics_do_not_read_test_targets(self) -> None:
        diagnostics = json.loads(SELECTION_DIAGNOSTICS.read_text(encoding="utf-8"))
        self.assertEqual(diagnostics["protocol_version"], self.protocol["protocol_version"])
        self.assertEqual(diagnostics["protocol_sha256"], sha256(PROTOCOL_PATH))
        self.assertEqual(diagnostics["scope"], "train_validation")
        self.assertFalse(diagnostics["test_targets_read"])
        self.assertEqual({record["dataset"] for record in diagnostics["records"]}, {
            "fx", "yields", "cross_asset", "crypto"
        })
        for record in diagnostics["records"]:
            self.assertFalse(any(key.startswith("test_") for key in record), record["dataset"])

    def test_pms_patch_layout_feasibility_guard(self) -> None:
        invalid = {
            "seq_len": 32,
            "ms_scales": [1, 2, 4, 8],
            "patch_len": 16,
            "stride": 8,
        }
        valid = {
            "seq_len": 16,
            "ms_scales": [1, 2, 4, 8],
            "patch_len": 8,
            "stride": 8,
        }
        self.assertIn(
            "infeasible PMS patch layout",
            model_params_feasibility_error("PMS_Mamba-PD", invalid),
        )
        self.assertIsNone(model_params_feasibility_error("PMS_Mamba-PD", valid))
        self.assertIsNone(model_params_feasibility_error("S_Mamba", invalid))

    def test_interrupted_optuna_trial_does_not_consume_budget(self) -> None:
        import optuna

        study = optuna.create_study(direction="minimize")
        interrupted = study.ask()

        remaining = prepare_study_resume(study, optuna, trials_target=3)

        trials = study.get_trials(deepcopy=False)
        self.assertEqual(trials[0].number, interrupted.number)
        self.assertEqual(trials[0].state, optuna.trial.TrialState.FAIL)
        self.assertIn("interrupted process", trials[0].user_attrs["error"])
        self.assertEqual(remaining, 3)

    def test_gpu_thermal_guard_waits_for_resume_temperature(self) -> None:
        experiment = Exp_Long_Term_Forecast.__new__(Exp_Long_Term_Forecast)
        experiment.args = SimpleNamespace(
            thermal_guard_temp=85,
            thermal_resume_temp=75,
            thermal_poll_seconds=1.0,
            use_gpu=True,
            gpu=0,
        )
        readings = [
            SimpleNamespace(stdout="86\n"),
            SimpleNamespace(stdout="74\n"),
        ]

        with patch(
            "experiments.exp_long_term_forecasting.subprocess.run",
            side_effect=readings,
        ) as query, patch("experiments.exp_long_term_forecasting.time.sleep") as sleep:
            experiment._wait_for_thermal_resume()

        self.assertEqual(query.call_count, 2)
        sleep.assert_called_once_with(1.0)

    def test_gpu_thermal_guard_checks_at_batch_interval(self) -> None:
        experiment = Exp_Long_Term_Forecast.__new__(Exp_Long_Term_Forecast)
        experiment.args = SimpleNamespace(thermal_check_batches=5)
        experiment._wait_for_thermal_resume = Mock()

        for batch_index in range(12):
            experiment._maybe_wait_for_thermal_resume(batch_index)

        self.assertEqual(experiment._wait_for_thermal_resume.call_count, 3)

    def test_explicit_splits_scaling_origins_and_ms_inverse(self) -> None:
        quality = {row["dataset"]: row for row in self.quality["datasets"]}
        for task_id, config in self.training.items():
            path = REPO_ROOT / config["root_path"] / config["data_path"]
            frame = pd.read_csv(path)
            dataset_name = task_id.removeprefix("financial_").removesuffix("_s").removesuffix("_ms")
            features = config["features"]
            selected_columns = [config["target"]] if features == "S" else list(frame.columns[1:])
            train_frame = frame[pd.to_datetime(frame["date"]) <= pd.Timestamp("2020-12-31")]
            expected_mean = train_frame[selected_columns].to_numpy(dtype=float).mean(axis=0)

            test_set = Dataset_Custom(
                root_path=str(path.parent),
                data_path=path.name,
                flag="test",
                size=[30, 15, 5],
                features=features,
                target=config["target"],
                timeenc=1,
                freq="d",
                split_dates=config["split_dates"],
            )
            np.testing.assert_allclose(test_set.scaler.mean_, expected_mean, rtol=0, atol=1e-10)
            expected_length = quality[dataset_name]["split_counts"]["test"] - 5 + 1
            self.assertEqual(len(test_set), expected_length, task_id)
            origins = test_set.forecast_origin_dates()
            self.assertEqual(len(origins), expected_length, task_id)
            self.assertEqual(origins.dtype.kind, "U", task_id)
            self.assertGreaterEqual(origins[0], "2023-01-01", task_id)
            self.assertLessEqual(origins[-1], "2026-06-30", task_id)

            if features == "MS":
                target_scaled = test_set.data_x[:10, -1:].copy()
                restored = test_set.inverse_transform_target(target_scaled)
                self.assertEqual(restored.shape, target_scaled.shape)
                self.assertTrue(np.isfinite(restored).all())


if __name__ == "__main__":
    unittest.main()
