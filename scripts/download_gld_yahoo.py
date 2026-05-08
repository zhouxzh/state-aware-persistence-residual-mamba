#!/usr/bin/env python
"""Download or refresh GLD daily history from Yahoo Finance.

The repo expects the GLD file to look like:
    date,close,High,Low,Open,Volume

Default behavior:
- reads the existing output file if present
- starts 14 days before the latest saved date
- downloads fresh data from Yahoo Finance
- merges on `date` and keeps the newest row per date
- writes back to `data/GLD/GLD.csv`

Examples:
    python scripts/download_gld_yahoo.py
    conda run -n mamba python scripts/download_gld_yahoo.py
    https_proxy=http://127.0.0.1:7890 conda run -n mamba python scripts/download_gld_yahoo.py
    conda run -n mamba python scripts/download_gld_yahoo.py --https-proxy http://127.0.0.1:7890
    python scripts/download_gld_yahoo.py --full-history
    python scripts/download_gld_yahoo.py --out /tmp/GLD.csv
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "data" / "GLD" / "GLD.csv"
DEFAULT_SYMBOL = "GLD"
DEFAULT_START = "2004-11-18"
DEFAULT_END = "2026-04-30"
UPDATE_BUFFER_DAYS = 14
DEFAULT_HTTPS_PROXY = "http://127.0.0.1:7890"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download GLD data from Yahoo Finance.")
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL, help="Yahoo ticker symbol.")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output CSV path. Default: {DEFAULT_OUT.relative_to(REPO_ROOT)}",
    )
    parser.add_argument(
        "--start",
        default="",
        help="Inclusive start date in YYYY-MM-DD. If omitted, uses incremental update logic.",
    )
    parser.add_argument(
        "--end",
        default="",
        help=f"Inclusive end date in YYYY-MM-DD. Default: {DEFAULT_END}",
    )
    parser.add_argument(
        "--full-history",
        action="store_true",
        help="Ignore the existing CSV and download the full history from the default start date.",
    )
    parser.add_argument(
        "--https-proxy",
        default=DEFAULT_HTTPS_PROXY,
        help=f"HTTPS proxy URL. Default: {DEFAULT_HTTPS_PROXY}",
    )
    return parser.parse_args()


def require_yfinance():
    try:
        import yfinance as yf  # type: ignore
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing dependency: yfinance\n"
            "Install it with:\n"
            "  conda run -n mamba python -m pip install yfinance"
        ) from exc
    return yf


def configure_proxy(https_proxy: str) -> None:
    proxy = https_proxy or os.environ.get("https_proxy", "") or os.environ.get("HTTPS_PROXY", "")
    if not proxy:
        return
    os.environ["https_proxy"] = proxy
    os.environ["HTTPS_PROXY"] = proxy


def infer_start(out_path: Path, explicit_start: str, full_history: bool) -> str:
    if explicit_start:
        return explicit_start
    if full_history or not out_path.exists():
        return DEFAULT_START

    existing = pd.read_csv(out_path, usecols=["date"])
    if existing.empty:
        return DEFAULT_START

    latest = pd.to_datetime(existing["date"], errors="coerce").max()
    if pd.isna(latest):
        return DEFAULT_START
    return (latest.date() - timedelta(days=UPDATE_BUFFER_DAYS)).isoformat()


def infer_end_inclusive(explicit_end: str) -> str:
    if explicit_end:
        return explicit_end
    return DEFAULT_END


def yahoo_end_exclusive(end_inclusive: str) -> str:
    end_date = datetime.strptime(end_inclusive, "%Y-%m-%d").date()
    return (end_date + timedelta(days=1)).isoformat()


def normalize_download_frame(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if df.empty:
        raise SystemExit(f"Yahoo returned no rows for {symbol}.")

    if isinstance(df.columns, pd.MultiIndex):
        levels = [set(df.columns.get_level_values(i)) for i in range(df.columns.nlevels)]
        extracted = None
        for level in range(df.columns.nlevels):
            if symbol in levels[level]:
                extracted = df.xs(symbol, axis=1, level=level, drop_level=True)
                break
        if extracted is None:
            df.columns = [col[0] for col in df.columns]
        else:
            df = extracted

    frame = df.reset_index()
    date_col = "Date" if "Date" in frame.columns else frame.columns[0]
    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = [col for col in required if col not in frame.columns]
    if missing:
        raise SystemExit(f"Downloaded data is missing required columns: {missing}")

    frame = frame.rename(columns={date_col: "date", "Close": "close"})
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    frame = frame[["date", "close", "High", "Low", "Open", "Volume"]]
    frame = frame.dropna(subset=["date", "close", "High", "Low", "Open"])

    for col in ["close", "High", "Low", "Open"]:
        frame[col] = frame[col].astype(float)
    frame["Volume"] = frame["Volume"].fillna(0).round().astype("int64")

    frame = frame.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    return frame.reset_index(drop=True)


def merge_with_existing(out_path: Path, fresh: pd.DataFrame, end_inclusive: str) -> pd.DataFrame:
    if not out_path.exists():
        return clip_to_end(fresh, end_inclusive)

    existing = pd.read_csv(out_path)
    missing_cols = {"date", "close", "High", "Low", "Open", "Volume"} - set(existing.columns)
    if missing_cols:
        raise SystemExit(
            f"Existing file {out_path} does not match the expected schema. Missing: {sorted(missing_cols)}"
        )

    existing = existing[["date", "close", "High", "Low", "Open", "Volume"]]
    combined = pd.concat([existing, fresh], ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"], errors="coerce")
    combined = combined.dropna(subset=["date"])
    combined = combined.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    combined["date"] = combined["date"].dt.strftime("%Y-%m-%d")
    combined["Volume"] = combined["Volume"].fillna(0).round().astype("int64")
    combined = combined.reset_index(drop=True)
    return clip_to_end(combined, end_inclusive)


def clip_to_end(df: pd.DataFrame, end_inclusive: str) -> pd.DataFrame:
    end_ts = pd.to_datetime(end_inclusive)
    clipped = df.copy()
    clipped["date"] = pd.to_datetime(clipped["date"], errors="coerce")
    clipped = clipped.dropna(subset=["date"])
    clipped = clipped[clipped["date"] <= end_ts].sort_values("date").reset_index(drop=True)
    clipped["date"] = clipped["date"].dt.strftime("%Y-%m-%d")
    clipped["Volume"] = clipped["Volume"].fillna(0).round().astype("int64")
    return clipped


def download_history(symbol: str, start: str, end: str) -> pd.DataFrame:
    yf = require_yfinance()
    raw = yf.download(
        symbol,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=False,
        actions=False,
        progress=False,
        threads=False,
    )
    return normalize_download_frame(raw, symbol)


def main() -> None:
    args = parse_args()
    configure_proxy(args.https_proxy)
    out_path = args.out.resolve()
    start = infer_start(out_path, args.start, args.full_history)
    end_inclusive = infer_end_inclusive(args.end)
    end_exclusive = yahoo_end_exclusive(end_inclusive)

    fresh = download_history(args.symbol, start, end_exclusive)
    final = (
        merge_with_existing(out_path, fresh, end_inclusive)
        if not args.full_history
        else clip_to_end(fresh, end_inclusive)
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(out_path, index=False, float_format="%.6f")

    print(
        f"Downloaded {len(fresh)} Yahoo rows for {args.symbol} from {start} to {end_inclusive} "
        f"(Yahoo request end sent as {end_exclusive}, exclusive)."
    )
    print(f"Saved {len(final)} rows to {out_path}.")
    print(f"Date range: {final['date'].iloc[0]} -> {final['date'].iloc[-1]}")


if __name__ == "__main__":
    main()
