#!/usr/bin/env python
import csv
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MAMBA_BEST = REPO_ROOT / "results" / "gld_mamba_hpo_best.csv"
SOURCE_BEST = REPO_ROOT / "results" / "gld_source_optimized_best.csv"
PREFERRED_LONG_HORIZONS = [120, 180, 270, 360]
DIAGNOSTIC_LONG_HORIZONS = [120, 180, 360]


def load_rows(path):
    if not path.exists():
        return []
    with path.open() as f:
        rows = list(csv.DictReader(f))
    parsed = []
    for row in rows:
        if row.get("status") != "complete":
            continue
        try:
            row["horizon"] = int(row["horizon"])
            row["rmse"] = float(row["rmse"])
            row["mae"] = float(row["mae"])
        except (KeyError, TypeError, ValueError):
            continue
        parsed.append(row)
    return parsed


def avg(values):
    return sum(values) / len(values)


def group_by_name(rows, name_key):
    grouped = defaultdict(dict)
    for row in rows:
        grouped[row[name_key]][row["horizon"]] = row
    return grouped


def choose_long_horizons(grouped):
    if any(
        all(horizon in by_horizon for horizon in PREFERRED_LONG_HORIZONS)
        for by_horizon in grouped.values()
    ):
        return PREFERRED_LONG_HORIZONS
    return DIAGNOSTIC_LONG_HORIZONS


def complete_long_summary(grouped, long_horizons):
    summaries = []
    for name, by_horizon in grouped.items():
        if not all(horizon in by_horizon for horizon in long_horizons):
            continue
        rows = [by_horizon[horizon] for horizon in long_horizons]
        summaries.append(
            {
                "name": name,
                "rmse": avg([row["rmse"] for row in rows]),
                "mae": avg([row["mae"] for row in rows]),
            }
        )
    return sorted(summaries, key=lambda row: row["rmse"])


def main():
    mamba_rows = load_rows(MAMBA_BEST)
    source_rows = load_rows(SOURCE_BEST)

    print("Mamba HPO best rows:")
    print(f"  {MAMBA_BEST.relative_to(REPO_ROOT)}")
    print(f"  complete rows: {len(mamba_rows)}")

    if not mamba_rows:
        print("No completed Mamba HPO rows found yet.")
        return

    mamba_grouped = group_by_name(mamba_rows, "variant")
    long_horizons = choose_long_horizons(mamba_grouped)
    print(f"Long-horizon summary uses: {long_horizons}")

    mamba_summary = complete_long_summary(mamba_grouped, long_horizons)
    if not mamba_summary:
        print(f"No Mamba variant has all long horizons {long_horizons} yet.")
    else:
        print("Mamba HPO long-horizon ranking by RMSE:")
        for item in mamba_summary:
            print(f"  {item['name']}: RMSE={item['rmse']:.4f}, MAE={item['mae']:.4f}")

    if not source_rows:
        print("No source-optimized baseline rows found for comparison.")
        return

    source_summary = complete_long_summary(group_by_name(source_rows, "model"), long_horizons)
    if source_summary:
        print("Source-optimized long-horizon reference:")
        for item in source_summary:
            if item["name"] in {"PatchTST", "NLinear", "TimesNet"}:
                print(f"  {item['name']}: RMSE={item['rmse']:.4f}, MAE={item['mae']:.4f}")

    if mamba_summary and source_summary:
        best_mamba = mamba_summary[0]
        best_source = source_summary[0]
        delta = (best_source["rmse"] - best_mamba["rmse"]) / best_source["rmse"] * 100
        print("Best Mamba vs best source-optimized model:")
        print(
            f"  {best_mamba['name']} RMSE={best_mamba['rmse']:.4f} "
            f"vs {best_source['name']} RMSE={best_source['rmse']:.4f} "
            f"({delta:+.2f}% relative RMSE change)"
        )


if __name__ == "__main__":
    main()
