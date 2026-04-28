#!/usr/bin/env python
import csv
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_CSV = REPO_ROOT / "results" / "gld_baselines.csv"
NS_CSV = REPO_ROOT / "results" / "gld_ns_mamba_ablation.csv"
LONG_HORIZONS = [120, 180, 360]
REFERENCE_MODELS = ["S_Mamba", "iTransformer"]


def load_rows(path):
    with path.open() as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["horizon"] = int(row["horizon"])
        if row.get("mse"):
            row["mse"] = float(row["mse"])
        if row.get("mae"):
            row["mae"] = float(row["mae"])
    return rows


def avg(values):
    return sum(values) / len(values)


def main():
    baseline_rows = load_rows(BASELINE_CSV)
    ns_rows = load_rows(NS_CSV)

    baseline_by_model = defaultdict(dict)
    for row in baseline_rows:
        if row["status"] == "complete" and row["model"] in REFERENCE_MODELS:
            baseline_by_model[row["model"]][row["horizon"]] = row

    baseline_avg = {
        model: avg([baseline_by_model[model][horizon]["mse"] for horizon in LONG_HORIZONS])
        for model in REFERENCE_MODELS
    }
    best_reference = min(baseline_avg.values())

    ns_by_variant = defaultdict(dict)
    for row in ns_rows:
        if row["status"] == "complete" and row["horizon"] in LONG_HORIZONS:
            ns_by_variant[row["variant"]][row["horizon"]] = row

    candidates = []
    for variant, rows_by_horizon in sorted(ns_by_variant.items()):
        if any(horizon not in rows_by_horizon for horizon in LONG_HORIZONS):
            continue
        variant_avg = avg([rows_by_horizon[horizon]["mse"] for horizon in LONG_HORIZONS])
        improves_one_horizon = any(
            rows_by_horizon[horizon]["mse"]
            < min(baseline_by_model[model][horizon]["mse"] for model in REFERENCE_MODELS)
            for horizon in LONG_HORIZONS
        )
        beats_both = all(variant_avg < value for value in baseline_avg.values())
        within_two_percent = variant_avg <= best_reference * 1.02
        promote = beats_both or (within_two_percent and improves_one_horizon)
        candidates.append(
            {
                "variant": variant,
                "long_avg_mse": variant_avg,
                "beats_both": beats_both,
                "improves_one_horizon": improves_one_horizon,
                "promote": promote,
            }
        )

    print("Reference long-horizon average MSE:")
    for model in REFERENCE_MODELS:
        print(f"  {model}: {baseline_avg[model]:.4f}")

    if not candidates:
        print("No NS_Mamba variant has complete diagnostic long-horizon rows yet.")
        return

    print("NS_Mamba diagnostic candidates:")
    for item in sorted(candidates, key=lambda row: row["long_avg_mse"]):
        print(
            "  {variant}: long_avg_mse={long_avg_mse:.4f}, "
            "beats_both={beats_both}, improves_one_horizon={improves_one_horizon}, "
            "promote={promote}".format(**item)
        )

    promoted = [item for item in candidates if item["promote"]]
    if promoted:
        best = min(promoted, key=lambda row: row["long_avg_mse"])
        print(f"Recommended full-run variant: {best['variant']}")
    else:
        best = min(candidates, key=lambda row: row["long_avg_mse"])
        print(f"No variant satisfies the promotion rule. Best diagnostic variant: {best['variant']}")


if __name__ == "__main__":
    main()
