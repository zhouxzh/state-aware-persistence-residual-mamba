#!/usr/bin/env python3
"""Generate evidence-traceable LaTeX tables for the completed benchmarks."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MANUSCRIPT_DIR = REPO_ROOT / "manuscript"
RESULTS_DIR = REPO_ROOT / "results"
MANIFEST_PATH = REPO_ROOT / "configs" / "optuna_datasets.json"

DATASETS = (
    ("gld", "GLD", 2),
    ("exchange", "Exchange", 2),
)
BASELINE_MODELS = {
    "Autoformer",
    "DLinear",
    "Informer",
    "NLinear",
    "Nonstationary_Transformer",
    "PatchTST",
    "Reformer",
    "TimesNet",
    "Transformer",
    "iTransformer",
}
MAMBA_MODELS = {"MS_Mamba-MD", "NS_Mamba-D", "PMS_Mamba-PD", "S_Mamba"}
DISPLAY_NAMES = {
    "MS_Mamba-MD": "MS-Mamba-MD",
    "NS_Mamba-D": "NS-Mamba-D",
    "PMS_Mamba-PD": "PMS-Mamba-PD",
    "S_Mamba": "S-Mamba",
    "Nonstationary_Transformer": "Non-stationary Transformer",
    "Last-value": "Last-value",
}


def latex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "_": r"\_",
        "%": r"\%",
        "&": r"\&",
        "#": r"\#",
    }
    return "".join(replacements.get(char, char) for char in str(value))


def display_model(model: str) -> str:
    return latex_escape(DISPLAY_NAMES.get(model, model))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-11)


def validate_phase_rows(
    dataset: str,
    phase: str,
    rows: list[dict[str, str]],
    horizons: list[int],
) -> None:
    expected_models = BASELINE_MODELS if phase == "baseline" else MAMBA_MODELS
    expected_pairs = {(model, horizon) for model in expected_models for horizon in horizons}
    observed_pairs = {(row["model"], int(row["horizon"])) for row in rows}
    if observed_pairs != expected_pairs or len(rows) != len(expected_pairs):
        raise ValueError(f"Incomplete {dataset}/{phase} result matrix")

    for row in rows:
        if row["dataset"] != dataset or row["phase"] != phase:
            raise ValueError(f"Dataset or phase mismatch in {dataset}/{phase}")
        if row["status"] != "complete":
            raise ValueError(f"Non-complete result in {dataset}/{phase}")
        if row["selection_eval_flag"] != "val" or row["final_eval_flag"] != "test":
            raise ValueError(f"Evaluation flag mismatch in {dataset}/{phase}")
        for metric in ("mae", "mse", "rmse", "rmsse", "overall_balanced_rmsse"):
            if not math.isfinite(float(row[metric])):
                raise ValueError(f"Non-finite {metric} in {dataset}/{phase}")
        if not math.isclose(
            float(row["rmse"]) ** 2,
            float(row["mse"]),
            rel_tol=5e-6,
            abs_tol=1e-10,
        ):
            raise ValueError(f"RMSE/MSE mismatch in {dataset}/{phase}")

    for model in expected_models:
        model_rows = [row for row in rows if row["model"] == model]
        grouped = {}
        for term in ("short", "middle", "long"):
            values = [float(row["rmsse"]) for row in model_rows if row["term"] == term]
            if not values:
                raise ValueError(f"Missing {term} horizons for {dataset}/{phase}/{model}")
            grouped[term] = sum(values) / len(values)
        balanced = sum(grouped.values()) / 3
        if not close(balanced, float(model_rows[0]["overall_balanced_rmsse"])):
            raise ValueError(f"Balanced RMSSE mismatch for {dataset}/{phase}/{model}")

    params_path = RESULTS_DIR / "optuna" / dataset / f"{phase}_best_params.json"
    payload = json.loads(params_path.read_text())
    if payload["dataset"] != dataset or payload["phase"] != phase:
        raise ValueError(f"Best-parameter metadata mismatch for {dataset}/{phase}")
    if [int(value) for value in payload["full_horizons"]] != horizons:
        raise ValueError(f"Full-horizon metadata mismatch for {dataset}/{phase}")
    for model in expected_models:
        model_rows = [row for row in rows if row["model"] == model]
        reported = float(payload["models"][model]["final_test_balanced_rmsse"])
        if not close(reported, float(model_rows[0]["overall_balanced_rmsse"])):
            raise ValueError(f"Best-parameter score mismatch for {dataset}/{phase}/{model}")


def load_results() -> tuple[dict[str, list[dict[str, str]]], dict]:
    manifest = json.loads(MANIFEST_PATH.read_text())
    combined = {}
    for dataset, _, _ in DATASETS:
        horizons = [int(value) for value in manifest[dataset]["horizons"]]
        rows = []
        for phase in ("baseline", "mamba"):
            phase_rows = read_csv(RESULTS_DIR / f"{dataset}_{phase}_optuna_best.csv")
            validate_phase_rows(dataset, phase, phase_rows, horizons)
            rows.extend(phase_rows)
        combined[dataset] = rows
    return combined, manifest


def read_target_values(path: Path, target: str) -> list[float]:
    rows = read_csv(path)
    if not rows or target not in rows[0]:
        raise ValueError(f"Missing target {target!r} in {path}")
    values = []
    for index, row in enumerate(rows, start=2):
        raw = row[target].strip()
        if not raw:
            raise ValueError(f"Missing target at {path}:{index}")
        value = float(raw)
        if not math.isfinite(value):
            raise ValueError(f"Non-finite target at {path}:{index}")
        values.append(value)
    return values


def horizon_term(config: dict, horizon: int) -> str:
    for term, horizons in config["term_groups"].items():
        if horizon in [int(value) for value in horizons]:
            return term
    raise ValueError(f"Horizon {horizon} is not assigned to a term group")


def compute_last_value_results(manifest: dict) -> dict[str, list[dict[str, object]]]:
    """Replay the loader's expanding-origin test windows with persistence forecasts."""
    output = {}
    for dataset, _, _ in DATASETS:
        config = manifest[dataset]
        source_path = REPO_ROOT / config["root_path"] / config["data_path"]
        values = read_target_values(source_path, config["target"])
        train_count = int(len(values) * 0.7)
        test_count = int(len(values) * 0.2)
        test_start = len(values) - test_count
        train_values = values[:train_count]
        scale = sum(
            (train_values[index] - train_values[index - 1]) ** 2
            for index in range(1, len(train_values))
        ) / (len(train_values) - 1)
        if scale <= 0:
            raise ValueError(f"Non-positive RMSSE scale for {dataset}")

        rows = []
        for horizon in [int(value) for value in config["horizons"]]:
            absolute_error = 0.0
            squared_error = 0.0
            value_count = 0
            origin_count = test_count - horizon + 1
            for origin in range(test_start, len(values) - horizon + 1):
                prediction = values[origin - 1]
                for target_value in values[origin : origin + horizon]:
                    error = target_value - prediction
                    absolute_error += abs(error)
                    squared_error += error * error
                    value_count += 1
            if value_count != origin_count * horizon:
                raise ValueError(f"Last-value window count mismatch for {dataset}/{horizon}")
            mse = squared_error / value_count
            rows.append(
                {
                    "dataset": dataset,
                    "model": "Last-value",
                    "horizon": horizon,
                    "term": horizon_term(config, horizon),
                    "origin_count": origin_count,
                    "forecast_value_count": value_count,
                    "mae": absolute_error / value_count,
                    "mse": mse,
                    "rmse": math.sqrt(mse),
                    "rmsse": math.sqrt(mse / scale),
                }
            )

        term_means = []
        for term in ("short", "middle", "long"):
            term_values = [float(row["rmsse"]) for row in rows if row["term"] == term]
            if not term_values:
                raise ValueError(f"Missing last-value {term} horizons for {dataset}")
            term_means.append(sum(term_values) / len(term_values))
        balanced = sum(term_means) / len(term_means)
        for row in rows:
            row["overall_balanced_rmsse"] = balanced
        output[dataset] = rows

    output_path = MANUSCRIPT_DIR / "data" / "last_value_baseline.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(output[DATASETS[0][0]][0])
    with output_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for dataset, _, _ in DATASETS:
            writer.writerows(output[dataset])
    return output


def model_summaries(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    summaries = []
    seen = set()
    for row in rows:
        key = (row["phase"], row["model"])
        if key in seen:
            continue
        seen.add(key)
        summaries.append(
            {
                "phase": row["phase"],
                "model": row["model"],
                "score": float(row["overall_balanced_rmsse"]),
                "rmse": float(row["overall_avg_rmse"]),
                "mae": float(row["overall_avg_mae"]),
            }
        )
    summaries.sort(key=lambda item: float(item["score"]))
    for rank, item in enumerate(summaries, start=1):
        item["rank"] = rank
    return summaries


def best_by_phase(summaries: list[dict[str, object]], phase: str) -> dict[str, object]:
    return min((item for item in summaries if item["phase"] == phase), key=lambda item: item["score"])


def write_summary_table(
    results: dict[str, list[dict[str, str]]],
    last_value: dict[str, list[dict[str, object]]],
) -> list[dict[str, object]]:
    summary_rows = []
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Descriptive balanced-RMSSE point estimates on the current test periods. The neural and Mamba entries are the post hoc within-family minima; Last-value is deterministic and requires no fitting. No uncertainty interval is available.}",
        r"\label{tab:benchmark-family-summary}",
        r"{\small",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{l r l r l r l}",
        r"\toprule",
        r"Dataset & Last-value & Neural baseline & RMSSE & Mamba & RMSSE & Lowest point estimate \\",
        r"\midrule",
    ]
    for dataset, label, decimals in DATASETS:
        summaries = model_summaries(results[dataset])
        baseline = best_by_phase(summaries, "baseline")
        mamba = best_by_phase(summaries, "mamba")
        naive_score = float(last_value[dataset][0]["overall_balanced_rmsse"])
        candidates = [
            ("Last-value", naive_score),
            (str(baseline["model"]), float(baseline["score"])),
            (str(mamba["model"]), float(mamba["score"])),
        ]
        observed_model, observed_score = min(candidates, key=lambda item: item[1])
        summary_rows.append(
            {
                "dataset": dataset,
                "last_value_rmsse": naive_score,
                "best_baseline": baseline["model"],
                "baseline_rmsse": baseline["score"],
                "best_mamba": mamba["model"],
                "mamba_rmsse": mamba["score"],
                "lowest_observed_model": observed_model,
                "lowest_observed_rmsse": observed_score,
            }
        )
        lines.append(
            f"{label} & {naive_score:.{decimals}f} & "
            f"{display_model(str(baseline['model']))} & {float(baseline['score']):.{decimals}f} & "
            f"{display_model(str(mamba['model']))} & {float(mamba['score']):.{decimals}f} & "
            f"{display_model(observed_model)} ({observed_score:.{decimals}f}) \\\\" 
        )
    lines.extend([r"\bottomrule", r"\end{tabular}%", r"}", r"}", r"\end{table}", ""])
    (MANUSCRIPT_DIR / "sections" / "results_benchmark_summary.tex").write_text("\n".join(lines))

    output_path = MANUSCRIPT_DIR / "data" / "benchmark_summary.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0]))
        writer.writeheader()
        writer.writerows(summary_rows)
    return summary_rows


def write_ranking_table(
    results: dict[str, list[dict[str, str]]],
    last_value: dict[str, list[dict[str, object]]],
) -> None:
    by_dataset = {dataset: model_summaries(rows) for dataset, rows in results.items()}
    lookup = {
        dataset: {str(item["model"]): item for item in summaries}
        for dataset, summaries in by_dataset.items()
    }
    models = ["Last-value"] + sorted(MAMBA_MODELS) + sorted(BASELINE_MODELS)
    best_scores = {}
    for dataset, _, _ in DATASETS:
        best_scores[dataset] = min(
            [float(item["score"]) for item in by_dataset[dataset]]
            + [float(last_value[dataset][0]["overall_balanced_rmsse"])]
        )
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Balanced-RMSSE point estimates for all evaluated methods. Neural models are validation-selected single-seed runs; Last-value is a deterministic reference. Bold marks the lowest observed value in each dataset. No cross-dataset rank is aggregated.}",
        r"\label{tab:benchmark-model-ranking}",
        r"{\small",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{l l r r}",
        r"\toprule",
        r"Model & Type & GLD & Exchange \\",
        r"\midrule",
    ]
    for model in models:
        values = []
        for dataset, _, decimals in DATASETS:
            score_value = (
                float(last_value[dataset][0]["overall_balanced_rmsse"])
                if model == "Last-value"
                else float(lookup[dataset][model]["score"])
            )
            score = f"{score_value:.{decimals}f}"
            if close(score_value, best_scores[dataset]):
                score = rf"\textbf{{{score}}}"
            values.append(score)
        model_type = "Reference" if model == "Last-value" else ("Mamba" if model in MAMBA_MODELS else "Neural baseline")
        lines.append(f"{display_model(model)} & {model_type} & {values[0]} & {values[1]} \\\\ ")
    lines.extend([r"\bottomrule", r"\end{tabular}%", r"}", r"}", r"\end{table}", ""])
    (MANUSCRIPT_DIR / "sections" / "results_model_ranking.tex").write_text("\n".join(lines))


def write_protocol_table(manifest: dict) -> None:
    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{Archived Optuna study records. The state column gives complete/pruned/other trial counts across all model studies in a row. Each study replays up to five top completed calibration trials on the full validation horizon set before one final test evaluation.}",
        r"\label{tab:benchmark-optuna-protocol}",
        r"{\scriptsize",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{l l r r l l}",
        r"\toprule",
        r"Dataset & Family & Trial records/model & Models & Trial states & Calibration horizons \\",
        r"\midrule",
    ]
    for dataset, label, _ in DATASETS:
        for phase in ("baseline", "mamba"):
            trials = read_csv(RESULTS_DIR / "optuna" / dataset / f"{phase}_trials.csv")
            counts_by_model = Counter(row["model"] for row in trials)
            targets = sorted(set(counts_by_model.values()))
            if len(targets) != 1:
                raise ValueError(f"Uneven trial record counts for {dataset}/{phase}: {targets}")
            states = Counter(row["state"] for row in trials)
            complete_count = states["TrialState.COMPLETE"]
            pruned_count = states["TrialState.PRUNED"]
            other_count = len(trials) - complete_count - pruned_count
            payload = json.loads((RESULTS_DIR / "optuna" / dataset / f"{phase}_best_params.json").read_text())
            calibration = ", ".join(str(value) for value in payload["calibration_horizons"])
            family = "Baseline" if phase == "baseline" else "Mamba"
            model_count = len(BASELINE_MODELS if phase == "baseline" else MAMBA_MODELS)
            lines.append(
                f"{label} & {family} & {targets[0]} & {model_count} & "
                f"{complete_count}/{pruned_count}/{other_count} & {calibration} \\\\" 
            )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}%",
            r"}",
            r"}",
            r"\end{table}",
            "",
        ]
    )
    (MANUSCRIPT_DIR / "sections" / "appendix" / "benchmark_protocol.tex").write_text("\n".join(lines))


def main() -> None:
    results, manifest = load_results()
    last_value = compute_last_value_results(manifest)
    write_summary_table(results, last_value)
    write_ranking_table(results, last_value)
    write_protocol_table(manifest)
    print("validated 336 trained-model test rows and computed 24 deterministic last-value rows")
    print("wrote benchmark LaTeX tables and manuscript/data result summaries")


if __name__ == "__main__":
    main()
