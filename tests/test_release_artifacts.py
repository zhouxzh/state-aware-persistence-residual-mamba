"""Release-level checks that run without provider data or CUDA hardware."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "reproducibility" / "financial_reference_evaluation_v1"
METRICS = RELEASE / "metrics"


def read_csv(name: str) -> list[dict[str, str]]:
    with (METRICS / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_release_configuration_uses_canonical_candidate_ids() -> None:
    config = json.loads(
        (ROOT / "configs" / "financial_reference_evaluation_v1.json").read_text(encoding="utf-8")
    )
    assert config["protocol_version"] == "financial_reference_evaluation_v1"
    assert set(config["candidates"]) == {"RegimeGatedMamba", "MultiScalePatchMamba"}
    assert config["candidates"]["RegimeGatedMamba"]["public_name"] == "Regime-Gated Mamba"


def test_metric_table_is_complete_and_has_provenance() -> None:
    rows = read_csv("all_model_metrics_by_seed.csv")
    assert len(rows) == 2640
    assert {"source_model_id", "model_id", "model", "dataset", "seed", "horizon"} <= set(rows[0])
    candidate_rows = [row for row in rows if row["model_id"] == "RegimeGatedMamba"]
    assert len(candidate_rows) == 240
    assert {row["horizon"] for row in candidate_rows} == {"1", "5", "20", "60", "120", "252"}
    assert {row["seed"] for row in candidate_rows} == {"2023", "2024", "2025", "2026", "2027"}
    assert {row["source_model_id"] for row in candidate_rows} == {"PMSV5_R6"}


def test_runtime_profile_supports_the_documented_inference_comparison() -> None:
    rows = {row["model_id"]: row for row in read_csv("matched_cuda_microbenchmark.csv")}
    selected = rows["RegimeGatedMamba"]
    assert selected["model"] == "Regime-Gated Mamba"
    assert float(selected["median_latency_ms"]) < float(rows["PatchTST"]["median_latency_ms"])
    assert float(selected["median_latency_ms"]) < float(rows["TimesNet"]["median_latency_ms"])
    assert int(selected["parameter_count"]) < int(rows["PatchTST"]["parameter_count"])


def test_required_reproduction_artifacts_exist() -> None:
    expected = {
        "all_model_metrics_by_seed.csv",
        "all_model_aggregate_metrics.csv",
        "balanced_path_rmsse_by_task_seed.csv",
        "candidate_models_metrics_by_seed.csv",
        "regime_gated_mamba_paired_contrasts.csv",
        "regime_gated_mamba_paired_task_seed_bootstrap.csv",
        "matched_cuda_microbenchmark.csv",
    }
    assert expected <= {path.name for path in METRICS.iterdir() if path.is_file()}
