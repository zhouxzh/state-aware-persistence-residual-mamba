"""Download and causally prepare the independent public SAPR-Mamba panels."""

from __future__ import annotations

import csv
import io
import json
import shutil
import urllib.request
import zipfile
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .data import SeriesInfo, causal_forward_fill, split_points, stable_series_key
from .io import DATA_ROOT, atomic_write_json, config_hashes, load_configs, sha256_path, utc_now


RAW_ROOT = DATA_ROOT / "real" / "raw"
PROCESSED_ROOT = DATA_ROOT / "real" / "processed"
MANIFEST_PATH = DATA_ROOT / "real" / "data_manifest.json"


def _download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "SAPR-Mamba-reproducibility/1.0"})
    temporary = destination.with_name(f".{destination.name}.part")
    with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    temporary.replace(destination)


def _raw_record(url: str, target: Path) -> dict:
    if not target.exists():
        _download(url, target)
    return {"url": url, "path": str(target.relative_to(DATA_ROOT)), "bytes": target.stat().st_size, "sha256": sha256_path(target)}


def download_real_panels(force: bool = False) -> dict:
    """Fetch only configured original URLs and preserve license/source-page evidence locally."""
    config = load_configs()["real_panels"]
    if force and RAW_ROOT.exists():
        raise RuntimeError("Refusing destructive force download: retain immutable raw files and create a new protocol version instead")
    panels = config["panels"]
    result = {"manifest_version": config["manifest_version"], "retrieved_at": utc_now(), "config_hashes": config_hashes(), "panels": {}}
    for name, panel in panels.items():
        evidence_path = RAW_ROOT / "source_evidence" / f"{name}_source_page.html"
        source_page = _raw_record(panel["source_page"], evidence_path)
        entry = {"license": panel["license"], "source_page": source_page, "raw_files": []}
        if "source_url" in panel:
            suffix = ".zip" if panel["source_url"].endswith(".zip") else ".csv"
            entry["raw_files"].append(_raw_record(panel["source_url"], RAW_ROOT / name / f"source{suffix}"))
        else:
            license_url = "https://raw.githubusercontent.com/zhouhaoyi/ETDataset/main/LICENSE"
            entry["license_file"] = _raw_record(license_url, RAW_ROOT / name / "LICENSE")
            for file_id, url in panel["source_urls"].items():
                entry["raw_files"].append(_raw_record(url, RAW_ROOT / name / f"{file_id}.csv"))
        result["panels"][name] = entry
    atomic_write_json(MANIFEST_PATH, result)
    return result


def _write_prepared(panel_id: str, values: np.ndarray, eligibility: np.ndarray, infos: list[SeriesInfo], quality: list[dict]) -> dict:
    PROCESSED_ROOT.mkdir(parents=True, exist_ok=True)
    data_path = PROCESSED_ROOT / f"{panel_id}.npz"
    temporary = data_path.with_name(f".{data_path.name}.tmp")
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, values=values.astype(np.float32), eligibility=eligibility.astype(bool))
    temporary.replace(data_path)
    roster_path = PROCESSED_ROOT / f"{panel_id}_roster.json"
    atomic_write_json(roster_path, {"panel_id": panel_id, "records": [asdict(info) for info in infos], "quality": quality})
    return {"panel_id": panel_id, "data": str(data_path.relative_to(DATA_ROOT)), "data_sha256": sha256_path(data_path), "roster": str(roster_path.relative_to(DATA_ROOT)), "roster_sha256": sha256_path(roster_path), "series_count": len(infos)}


def _eligible_test_origin_count(eligibility: np.ndarray, train_end: int, valid_end: int, input_length: int, horizon: int) -> int:
    count = 0
    for origin in range(max(input_length, valid_end), len(eligibility) - horizon + 1, horizon):
        if eligibility[origin - input_length:origin + horizon].all():
            count += 1
    return count


def _panel_series(values: list[np.ndarray], ids: list[str], period: int, source: str, max_gap: int, minimum_fraction: float, cap: int | None, input_length: int, horizon: int, minimum_test_origins: int) -> tuple[np.ndarray, np.ndarray, list[SeriesInfo], list[dict]]:
    accepted = []
    quality = []
    for identifier, raw_values in zip(ids, values):
        original = np.asarray(raw_values, dtype=np.float64)
        cleaned, eligible = causal_forward_fill(original, max_gap)
        nonmissing_fraction = float(np.isfinite(original).mean())
        record = {"series_id": identifier, "nonmissing_fraction": nonmissing_fraction, "longest_unresolved_gap": int(_longest_false(eligible)), "included": False, "exclusion_reason": ""}
        if nonmissing_fraction < minimum_fraction:
            record["exclusion_reason"] = "nonmissing_fraction_below_threshold"
            quality.append(record)
            continue
        train_end, valid_end = split_points(len(cleaned))
        test_origins = _eligible_test_origin_count(eligible, train_end, valid_end, input_length, horizon)
        training_observed = cleaned[:train_end][np.isfinite(cleaned[:train_end])]
        if training_observed.size < 2:
            record["exclusion_reason"] = "insufficient_finite_training_observations"
            quality.append(record)
            continue
        record.update({
            "eligible_test_origins": test_origins,
            "training_mean": float(np.mean(training_observed)),
            "training_std": float(np.std(training_observed, ddof=0)),
        })
        if test_origins < minimum_test_origins:
            record["exclusion_reason"] = "eligible_test_origins_below_threshold"
            quality.append(record)
            continue
        accepted.append((identifier, cleaned, eligible, nonmissing_fraction, train_end, valid_end, record))
    accepted.sort(key=lambda item: stable_series_key(item[0]))
    if cap is not None:
        retained, excluded = accepted[:cap], accepted[cap:]
        for _, _, _, _, _, _, record in excluded:
            record["exclusion_reason"] = "hash_order_cap"
            quality.append(record)
        accepted = retained
    if not accepted:
        raise RuntimeError(f"No {source} series satisfy frozen quality rules")
    lengths = {len(item[1]) for item in accepted}
    if len(lengths) != 1:
        raise RuntimeError(f"{source} selected series have unequal regularized lengths")
    matrix = np.stack([item[1] for item in accepted])
    eligibility = np.stack([item[2] for item in accepted])
    infos = [SeriesInfo(identifier, period, train_end, valid_end, source) for identifier, _, _, _, train_end, _, _ in accepted]
    for _, _, _, _, _, _, record in accepted:
        record["included"] = True
        quality.append(record)
    return matrix, eligibility, infos, quality


def _longest_false(mask: np.ndarray) -> int:
    longest = current = 0
    for value in mask:
        current = 0 if value else current + 1
        longest = max(longest, current)
    return longest


def _prepare_electricity(config: dict) -> dict:
    import pandas as pd

    path = RAW_ROOT / "electricity" / "source.zip"
    with zipfile.ZipFile(path) as archive:
        candidates = [
            name for name in archive.namelist()
            if name.lower().endswith(".txt") and not name.startswith("__MACOSX/")
        ]
        if len(candidates) != 1:
            raise RuntimeError("Electricity archive does not contain exactly one text table")
        with archive.open(candidates[0]) as handle:
            frame = pd.read_csv(handle, sep=";", decimal=",", index_col=0, parse_dates=True)
    frame = frame.sort_index().asfreq("15min")
    values, eligibility, infos, quality = _panel_series(
        [frame[column].to_numpy() for column in frame.columns], list(frame.columns), int(config["period"]), "electricity",
        int(config["short_gap_limit"]), float(config["minimum_nonmissing_fraction"]), 100, int(config["input_length"]), max(config["horizons"]), int(config["minimum_eligible_test_origins"]),
    )
    return _write_prepared("electricity", values, eligibility, infos, quality)


def _prepare_beijing(config: dict) -> dict:
    import pandas as pd

    path = RAW_ROOT / "beijing_air_quality" / "source.zip"
    entries: list[np.ndarray] = []
    identifiers: list[str] = []
    with zipfile.ZipFile(path) as archive:
        nested = [name for name in archive.namelist() if name.lower().endswith(".zip") and "PRSA" in name]
        if len(nested) != 1:
            raise RuntimeError("Beijing archive must contain exactly one PRSA station-data archive")
        with zipfile.ZipFile(io.BytesIO(archive.read(nested[0]))) as station_archive:
            members = sorted(name for name in station_archive.namelist() if name.lower().endswith(".csv"))
            if not members:
                raise RuntimeError("Nested Beijing station archive contains no CSV files")
            for member in members:
                with station_archive.open(member) as handle:
                    frame = pd.read_csv(handle)
                required = {"year", "month", "day", "hour", "PM2.5", "station"}
                if not required.issubset(frame.columns):
                    raise RuntimeError(f"Beijing station member lacks required columns: {member}")
                index = pd.to_datetime(frame[["year", "month", "day", "hour"]])
                series = pd.Series(frame["PM2.5"].to_numpy(), index=index).sort_index().asfreq("h")
                station = str(frame["station"].iloc[0])
                entries.append(series.to_numpy())
                identifiers.append(station)
    values, eligibility, infos, quality = _panel_series(
        entries, identifiers, int(config["period"]), "beijing_air_quality", int(config["short_gap_limit"]),
        float(config["minimum_nonmissing_fraction"]), None, int(config["input_length"]), max(config["horizons"]), int(config["minimum_eligible_test_origins"]),
    )
    return _write_prepared("beijing_air_quality", values, eligibility, infos, quality)


def _prepare_ett(config: dict) -> list[dict]:
    import pandas as pd

    outputs = []
    for file_id, period in config["period_by_file"].items():
        frame = pd.read_csv(RAW_ROOT / "ett" / f"{file_id}.csv")
        if "OT" not in frame:
            raise RuntimeError(f"ETT file lacks OT target: {file_id}")
        values, eligibility, infos, quality = _panel_series(
            [frame["OT"].to_numpy()], [file_id], int(period), f"ett_{file_id}",
            max(1, int(round(float(period) * float(config["short_gap_fraction_of_period"])))),
            float(config["minimum_nonmissing_fraction"]), None, 4 * int(period), int(period), int(config["minimum_eligible_test_origins"]),
        )
        outputs.append(_write_prepared(f"ett_{file_id}", values, eligibility, infos, quality))
    return outputs


def prepare_real_panels() -> dict:
    if not MANIFEST_PATH.is_file():
        raise RuntimeError("No real data manifest; run download before preparation")
    config = load_configs()["real_panels"]["panels"]
    output = {"prepared_at": utc_now(), "config_hashes": config_hashes(), "panels": []}
    output["panels"].append(_prepare_electricity(config["electricity"]))
    output["panels"].append(_prepare_beijing(config["beijing_air_quality"]))
    output["panels"].extend(_prepare_ett(config["ett"]))
    atomic_write_json(PROCESSED_ROOT / "prepared_manifest.json", output)
    return output


def load_prepared_panel(panel_id: str) -> tuple[np.ndarray, np.ndarray, list[SeriesInfo], list[dict]]:
    data_path = PROCESSED_ROOT / f"{panel_id}.npz"
    roster_path = PROCESSED_ROOT / f"{panel_id}_roster.json"
    if not data_path.is_file() or not roster_path.is_file():
        raise FileNotFoundError(f"Prepared panel missing: {panel_id}")
    with np.load(data_path) as payload:
        values, eligibility = payload["values"], payload["eligibility"]
    roster = json.loads(roster_path.read_text(encoding="utf-8"))
    infos = [SeriesInfo(**record) for record in roster["records"]]
    metadata = []
    quality_by_id = {item["series_id"]: item for item in roster["quality"] if item["included"]}
    for info in infos:
        metadata.append({
            "series_id": info.series_id,
            "mechanism": "real",
            "strength": float("nan"),
            "training_mean": float(quality_by_id[info.series_id]["training_mean"]),
            "training_std": max(float(quality_by_id[info.series_id]["training_std"]), 1e-6),
        })
    return values, eligibility, infos, metadata
