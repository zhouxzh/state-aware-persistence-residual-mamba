#!/usr/bin/env python
"""Prepare the predeclared Traffic Hourly V7 external confirmation source."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("SAPR_MAMBA_VERSION", "v7")

from scripts.sapr_mamba_v3_sources import _parse_tsf, _prepare_panel
from utils.sapr_mamba.io import DATA_ROOT, atomic_write_json, sha256_path, utc_now


CONFIG = REPO_ROOT / "configs" / "sapr_mamba_v7" / "real_panels.json"
RAW = DATA_ROOT / "real" / "raw" / "traffic_hourly"
PROCESSED = DATA_ROOT / "real" / "processed"


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, destination: Path, expected_bytes: int | None = None, retries: int = 3) -> None:
    if destination.is_file() and (expected_bytes is None or destination.stat().st_size == expected_bytes):
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
        destination.replace(destination.with_name(f"{destination.name}.invalid-{stamp}"))
    if expected_bytes is not None:
        # The public mirror occasionally truncates large streaming responses.
        # Fetch independently verifiable byte ranges and resume an interrupted
        # local transfer rather than accepting an incomplete archive.
        partial = destination.with_name(f".{destination.name}.range.part")
        if partial.exists() and partial.stat().st_size > expected_bytes:
            partial.unlink()
        offset = partial.stat().st_size if partial.exists() else 0
        chunk_size = 512 * 1024
        with partial.open("ab") as handle:
            while offset < expected_bytes:
                end = min(expected_bytes - 1, offset + chunk_size - 1)
                last_error: Exception | None = None
                for attempt in range(1, retries + 1):
                    try:
                        request = urllib.request.Request(url, headers={
                            "User-Agent": "SAPR-Mamba-V7/1.0", "Accept-Encoding": "identity",
                            "Range": f"bytes={offset}-{end}",
                        })
                        with urllib.request.urlopen(request, timeout=300) as response:
                            content_range = response.headers.get("Content-Range", "")
                            expected_range = f"bytes {offset}-{end}/{expected_bytes}"
                            data = response.read()
                        if content_range != expected_range or len(data) != end - offset + 1:
                            raise RuntimeError(f"range_response_mismatch:{content_range}:{len(data)}")
                        handle.write(data)
                        handle.flush()
                        os.fsync(handle.fileno())
                        offset = end + 1
                        break
                    except Exception as exc:
                        last_error = exc
                        time.sleep(attempt)
                else:
                    raise RuntimeError(f"range_download_failed:{destination.name}:{offset}:{last_error!r}")
        if partial.stat().st_size != expected_bytes:
            raise RuntimeError(f"range_download_incomplete:{partial.stat().st_size}:{expected_bytes}")
        partial.replace(destination)
        return
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        temporary = destination.with_name(f".{destination.name}.{attempt}.part")
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "SAPR-Mamba-V7/1.0", "Accept-Encoding": "identity"})
            with urllib.request.urlopen(request, timeout=300) as response, temporary.open("wb") as handle:
                shutil.copyfileobj(response, handle, length=1024 * 1024)
            if expected_bytes is not None and temporary.stat().st_size != expected_bytes:
                raise RuntimeError(f"download_byte_count_mismatch:{temporary.stat().st_size}:{expected_bytes}")
            temporary.replace(destination)
            return
        except Exception as exc:
            last_error = exc
            if temporary.exists():
                stamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
                temporary.replace(temporary.with_name(f"{destination.name}.invalid-attempt{attempt}-{stamp}"))
            time.sleep(attempt)
    raise RuntimeError(f"download_failed:{destination.name}:{last_error!r}")


def prepare() -> dict:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))["panels"]["traffic_hourly"]
    record_path = RAW / "zenodo_record.json"
    archive_path = RAW / config["archive_key"]
    download(config["record_api"], record_path)
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if record.get("metadata", {}).get("license", {}).get("id") != "cc-by-4.0":
        raise RuntimeError("Traffic Hourly Zenodo license is no longer CC BY 4.0")
    files = {item["key"]: item for item in record.get("files", [])}
    item = files.get(config["archive_key"])
    if item is None or int(item["size"]) != int(config["archive_bytes"]):
        raise RuntimeError("Traffic Hourly Zenodo file metadata changed")
    if item.get("checksum", "").removeprefix("md5:") != config["zenodo_md5"]:
        raise RuntimeError("Traffic Hourly Zenodo MD5 changed")
    download(config["source_url"], archive_path, int(config["archive_bytes"]))
    if archive_path.stat().st_size != int(config["archive_bytes"]) or md5(archive_path) != config["zenodo_md5"]:
        raise RuntimeError("Traffic Hourly archive integrity check failed")
    _, parsed = _parse_tsf(archive_path)
    source = dict(config)
    source.update({
        "source_cluster": config["source_cluster"], "domain": "transport", "external_holdout": True,
        "state_threshold_policy": {"source": "selected_series_train_windows_only", "quantile": 0.75, "minimum": 1.5, "maximum": 4.0, "minimum_test_series_per_state": 20},
    })
    result = _prepare_panel("traffic_hourly", source, archive_path, PROCESSED)
    result.update({
        "raw_archive": str(archive_path.relative_to(DATA_ROOT)), "raw_archive_sha256": sha256_path(archive_path),
        "record": str(record_path.relative_to(DATA_ROOT)), "record_sha256": sha256_path(record_path), "parsed_series_count": len(parsed),
    })
    manifest = {"study": "sapr_mamba_v7", "prepared_at": utc_now(), "source": result, "selection_uses_test_results": False}
    atomic_write_json(PROCESSED / "prepared_manifest.json", {"prepared_at": manifest["prepared_at"], "panels": [result]})
    atomic_write_json(DATA_ROOT / "real" / "external_confirmation_manifest.json", manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


if __name__ == "__main__":
    prepare()
