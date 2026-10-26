#!/usr/bin/env python
"""Independent, mechanism-stratified analysis for the frozen SAPR Sim V1 matrix."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("SAPR_MAMBA_VERSION", "sim_v1")

from utils.sapr_mamba.analysis import artifact_entry, holm_adjust, paired_percentile_bootstrap, write_checksum_manifest, write_csv
from utils.sapr_mamba.io import DATA_ROOT, RESULT_ROOT, atomic_write_json, sha256_path, utc_now


STUDY_VERSION = os.environ["SAPR_MAMBA_VERSION"]
if STUDY_VERSION not in {"sim_v1", "sim_v2", "sim_v3", "sim_v5", "canonical_v1", "canonical_v2", "bocpd_confirm_v1"} and not (STUDY_VERSION.startswith("bocpd_e") and STUDY_VERSION[7:].isdigit()):
    raise ValueError("sapr_sim analyzer requires a configured simulation namespace")
CONFIG = REPO_ROOT / "configs" / f"sapr_mamba_{STUDY_VERSION}"
ROOT = RESULT_ROOT / "synthetic"
OUT = REPO_ROOT / "docs" / "analysis" / f"sapr_{STUDY_VERSION}"
DOC = REPO_ROOT / "docs" / "current" / f"sapr_{STUDY_VERSION}_results.md"
REPRO = REPO_ROOT / "reproducibility" / f"sapr_{STUDY_VERSION}"

GROUPS = {
    "T0": ("stable", "stable"),
    "T1": ("visible_level_shift", "visible_change"),
    "T2": ("future_jump", "unseen_change"),
    "T3": ("continuing_trend", "visible_change"),
    "T4": ("trend_break", "visible_change"),
    "T5": ("stable_season", "stable"),
    "T6": ("seasonal_change", "visible_change"),
    "T7": ("variance_shift", "visible_change"),
    "T8": ("random_walk", "stable"),
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def cfg(name: str) -> dict:
    return read_json(CONFIG / f"{name}.json")


def expected_tasks(protocol: dict) -> list[tuple[str, int]]:
    return [(model, int(seed)) for model in protocol["models"] for seed in protocol["seeds"]]


def archive_for(model: str, seed: int) -> tuple[dict, Path]:
    manifest_path = ROOT / f"{model}_seed{seed}" / "task_manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"missing_task_manifest:{model}:{seed}")
    manifest = read_json(manifest_path)
    if manifest.get("status") != "complete":
        raise RuntimeError(f"task_not_complete:{model}:{seed}:{manifest.get('status')}")
    item = manifest.get("artifacts", {}).get("prediction_archive")
    if not isinstance(item, dict):
        raise RuntimeError(f"missing_prediction_archive:{model}:{seed}")
    path = Path(item["path"])
    if not path.is_file() or sha256_path(path) != item["sha256"]:
        raise RuntimeError(f"invalid_prediction_archive:{model}:{seed}")
    return manifest, path


def load_archives(protocol: dict) -> tuple[dict[tuple[str, int], dict], dict[str, object]]:
    loaded: dict[tuple[str, int], dict] = {}
    expected_keys: set[str] | None = None
    shape: tuple[int, ...] | None = None
    source_signature: dict[str, np.ndarray] | None = None
    for model, seed in expected_tasks(protocol):
        _, path = archive_for(model, seed)
        # Task manifests verify the archive checksum before it is opened. Labels
        # from the first frozen runner are object arrays, so NumPy requires this
        # compatibility setting to read the otherwise numeric archive.
        with np.load(path, allow_pickle=True) as payload:
            arrays = {key: payload[key] for key in payload.files}
        required = {"prediction", "target", "gate", "residual", "state", "change_score", "series_index", "origin", "phi", "true_label"}
        if not required <= arrays.keys():
            raise RuntimeError(f"incomplete_archive_columns:{model}:{seed}")
        if arrays["prediction"].shape != arrays["target"].shape or arrays["prediction"].ndim != 2:
            raise RuntimeError(f"invalid_prediction_shape:{model}:{seed}")
        if expected_keys is None:
            expected_keys, shape = set(arrays), arrays["prediction"].shape
            source_signature = {key: arrays[key] for key in ("target", "state", "change_score", "series_index", "origin", "true_label")}
        else:
            if set(arrays) != expected_keys or arrays["prediction"].shape != shape:
                raise RuntimeError(f"archive_contract_mismatch:{model}:{seed}")
            assert source_signature is not None
            for key, expected in source_signature.items():
                if not np.array_equal(arrays[key], expected):
                    raise RuntimeError(f"archive_source_mismatch:{model}:{seed}:{key}")
        loaded[(model, seed)] = arrays
    assert source_signature is not None
    return loaded, source_signature


def sequence_metrics(archives: dict[tuple[str, int], dict], settings: dict, roster: list[dict]) -> list[dict]:
    rows: list[dict] = []
    horizons = tuple(int(value) for value in settings["horizons"])
    mechanism_by_index = np.asarray([record["mechanism"] for record in roster], dtype=object)
    id_by_index = np.asarray([record["series_id"] for record in roster], dtype=object)
    for (model, seed), arrays in sorted(archives.items()):
        mechanisms = mechanism_by_index[arrays["series_index"]]
        for group, (mechanism, label) in GROUPS.items():
            group_mask = (mechanisms == mechanism) & (arrays["true_label"].astype(str) == label)
            for series_index in np.unique(arrays["series_index"][group_mask]):
                series_mask = group_mask & (arrays["series_index"] == series_index)
                for horizon in horizons:
                    error = arrays["prediction"][series_mask, :horizon] - arrays["target"][series_mask, :horizon]
                    rows.append({
                        "group": group,
                        "mechanism": mechanism,
                        "true_label": label,
                        "model": model,
                        "seed": seed,
                        "series_index": int(series_index),
                        "series_id": str(id_by_index[int(series_index)]),
                        "horizon": horizon,
                        "origins": int(series_mask.sum()),
                        "points": int(error.size),
                        "rmse": float(np.sqrt(np.mean(np.square(error)))),
                        "gate_mean": float(np.mean(arrays["gate"][series_mask, :horizon])),
                    })
    return rows


def average_by_series(rows: list[dict], group: str, model: str, horizon: int) -> dict[str, float]:
    values: dict[str, list[float]] = {}
    for row in rows:
        if row["group"] == group and row["model"] == model and int(row["horizon"]) == int(horizon):
            values.setdefault(row["series_id"], []).append(float(row["rmse"]))
    return {series_id: float(np.mean(scores)) for series_id, scores in values.items()}


def comparison(rows: list[dict], family: str, group: str, left: str, right: str, horizon: int, replicates: int, relative: bool = False) -> dict:
    lhs, rhs = average_by_series(rows, group, left, horizon), average_by_series(rows, group, right, horizon)
    shared = sorted(set(lhs) & set(rhs))
    if not shared:
        raise RuntimeError(f"no_paired_series:{group}:{left}:{right}:h{horizon}")
    left_values = np.asarray([lhs[key] for key in shared], dtype=float)
    right_values = np.asarray([rhs[key] for key in shared], dtype=float)
    delta = left_values / right_values - 1.0 if relative else left_values - right_values
    seed = int.from_bytes(hashlib.sha256(f"{family}:{group}:{left}:{right}:{horizon}".encode()).digest()[:4], "big")
    result = paired_percentile_bootstrap(delta, replicates, seed)
    return {
        "family": family,
        "group": group,
        "mechanism": GROUPS[group][0],
        "true_label": GROUPS[group][1],
        "left_model": left,
        "right_model": right,
        "horizon": horizon,
        "metric": "relative_series_rmse" if relative else "series_rmse_difference",
        **result,
    }


def frozen_comparisons(rows: list[dict], settings: dict, protocol: dict) -> list[dict]:
    horizons = tuple(int(value) for value in settings["horizons"])
    replicates = int(protocol["evaluation"]["bootstrap_replicates"])
    bocpd_study = STUDY_VERSION == "bocpd_confirm_v1" or STUDY_VERSION.startswith("bocpd_e")
    primary_gate = "M3-bocpd" if bocpd_study else "M3-trigger-gate" if STUDY_VERSION == "sim_v5" else "M3"
    definitions: list[tuple[str, str, str, str, bool]] = [
        ("A", "T0", "M2", "M0", True), ("A", "T0", primary_gate, "M0", True),
        *[("B", "T2", model, "M0", False) for model in ("M1", "DLinear", "M2", primary_gate)],
        *[("C", group, "M2", comparator, False) for group in ("T3", "T4", "T6") for comparator in ("M1", "DLinear")],
        *[("D", group, primary_gate, "M3-constant-gate", False) for group in ("T0", "T2", "T3", "T4", "T6", "T7", "T8")],
        *[("D", group, primary_gate, "M0", False) for group in ("T0", "T2", "T7", "T8")],
        *[("E", "T7", model, "M0", False) for model in ("M1", "M2", primary_gate)],
        *[("F", "T1", left, right, False) for left, right in (("M1", "M0"), ("DLinear", "M0"), ("M2", "M1"), ("M2", "DLinear"))],
        *[("F", group, "M2", right, False) for group in ("T4", "T6") for right in ("M0", "M1", "DLinear")],
        *[("G", "T8", model, "M0", False) for model in ("M1", "DLinear", "M2", primary_gate)],
        *[("H", "T5", model, "SeasonalNaive", False) for model in ("M0", "M2", primary_gate)],
    ]
    if STUDY_VERSION == "sim_v5":
        definitions += [("I", "T4", primary_gate, control, False) for control in ("M3-hidden-only", "M3-no-state-feature")]
    elif bocpd_study:
        definitions += [("I", group, primary_gate, "M3-bocpd-shuffle", False) for group in ("T3", "T4", "T6")]
        definitions += [("J", group, "M3-oracle", primary_gate, False) for group in ("T3", "T4", "T6")]
    output = [comparison(rows, family, group, left, right, horizon, replicates, relative) for horizon in horizons for family, group, left, right, relative in definitions]
    for family in sorted({row["family"] for row in output}):
        selected = [index for index, row in enumerate(output) if row["family"] == family]
        adjusted = holm_adjust([output[index]["p_two_sided"] for index in selected])
        for index, p_holm in zip(selected, adjusted):
            output[index]["p_holm"] = p_holm
            output[index]["significant_favorable"] = bool(output[index]["estimate"] < 0 and p_holm < 0.05)
    return output


def detector_audit(signature: dict[str, np.ndarray], roster: list[dict]) -> list[dict]:
    mechanisms = np.asarray([record["mechanism"] for record in roster], dtype=object)[signature["series_index"]]
    labels = signature["true_label"].astype(str)
    states = signature["state"].astype(int)
    rows = []
    for mechanism in sorted(set(mechanisms.tolist())):
        for label in sorted(set(labels[mechanisms == mechanism].tolist())):
            mask = (mechanisms == mechanism) & (labels == label)
            counts = Counter(states[mask].tolist())
            rows.append({"mechanism": mechanism, "true_label": label, "origins": int(mask.sum()), "detector_stable": int(counts[0]), "detector_change": int(counts[1]), "detector_change_rate": float(np.mean(states[mask]))})
    return rows


def verdict(comparisons: list[dict]) -> dict:
    bocpd_study = STUDY_VERSION == "bocpd_confirm_v1" or STUDY_VERSION.startswith("bocpd_e")
    primary_gate = "M3-bocpd" if bocpd_study else "M3-trigger-gate" if STUDY_VERSION == "sim_v5" else "M3"
    def chosen(family: str, group: str, left: str, right: str, horizon: int = 96) -> dict:
        return next(row for row in comparisons if row["family"] == family and row["group"] == group and row["left_model"] == left and row["right_model"] == right and row["horizon"] == horizon)
    safety = chosen("A", "T0", primary_gate, "M0")
    t0_pass = bool(safety["estimate"] <= 0.02 and safety["ci_high"] <= 0.05)
    leak = [row for row in comparisons if row["family"] == "B"]
    leakage_pass = not any(row["significant_favorable"] for row in leak)
    walk = [row for row in comparisons if row["family"] == "G"]
    walk_pass = not any(row["significant_favorable"] for row in walk)
    patch_rows = [row for row in comparisons if row["family"] == "F" and row["group"] in {"T4", "T6"} and row["left_model"] == "M2"]
    patch_groups = {group for group in ("T4", "T6") if all(row["significant_favorable"] for row in patch_rows if row["group"] == group and row["right_model"] in {"M0", "M1", "DLinear"})}
    patch_pass = bool(t0_pass and leakage_pass and walk_pass and patch_groups)
    if STUDY_VERSION == "sim_v5":
        signal_rows = [row for row in comparisons if row["family"] == "D" and row["group"] == "T4" and row["left_model"] == primary_gate and row["right_model"] == "M3-constant-gate"]
        gate_open = bool(signal_rows) and all(row["significant_favorable"] for row in signal_rows)
        attribution_rows = [row for row in comparisons if row["family"] == "I" and row["group"] == "T4"]
        gate_attribution = bool(attribution_rows) and any(row["significant_favorable"] for row in attribution_rows)
    elif bocpd_study:
        signal_groups = ("T3", "T4", "T6")
        signal_rows = [row for row in comparisons if row["family"] == "D" and row["group"] in signal_groups and row["left_model"] == primary_gate and row["right_model"] == "M3-constant-gate"]
        by_group = {group: [row for row in signal_rows if row["group"] == group] for group in signal_groups}
        gate_open = any(values and all(row["significant_favorable"] for row in values) for values in by_group.values())
        attribution_rows = [row for row in comparisons if row["family"] == "I" and row["left_model"] == primary_gate]
        gate_attribution = bool(attribution_rows) and any(row["significant_favorable"] for row in attribution_rows)
    else:
        gate_open = any(row["significant_favorable"] for row in comparisons if row["family"] == "D" and row["group"] in {"T3", "T4", "T6"} and row["right_model"] == "M3-constant-gate")
        gate_attribution = None
    gate_close = not any(row["significant_favorable"] for row in comparisons if row["family"] == "D" and row["group"] in {"T0", "T2", "T7", "T8"} and row["left_model"] == primary_gate and row["right_model"] == "M3-constant-gate")
    result = {"T0_safety_pass": t0_pass, "T2_leakage_pass": leakage_pass, "T8_random_walk_pass": walk_pass, "patch_candidate_groups": sorted(patch_groups), "patch_claim_pass": patch_pass, "gate_open_evidence": gate_open, "gate_close_evidence": gate_close, "state_gate_claim_pass": bool(gate_open and gate_close and t0_pass)}
    if gate_attribution is not None:
        result["gate_attribution_evidence"] = gate_attribution
        result["state_gate_claim_pass"] = bool(result["state_gate_claim_pass"] and gate_attribution)
    return result


def markdown(comparisons: list[dict], coverage: dict, detector: list[dict], decision: dict) -> str:
    lines = [f"# SAPR {STUDY_VERSION.upper()} Results", "", f"This report is generated solely from frozen `{STUDY_VERSION}` task archives. It does not pool V2/V3 or real-data results.", "", "## Decision", ""]
    for key, value in decision.items():
        lines.append(f"- `{key}`: `{value}`")
    lines += ["", "## Coverage", "", "| Mechanism | true stable | true visible | true unseen | detector stable | detector change |", "|---|---:|---:|---:|---:|---:|"]
    for row in coverage["rows"]:
        lines.append(f"| {row['mechanism']} | {row['true_stable_origins']} | {row['true_visible_origins']} | {row['true_unseen_origins']} | {row['detector_stable_origins']} | {row['detector_change_origins']} |")
    lines += ["", "## Frozen Comparisons", "", "Negative estimates favor the left model. Bootstrap units are independent test sequences after averaging matched seeds. Holm adjustment is within the frozen A-H family.", "", "| family | group | comparison | H | metric | n | estimate | 95% CI | Holm p |", "|---|---|---|---:|---|---:|---:|---|---:|"]
    for row in comparisons:
        lines.append(f"| {row['family']} | {row['group']} | {row['left_model']} - {row['right_model']} | {row['horizon']} | {row['metric']} | {row['n']} | {row['estimate']:.6f} | [{row['ci_low']:.6f}, {row['ci_high']:.6f}] | {row['p_holm']:.6g} |")
    lines += ["", "## Detector Audit", "", "| Mechanism | true label | origins | detector stable | detector change | change rate |", "|---|---|---:|---:|---:|---:|"]
    for row in detector:
        lines.append(f"| {row['mechanism']} | {row['true_label']} | {row['origins']} | {row['detector_stable']} | {row['detector_change']} | {row['detector_change_rate']:.4f} |")
    return "\n".join(lines) + "\n"


def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("analyze", "verify"), required=True)
    args = parser.parse_args()
    protocol, settings = cfg("protocol"), cfg("synthetic")
    if args.stage == "verify":
        manifest = read_json(OUT / "analysis_manifest.json")
        for item in manifest["artifacts"].values():
            path = REPO_ROOT / item["path"]
            if not path.is_file() or sha256_path(path) != item["sha256"]:
                raise SystemExit(f"verification_failed:{path}")
        print(json.dumps({"status": "verified", "analysis_manifest": str((OUT / "analysis_manifest.json").relative_to(REPO_ROOT))}, indent=2))
        return
    archives, signature = load_archives(protocol)
    roster = read_json(DATA_ROOT / "synthetic" / "test_roster.json")["records"]
    metrics = sequence_metrics(archives, settings, roster)
    comparisons = frozen_comparisons(metrics, settings, protocol)
    detector = detector_audit(signature, roster)
    coverage = read_json(REPO_ROOT / "docs" / "current" / f"sapr_{STUDY_VERSION}_coverage.json")
    decision = verdict(comparisons)
    OUT.mkdir(parents=True, exist_ok=True)
    metrics_path, comparisons_path, detector_path, decision_path = OUT / "sequence_metrics.csv", OUT / "frozen_comparisons.csv", OUT / "detector_truth_audit.csv", OUT / "decision.json"
    write_csv(metrics_path, metrics, ("group", "mechanism", "true_label", "model", "seed", "series_index", "series_id", "horizon", "origins", "points", "rmse", "gate_mean"))
    write_csv(comparisons_path, comparisons, ("family", "group", "mechanism", "true_label", "left_model", "right_model", "horizon", "metric", "n", "estimate", "ci_low", "ci_high", "p_two_sided", "p_holm", "significant_favorable"))
    write_csv(detector_path, detector, ("mechanism", "true_label", "origins", "detector_stable", "detector_change", "detector_change_rate"))
    atomic_write_json(decision_path, decision)
    DOC.write_text(markdown(comparisons, coverage, detector, decision), encoding="utf-8")
    REPRO.mkdir(parents=True, exist_ok=True)
    for source, destination in ((metrics_path, REPRO / "sequence_metrics.csv"), (comparisons_path, REPRO / "frozen_comparisons.csv"), (detector_path, REPRO / "detector_truth_audit.csv"), (decision_path, REPRO / "decision.json"), (DOC, REPRO / "results.md"), (REPO_ROOT / "docs" / "current" / f"sapr_{STUDY_VERSION}_coverage.json", REPRO / "coverage.json")):
        destination.write_bytes(source.read_bytes())
    checksums = write_checksum_manifest(REPRO, REPRO / "checksums.json")
    paths = {"sequence_metrics": metrics_path, "frozen_comparisons": comparisons_path, "detector_audit": detector_path, "decision": decision_path, "results": DOC, "checksums": REPRO / "checksums.json"}
    artifacts = {name: artifact_entry(path) for name, path in paths.items()}
    manifest_artifacts = {name: {"path": str(path.relative_to(REPO_ROOT)), "sha256": artifacts[name]["sha256"]} for name, path in paths.items()}
    atomic_write_json(OUT / "analysis_manifest.json", {"study": STUDY_VERSION, "status": "complete", "created_at": utc_now(), "task_count": len(archives), "coverage_passed": coverage["passed"], "decision": decision, "artifacts": manifest_artifacts, "reproducibility": checksums})
    print(json.dumps({"status": "complete", "tasks": len(archives), "decision": decision}, indent=2))


if __name__ == "__main__":
    run()
