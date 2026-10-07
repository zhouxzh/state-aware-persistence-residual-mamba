#!/usr/bin/env python
"""Audit and deterministically expand the V3 public-source candidate pool.

This command never ranks sources by model performance. It records only source
metadata and pre-model eligibility; parsers may be added in later protocol
amendments without mutating the verified V2 source manifests.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
import urllib.request
import zipfile
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("SAPR_MAMBA_VERSION", "v3")

from utils.sapr_mamba.data import SeriesInfo, causal_forward_fill, split_points, stable_series_key
from utils.sapr_mamba.features import causal_features, change_score
from utils.sapr_mamba.io import DATA_ROOT, atomic_write_json, config_hashes, sha256_path, utc_now


CONFIG_ROOT = REPO_ROOT / "configs" / "sapr_mamba_v3"
REGISTRY = CONFIG_ROOT / "candidate_sources.json"
AUDIT = DATA_ROOT / "source_pool_audit.json"
AMENDMENT = CONFIG_ROOT / "amendments" / "v3.1_public_multiseries_sources.json"
EXTENSION_ROOT = DATA_ROOT / "real" / "source_extensions" / "v3.1"


def _sha256(path: Path) -> str:
    return sha256_path(path)


def _data_path(path: Path) -> str:
    try:
        return str(path.relative_to(DATA_ROOT))
    except ValueError:
        return str(path)


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fetch(url: str, destination: Path, retries: int = 3, expected_bytes: int | None = None) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and (expected_bytes is None or destination.stat().st_size == expected_bytes):
        return
    if destination.exists():
        suffix = datetime.now().strftime("%Y%m%dT%H%M%S%f")
        destination.rename(destination.with_name(f"{destination.name}.invalid-{suffix}"))
    last_error = None
    for attempt in range(1, retries + 1):
        temporary = destination.with_name(f".{destination.name}.{attempt}.part")
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "SAPR-Mamba-V3/3.1"})
            with urllib.request.urlopen(request, timeout=180) as response, temporary.open("wb") as output:
                shutil.copyfileobj(response, output)
            if expected_bytes is not None and temporary.stat().st_size != expected_bytes:
                raise RuntimeError(f"byte_count_mismatch:{temporary.stat().st_size}:{expected_bytes}")
            os.replace(temporary, destination)
            return
        except Exception as exc:  # preserve each attempt's diagnostic before retrying
            last_error = repr(exc)
            if temporary.exists():
                suffix = datetime.now().strftime("%Y%m%dT%H%M%S%f")
                temporary.rename(temporary.with_name(f"{destination.name}.failed-{attempt}-{suffix}.part"))
    raise RuntimeError(f"download_failed:{url}:{last_error}")


def _validate_record(record: dict, source: dict) -> None:
    if record.get("metadata", {}).get("license", {}).get("id") != "cc-by-4.0":
        raise RuntimeError(f"license_not_verified:{source['source_id']}")
    files = {item["key"]: item for item in record.get("files", [])}
    item = files.get(source["archive_key"])
    if item is None:
        raise RuntimeError(f"zenodo_file_missing:{source['source_id']}")
    if int(item["size"]) != int(source["archive_bytes"]):
        raise RuntimeError(f"zenodo_size_changed:{source['source_id']}")
    if item.get("checksum", "").removeprefix("md5:") != source["zenodo_md5"]:
        raise RuntimeError(f"zenodo_checksum_changed:{source['source_id']}")


def _parse_tsf(archive_path: Path) -> tuple[list[dict], list[tuple[str, np.ndarray]]]:
    with zipfile.ZipFile(archive_path) as archive:
        members = sorted(name for name in archive.namelist() if name.lower().endswith(".tsf"))
        if len(members) != 1:
            raise RuntimeError(f"expected_one_tsf_file:{archive_path.name}:{members}")
        with archive.open(members[0]) as raw:
            header = []
            data_started = False
            records = []
            attributes = []
            for binary_line in raw:
                try:
                    line = binary_line.decode("utf-8-sig").strip()
                except UnicodeDecodeError:
                    line = binary_line.decode("latin-1").strip()
                if not line or line.startswith("#"):
                    continue
                if not data_started:
                    header.append(line)
                    if line.lower().startswith("@attribute"):
                        parts = line.split()
                        if len(parts) < 3:
                            raise RuntimeError(f"invalid_tsf_attribute:{line}")
                        attributes.append((parts[1], parts[2].lower()))
                    if line.lower() == "@data":
                        data_started = True
                    continue
                fields = line.split(":")
                if len(fields) != len(attributes) + 1:
                    raise RuntimeError(f"tsf_field_count_mismatch:{members[0]}:{len(fields)}:{len(attributes)}")
                metadata = fields[:-1]
                raw_values = fields[-1].split(",")
                values = np.asarray([
                    np.nan if token.strip() in {"", "?", "NaN", "nan"} else float(token)
                    for token in raw_values
                ], dtype=np.float64)
                id_index = next((i for i, item in enumerate(attributes) if item[1] == "string"), 0)
                records.append((metadata[id_index], values))
    if not data_started or not records:
        raise RuntimeError(f"empty_tsf_dataset:{archive_path.name}")
    return header, records


def _window_count(mask: np.ndarray, lower: int, input_length: int, horizon: int, stride: int) -> int:
    count = 0
    for origin in range(max(input_length, lower), len(mask) - horizon + 1, stride):
        if mask[origin - input_length:origin + horizon].all():
            count += 1
    return count


def _prepare_panel(source_id: str, source: dict, archive_path: Path, output_root: Path) -> dict:
    _header, raw_records = _parse_tsf(archive_path)
    period = int(source["period"])
    input_length = int(source["input_length"])
    horizons = [int(value) for value in source["horizons"]]
    maximum_horizon = max(horizons)
    eligible = []
    quality = []
    for series_id, raw_values in raw_records:
        original_length = len(raw_values)
        record = {"series_id": str(series_id), "original_length": original_length, "included": False, "exclusion_reason": ""}
        nonmissing = float(np.isfinite(raw_values).mean())
        record["nonmissing_fraction"] = nonmissing
        if nonmissing < float(source["minimum_nonmissing_fraction"]):
            record["exclusion_reason"] = "nonmissing_fraction_below_threshold"
            quality.append(record)
            continue
        try:
            train_end, valid_end = split_points(original_length)
        except ValueError:
            record["exclusion_reason"] = "series_too_short_for_chronological_split"
            quality.append(record)
            continue
        values, mask = causal_forward_fill(raw_values, int(source["maximum_gap"]))
        test_origins = _window_count(mask, valid_end, input_length, maximum_horizon, maximum_horizon)
        record.update({"train_end": train_end, "valid_end": valid_end, "eligible_test_origins": test_origins})
        minimum_origins = int(source.get("minimum_test_origins", 1))
        if original_length < input_length + maximum_horizon or test_origins < minimum_origins:
            record["exclusion_reason"] = "insufficient_length_or_test_origins"
            quality.append(record)
            continue
        train_mask = mask[:train_end]
        train_values = values[:train_end][train_mask]
        if train_values.size < 2:
            record["exclusion_reason"] = "insufficient_training_values"
            quality.append(record)
            continue
        record.update({
            "training_mean": float(np.mean(train_values)),
            "training_std": float(np.std(train_values, ddof=0)),
        })
        eligible.append((str(series_id), values, mask, record))

    eligible.sort(key=lambda item: stable_series_key(item[0]))
    selected = eligible[:int(source["series_cap"])]
    selected_ids = {item[0] for item in selected}
    for item in eligible[len(selected):]:
        row = item[3]
        row["exclusion_reason"] = "deterministic_series_cap"
        quality.append(row)
    if len(selected) < int(source["minimum_source_series"]):
        raise RuntimeError(f"source_below_minimum_independent_series:{source_id}:{len(selected)}")
    threshold_policy = source["state_threshold_policy"]
    training_scores = []
    sequence_test_scores = {}
    for series_id, values, mask, quality_row in selected:
        train_end, valid_end = int(quality_row["train_end"]), int(quality_row["valid_end"])
        for origin in range(input_length, train_end - maximum_horizon + 1, maximum_horizon):
            if mask[origin - input_length:origin + maximum_horizon].all():
                phi = causal_features(values[origin - input_length:origin], period, 1e-6)
                training_scores.append(change_score(phi))
        test_scores = []
        for origin in range(max(input_length, valid_end), len(values) - maximum_horizon + 1, maximum_horizon):
            if mask[origin - input_length:origin + maximum_horizon].all():
                phi = causal_features(values[origin - input_length:origin], period, 1e-6)
                test_scores.append(change_score(phi))
        sequence_test_scores[series_id] = test_scores
    if not training_scores:
        raise RuntimeError(f"no_training_windows_for_state_threshold:{source_id}")
    threshold = float(np.clip(
        np.quantile(np.asarray(training_scores, dtype=np.float64), float(threshold_policy["quantile"])),
        float(threshold_policy["minimum"]),
        float(threshold_policy["maximum"]),
    ))
    for _series_id, _values, _mask, quality_row in selected:
        scores = sequence_test_scores[_series_id]
        quality_row["stable_test_origins"] = sum(score < threshold for score in scores)
        quality_row["change_test_origins"] = sum(score >= threshold for score in scores)
    stable_series = sum(row["stable_test_origins"] > 0 for _, _, _, row in selected)
    change_series = sum(row["change_test_origins"] > 0 for _, _, _, row in selected)
    maximum_length = max(len(item[1]) for item in selected)
    matrix = np.zeros((len(selected), maximum_length), dtype=np.float32)
    eligibility = np.zeros((len(selected), maximum_length), dtype=bool)
    infos = []
    for index, (series_id, values, mask, quality_row) in enumerate(selected):
        matrix[index, :len(values)] = values
        eligibility[index, :len(mask)] = mask
        quality_row["included"] = True
        quality.append(quality_row)
        infos.append({
            "series_id": series_id,
            "period": period,
            "train_end": int(quality_row["train_end"]),
            "valid_end": int(quality_row["valid_end"]),
            "source": source_id,
            "mechanism": "real",
            "strength": None,
            "change_point": -1,
        })
    output_root.mkdir(parents=True, exist_ok=True)
    data_path = output_root / f"{source_id}.npz"
    roster_path = output_root / f"{source_id}_roster.json"
    temporary = data_path.with_name(f".{data_path.name}.tmp")
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, values=matrix, eligibility=eligibility)
    os.replace(temporary, data_path)
    atomic_write_json(roster_path, {"panel_id": source_id, "records": infos, "quality": quality})
    return {
        "panel_id": source_id,
        "source_cluster": source["source_cluster"],
        "domain": source["domain"],
        "external_holdout": bool(source["external_holdout"]),
        "change_threshold": threshold,
        "threshold_source": threshold_policy["source"],
        "threshold_training_windows": len(training_scores),
        "stable_test_series": stable_series,
        "change_test_series": change_series,
        "stable_coverage_eligible": stable_series >= int(threshold_policy["minimum_test_series_per_state"]),
        "change_coverage_eligible": change_series >= int(threshold_policy["minimum_test_series_per_state"]),
        "data": _data_path(data_path),
        "data_sha256": sha256_path(data_path),
        "roster": _data_path(roster_path),
        "roster_sha256": sha256_path(roster_path),
        "series_count": len(selected),
        "original_series_count": len(raw_records),
        "horizons": horizons,
    }


def prepare_extension() -> dict:
    amendment = json.loads(AMENDMENT.read_text(encoding="utf-8"))
    extension_root = EXTENSION_ROOT
    raw_root = extension_root / "raw"
    processed_root = extension_root / "processed"
    output = {"amendment_id": amendment["amendment_id"], "prepared_at": utc_now(), "sources": []}
    for source_id in amendment["source_selection_order"]:
        source = dict(amendment["datasets"][source_id])
        source.setdefault("source_cluster", amendment["source_clusters"][source_id])
        source.setdefault(
            "external_holdout",
            amendment["source_clusters"][source_id] in amendment["external_holdout_clusters"],
        )
        source.setdefault("series_cap", amendment["deterministic_series_cap"])
        source.setdefault("minimum_source_series", amendment["minimum_eligible_series_per_source"])
        source.setdefault("minimum_test_origins", amendment["minimum_test_origins_per_series"])
        source.setdefault("state_threshold_policy", amendment["state_threshold_policy"])
        record_path = raw_root / source_id / "zenodo_record.json"
        archive_path = raw_root / source_id / source["archive_key"]
        _fetch(source["record_api"], record_path)
        record = json.loads(record_path.read_text(encoding="utf-8"))
        _validate_record(record, source)
        _fetch(source["source_url"], archive_path, expected_bytes=int(source["archive_bytes"]))
        if _md5(archive_path) != source["zenodo_md5"]:
            raise RuntimeError(f"archive_checksum_mismatch:{source_id}")
        output["sources"].append(_prepare_panel(source_id, source, archive_path, processed_root))
        output["sources"][-1]["raw_archive"] = str(archive_path.relative_to(DATA_ROOT))
        output["sources"][-1]["raw_archive_sha256"] = sha256_path(archive_path)
    atomic_write_json(extension_root / "prepared_manifest.json", output)
    atomic_write_json(extension_root / "state_thresholds.json", {
        "amendment_id": amendment["amendment_id"],
        "source": amendment["state_threshold_policy"]["source"],
        "thresholds": {item["panel_id"]: item["change_threshold"] for item in output["sources"]},
        "prepared_manifest_sha256": sha256_path(extension_root / "prepared_manifest.json"),
    })
    print(json.dumps(output, indent=2, sort_keys=True))
    return output


def integrate_extension() -> dict:
    """Atomically expose prepared amendment panels to the resumable V3 runner."""
    extension_root = EXTENSION_ROOT
    manifest_path = extension_root / "prepared_manifest.json"
    thresholds_path = extension_root / "state_thresholds.json"
    if not manifest_path.is_file() or not thresholds_path.is_file():
        raise RuntimeError("V3.1 extension sources must be prepared before integration")
    extension = json.loads(manifest_path.read_text(encoding="utf-8"))
    main_processed = DATA_ROOT / "real" / "processed"
    main_processed.mkdir(parents=True, exist_ok=True)
    copied = []
    for panel in extension["sources"]:
        for key, suffix in (("data", ".npz"), ("roster", "_roster.json")):
            # Prepared-manifest paths are relative to the V3 data root, not
            # the repository root (e.g. ``real/source_extensions/v3.1/...``).
            source = DATA_ROOT / panel[key]
            destination = main_processed / (panel["panel_id"] + suffix)
            if destination.exists():
                if sha256_path(destination) != sha256_path(source):
                    raise RuntimeError(f"refusing_to_overwrite_existing_panel:{panel['panel_id']}")
            else:
                temporary = destination.with_name(f".{destination.name}.tmp")
                shutil.copy2(source, temporary)
                os.replace(temporary, destination)
            copied.append({"path": str(destination.relative_to(DATA_ROOT)), "sha256": sha256_path(destination)})
    thresholds = json.loads(thresholds_path.read_text(encoding="utf-8"))
    active_thresholds_path = DATA_ROOT / "real" / "source_thresholds_v3.1.json"
    atomic_write_json(active_thresholds_path, thresholds)
    prepared_path = main_processed / "prepared_manifest.json"
    existing = json.loads(prepared_path.read_text(encoding="utf-8"))
    existing_panels = {item["panel_id"] for item in existing["panels"]}
    added = [item for item in extension["sources"] if item["panel_id"] not in existing_panels]
    if added:
        updated = dict(existing)
        updated["prepared_at_v3_1"] = utc_now()
        updated["amendment_id"] = extension["amendment_id"]
        updated["panels"] = [*existing["panels"], *added]
        updated["source_extension_manifest_sha256"] = sha256_path(manifest_path)
        atomic_write_json(prepared_path, updated)
    else:
        updated = existing
    amendment = json.loads(AMENDMENT.read_text(encoding="utf-8"))
    result = {
        "amendment_id": extension["amendment_id"],
        "integrated_panels": [item["panel_id"] for item in added],
        "prepared_panel_count": len(updated["panels"]),
        "prepared_manifest_sha256": sha256_path(prepared_path),
        "thresholds_path": str(active_thresholds_path.relative_to(DATA_ROOT)),
        "thresholds_sha256": sha256_path(active_thresholds_path),
        "copied_artifacts": copied,
    }
    from utils.sapr_mamba.io import code_hashes, git_state

    lock_path = CONFIG_ROOT / "amendments" / "v3.1_protocol.lock.json"
    amendment_lock = {
        "amendment_id": extension["amendment_id"],
        "parent_protocol_lock": str((CONFIG_ROOT / "protocol.lock.json").relative_to(REPO_ROOT)),
        "parent_protocol_lock_sha256": sha256_path(CONFIG_ROOT / "protocol.lock.json"),
        "amendment_sha256": sha256_path(AMENDMENT),
        "prepared_manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "prepared_manifest_sha256": sha256_path(manifest_path),
        "integrated_manifest_sha256": sha256_path(prepared_path),
        "thresholds_sha256": sha256_path(active_thresholds_path),
        "source_cluster_policy": amendment["source_clusters"],
        "external_holdout_clusters": amendment["external_holdout_clusters"],
        "code_hashes": code_hashes(),
        "git": git_state(),
        "frozen_at": utc_now(),
    }
    if lock_path.exists():
        existing_lock = json.loads(lock_path.read_text(encoding="utf-8"))
        comparable = {key: value for key, value in amendment_lock.items() if key not in {"git", "frozen_at"}}
        old_comparable = {key: value for key, value in existing_lock.items() if key not in {"git", "frozen_at"}}
        if comparable != old_comparable:
            raise RuntimeError("refusing_to_overwrite_v3_1_protocol_lock")
    else:
        atomic_write_json(lock_path, amendment_lock)
    result["amendment_lock"] = str(lock_path.relative_to(REPO_ROOT))
    result["amendment_lock_sha256"] = sha256_path(lock_path)
    atomic_write_json(extension_root / "integration_manifest.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def audit_sources() -> dict:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    entries = []
    for order, source in enumerate(registry["sources"], start=1):
        status = source.get("status", "candidate")
        if status == "verified_v2_reuse":
            eligibility = "eligible_existing_parser"
        elif source.get("parser") == "generic_datetime_numeric":
            eligibility = "candidate_requires_parser_and_license_check"
        else:
            eligibility = "candidate_requires_audit"
        entries.append({
            "order": order,
            "source_id": source["source_id"],
            "domain": source["domain"],
            "cluster": source["cluster"],
            "external_holdout": bool(source.get("external_holdout", False)),
            "status": status,
            "eligibility": eligibility,
            "source_url": source["source_url"],
            "license": source["license"],
        })
    payload = {
        "study": "sapr_mamba_v3",
        "audited_at": utc_now(),
        "selection_rule": registry["selection_rule"],
        "config_hashes": config_hashes(),
        "registry_sha256": sha256_path(REGISTRY),
        "sources": entries,
        "eligible_existing": [row["source_id"] for row in entries if row["eligibility"] == "eligible_existing_parser"],
        "candidate_expansion_order": [row["source_id"] for row in entries if row["eligibility"] != "eligible_existing_parser"],
        "status": "complete_with_limitations" if any(row["eligibility"] != "eligible_existing_parser" for row in entries) else "complete",
    }
    atomic_write_json(AUDIT, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("audit", "prepare", "integrate"), default="audit")
    args = parser.parse_args()
    action = {"audit": audit_sources, "prepare": prepare_extension, "integrate": integrate_extension}[args.stage]
    action()


if __name__ == "__main__":
    main()
