"""Release-level checks that do not require raw provider data or CUDA."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from utils.financial.s_only_report import checksum_problems, checksum_rows, contrasts
from utils.financial.common import sha256_path


ROOT = Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_protocols_have_separate_s_only_rosters_and_expected_counts() -> None:
    expectations = {"v1": (4, 72, 1320), "v2": (18, 324, 5940)}
    for release, (task_count, deterministic_rows, learned_rows) in expectations.items():
        root = ROOT / "reproducibility" / f"financial_s_only_{release}"
        protocol = json.loads((root / "protocol.json").read_text())
        manifest = json.loads((root / "training_datasets.json").read_text())
        status = json.loads((root / "release_status.json").read_text())
        tasks = protocol.get("tasks", protocol.get("target_roster"))
        assert len(tasks) == task_count
        assert set(tasks) == set(manifest)
        assert all(task.endswith("_s") and value["features"] == "S" for task, value in manifest.items())
        assert status["complete_deterministic_rows"] == deterministic_rows
        assert status["expected_deterministic_rows"] == deterministic_rows
        assert status["expected_learned_horizon_rows"] == learned_rows
        complete_learned = status["complete_learned_horizon_rows"]
        assert 0 <= complete_learned <= learned_rows
        # A learned seed bundle is complete only after its six frozen horizons
        # have checkpoints and forecast artifacts. A fully populated release
        # can be verified; otherwise it remains a resumable incomplete record.
        assert complete_learned % len(protocol["horizons"]) == 0
        expected_status = "verified" if complete_learned == learned_rows else "incomplete"
        assert status["status"] == expected_status


def test_deterministic_metric_tables_are_complete_and_have_local_bundle_provenance() -> None:
    expectations = {"v1": 72, "v2": 324}
    for release, expected_count in expectations.items():
        root = ROOT / "reproducibility" / f"financial_s_only_{release}"
        rows = read_csv(root / "metrics" / "deterministic_metrics.csv")
        assert len(rows) == expected_count
        assert {"dataset", "model_id", "horizon", "path_mae", "path_rmse", "path_rmsse", "bundle_sha256"} <= set(rows[0])
        assert {row["model_id"] for row in rows} == {"LastValue", "RandomWalkDrift", "ARIMA"}
        assert all(row["bundle"].startswith("results/financial_s_only_retrospective_") for row in rows)
        assert all(len(row["bundle_sha256"]) == 64 for row in rows)


def test_recorded_profiles_are_s_only_and_compare_the_gate_ablation() -> None:
    expected_tasks = {
        "v1": "financial_cross_asset_s",
        "v2": "financial_cross_asset_gld_s",
    }
    for release, task in expected_tasks.items():
        root = ROOT / "reproducibility" / f"financial_s_only_{release}" / "metrics"
        rows = {row["model_id"]: row for row in read_csv(root / "matched_cuda_microbenchmark.csv")}
        assert set(rows) == {"RegimeGatedMamba", "UngatedRegimeLinearMamba", "PatchTST", "TimesNet"}
        assert rows["RegimeGatedMamba"]["task"] == task
        assert float(rows["RegimeGatedMamba"]["median_latency_ms"]) < float(rows["PatchTST"]["median_latency_ms"])
        assert float(rows["RegimeGatedMamba"]["median_latency_ms"]) < float(rows["TimesNet"]["median_latency_ms"])
        assert int(rows["UngatedRegimeLinearMamba"]["parameter_count"]) < int(rows["RegimeGatedMamba"]["parameter_count"])


def test_checksum_manifest_can_cover_the_final_release_status(tmp_path: Path) -> None:
    artifact = tmp_path / "metrics" / "metrics_by_seed.csv"
    artifact.parent.mkdir()
    artifact.write_text("dataset,model\nexample,RegimeGatedMamba\n", encoding="utf-8")
    status = tmp_path / "release_status.json"
    status.write_text('{"status":"verified"}\n', encoding="utf-8")
    rows = checksum_rows(tmp_path, [artifact, status])
    (tmp_path / "SHA256SUMS.json").write_text(json.dumps(rows), encoding="utf-8")
    assert checksum_problems(tmp_path) == []
    status.write_text('{"status":"incomplete"}\n', encoding="utf-8")
    assert checksum_problems(tmp_path) == ["checksum_mismatch:release_status.json"]


def test_release_local_selections_and_model_map_cover_the_active_roster() -> None:
    for release in ("v1", "v2"):
        root = ROOT / "reproducibility" / f"financial_s_only_{release}"
        model_map = json.loads((root / "model_identity_map.json").read_text())["models"]
        assert len(model_map) == 14
        assert {item["model_id"] for item in model_map} >= {"RegimeGatedMamba", "UngatedRegimeLinearMamba", "LastValue", "ARIMA"}
        selections = json.loads((root / "selection_manifest.json").read_text())["entries"]
        assert len(selections) == 8
        assert all(item["source"] == "release-local frozen selection snapshot" for item in selections)


def test_paired_contrasts_use_scale_normalized_path_rmsse() -> None:
    origins = np.array(["2024-01-01", "2024-01-02"])
    proposed = (origins, np.array([1.0, 4.0]))
    references = {
        "LastValue": (origins, np.array([4.0, 9.0])),
        "RandomWalkDrift": (origins, np.array([4.0, 9.0])),
        "ARIMA": (origins, np.array([4.0, 9.0])),
        "UngatedRegimeLinearMamba": (origins, np.array([4.0, 9.0])),
    }
    learned = {
        ("financial_example_s", "RegimeGatedMamba", 1, 2023): proposed,
        ("financial_example_s", "UngatedRegimeLinearMamba", 1, 2023): references["UngatedRegimeLinearMamba"],
    }
    deterministic = {
        ("financial_example_s", model_id, 1, "deterministic"): values
        for model_id, values in references.items()
        if model_id != "UngatedRegimeLinearMamba"
    }
    table, _ = contrasts({"horizons": [1], "seeds": [2023]}, learned, deterministic)
    assert set(table.columns) >= {"mean_path_scaled_mse_difference", "mean_path_rmsse_difference"}
    expected = np.sqrt(np.mean(proposed[1])) - np.sqrt(np.mean(references["LastValue"][1]))
    assert np.allclose(table["mean_path_rmsse_difference"].to_numpy(), expected)


def test_v1_figure_manifest_binds_rendered_files_to_verified_inputs() -> None:
    manifest = json.loads((ROOT / "docs" / "figures" / "financial_s_only_v1_figure_manifest.json").read_text())
    assert manifest["release"] == "financial_s_only_v1"
    assert manifest["release_status"] == "verified"
    for entry in [*manifest["source_files"], *manifest["output_files"]]:
        path = ROOT / entry["path"]
        assert path.is_file()
        assert sha256_path(path) == entry["sha256"]
