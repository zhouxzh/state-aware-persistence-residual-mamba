#!/usr/bin/env python
"""Prepare the locked KDD Cup 2018 V8 external confirmation source."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("SAPR_MAMBA_VERSION", "v8")

from scripts.sapr_mamba_v3_sources import _parse_tsf, _prepare_panel
from utils.sapr_mamba.io import DATA_ROOT, atomic_write_json, sha256_path, utc_now


CONFIG = REPO_ROOT / "configs" / "sapr_mamba_v8" / "real_panels.json"
PANEL = "kdd_cup_2018"
RAW = DATA_ROOT / "real" / "raw" / PANEL
PROCESSED = DATA_ROOT / "real" / "processed"


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download_ranges(url: str, destination: Path, total: int) -> None:
    if destination.is_file() and destination.stat().st_size == total:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    part = destination.with_name(f".{destination.name}.range.part")
    if part.exists() and part.stat().st_size > total:
        part.unlink()
    offset = part.stat().st_size if part.exists() else 0
    chunk = 512 * 1024
    with part.open("ab") as handle:
        while offset < total:
            end = min(total - 1, offset + chunk - 1)
            for attempt in range(1, 4):
                try:
                    request = urllib.request.Request(url, headers={"User-Agent": "SAPR-Mamba-V8/1.0", "Accept-Encoding": "identity", "Range": f"bytes={offset}-{end}"})
                    with urllib.request.urlopen(request, timeout=300) as response:
                        data, content_range = response.read(), response.headers.get("Content-Range", "")
                    if content_range != f"bytes {offset}-{end}/{total}" or len(data) != end - offset + 1:
                        raise RuntimeError(f"range_response_mismatch:{content_range}:{len(data)}")
                    handle.write(data); handle.flush(); os.fsync(handle.fileno())
                    offset = end + 1
                    break
                except Exception:
                    if attempt == 3:
                        raise
                    time.sleep(attempt)
    if part.stat().st_size != total:
        raise RuntimeError("range_download_incomplete")
    part.replace(destination)


def prepare() -> dict:
    source = json.loads(CONFIG.read_text(encoding="utf-8"))["panels"][PANEL]
    record_path, archive_path = RAW / "zenodo_record.json", RAW / source["archive_key"]
    if not record_path.is_file():
        request = urllib.request.Request(source["record_api"], headers={"User-Agent": "SAPR-Mamba-V8/1.0"})
        with urllib.request.urlopen(request, timeout=60) as response:
            record_path.parent.mkdir(parents=True, exist_ok=True)
            record_path.write_bytes(response.read())
    record = json.loads(record_path.read_text(encoding="utf-8"))
    item = {entry["key"]: entry for entry in record.get("files", [])}.get(source["archive_key"])
    if record.get("metadata", {}).get("license", {}).get("id") != "cc-by-4.0" or item is None:
        raise RuntimeError("KDD source metadata or license changed")
    if int(item["size"]) != int(source["archive_bytes"]) or item.get("checksum", "").removeprefix("md5:") != source["zenodo_md5"]:
        raise RuntimeError("KDD source archive metadata changed")
    download_ranges(source["source_url"], archive_path, int(source["archive_bytes"]))
    if md5(archive_path) != source["zenodo_md5"]:
        raise RuntimeError("KDD archive MD5 mismatch")
    _, parsed = _parse_tsf(archive_path)
    prepared_source = dict(source)
    prepared_source.update({"source_cluster": source["source_cluster"], "domain": "environment", "external_holdout": True, "state_threshold_policy": {"source": "selected_series_train_windows_only", "quantile": 0.75, "minimum": 1.5, "maximum": 4.0, "minimum_test_series_per_state": 20}})
    result = _prepare_panel(PANEL, prepared_source, archive_path, PROCESSED)
    result.update({"raw_archive": str(archive_path.relative_to(DATA_ROOT)), "raw_archive_sha256": sha256_path(archive_path), "record": str(record_path.relative_to(DATA_ROOT)), "record_sha256": sha256_path(record_path), "parsed_series_count": len(parsed)})
    manifest = {"study": "sapr_mamba_v8", "prepared_at": utc_now(), "source": result, "selection_uses_test_results": False}
    atomic_write_json(PROCESSED / "prepared_manifest.json", {"prepared_at": manifest["prepared_at"], "panels": [result]})
    atomic_write_json(DATA_ROOT / "real" / "external_confirmation_manifest.json", manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    prepare()
