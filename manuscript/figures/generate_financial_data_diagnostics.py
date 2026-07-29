#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


FIGURE_DIR = Path(__file__).resolve().parent
REPO_ROOT = FIGURE_DIR.parents[1]
PROTOCOL_PATH = REPO_ROOT / "configs" / "financial_benchmark.json"
DATA_ROOT = REPO_ROOT / "data" / "financial"
QUALITY_REPORT = DATA_ROOT / "manifests" / "quality_report.json"
PANEL_ORDER = ("fx", "yields", "cross_asset", "crypto")
PANEL_LABELS = {
    "fx": "Foreign exchange: GBP/USD",
    "yields": "Treasury yields: 10-year",
    "cross_asset": "Cross asset: GLD",
    "crypto": "Cryptoasset: BTC/USDT",
}
BLUE = "#0072B2"
VERMILLION = "#D55E00"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot frozen financial data diagnostics.")
    parser.add_argument(
        "--include-test",
        action="store_true",
        help="Plot the final period; requires unlocked full diagnostics.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    quality_payload = json.loads(QUALITY_REPORT.read_text(encoding="utf-8"))
    quality = {record["dataset"]: record for record in quality_payload["datasets"]}
    suffix = "full" if args.include_test else "selection_safe"
    diagnostics_path = DATA_ROOT / "manifests" / f"nonstationarity_diagnostics_{suffix}.json"
    if not diagnostics_path.is_file():
        raise RuntimeError(f"missing diagnostics: {diagnostics_path}")
    diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    if diagnostics.get("protocol_sha256") != hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest():
        raise RuntimeError("diagnostic protocol hash mismatch")
    if bool(diagnostics.get("test_targets_read")) != bool(args.include_test):
        raise RuntimeError("diagnostic evidence scope does not match the requested figure")

    figure, axes = plt.subplots(
        len(PANEL_ORDER),
        2,
        figsize=(11.2, 9.0),
        sharex="row",
        constrained_layout=True,
    )
    train_end = pd.Timestamp(protocol["splits"]["train_end"])
    validation_start = pd.Timestamp(protocol["splits"]["validation_start"])
    validation_end = pd.Timestamp(protocol["splits"]["validation_end"])
    test_start = pd.Timestamp(protocol["splits"]["test_start"])
    rolling_window = int(protocol["nonstationarity_diagnostics"]["rolling_window"])

    for row_index, name in enumerate(PANEL_ORDER):
        config = protocol["datasets"][name]
        nrows = None
        if not args.include_test:
            counts = quality[name]["split_counts"]
            nrows = int(counts["train"] + counts["validation"])
        frame = pd.read_csv(DATA_ROOT / "processed" / f"{name}.csv", nrows=nrows)
        dates = pd.to_datetime(frame["date"], errors="raise")
        target = frame[config["target"]].astype(float)
        train = target[dates <= train_end]
        standardized = (target - train.mean()) / train.std(ddof=1)
        trailing_volatility = target.diff().rolling(rolling_window).std().shift(1)
        train_volatility = trailing_volatility[dates <= train_end].dropna()
        volatility_ratio = trailing_volatility / train_volatility.median()

        level_axis, volatility_axis = axes[row_index]
        level_axis.plot(dates, standardized, color=BLUE, linewidth=0.9)
        volatility_axis.plot(dates, volatility_ratio, color=VERMILLION, linewidth=0.9)
        for axis in (level_axis, volatility_axis):
            axis.axvspan(validation_start, validation_end, color="#E6E6E6", alpha=0.8, linewidth=0)
            axis.axvline(validation_start, color="#555555", linewidth=0.8, linestyle="--")
            if args.include_test:
                axis.axvline(test_start, color="#111111", linewidth=0.9, linestyle=":")
            axis.axhline(0.0 if axis is level_axis else 1.0, color="#777777", linewidth=0.6)
            axis.grid(axis="y", color="#D9D9D9", linewidth=0.5)
            axis.spines[["top", "right"]].set_visible(False)
            axis.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=7))
            axis.xaxis.set_major_formatter(mdates.ConciseDateFormatter(axis.xaxis.get_major_locator()))
        level_axis.set_ylabel(PANEL_LABELS[name], fontsize=9)

    axes[0, 0].set_title("Target level standardized by training data", fontsize=10)
    axes[0, 1].set_title(f"Trailing {rolling_window}-observation difference volatility", fontsize=10)
    axes[-1, 0].set_xlabel("Date")
    axes[-1, 1].set_xlabel("Date")

    stem = f"financial_nonstationarity_{suffix}"
    metadata = {
        "Title": "Financial nonstationarity diagnostics",
        "Author": "Generated from financial_confirmatory_v1 data artifacts",
        "Subject": diagnostics["scope"],
    }
    figure.savefig(FIGURE_DIR / f"{stem}.pdf", metadata=metadata)
    figure.savefig(
        FIGURE_DIR / f"{stem}.png",
        dpi=300,
        metadata={"Software": "Matplotlib", "Scope": diagnostics["scope"]},
    )
    plt.close(figure)
    print(f"wrote {FIGURE_DIR / (stem + '.pdf')}")
    print(f"wrote {FIGURE_DIR / (stem + '.png')}")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"Financial diagnostic figure generation blocked: {exc}") from None
