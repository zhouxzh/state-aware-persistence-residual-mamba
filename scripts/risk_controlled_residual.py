#!/usr/bin/env python
"""Theory-first Stage A runner for risk-controlled capped residual admission.

No trainable model is fit.  Calibration repeats operate on independent complete
series, and target tests remain locked until all calibration decisions freeze.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import resource
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from scipy.special import gamma, roots_genlaguerre, roots_hermitenorm

from utils.sapr_mamba.io import atomic_write_json, sha256_path, utc_now


CONFIG = ROOT / os.environ.get("RCR_CONFIG_DIR", "configs/risk_controlled_residual_v1")
RUN = ROOT / os.environ.get("RCR_RUN_ROOT", "results/risk_controlled_residual_v1")
RUN_ID = os.environ.get("RCR_RUN_ID", "risk_controlled_residual_v1")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def config() -> dict:
    return read_json(CONFIG / "protocol.json")


def paths() -> dict[str, Path]:
    root = RUN.resolve()
    if ROOT not in (root, *root.parents):
        raise RuntimeError("risk-controlled run root must remain inside this repository")
    values = {name: root / name for name in ("protocol", "pilot", "chunks", "target", "metrics", "reports", "failures", "monitor", "logs")}
    return values | {"root": root}


def digest(path: Path) -> str:
    return sha256_path(path)


def source_hashes() -> dict[str, str]:
    return {
        "runner": digest(Path(__file__)),
        "protocol_config": digest(CONFIG / "protocol.json"),
        "research_plan": digest(ROOT / "docs/RISK_CONTROLLED_RESIDUAL_RESEARCH_PLAN.md"),
    }


def stable_seed(*parts: object) -> int:
    raw = "|".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big") % (2**63 - 1)


def panel_items(protocol: dict) -> list[tuple[str, np.ndarray]]:
    return [(name, np.asarray(theta, dtype=np.float64)) for name, theta in protocol["panels"].items()]


def candidate_coefficients(protocol: dict, count: int) -> np.ndarray:
    values = np.asarray(protocol["candidate_coefficients"], dtype=np.float64)
    if count > len(values):
        raise ValueError(f"candidate count {count} exceeds frozen coefficient list")
    return values[:count]


def expected_loss(theta: float, shift: float, protocol: dict, normal_nodes: int, radial_nodes: int) -> float:
    """E||Y-shift*v||/sqrt(H) using deterministic Gaussian quadrature.

    The direction parallel to v is integrated with Gauss-Hermite.  The squared
    perpendicular norm is chi-square(H-1), integrated with generalized Laguerre.
    """
    horizon, sigma = int(protocol["horizon"]), float(protocol["sigma"])
    z, wz = roots_hermitenorm(int(normal_nodes))
    radial, wr = roots_genlaguerre(int(radial_nodes), (horizon - 1) / 2 - 1)
    mean_parallel = (float(theta) - float(shift)) * math.sqrt(horizon) / sigma
    length = np.sqrt((mean_parallel + z[:, None]) ** 2 + 2.0 * radial[None, :])
    expectation = float(np.sum((wz[:, None] / math.sqrt(2 * math.pi)) * (wr[None, :] / gamma((horizon - 1) / 2)) * length))
    return sigma * expectation / math.sqrt(horizon)


def risk_delta(theta: float, shift: float, protocol: dict, normal_nodes: int, radial_nodes: int) -> float:
    return expected_loss(theta, shift, protocol, normal_nodes, radial_nodes) - expected_loss(theta, 0.0, protocol, normal_nodes, radial_nodes)


def true_target_risk(theta: float, shift: float, rho: float, protocol: dict, nodes: tuple[int, int]) -> float:
    source = risk_delta(theta, shift, protocol, *nodes)
    contamination = risk_delta(-1.0, shift, protocol, *nodes)
    return (1.0 - float(rho)) * source + float(rho) * contamination


def beta(cap: float, candidates: int, groups: int, alpha: float, n: int) -> float:
    return float(cap) * math.sqrt(2.0 * math.log(2.0 * candidates * groups / float(alpha)) / int(n))


def prior_seeds_and_ids() -> tuple[set[int], set[str]]:
    seeds, identifiers = set(), set()
    for path in ROOT.glob("results/*/protocol/*.json"):
        try:
            payload = read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        for key in ("generator_seed", "random_seed"):
            if key in payload:
                seeds.add(int(payload[key]))
        seeds.update(int(value) for value in payload.get("training_seeds", []))
    for path in ROOT.glob("results/*/data/*roster.json"):
        try:
            identifiers.update(str(item["series_id"]) for item in read_json(path).get("records", []))
        except (OSError, json.JSONDecodeError, KeyError):
            continue
    return seeds, identifiers


def require_sealed() -> tuple[dict, dict[str, Path]]:
    protocol, destination = config(), paths()
    sealed = destination["protocol"] / "protocol.json"
    if not sealed.is_file():
        raise RuntimeError("risk-controlled protocol must be sealed")
    payload = read_json(sealed)
    allowed = {"sealed", "literature_passed", "pilot_passed", "main_running", "main_complete", "target_complete", "complete"}
    if payload.get("status") not in allowed:
        raise RuntimeError(f"unexpected protocol status: {payload.get('status')!r}")
    if payload.get("source_hashes") != source_hashes():
        raise RuntimeError("source or configuration hash differs from sealed risk-controlled protocol")
    return protocol, destination


def seal() -> None:
    protocol, destination = config(), paths()
    sealed = destination["protocol"] / "protocol.json"
    if sealed.exists():
        raise RuntimeError("protocol already sealed; use a new namespace for any revision")
    for path in destination.values():
        path.mkdir(parents=True, exist_ok=True)
    prior_seeds, prior_ids = prior_seeds_and_ids()
    new_streams = {int(protocol["random_seed"])} | {stable_seed(protocol["random_seed"], stage) for stage in ("pilot", "main", "target", "analysis")}
    if new_streams & prior_seeds:
        raise RuntimeError(f"seed collision: {sorted(new_streams & prior_seeds)}")
    trial_ids = {f"{protocol['series_id_prefix']}{stage}_{index:06d}" for stage in ("pilot", "main", "target") for index in range(4)}
    if trial_ids & prior_ids:
        raise RuntimeError("series ID collision")
    grid = protocol["grid"]
    expected = len(protocol["panels"]) * len(grid["cap_sigma"]) * len(grid["candidate_counts"]) * len(grid["calibration_series_per_group"]) * len(grid["rho"])
    if expected != 384:
        raise RuntimeError(f"unexpected main grid size: {expected}")
    payload = dict(protocol) | {
        "status": "sealed",
        "sealed_at": utc_now(),
        "run_id": RUN_ID,
        "source_hashes": source_hashes(),
        "expected_main_cells": expected,
        "test_access": "locked",
        "target_numeric_materialized": False,
    }
    atomic_write_json(sealed, payload)
    atomic_write_json(destination["protocol"] / "seed_manifest.json", {"status": "passed", "prior_seed_count": len(prior_seeds), "prior_id_count": len(prior_ids), "new_streams": sorted(new_streams), "seed_intersection": [], "series_id_intersection": [], "created_at": utc_now()})
    print(json.dumps({"status": "sealed", "main_cells": expected, "target_numeric_materialized": False}, indent=2))


def literature_gate() -> None:
    protocol, destination = require_sealed()
    records = []
    for query in protocol["literature_gate"]["queries"]:
        url = "https://api.crossref.org/works?" + urllib.parse.urlencode({"query": query, "rows": 5, "select": "DOI,title,author,published,container-title,type"})
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                items = json.loads(response.read().decode("utf-8"))["message"]["items"]
            records.append({"query": query, "status": "retrieved", "items": items})
        except Exception as exc:
            records.append({"query": query, "status": "unavailable", "error": repr(exc), "items": []})
    report = {"status": "passed_conservative_no_novelty_claim", "created_at": utc_now(), "policy": protocol["literature_gate"]["policy"], "records": records, "publication_framing": "theory/application benchmark; no automated novelty claim"}
    atomic_write_json(destination["reports"] / "literature_gate.json", report)
    sealed = read_json(destination["protocol"] / "protocol.json"); sealed["status"] = "literature_passed"; atomic_write_json(destination["protocol"] / "protocol.json", sealed)
    print(json.dumps({"status": report["status"], "queries": len(records)}, indent=2))


def losses(theta: np.ndarray, cap: float, coefficients: np.ndarray, protocol: dict, repeats: int, n_max: int, rng: np.random.Generator) -> np.ndarray:
    """Returns D[repeat, group, sequence, candidate] on source distribution P."""
    horizon, sigma = int(protocol["horizon"]), float(protocol["sigma"])
    normal = rng.normal(size=(repeats, len(theta), n_max))
    radial = rng.chisquare(horizon - 1, size=(repeats, len(theta), n_max))
    parallel = theta[None, :, None] * math.sqrt(horizon) / sigma + normal
    baseline = np.sqrt(parallel ** 2 + radial) * sigma / math.sqrt(horizon)
    shifts = coefficients * float(cap) * math.sqrt(horizon) / sigma
    candidate = np.sqrt((parallel[..., None] - shifts[None, None, None, :]) ** 2 + radial[..., None]) * sigma / math.sqrt(horizon)
    return candidate - baseline[..., None]


def cell_key(panel: str, cap: float, k: int, n: int, rho: float) -> str:
    return f"{panel}|c{cap:.5g}|K{k}|n{n}|rho{rho:.5g}"


def empty_summary() -> dict:
    return {"repeats": 0, "accept_count": 0, "error_accept_count": 0, "fallback_count": 0, "selected_counts": defaultdict(int), "mean_selected_worst_sum": 0.0}


def select_candidate(upper: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Apply the frozen all-group rule, returning IDs and selected bounds.

    ``upper`` is indexed repeat, group, candidate.  ``argmin`` provides the
    predeclared lowest-candidate-ID tie break because candidates retain their
    frozen order.
    """
    feasible = np.all(upper <= 0.0, axis=1)
    worst = np.max(upper, axis=1)
    masked = np.where(feasible, worst, np.inf)
    selected = np.argmin(masked, axis=1)
    selected[np.all(~feasible, axis=1)] = -1
    chosen_worst = np.where(selected >= 0, masked[np.arange(len(selected)), selected.clip(min=0)], np.nan)
    return selected, chosen_worst


def quadrature_audit(protocol: dict) -> dict:
    """Check the frozen production quadrature against the denser audit rule."""
    low_nodes = (int(protocol["truth"]["normal_nodes"]), int(protocol["truth"]["radial_nodes"]))
    high_nodes = (int(protocol["truth"]["validation_normal_nodes"]), int(protocol["truth"]["validation_radial_nodes"]))
    tolerance = float(protocol["truth"]["absolute_tolerance"])
    comparisons = []
    for panel_name, theta in panel_items(protocol):
        for theta_g in theta:
            for cap in protocol["grid"]["cap_sigma"]:
                for coefficient in candidate_coefficients(protocol, len(protocol["candidate_coefficients"])):
                    shift = float(cap) * float(coefficient)
                    low = risk_delta(float(theta_g), shift, protocol, *low_nodes)
                    high = risk_delta(float(theta_g), shift, protocol, *high_nodes)
                    comparisons.append({"panel": panel_name, "theta": float(theta_g), "cap": float(cap), "coefficient": float(coefficient), "low": low, "high": high, "absolute_difference": abs(low - high)})
    maximum = max(item["absolute_difference"] for item in comparisons)
    if maximum > tolerance:
        raise RuntimeError(f"quadrature audit failed: {maximum:.3e} exceeds {tolerance:.3e}")
    return {"status": "passed", "production_nodes": low_nodes, "validation_nodes": high_nodes, "tolerance": tolerance, "maximum_absolute_difference": maximum, "comparisons": comparisons}


def update_summary(summary: dict, selected: np.ndarray, worst: np.ndarray, harmful: np.ndarray) -> None:
    summary["repeats"] += len(selected)
    accepted = selected >= 0
    summary["accept_count"] += int(np.sum(accepted))
    summary["fallback_count"] += int(np.sum(~accepted))
    summary["error_accept_count"] += int(np.sum(accepted & harmful))
    summary["mean_selected_worst_sum"] += float(np.sum(worst[accepted]))
    for item in selected[accepted]:
        summary["selected_counts"][str(int(item))] += 1


def finalize_summary(summary: dict) -> dict:
    repeats = max(int(summary["repeats"]), 1)
    accepted = int(summary["accept_count"])
    return {
        "repeats": repeats,
        "accept_count": accepted,
        "fallback_count": int(summary["fallback_count"]),
        "error_accept_count": int(summary["error_accept_count"]),
        "accept_rate": accepted / repeats,
        "fallback_rate": int(summary["fallback_count"]) / repeats,
        "error_accept_rate": int(summary["error_accept_count"]) / repeats,
        "mean_selected_worst_upper": None if not accepted else float(summary["mean_selected_worst_sum"]) / accepted,
        "selected_counts": dict(summary["selected_counts"]),
    }


def simulate_chunk(protocol: dict, panel_name: str, theta: np.ndarray, start: int, count: int, n_max: int, caps: list[float], candidate_counts: list[int], sample_sizes: list[int], rhos: list[float], seed_namespace: str) -> dict:
    rng = np.random.default_rng(stable_seed(protocol["random_seed"], seed_namespace, panel_name, start))
    groups, alpha = int(protocol["groups"]), float(protocol["alpha"])
    high_nodes = (int(protocol["truth"]["validation_normal_nodes"]), int(protocol["truth"]["validation_radial_nodes"]))
    records = {}
    for cap in caps:
        coefficients = candidate_coefficients(protocol, max(candidate_counts))
        values = losses(theta, cap, coefficients, protocol, count, n_max, rng)
        cumulative = np.cumsum(values, axis=2)
        for n in sample_sizes:
            means = cumulative[:, :, int(n) - 1, :] / float(n)
            for k in candidate_counts:
                radius = beta(cap, k, groups, alpha, n)
                for rho in rhos:
                    # Truth is evaluated per target mixture.  It must not use
                    # a loop-local rho from an earlier cell.
                    truth = np.asarray([[true_target_risk(float(theta[g]), float(coefficients[j] * cap), float(rho), protocol, high_nodes) for g in range(groups)] for j in range(k)])
                    harmful_candidates = np.any(truth > 0.0, axis=1)
                    upper = means[:, :, :k] + radius + 2.0 * cap * float(rho)
                    selected, chosen_worst = select_candidate(upper)
                    key = cell_key(panel_name, cap, k, n, rho)
                    bucket = empty_summary()
                    update_summary(bucket, selected, chosen_worst, np.where(selected >= 0, harmful_candidates[selected.clip(min=0)], False))
                    records[key] = finalize_summary(bucket)
    return {"panel": panel_name, "start": start, "count": count, "records": records}


def merge_records(target: dict, source: dict) -> None:
    for key, row in source.items():
        current = target.setdefault(key, empty_summary())
        repeats, accepted = int(row["repeats"]), int(row["accept_count"])
        current["repeats"] += repeats
        current["accept_count"] += accepted
        current["fallback_count"] += int(row["fallback_count"])
        current["error_accept_count"] += int(row["error_accept_count"])
        if row["mean_selected_worst_upper"] is not None:
            current["mean_selected_worst_sum"] += float(row["mean_selected_worst_upper"]) * accepted
        for candidate, count in row["selected_counts"].items():
            current["selected_counts"][candidate] += int(count)


def run_calibration(stage: str) -> None:
    protocol, destination = require_sealed()
    if stage == "pilot":
        setting = protocol["pilot"]
        repeats, n_max = int(setting["repeats_per_panel"]), int(setting["source_series_per_group"])
        caps, counts, samples, rhos = [float(setting["cap_sigma"])], [int(setting["candidate_count"])], [n_max], list(setting["rho"])
        output = destination["pilot"] / "calibration.json"
    else:
        setting = protocol["grid"]
        repeats, n_max = int(setting["calibration_repeats"]), max(map(int, setting["calibration_series_per_group"]))
        caps, counts, samples, rhos = list(map(float, setting["cap_sigma"])), list(map(int, setting["candidate_counts"])), list(map(int, setting["calibration_series_per_group"])), list(map(float, setting["rho"]))
        output = destination["metrics"] / "calibration_summary.csv"
    chunks = []
    step = int(protocol["resources"]["chunk_repeats"])
    for panel_name, theta in panel_items(protocol):
        for start in range(0, repeats, step):
            path = destination["chunks"] / stage / panel_name / f"{start:06d}.json"
            if not path.is_file():
                result = simulate_chunk(protocol, panel_name, theta, start, min(step, repeats - start), n_max, caps, counts, samples, rhos, stage)
                atomic_write_json(path, result)
            chunks.append(path)
    aggregate = {}
    for path in chunks:
        merge_records(aggregate, read_json(path)["records"])
    rows = []
    for key, row in sorted(aggregate.items()):
        panel, cap, k, n, rho = key.split("|")
        payload = finalize_summary(row)
        rows.append({"panel": panel, "cap": cap, "candidate_count": k, "series_per_group": n, "rho": rho, **payload})
    if stage == "pilot":
        elapsed = sum(path.stat().st_size for path in chunks)
        report = {"status": "measured", "created_at": utc_now(), "cells": len(rows), "chunk_files": len(chunks), "bytes": elapsed, "results": rows, "target_numeric_materialized": False}
        atomic_write_json(output, report)
        print(json.dumps({"status": "pilot_measured", "cells": len(rows)}, indent=2))
    else:
        columns = ("panel", "cap", "candidate_count", "series_per_group", "rho", "repeats", "accept_count", "fallback_count", "error_accept_count", "accept_rate", "fallback_rate", "error_accept_rate", "mean_selected_worst_upper", "selected_counts")
        with output.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns); writer.writeheader(); writer.writerows(rows)
        atomic_write_json(destination["metrics"] / "calibration_manifest.json", {"status": "complete", "created_at": utc_now(), "cells": len(rows), "chunk_files": len(chunks), "summary_sha256": digest(output), "target_numeric_materialized": False})
        sealed = read_json(destination["protocol"] / "protocol.json"); sealed["status"] = "main_complete"; atomic_write_json(destination["protocol"] / "protocol.json", sealed)
        print(json.dumps({"status": "main_complete", "cells": len(rows)}, indent=2))


def pilot_target_validation(protocol: dict) -> dict:
    """Use the separate pilot stream to check target generation and quadrature.

    These draws are deliberately kept under ``pilot/`` and cannot be reused by
    the locked 100,000-series target test.
    """
    setting = protocol["pilot"]
    horizon, sigma = int(protocol["horizon"]), float(protocol["sigma"])
    count, cap = int(setting["target_series_per_group"]), float(setting["cap_sigma"])
    coefficients = candidate_coefficients(protocol, int(setting["candidate_count"]))
    nodes = (int(protocol["truth"]["validation_normal_nodes"]), int(protocol["truth"]["validation_radial_nodes"]))
    rows = []
    for panel_name, theta in panel_items(protocol):
        for rho in map(float, setting["rho"]):
            for group, theta_g in enumerate(theta):
                rng = np.random.default_rng(stable_seed(protocol["random_seed"], "pilot_target", panel_name, rho, group))
                contaminated = rng.random(count) < rho
                target_theta = np.where(contaminated, -1.0, float(theta_g))
                parallel = target_theta * math.sqrt(horizon) / sigma + rng.normal(size=count)
                radial = rng.chisquare(horizon - 1, size=count)
                baseline = np.sqrt(parallel**2 + radial) * sigma / math.sqrt(horizon)
                for candidate_id, coefficient in enumerate(coefficients):
                    shift = float(coefficient) * cap * math.sqrt(horizon) / sigma
                    observed = np.sqrt((parallel - shift) ** 2 + radial) * sigma / math.sqrt(horizon) - baseline
                    analytic = true_target_risk(float(theta_g), float(coefficient) * cap, rho, protocol, nodes)
                    rows.append({"panel": panel_name, "rho": rho, "group": group, "candidate_id": candidate_id, "series": count, "estimate": float(np.mean(observed)), "analytic": analytic, "absolute_difference": abs(float(np.mean(observed)) - analytic)})
    return {"series_per_group": count, "rows": rows, "maximum_absolute_difference": max(row["absolute_difference"] for row in rows)}


def pilot() -> None:
    protocol, destination = require_sealed()
    if not (destination["reports"] / "literature_gate.json").is_file():
        raise RuntimeError("literature gate must run before pilot")
    started, cpu_started = time.monotonic(), time.process_time()
    run_calibration("pilot")
    elapsed, cpu_elapsed = time.monotonic() - started, time.process_time() - cpu_started
    resources = protocol["resources"]
    if elapsed > float(resources["max_wall_hours"]) * 3600:
        raise RuntimeError("pilot exceeded wall-clock budget")
    setting, grid = protocol["pilot"], protocol["grid"]
    pilot_work = len(protocol["panels"]) * int(setting["repeats_per_panel"]) * int(setting["source_series_per_group"]) * int(setting["candidate_count"])
    main_work = len(protocol["panels"]) * int(grid["calibration_repeats"]) * max(map(int, grid["calibration_series_per_group"])) * len(protocol["candidate_coefficients"]) * len(grid["cap_sigma"])
    projected_cpu_hours = cpu_elapsed * main_work / pilot_work / 3600.0
    if projected_cpu_hours > float(resources["max_cpu_core_hours"]):
        raise RuntimeError(f"pilot projects {projected_cpu_hours:.2f} CPU-core-hours, above the frozen {resources['max_cpu_core_hours']} limit")
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    memory_limit = float(resources["max_memory_gib"]) * 1024**3
    if peak_rss > memory_limit:
        raise RuntimeError("pilot exceeded frozen process-memory limit")
    pilot_report = read_json(destination["pilot"] / "calibration.json") | {
        "elapsed_seconds": elapsed,
        "cpu_seconds": cpu_elapsed,
        "peak_rss_bytes": peak_rss,
        "memory_limit_bytes": memory_limit,
        "projected_main_cpu_core_hours": projected_cpu_hours,
        "quadrature_audit": quadrature_audit(protocol),
        "target_generation_validation": pilot_target_validation(protocol),
        "status": "passed",
    }
    atomic_write_json(destination["pilot"] / "calibration.json", pilot_report)
    sealed = read_json(destination["protocol"] / "protocol.json")
    sealed["status"] = "pilot_passed"
    atomic_write_json(destination["protocol"] / "protocol.json", sealed)


def main_grid() -> None:
    protocol, destination = require_sealed()
    if not (destination["pilot"] / "calibration.json").is_file() or read_json(destination["pilot"] / "calibration.json").get("status") != "passed":
        raise RuntimeError("pilot must pass before the main grid")
    if (destination["target"] / "target_test_access.json").exists():
        raise RuntimeError("target test access ledger already exists")
    started, cpu_started = time.monotonic(), time.process_time()
    sealed = read_json(destination["protocol"] / "protocol.json"); sealed["status"] = "main_running"; atomic_write_json(destination["protocol"] / "protocol.json", sealed)
    run_calibration("main")
    elapsed = time.monotonic() - started
    core_hours = (time.process_time() - cpu_started) / 3600.0
    if core_hours > float(protocol["resources"]["max_cpu_core_hours"]):
        raise RuntimeError("main grid exceeded CPU-core-hour budget")
    manifest = read_json(destination["metrics"] / "calibration_manifest.json") | {"elapsed_seconds": elapsed, "estimated_cpu_core_hours": core_hours}
    atomic_write_json(destination["metrics"] / "calibration_manifest.json", manifest)


def target_test() -> None:
    protocol, destination = require_sealed()
    if read_json(destination["protocol"] / "protocol.json").get("status") != "main_complete":
        raise RuntimeError("main grid must complete before target test")
    ledger = destination["target"] / "target_test_access.json"
    if ledger.exists():
        raise RuntimeError("target test is one-time only")
    atomic_write_json(ledger, {"status": "authorized_once", "created_at": utc_now(), "target_numeric_materialized": True})
    horizon, sigma = int(protocol["horizon"]), float(protocol["sigma"])
    m = int(protocol["target_test"]["simultaneous_entries"])
    size, chunk = int(protocol["target_test"]["series_per_group"]), int(protocol["target_test"]["chunk_size"])
    rows = []
    for panel_name, theta in panel_items(protocol):
        for rho in protocol["grid"]["rho"]:
            for group, theta_g in enumerate(theta):
                sums = {(cap, index): 0.0 for cap in protocol["grid"]["cap_sigma"] for index in range(len(protocol["candidate_coefficients"]))}
                rng = np.random.default_rng(stable_seed(protocol["random_seed"], "target", panel_name, rho, group))
                seen = 0
                while seen < size:
                    width = min(chunk, size - seen)
                    contaminate = rng.random(width) < float(rho)
                    target_theta = np.where(contaminate, -1.0, float(theta_g))
                    normal = rng.normal(size=width)
                    radial = rng.chisquare(horizon - 1, size=width)
                    parallel = target_theta * math.sqrt(horizon) / sigma + normal
                    baseline = np.sqrt(parallel**2 + radial) * sigma / math.sqrt(horizon)
                    for cap in protocol["grid"]["cap_sigma"]:
                        coefficients = candidate_coefficients(protocol, len(protocol["candidate_coefficients"]))
                        shifts = coefficients * float(cap) * math.sqrt(horizon) / sigma
                        candidate = np.sqrt((parallel[:, None] - shifts[None, :]) ** 2 + radial[:, None]) * sigma / math.sqrt(horizon)
                        values = candidate - baseline[:, None]
                        for index in range(values.shape[1]):
                            sums[(cap, index)] += float(values[:, index].sum())
                    seen += width
                for cap in protocol["grid"]["cap_sigma"]:
                    radius = float(cap) * math.sqrt(2.0 * math.log(2.0 * m / float(protocol["eta"])) / size)
                    for index, coefficient in enumerate(protocol["candidate_coefficients"]):
                        estimate = sums[(cap, index)] / size
                        rows.append({"panel": panel_name, "rho": rho, "group": group, "cap": cap, "candidate_id": index, "coefficient": coefficient, "series": size, "estimate": estimate, "lower": estimate - radius, "upper": estimate + radius, "test_radius": radius})
    output = destination["target"] / "target_risk.csv"
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    atomic_write_json(ledger, read_json(ledger) | {"target_risk_sha256": digest(output), "rows": len(rows), "target_numeric_materialized": True})
    sealed = read_json(destination["protocol"] / "protocol.json"); sealed["status"] = "target_complete"; sealed["target_numeric_materialized"] = True; atomic_write_json(destination["protocol"] / "protocol.json", sealed)
    print(json.dumps({"status": "target_complete", "rows": len(rows)}, indent=2))


def analyze() -> None:
    protocol, destination = require_sealed()
    if read_json(destination["protocol"] / "protocol.json").get("status") != "target_complete":
        raise RuntimeError("target test must complete before analysis")
    calibration = list(csv.DictReader((destination["metrics"] / "calibration_summary.csv").open(encoding="utf-8", newline="")))
    target = list(csv.DictReader((destination["target"] / "target_risk.csv").open(encoding="utf-8", newline="")))
    decision = {cell_key(row["panel"], float(row["cap"].removeprefix("c")), int(row["candidate_count"].removeprefix("K")), int(row["series_per_group"].removeprefix("n")), float(row["rho"].removeprefix("rho"))): row for row in calibration}
    target_index = {(row["panel"], float(row["rho"]), float(row["cap"]), int(row["candidate_id"]), int(row["group"])): row for row in target}
    audits = []
    for key, row in decision.items():
        selected = json.loads(row["selected_counts"].replace("'", '"')) if row["selected_counts"] else {}
        audits.append({"cell": key, "accept_rate": float(row["accept_rate"]), "fallback_rate": float(row["fallback_rate"]), "error_accept_rate": float(row["error_accept_rate"]), "target_rows_available": sum((row["panel"], float(row["rho"].removeprefix("rho")), float(row["cap"].removeprefix("c")), int(candidate), group) in target_index for candidate in selected for group in range(int(protocol["groups"])))})
    report = {"status": "complete", "created_at": utc_now(), "protocol_version": protocol["protocol_version"], "conservative_literature_framing": "theory/application benchmark; no novelty claim", "calibration_summary_sha256": digest(destination["metrics"] / "calibration_summary.csv"), "target_risk_sha256": digest(destination["target"] / "target_risk.csv"), "literature_gate_sha256": digest(destination["reports"] / "literature_gate.json"), "audit_rows": audits}
    atomic_write_json(destination["reports"] / "analysis_report.json", report)
    sealed = read_json(destination["protocol"] / "protocol.json"); sealed["status"] = "complete"; atomic_write_json(destination["protocol"] / "protocol.json", sealed)
    print(json.dumps({"status": "complete", "cells": len(audits)}, indent=2))


def verify() -> None:
    protocol, destination = require_sealed()
    required = [destination["reports"] / "literature_gate.json", destination["pilot"] / "calibration.json", destination["metrics"] / "calibration_summary.csv", destination["target"] / "target_risk.csv", destination["reports"] / "analysis_report.json"]
    missing = [str(path) for path in required if not path.is_file()]
    result = {"status": "passed" if not missing else "failed", "created_at": utc_now(), "missing": missing, "hashes": {str(path.relative_to(destination["root"])): digest(path) for path in required if path.is_file()}, "target_access": read_json(destination["target"] / "target_test_access.json") if (destination["target"] / "target_test_access.json").is_file() else None}
    atomic_write_json(destination["reports"] / "release_binding.json", result)
    if missing:
        raise RuntimeError("missing required Stage A outputs")
    print(json.dumps(result, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("seal", "literature-gate", "pilot", "main", "target-test", "analyze", "verify"):
        commands.add_parser(name)
    args = parser.parse_args()
    if args.command == "seal": seal()
    elif args.command == "literature-gate": literature_gate()
    elif args.command == "pilot": pilot()
    elif args.command == "main": main_grid()
    elif args.command == "target-test": target_test()
    elif args.command == "analyze": analyze()
    else: verify()


if __name__ == "__main__":
    main()
