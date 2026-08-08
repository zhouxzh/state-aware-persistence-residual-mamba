#!/usr/bin/env python
"""
Download non-stationary benchmark datasets from thuml/Time-Series-Library (HuggingFace).

Usage:
    python scripts/download_datasets.py              # download all datasets below
    python scripts/download_datasets.py --dry-run    # show what would be downloaded
    python scripts/download_datasets.py --datasets Exchange,ETT,Weather  # select subsets

Dataset groups:
    Exchange   – exchange_rate.csv  (8 series, daily)
    ETT        – ETTh1, ETTh2, ETTm1, ETTm2  (7 series, hour / 15-min)
    Electricity – electricity.csv  (321 clients, hourly)
    Traffic    – traffic.csv  (862 sensors, hourly)
    Weather    – weather.csv  (21 indicators, 10-min)
    ILI        – national_illness.csv  (7 series, weekly)
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

REPO_ID = "thuml/Time-Series-Library"
REPO_TYPE = "dataset"
DIRECT_BASE_URL = "https://huggingface.co/datasets/thuml/Time-Series-Library/resolve/main"

DATASET_GROUPS = {
    "Exchange": [
        ("exchange_rate/exchange_rate.csv", "data/Exchange/exchange_rate.csv"),
    ],
    "ETT": [
        ("ETT-small/ETTh1.csv", "data/ETT/ETTh1.csv"),
        ("ETT-small/ETTh2.csv", "data/ETT/ETTh2.csv"),
        ("ETT-small/ETTm1.csv", "data/ETT/ETTm1.csv"),
        ("ETT-small/ETTm2.csv", "data/ETT/ETTm2.csv"),
    ],
    "Electricity": [
        ("electricity/electricity.csv", "data/Electricity/electricity.csv"),
    ],
    "Traffic": [
        ("traffic/traffic.csv", "data/Traffic/traffic.csv"),
    ],
    "Weather": [
        ("weather/weather.csv", "data/Weather/weather.csv"),
    ],
    "ILI": [
        ("illness/national_illness.csv", "data/ILI/national_illness.csv"),
    ],
}

ALL_GROUPS = list(DATASET_GROUPS.keys())


def parse_args():
    parser = argparse.ArgumentParser(description="Download Time-Series-Library benchmark datasets")
    parser.add_argument(
        "--datasets",
        type=str,
        default=",".join(ALL_GROUPS),
        help=f"Comma-separated dataset groups to download. Choices: {ALL_GROUPS}",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print download plan without downloading")
    parser.add_argument(
        "--mirror",
        type=str,
        default="https://hf-mirror.com",
        help="HF endpoint override (default: https://hf-mirror.com)",
    )
    return parser.parse_args()


def download_file(repo_id, repo_type, repo_file, local_path, dry_run):
    """Download a single file from HuggingFace Hub using hf_hub_download."""
    from huggingface_hub import hf_hub_download

    dest = REPO_ROOT / local_path
    if dest.exists():
        print(f"  [skip] already exists: {local_path}")
        return

    if dry_run:
        print(f"  [plan] {repo_file}  ->  {local_path}")
        return

    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        temp_path = hf_hub_download(
            repo_id=repo_id,
            repo_type=repo_type,
            filename=repo_file,
            cache_dir=REPO_ROOT / "data" / ".hf_cache",
        )
        shutil.copy2(temp_path, dest)
    except Exception as exc:
        quoted_path = urllib.parse.quote(repo_file, safe="/")
        direct_url = f"{DIRECT_BASE_URL}/{quoted_path}?download=true"
        print(f"  [fallback] Hub client failed ({type(exc).__name__}); using direct resolve URL")
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix=f".{dest.name}.", suffix=".part", dir=dest.parent, delete=False
            ) as handle:
                temporary = Path(handle.name)
                with urllib.request.urlopen(direct_url, timeout=180) as response:
                    shutil.copyfileobj(response, handle)
            temporary.replace(dest)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
    print(f"  [done] {local_path}")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(selected):
    records = []
    for group_name in selected:
        for repo_file, local_path in DATASET_GROUPS[group_name]:
            path = REPO_ROOT / local_path
            if not path.is_file():
                continue
            records.append({
                "group": group_name,
                "source_repo": REPO_ID,
                "source_revision": "main",
                "source_path": repo_file,
                "local_path": local_path,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
    output = REPO_ROOT / "data" / "benchmark_download_manifest.json"
    temporary = output.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({"record_count": len(records), "records": records}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)
    print(f"Manifest: {output.relative_to(REPO_ROOT)} ({len(records)} files)")


def main():
    args = parse_args()
    os.environ["HF_ENDPOINT"] = args.mirror

    selected = [name.strip() for name in args.datasets.split(",") if name.strip()]
    invalid = [name for name in selected if name not in DATASET_GROUPS]
    if invalid:
        print(f"Unknown dataset groups: {invalid}. Choices: {ALL_GROUPS}")
        sys.exit(1)

    total_files = sum(len(DATASET_GROUPS[name]) for name in selected)
    print(f"Mirror: {args.mirror}")
    print(f"Groups: {selected}")
    print(f"Files:  {total_files}")
    if args.dry_run:
        print("(dry-run — no files will be written)\n")
    else:
        print()

    for group_name in selected:
        print(f"[{group_name}]")
        for repo_file, local_path in DATASET_GROUPS[group_name]:
            download_file(REPO_ID, REPO_TYPE, repo_file, local_path, args.dry_run)
        print()

    if not args.dry_run:
        write_manifest(selected)

    print("Done.")


if __name__ == "__main__":
    main()
