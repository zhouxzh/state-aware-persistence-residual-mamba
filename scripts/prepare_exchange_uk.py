#!/usr/bin/env python3
"""Extract the non-missing United Kingdom rate used by the S-mode benchmark."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO_ROOT / "data" / "Exchange" / "daily.csv"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "Exchange" / "exchange_rate.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify that the existing output matches the deterministic extraction.",
    )
    return parser.parse_args()


def extract(input_path: Path) -> pd.DataFrame:
    raw = pd.read_csv(input_path)
    required = {"Date", "Country", "Exchange rate"}
    missing = required - set(raw.columns)
    if missing:
        raise SystemExit(f"Missing columns in {input_path}: {sorted(missing)}")

    selected = raw.loc[raw["Country"].eq("United Kingdom"), ["Date", "Exchange rate"]].copy()
    selected["Date"] = pd.to_datetime(selected["Date"], errors="raise")
    selected["Exchange rate"] = pd.to_numeric(selected["Exchange rate"], errors="coerce")
    selected = selected.dropna(subset=["Exchange rate"]).sort_values("Date")
    if selected["Date"].duplicated().any():
        raise SystemExit("Duplicate United Kingdom dates remain after filtering")

    selected["Date"] = selected["Date"].dt.strftime("%Y-%m-%d")
    return selected.rename(columns={"Date": "date", "Exchange rate": "OT"}).reset_index(drop=True)


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve()
    output_path = args.output.resolve()
    expected = extract(input_path)

    if args.check:
        if not output_path.exists():
            raise SystemExit(f"Output does not exist: {output_path}")
        observed = pd.read_csv(output_path, dtype={"date": str})
        observed["OT"] = pd.to_numeric(observed["OT"], errors="raise")
        if not observed.equals(expected):
            raise SystemExit(f"Output differs from deterministic extraction: {output_path}")
        print(f"verified {len(expected)} rows in {output_path.relative_to(REPO_ROOT)}")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    expected.to_csv(output_path, index=False)
    print(f"wrote {len(expected)} rows to {output_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
