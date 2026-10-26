#!/usr/bin/env python
"""Analyze post-V3 validation-selected V5 diagnostics separately from V3 claims."""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("SAPR_MAMBA_VERSION", "v3")

from utils.sapr_mamba.analysis import holm_adjust, paired_percentile_bootstrap, write_csv
from utils.sapr_mamba.io import atomic_write_json, sha256_path, utc_now


V3 = REPO_ROOT / "results" / "sapr_mamba_v3" / "real" / "metrics_all.csv"
DEFAULT_V5 = REPO_ROOT / "results" / "sapr_mamba_v5" / "real"
DEFAULT_OUT = REPO_ROOT / "docs" / "analysis" / "sapr_mamba_v5"
PREPARED = REPO_ROOT / "data" / "sapr_mamba_v3" / "real" / "processed" / "prepared_manifest.json"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _means(rows: list[dict[str, str]], model: str) -> dict[tuple[str, str, int, str], float]:
    grouped: dict[tuple[str, str, int, str], list[float]] = defaultdict(list)
    for row in rows:
        if row["model"] == model:
            grouped[(row["dataset"], row["series_id"], int(row["horizon"]), row["state"])].append(float(row["rmse"]))
    return {key: float(np.mean(values)) for key, values in grouped.items()}


def analyze(results_root: Path, output_root: Path, model: str, study: str) -> dict:
    metrics = results_root / "metrics_all.csv"
    if not V3.is_file() or not metrics.is_file():
        raise SystemExit("V3 and V5 combined metrics are required")
    panels = json.loads(PREPARED.read_text(encoding="utf-8"))["panels"]
    source = {str(row["panel_id"]): str(row.get("source_cluster") or ("ett" if str(row["panel_id"]).startswith("ett_") else row["panel_id"])) for row in panels}
    m3, m5 = _means(read_rows(V3), "M3"), _means(read_rows(metrics), model)
    grouped: dict[tuple[str, int, str], list[float]] = defaultdict(list)
    for key, value in m5.items():
        if key in m3:
            grouped[(source[key[0]], key[2], key[3])].append(value - m3[key])
    comparisons = []
    for index, ((cluster, horizon, state), values) in enumerate(sorted(grouped.items())):
        comparisons.append({
            "comparison": f"{model}_minus_M3", "source": cluster, "horizon": horizon, "state": state,
            "metric": "raw_rmse", "post_v3_diagnostic": True,
            **paired_percentile_bootstrap(np.asarray(values, dtype=np.float64), 10000, 150000 + index),
        })
    for row, adjusted in zip(comparisons, holm_adjust([float(row["p_two_sided"]) for row in comparisons])):
        row["p_holm"] = adjusted
    selections: dict[str, Counter[str]] = defaultdict(Counter)
    for path in sorted(results_root.glob(f"*/{model}_seed*/validation_model_selection.csv")):
        panel = path.parents[1].name
        selections[panel].update(row["selected_model"] for row in read_rows(path))
    all_selected_models = sorted({name for counts in selections.values() for name in counts})
    selection_rows = [
        {"panel": panel, "series_seed_units": sum(counts.values()), **{name: counts[name] for name in all_selected_models}}
        for panel, counts in sorted(selections.items())
    ]
    output_root.mkdir(parents=True, exist_ok=True)
    comparison_path = output_root / "post_v3_vs_m3_diagnostic.csv"
    write_csv(comparison_path, comparisons, ("comparison", "source", "horizon", "state", "metric", "post_v3_diagnostic", "n", "estimate", "ci_low", "ci_high", "p_two_sided", "p_holm"))
    selection_path = output_root / "validation_selection_summary.csv"
    candidate_columns = sorted({key for row in selection_rows for key in row if key not in {"panel", "series_seed_units"}})
    write_csv(selection_path, selection_rows, ("panel", "series_seed_units", *candidate_columns))
    manifest = {"study": study, "status": "complete", "interpretation": "post-V3 diagnostic; V3 claims remain unchanged", "created_at": utc_now(), "comparison_rows": len(comparisons), "v3_metrics_sha256": sha256_path(V3), "diagnostic_metrics_sha256": sha256_path(metrics)}
    atomic_write_json(output_root / "analysis_manifest.json", manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    parser = __import__("argparse").ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_V5)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--model", default="M5-validation-selection")
    parser.add_argument("--study", default="sapr_mamba_v5")
    args = parser.parse_args()
    analyze(args.results_root, args.output_root, args.model, args.study)
