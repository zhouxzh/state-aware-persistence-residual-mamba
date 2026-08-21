"""Regression checks for the derived V2 analysis bundle."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from utils.financial.common import sha256_path


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "docs" / "analysis" / "financial_s_only_v2"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_v2_analysis_tables_have_expected_shapes_and_headlines() -> None:
    model_rows = read_rows(ANALYSIS / "model_summary.csv")
    horizon_rows = read_rows(ANALYSIS / "horizon_summary.csv")
    family_rows = read_rows(ANALYSIS / "family_summary.csv")
    target_rows = read_rows(ANALYSIS / "target_summary.csv")
    cell_rows = read_rows(ANALYSIS / "regime_gated_cell_metrics.csv")
    seed_rows = read_rows(ANALYSIS / "seed_stability.csv")
    assert len(model_rows) == 14
    assert len(horizon_rows) == 14 * 6
    assert len(family_rows) == 14 * 4
    assert len(target_rows) == 18
    assert len(cell_rows) == 108
    assert len(seed_rows) == 108
    proposed = next(row for row in model_rows if row["model_id"] == "RegimeGatedMamba")
    assert float(proposed["mean_path_rmsse_rank"]) == 6.25
    assert proposed["rank1_cells"] == "4"
    assert proposed["top3_cells"] == "24"
    assert {row["horizon"] for row in seed_rows} == {"1", "5", "20", "60", "120", "252"}
    assert {row["family"] for row in target_rows} == {"Cross asset", "Crypto", "Foreign exchange", "Treasury yields"}


def test_v2_analysis_manifest_binds_sources_and_outputs() -> None:
    manifest = json.loads((ANALYSIS / "analysis_manifest.json").read_text(encoding="utf-8"))
    assert manifest["release"] == "financial_s_only_v2"
    assert manifest["analysis_version"] == "s_only_result_analysis_v1"
    for entry in [*manifest["source_files"], *manifest["output_files"]]:
        path = ROOT / entry["path"]
        assert path.is_file()
        assert sha256_path(path) == entry["sha256"]


def test_v2_cell_analysis_keeps_raw_metrics_and_named_normalization() -> None:
    rows = read_rows(ANALYSIS / "regime_gated_cell_metrics.csv")
    required = {
        "rgm_path_mae",
        "rgm_path_rmse",
        "rgm_path_rmsse",
        "rgm_over_lastvalue_mae_ratio",
        "rgm_over_lastvalue_rmse_ratio",
        "rgm_over_lastvalue_rmsse_ratio",
        "rgm_minus_PatchTST_path_rmsse",
        "rgm_minus_TimesNet_path_rmsse",
    }
    assert required <= set(rows[0])
    assert all(float(row["rgm_seed_count"]) == 5 for row in rows)
