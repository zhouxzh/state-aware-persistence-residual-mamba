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
from experiments.exp_long_term_forecasting import (
    Exp_Long_Term_Forecast,
    HorizonWeightedMSELoss,
)
from layers.NonStationaryGate import NonStationaryGate
from model.PMS_Mamba import Model as PMSMambaModel, PersistenceChangeGate
from scripts.optuna.run_dataset_optuna import (
    model_params_feasibility_error,
    prepare_study_resume,
    sample_v4_fast_mamba_params,
)
from scripts.financial.run_pms_v3 import adaptive_external_batch_size, evaluate_runtime_gate


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = REPO_ROOT / "configs" / "financial_benchmark.json"
DATA_ROOT = REPO_ROOT / "data" / "financial"
TRAINING_MANIFEST = DATA_ROOT / "manifests" / "training_datasets.json"
QUALITY_REPORT = DATA_ROOT / "manifests" / "quality_report.json"
DOWNLOAD_MANIFEST = DATA_ROOT / "manifests" / "download_manifest.json"
SELECTION_DIAGNOSTICS = DATA_ROOT / "manifests" / "nonstationarity_diagnostics_selection_safe.json"
V3_PROTOCOL_PATH = REPO_ROOT / "configs" / "pms_mamba_v3.json"
V3_EXTERNAL_TASKS = (
    REPO_ROOT
    / "reproducibility"
    / "nonstationary_analysis_v3"
    / "protocol"
    / "external_tasks.json"
)


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

    def test_horizon_weighted_mse_is_scale_invariant_when_normalized(self) -> None:
        import torch

        prediction = torch.tensor([[[1.0], [2.0], [4.0]]])
        target = torch.zeros_like(prediction)
        scale = torch.tensor([[[2.0]]])
        criterion = HorizonWeightedMSELoss(normalized=True, horizon_weighting="balanced")

        first = criterion(prediction, target, scale=scale)
        second = criterion(prediction * 5.0, target, scale=scale * 5.0)

        self.assertAlmostEqual(float(first), float(second), places=7)

    def test_long_horizon_weighting_penalizes_late_errors_more(self) -> None:
        import torch

        target = torch.zeros((1, 3, 1))
        early_error = torch.tensor([[[1.0], [0.0], [0.0]]])
        late_error = torch.tensor([[[0.0], [0.0], [1.0]]])
        criterion = HorizonWeightedMSELoss(normalized=False, horizon_weighting="long")

        self.assertGreater(
            float(criterion(late_error, target)),
            float(criterion(early_error, target)),
        )

    def test_pms_residual_target_anchors_last_observation_after_denormalization(self) -> None:
        import torch
        import torch.nn as nn

        class ZeroBranch(nn.Module):
            def __init__(self, pred_len: int) -> None:
                super().__init__()
                self.pred_len = pred_len

            def forward(self, value: torch.Tensor) -> torch.Tensor:
                return torch.zeros(
                    value.size(0), value.size(2), self.pred_len,
                    dtype=value.dtype, device=value.device,
                )

        model = PMSMambaModel.__new__(PMSMambaModel)
        nn.Module.__init__(model)
        model.pred_len = 3
        model.use_norm = True
        model.residual_target = True
        model.ms_use_decomp = False
        model.ms_scales = [1]
        model.component_count = 1
        model.decomp = None
        model.branches = nn.ModuleList([ZeroBranch(model.pred_len)])
        model.scale_gate = None
        model.register_parameter("scale_logits", None)
        inputs = torch.tensor([[[1.0], [2.0], [4.0], [7.0]]])

        output, _ = model.forecast(inputs, None, None, None)

        expected = inputs[:, -1:, :].expand(-1, model.pred_len, -1)
        torch.testing.assert_close(output, expected)

    def test_pms_cumulative_head_reconstructs_level_path(self) -> None:
        import torch
        import torch.nn as nn

        model = PMSMambaModel.__new__(PMSMambaModel)
        nn.Module.__init__(model)
        model.forecast_head = "cumulative"
        model.use_norm = False
        encoded_increments = torch.tensor([[[1.0], [2.0], [-0.5]]])
        inputs = torch.tensor([[[3.0], [5.0]]])

        output = model._apply_forecast_head(
            encoded_increments,
            inputs,
            means=None,
            stdev=None,
        )

        torch.testing.assert_close(output, torch.tensor([[[6.0], [8.0], [7.5]]]))

    def test_pms_cumulative_auxiliary_loss_uses_step_increments(self) -> None:
        import torch
        import torch.nn as nn

        model = PMSMambaModel.__new__(PMSMambaModel)
        nn.Module.__init__(model)
        model.forecast_head = "cumulative"
        model.increment_loss_weight = 0.1
        model.change_gate_regularization = 0.0
        prediction = torch.tensor([[[3.0], [5.0], [8.0]]])
        target = torch.tensor([[[3.0], [4.0], [6.0]]])
        inputs = torch.tensor([[[1.0], [2.0]]])

        loss = model.auxiliary_loss(prediction, target, inputs)

        expected = 0.1 * torch.tensor((0.0 ** 2 + 1.0 ** 2 + 1.0 ** 2) / 3.0)
        torch.testing.assert_close(loss, expected)

    def test_persistence_change_gate_is_bounded_and_encoder_only(self) -> None:
        import torch

        torch.manual_seed(20260804)
        gate = PersistenceChangeGate(
            pred_len=6,
            hidden_dim=8,
            recent_ratio=0.25,
            dropout=0.0,
        ).eval()
        encoder = torch.randn(2, 32, 3)

        first = gate(encoder)
        second = gate(encoder.clone())

        self.assertEqual(tuple(first.shape), (2, 3, 6))
        self.assertTrue(torch.all((first >= 0.0) & (first <= 1.0)))
        torch.testing.assert_close(first, second)

    def test_fast_single_pms_branch_returns_a_forecast_path(self) -> None:
        import torch

        if not torch.cuda.is_available():
            self.skipTest("the installed mamba_ssm selective-scan kernel requires CUDA")

        config = SimpleNamespace(
            seq_len=32,
            pred_len=6,
            output_attention=False,
            use_norm=1,
            residual_target=0,
            forecast_head="persistence_change",
            increment_loss_weight=0.0,
            change_gate_regularization=0.01,
            pms_branch_mode="fast_single",
            pms_fast_patch_len=8,
            pms_fast_stride=4,
            pms_fast_linear_skip=1,
            ms_use_decomp=0,
            ms_fusion="mean",
            ms_scales=[1],
            moving_avg=5,
            d_model=16,
            d_state=8,
            d_ff=32,
            e_layers=1,
            dropout=0.0,
            activation="gelu",
            ns_recent_ratio=0.25,
            patch_len=8,
            stride=4,
        )
        model = PMSMambaModel(config).cuda().eval()
        output = model(torch.randn(2, 32, 3, device="cuda"), None, None, None)

        self.assertEqual(tuple(output.shape), (2, 6, 3))
        self.assertTrue(torch.isfinite(output).all())

    def test_regime_linear_pms_branch_returns_a_forecast_path(self) -> None:
        import torch

        if not torch.cuda.is_available():
            self.skipTest("the installed mamba_ssm selective-scan kernel requires CUDA")
        config = SimpleNamespace(
            seq_len=32,
            pred_len=6,
            output_attention=False,
            use_norm=1,
            residual_target=0,
            forecast_head="persistence_change",
            increment_loss_weight=0.0,
            change_gate_regularization=0.01,
            pms_change_scale=1.0,
            pms_branch_mode="regime_linear",
            pms_regime_channel_gate=1,
            pms_regime_decomp=1,
            ms_use_decomp=0,
            ms_fusion="mean",
            ms_scales=[1],
            moving_avg=5,
            d_model=32,
            d_state=8,
            d_ff=64,
            e_layers=1,
            dropout=0.0,
            activation="gelu",
            ns_recent_ratio=0.25,
            patch_len=8,
            stride=4,
        )
        model = PMSMambaModel(config).cuda().eval()
        output = model(torch.randn(2, 32, 3, device="cuda"), None, None, None)

        self.assertEqual(tuple(output.shape), (2, 6, 3))
        self.assertTrue(torch.isfinite(output).all())

    def test_inverted_single_pms_branch_returns_a_forecast_path(self) -> None:
        import torch

        if not torch.cuda.is_available():
            self.skipTest("the installed mamba_ssm selective-scan kernel requires CUDA")
        config = SimpleNamespace(
            seq_len=32,
            pred_len=6,
            output_attention=False,
            use_norm=1,
            residual_target=0,
            forecast_head="level",
            increment_loss_weight=0.0,
            change_gate_regularization=0.0,
            pms_change_scale=1.0,
            pms_branch_mode="inverted_single",
            pms_inverted_decomp=1,
            ms_use_decomp=0,
            ms_fusion="mean",
            ms_scales=[1],
            moving_avg=5,
            d_model=32,
            d_state=8,
            d_ff=64,
            e_layers=1,
            dropout=0.0,
            activation="gelu",
            ns_recent_ratio=0.25,
            patch_len=8,
            stride=4,
        )
        model = PMSMambaModel(config).cuda().eval()
        output = model(torch.randn(2, 32, 3, device="cuda"), None, None, None)

        self.assertEqual(tuple(output.shape), (2, 6, 3))
        self.assertTrue(torch.isfinite(output).all())

    def test_fused_dual_pms_branch_returns_a_forecast_path(self) -> None:
        import torch

        if not torch.cuda.is_available():
            self.skipTest("the installed mamba_ssm selective-scan kernel requires CUDA")
        config = SimpleNamespace(
            seq_len=64,
            pred_len=6,
            output_attention=False,
            use_norm=1,
            residual_target=0,
            forecast_head="persistence_change",
            increment_loss_weight=0.0,
            change_gate_regularization=0.0,
            pms_change_scale=1.0,
            pms_branch_mode="fused_dual",
            pms_fine_patch_len=8,
            pms_fine_stride=4,
            pms_coarse_patch_len=16,
            pms_coarse_stride=8,
            ms_use_decomp=1,
            ms_fusion="mean",
            ms_scales=[1, 2],
            moving_avg=5,
            d_model=16,
            d_state=8,
            d_ff=32,
            e_layers=1,
            dropout=0.0,
            activation="gelu",
            ns_recent_ratio=0.25,
            patch_len=8,
            stride=4,
        )
        model = PMSMambaModel(config).cuda().eval()
        output = model(torch.randn(2, 64, 3, device="cuda"), None, None, None)

        self.assertEqual(tuple(output.shape), (2, 6, 3))
        self.assertTrue(torch.isfinite(output).all())

    def test_shared_multiscale_pms_branch_returns_a_forecast_path(self) -> None:
        import torch

        if not torch.cuda.is_available():
            self.skipTest("the installed mamba_ssm selective-scan kernel requires CUDA")
        config = SimpleNamespace(
            seq_len=64,
            pred_len=6,
            output_attention=False,
            use_norm=1,
            residual_target=0,
            forecast_head="persistence_change",
            increment_loss_weight=0.0,
            change_gate_regularization=0.0,
            pms_change_scale=1.0,
            pms_branch_mode="shared_multiscale",
            ms_use_decomp=1,
            ms_fusion="mean",
            ms_scales=[1, 2, 4],
            moving_avg=5,
            d_model=16,
            d_state=8,
            d_ff=32,
            e_layers=1,
            dropout=0.0,
            activation="gelu",
            ns_recent_ratio=0.25,
            patch_len=8,
            stride=4,
        )
        model = PMSMambaModel(config).cuda().eval()
        output = model(torch.randn(2, 64, 3, device="cuda"), None, None, None)

        self.assertEqual(tuple(output.shape), (2, 6, 3))
        self.assertTrue(torch.isfinite(output).all())

    def test_persistence_change_scale_shrinks_predicted_changes(self) -> None:
        import torch
        import torch.nn as nn

        class FixedGate(nn.Module):
            def forward(self, x):
                return torch.ones(x.size(0), x.size(2), 2, device=x.device)

        model = PMSMambaModel.__new__(PMSMambaModel)
        nn.Module.__init__(model)
        model.pred_len = 2
        model.forecast_head = "persistence_change"
        model.use_norm = False
        model.pms_change_scale = 0.25
        model.change_gate = FixedGate()
        model._last_change_gate = None
        path = torch.tensor([[[4.0], [8.0]]])
        raw = torch.tensor([[[10.0]]])

        output = model._apply_forecast_head(path, raw, means=None, stdev=None)

        torch.testing.assert_close(output, torch.tensor([[[11.0], [12.0]]]))

    def test_v3_patch_layout_requires_four_tokens_per_branch(self) -> None:
        params = {
            "seq_len": 64,
            "ms_scales": [1, 2, 4],
            "patch_len": 32,
            "stride": 16,
            "pms_min_patch_tokens": 4,
        }
        self.assertIn(
            "below pms_min_patch_tokens=4",
            model_params_feasibility_error("PMS_Mamba-PD", params),
        )
        params.update(seq_len=256)
        self.assertIsNone(model_params_feasibility_error("PMS_Mamba-PD", params))

    def test_v4_fast_search_space_keeps_a_single_latency_compatible_branch(self) -> None:
        import optuna

        trial = optuna.create_study(direction="minimize").ask()
        params = sample_v4_fast_mamba_params(trial, "PMS_Mamba-PD")

        self.assertEqual(params["pms_branch_mode"], "fast_single")
        self.assertEqual(params["e_layers"], 1)
        self.assertEqual(params["ms_use_decomp"], 0)
        self.assertEqual(params["pms_fast_linear_skip"], 0)
        self.assertIsNone(model_params_feasibility_error("PMS_Mamba-PD", params))

    def test_v3_horizon_amendment_preserves_pretest_chronology(self) -> None:
        protocol = json.loads(V3_PROTOCOL_PATH.read_text(encoding="utf-8"))
        self.assertEqual(protocol["selection_horizons"], [1, 5, 20, 60, 120])
        self.assertEqual(protocol["deferred_financial_diagnostic_horizons"], [252])
        self.assertEqual(protocol["merge_gate_splits"]["validation_start"], "2022-01-01")
        self.assertEqual(protocol["merge_gate_splits"]["validation_end"], "2022-12-31")
        self.assertEqual(protocol["evidence_boundary"]["prohibited_for_selection"],
                         "financial 2023-01-01 through 2026-06-30")

    def test_v3_external_manifest_freezes_s_and_m_without_test_access(self) -> None:
        payload = json.loads(V3_EXTERNAL_TASKS.read_text(encoding="utf-8"))
        tasks = payload["tasks"]
        self.assertEqual(payload["task_count"], 16)
        self.assertTrue(payload["generated_without_reading_target_values"])
        self.assertEqual(sum(
            config["evidence_status"] == "untouched_confirmatory"
            for config in tasks.values()
        ), 12)
        for config in tasks.values():
            self.assertIn(config["input_mode"], {"S", "M"})
            self.assertFalse(config["test_targets_read"])
            path = REPO_ROOT / config["root_path"] / config["data_path"]
            self.assertEqual(sha256(path), config["data_sha256"])

    def test_external_batch_rule_bounds_high_dimensional_tasks(self) -> None:
        self.assertEqual(adaptive_external_batch_size(16, 862), 2)
        self.assertEqual(adaptive_external_batch_size(16, 321), 6)
        self.assertEqual(adaptive_external_batch_size(16, 7), 16)

    def test_v3_runtime_gate_requires_both_deep_references(self) -> None:
        passed, comparisons = evaluate_runtime_gate(
            {"PMS_Mamba-V3": 3.0, "TimesNet": 12.0, "PatchTST": 2.0},
            "PMS_Mamba-V3",
            ["TimesNet", "PatchTST"],
        )

        self.assertFalse(passed)
        self.assertTrue(comparisons["TimesNet"]["candidate_is_faster"])
        self.assertFalse(comparisons["PatchTST"]["candidate_is_faster"])
        self.assertEqual(comparisons["TimesNet"]["candidate_speedup"], 4.0)

    def test_nonstationary_gate_shape_normalization_and_replay(self) -> None:
        import torch

        torch.manual_seed(20260725)
        gate = NonStationaryGate(
            d_model=8,
            hidden_dim=16,
            gate_dim=6,
            num_gates=4,
            dropout=0.0,
            activation="softmax",
        ).eval()
        inputs = torch.randn(2, 16, 3)

        first = gate(inputs, target_tokens=3)
        second = gate(inputs, target_tokens=3)

        self.assertEqual(tuple(first.shape), (2, 3, 4, 6))
        torch.testing.assert_close(first.sum(dim=2), torch.ones(2, 3, 6))
        torch.testing.assert_close(first, second)

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
