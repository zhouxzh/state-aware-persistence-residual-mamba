#!/usr/bin/env python
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd


MANUSCRIPT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = MANUSCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.financial.common import atomic_write_bytes, atomic_write_json, sha256_path


PROTOCOL_PATH = REPO_ROOT / "configs" / "financial_benchmark.json"
TRAINING_MANIFEST = REPO_ROOT / "data" / "financial" / "manifests" / "training_datasets.json"
QUALITY_REPORT = REPO_ROOT / "data" / "financial" / "manifests" / "quality_report.json"
ANALYSIS_ROOT = REPO_ROOT / "results" / "financial_confirmatory" / "analysis"
OUTPUT_SECTION = MANUSCRIPT_DIR / "sections" / "results_financial_confirmatory.tex"
OUTPUT_PROTOCOL = MANUSCRIPT_DIR / "sections" / "appendix" / "financial_protocol.tex"
OUTPUT_DATA = MANUSCRIPT_DIR / "data"


def latex_escape(value: object) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
    }
    return "".join(replacements.get(character, character) for character in text)


def require_file(path: Path) -> None:
    if not path.is_file():
        raise RuntimeError(f"missing required evidence artifact: {path}")


def load_and_validate() -> tuple[dict, dict, dict, pd.DataFrame, pd.DataFrame]:
    required = [
        PROTOCOL_PATH,
        TRAINING_MANIFEST,
        QUALITY_REPORT,
        REPO_ROOT / "data" / "financial" / "manifests" / "nonstationarity_diagnostics_full.json",
        ANALYSIS_ROOT / "analysis_manifest.json",
        ANALYSIS_ROOT / "neural_metrics_by_seed.csv",
        ANALYSIS_ROOT / "statistical_metrics.csv",
        ANALYSIS_ROOT / "aggregate_metrics.csv",
        ANALYSIS_ROOT / "bootstrap_contrasts.csv",
        ANALYSIS_ROOT / "s_ms_comparison.csv",
        ANALYSIS_ROOT / "regime_metrics.csv",
    ]
    for path in required:
        require_file(path)

    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    training = json.loads(TRAINING_MANIFEST.read_text(encoding="utf-8"))
    quality = json.loads(QUALITY_REPORT.read_text(encoding="utf-8"))
    analysis_manifest = json.loads(
        (ANALYSIS_ROOT / "analysis_manifest.json").read_text(encoding="utf-8")
    )
    diagnostics = json.loads(
        (REPO_ROOT / "data" / "financial" / "manifests" / "nonstationarity_diagnostics_full.json")
        .read_text(encoding="utf-8")
    )
    if diagnostics.get("protocol_version") != protocol["protocol_version"]:
        raise RuntimeError("nonstationarity diagnostics protocol mismatch")
    if diagnostics.get("protocol_sha256") != training[next(iter(training))]["protocol_sha256"]:
        raise RuntimeError("nonstationarity diagnostics protocol hash mismatch")
    if diagnostics.get("test_targets_read") is not True or diagnostics.get("scope") != "train_validation_test":
        raise RuntimeError("full-period nonstationarity diagnostics are not unlocked")
    neural = pd.read_csv(ANALYSIS_ROOT / "neural_metrics_by_seed.csv")
    aggregate = pd.read_csv(ANALYSIS_ROOT / "aggregate_metrics.csv")
    statistical = pd.read_csv(ANALYSIS_ROOT / "statistical_metrics.csv")
    contrasts = pd.read_csv(ANALYSIS_ROOT / "bootstrap_contrasts.csv")
    mode_pairs = pd.read_csv(ANALYSIS_ROOT / "s_ms_comparison.csv")
    regime_metrics = pd.read_csv(ANALYSIS_ROOT / "regime_metrics.csv")

    task_ids = sorted(training)
    expected_neural = {
        (task, model, int(seed), int(horizon))
        for task in task_ids
        for model in protocol["level_models"]
        for seed in protocol["final_seeds"]
        for horizon in protocol["horizons"]
    }
    observed_neural = {
        (str(row.dataset), str(row.model), int(row.seed), int(row.horizon))
        for row in neural.itertuples()
    }
    if observed_neural != expected_neural or len(neural) != len(expected_neural):
        raise RuntimeError("neural result matrix is incomplete or contains duplicates")

    expected_statistical_count = sum(
        (4 if config["features"] == "MS" else 3) * len(protocol["horizons"])
        for config in training.values()
    )
    expected_contrasts = len(task_ids) * 3 * 2 * len(protocol["horizons"])
    expected_pairs = 4 * (len(protocol["level_models"]) + 3) * len(protocol["horizons"])
    expected_regimes = (
        len(task_ids) * len(protocol["level_models"]) * len(protocol["horizons"]) * 3
        + expected_statistical_count * 3
    )
    expected_counts = {
        "neural_run_count": len(expected_neural),
        "statistical_run_count": expected_statistical_count,
        "contrast_count": expected_contrasts,
        "s_ms_pair_count": expected_pairs,
        "regime_metric_count": expected_regimes,
    }
    for field, expected in expected_counts.items():
        if int(analysis_manifest.get(field, -1)) != expected:
            raise RuntimeError(f"analysis manifest count mismatch for {field}")
    if len(statistical) != expected_statistical_count:
        raise RuntimeError("statistical result matrix is incomplete")
    if len(contrasts) != expected_contrasts or len(mode_pairs) != expected_pairs:
        raise RuntimeError("paired analysis matrix is incomplete")
    if len(regime_metrics) != expected_regimes:
        raise RuntimeError("regime analysis matrix is incomplete")
    if analysis_manifest.get("protocol_version") != protocol["protocol_version"]:
        raise RuntimeError("analysis protocol version does not match the frozen protocol")
    if analysis_manifest.get("protocol_sha256") != training[next(iter(training))]["protocol_sha256"]:
        raise RuntimeError("analysis protocol hash does not match the frozen protocol")
    if int(analysis_manifest.get("bootstrap_replicates", 0)) != 10000:
        raise RuntimeError("confirmatory bootstrap must contain 10,000 replicates")

    numeric = neural[["path_mae", "path_mse", "path_rmse", "path_rmsse"]].to_numpy()
    if not pd.notna(numeric).all() or not all(math.isfinite(float(value)) for value in numeric.ravel()):
        raise RuntimeError("neural metrics contain missing or non-finite values")
    return protocol, training, quality, neural, aggregate


def selected_non_mamba(task: str, protocol: dict, training: dict) -> str:
    path = REPO_ROOT / "results" / "optuna" / task / "baseline_best_params.json"
    require_file(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("protocol_version") != protocol["protocol_version"]:
        raise RuntimeError(f"selection protocol mismatch: {path}")
    if payload.get("protocol_sha256") != training[task]["protocol_sha256"]:
        raise RuntimeError(f"selection protocol hash mismatch: {path}")
    if payload.get("data_sha256") != training[task]["data_sha256"]:
        raise RuntimeError(f"selection data hash mismatch: {path}")
    if list(map(int, payload.get("full_horizons", []))) != protocol["horizons"]:
        raise RuntimeError(f"selection horizon mismatch: {path}")
    models = payload.get("models", {})
    expected = {"DLinear", "NLinear", "PatchTST", "TimesNet", "iTransformer"}
    if set(models) != expected:
        raise RuntimeError(f"selection model set mismatch: {path}")
    for model, record in models.items():
        if record.get("selection_eval_flag") != "val":
            raise RuntimeError(f"selection did not use validation data: {task}/{model}")
        if record.get("final_eval_flag") != "not_opened":
            raise RuntimeError(f"selection record accessed test data: {task}/{model}")
    scores = {
        model: float(record["best_validation_replay_balanced_rmsse"])
        for model, record in models.items()
    }
    if any(not math.isfinite(score) for score in scores.values()):
        raise RuntimeError(f"selection score is non-finite: {path}")
    return min(scores, key=scores.get)


def neural_scores(neural: pd.DataFrame) -> pd.DataFrame:
    per_seed = (
        neural.groupby(["dataset", "model", "seed"], as_index=False)["path_rmsse"]
        .mean()
        .rename(columns={"path_rmsse": "balanced_rmsse"})
    )
    return per_seed.groupby(["dataset", "model"], as_index=False)["balanced_rmsse"].agg(
        mean="mean", std="std"
    )


def deterministic_scores(aggregate: pd.DataFrame) -> pd.DataFrame:
    deterministic = aggregate[aggregate["model"].isin(["Last-value", "Random-walk-drift", "ARIMA", "VAR-difference"])]
    return (
        deterministic.groupby(["dataset", "model"], as_index=False)["path_rmsse_mean"]
        .mean()
        .rename(columns={"path_rmsse_mean": "mean"})
    )


def score_cell(scores: pd.DataFrame, task: str, model: str) -> str:
    row = scores[(scores["dataset"] == task) & (scores["model"] == model)]
    if len(row) != 1:
        raise RuntimeError(f"missing summary score for {task}/{model}")
    record = row.iloc[0]
    if "std" in row.columns and pd.notna(record.get("std")):
        return f"{float(record['mean']):.3f} $\\pm$ {float(record['std']):.3f}"
    return f"{float(record['mean']):.3f}"


def task_label(task: str) -> str:
    stem, mode = task.rsplit("_", 1)
    family = stem.removeprefix("financial_").replace("_", " ").title()
    return f"{family} ({mode.upper()})"


def build_results_section(protocol: dict, training: dict, neural: pd.DataFrame, aggregate: pd.DataFrame) -> str:
    learned = neural_scores(neural)
    deterministic = deterministic_scores(aggregate)
    lines = [
        "% AUTO-GENERATED by manuscript/scripts/generate_financial_results.py. DO NOT EDIT.",
        r"\subsection{Confirmatory financial benchmark}",
        (
            r"Table~\ref{tab:financial-confirmatory-summary} reports the prespecified path-RMSSE "
            r"summary across the six forecast horizons. Neural entries are mean $\pm$ standard "
            r"deviation over five seeds; the last-value reference is deterministic. The non-Mamba "
            r"column is selected using validation data only."
        ),
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Confirmatory financial level-forecasting results. Lower path RMSSE is better.}",
        r"\label{tab:financial-confirmatory-summary}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{lcccccc}",
        r"\toprule",
        r"Task & Last value & Selected non-Mamba & S-Mamba & NS-Mamba-D & MS-Mamba-MD & PMS-Mamba-PD \\",
        r"\midrule",
    ]
    for task in sorted(training):
        baseline = selected_non_mamba(task, protocol, training)
        baseline_cell = f"{latex_escape(baseline)}: {score_cell(learned, task, baseline)}"
        lines.append(
            " & ".join(
                [
                    latex_escape(task_label(task)),
                    score_cell(deterministic, task, "Last-value"),
                    baseline_cell,
                    score_cell(learned, task, "S_Mamba"),
                    score_cell(learned, task, "NS_Mamba-D"),
                    score_cell(learned, task, "MS_Mamba-MD"),
                    score_cell(learned, task, "PMS_Mamba-PD"),
                ]
            )
            + r" \\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}%",
            r"}",
            r"\end{table*}",
            (
                r"Horizon-specific estimates, S-versus-MS comparisons, and the prespecified paired "
                r"moving-block bootstrap contrasts are provided in the generated supplementary data."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def build_protocol_appendix(protocol: dict, quality: dict) -> str:
    records = {record["dataset"]: record for record in quality["datasets"]}
    lines = [
        "% AUTO-GENERATED by manuscript/scripts/generate_financial_results.py. DO NOT EDIT.",
        r"\subsection{Frozen financial data protocol}",
        r"\label{app:financial-protocol}",
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Frozen financial panels after complete-case alignment.}",
        r"\label{tab:financial-data-protocol}",
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Panel & Rows & Train & Validation & Test \\",
        r"\midrule",
    ]
    for name in ("fx", "yields", "cross_asset", "crypto"):
        record = records[name]
        counts = record["split_counts"]
        lines.append(
            f"{latex_escape(name.replace('_', ' ').title())} & {record['rows']} & "
            f"{counts['train']} & {counts['validation']} & {counts['test']} " + r"\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
            (
                f"The frozen cutoff is {latex_escape(protocol['data_cutoff'])}. "
                f"Training ends on {latex_escape(protocol['splits']['train_end'])}; validation covers "
                f"{latex_escape(protocol['splits']['validation_start'])} through "
                f"{latex_escape(protocol['splits']['validation_end'])}; and the untouched final period "
                f"covers {latex_escape(protocol['splits']['test_start'])} through "
                f"{latex_escape(protocol['splits']['test_end'])}."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    protocol, training, quality, neural, aggregate = load_and_validate()
    atomic_write_bytes(OUTPUT_SECTION, build_results_section(protocol, training, neural, aggregate).encode("utf-8"))
    atomic_write_bytes(OUTPUT_PROTOCOL, build_protocol_appendix(protocol, quality).encode("utf-8"))

    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    copied = {}
    for name in (
        "aggregate_metrics.csv",
        "bootstrap_contrasts.csv",
        "neural_metrics_by_seed.csv",
        "s_ms_comparison.csv",
        "regime_metrics.csv",
        "nonstationarity_diagnostics_full.csv",
    ):
        if name.startswith("nonstationarity_"):
            source = REPO_ROOT / "data" / "financial" / "manifests" / name
        else:
            source = ANALYSIS_ROOT / name
        destination = OUTPUT_DATA / f"financial_{name}"
        atomic_write_bytes(destination, source.read_bytes())
        copied[str(destination.relative_to(REPO_ROOT))] = sha256_path(destination)
    atomic_write_json(
        OUTPUT_DATA / "financial_generation_manifest.json",
        {
            "protocol_version": protocol["protocol_version"],
            "source_analysis_manifest_sha256": sha256_path(ANALYSIS_ROOT / "analysis_manifest.json"),
            "generated_files": copied,
        },
    )
    print(f"wrote {OUTPUT_SECTION.relative_to(REPO_ROOT)}")
    print(f"wrote {OUTPUT_PROTOCOL.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"Financial manuscript generation blocked: {exc}") from None
