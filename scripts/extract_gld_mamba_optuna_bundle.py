#!/usr/bin/env python
"""Extract the best GLD Optuna Mamba hyperparameters into a reproducible bundle.

Outputs a self-contained folder under ``scripts/gld_mamba_optuna_bundle/``
with:

- the best per-horizon baseline rows
- a per-model hyperparameter summary
- a per-horizon winner summary
- a reproduction config JSON with the selected study settings

The bundle is meant to be plot-ready for manuscript figures and easy to reuse for
re-running the published baseline sweep.
"""

import argparse
import csv
import json
import shlex
import shutil
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_ROOT = REPO_ROOT / "manuscript"
DEFAULT_BEST_CSV = REPO_ROOT / "results" / "gld_mamba_optuna_best.csv"
DEFAULT_BEST_PARAMS_JSON = REPO_ROOT / "results" / "optuna" / "gld" / "mamba_best_params.json"
DEFAULT_MANIFEST = REPO_ROOT / "configs" / "optuna_datasets.json"
DEFAULT_BUNDLE_ROOT = REPO_ROOT / "scripts" / "gld_mamba_optuna_bundle"

HORIZONS = [1, 3, 5, 7, 14, 30, 60, 90, 120, 180, 270, 360]
TERMS = ["short", "middle", "long"]
MODEL_ORDER = [
    "PMS_Mamba-PD",
    "NS_Mamba-D",
    "MS_Mamba-MD",
    "S_Mamba",
]


def parse_args():
    parser = argparse.ArgumentParser(description="Extract GLD Optuna Mamba reproduction artifacts.")
    parser.add_argument("--best-csv", type=Path, default=DEFAULT_BEST_CSV)
    parser.add_argument("--best-params-json", type=Path, default=DEFAULT_BEST_PARAMS_JSON)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--bundle-root", type=Path, default=DEFAULT_BUNDLE_ROOT)
    parser.add_argument("--study-suffix", default="fullcal_v1")
    return parser.parse_args()


def latex_escape(text):
    return text.replace("_", r"\_")


def params_compact(params):
    ordered = [
        "seq_len",
        "batch_size",
        "learning_rate",
        "d_model",
        "d_ff",
        "factor",
        "moving_avg",
        "individual",
        "patch_len",
        "stride",
        "top_k",
        "num_kernels",
        "use_norm",
        "p_hidden_layers",
        "p_hidden_dims",
    ]
    parts = []
    for key in ordered:
        if key not in params:
            continue
        value = params[key]
        if isinstance(value, list):
            value = "[" + ",".join(str(item) for item in value) + "]"
        elif isinstance(value, bool):
            value = str(value).lower()
        parts.append(f"{key}={value}")
    return ", ".join(parts)


def load_best_rows(path):
    with path.open() as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit(f"no rows found in {path}")
    for row in rows:
        row["horizon"] = int(row["horizon"])
        row["seq_len"] = int(row["seq_len"])
        row["label_len"] = int(row["label_len"])
        row["pred_len"] = int(row["pred_len"])
        row["mae"] = float(row["mae"])
        row["mse"] = float(row["mse"])
        row["rmse"] = float(row["rmse"])
        row["mape"] = float(row["mape"])
        row["mspe"] = float(row["mspe"])
        row["rmsse"] = float(row["rmsse"])
        row["short_avg_rmse"] = float(row["short_avg_rmse"])
        row["middle_avg_rmse"] = float(row["middle_avg_rmse"])
        row["long_avg_rmse"] = float(row["long_avg_rmse"])
        row["overall_avg_rmse"] = float(row["overall_avg_rmse"])
        row["short_avg_mae"] = float(row["short_avg_mae"])
        row["middle_avg_mae"] = float(row["middle_avg_mae"])
        row["long_avg_mae"] = float(row["long_avg_mae"])
        row["overall_avg_mae"] = float(row["overall_avg_mae"])
        row["short_avg_rmsse"] = float(row["short_avg_rmsse"])
        row["middle_avg_rmsse"] = float(row["middle_avg_rmsse"])
        row["long_avg_rmsse"] = float(row["long_avg_rmsse"])
        row["overall_avg_rmsse"] = float(row["overall_avg_rmsse"])
        row["overall_balanced_rmsse"] = float(row["overall_balanced_rmsse"])
        row["calibration_balanced_rmsse"] = float(row["calibration_balanced_rmsse"])
        row["selection_balanced_rmsse"] = float(row["selection_balanced_rmsse"])
    return rows


def load_params(path):
    with path.open() as f:
        return json.load(f)


def load_manifest(path):
    with path.open() as f:
        payload = json.load(f)
    if "gld" not in payload:
        raise SystemExit(f"dataset manifest does not contain gld: {path}")
    return payload["gld"]


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_model_summary(best_rows, params_payload, study_suffix):
    rows_by_model = defaultdict(list)
    for row in best_rows:
        rows_by_model[row["model"]].append(row)

    summary_rows = []
    for model in MODEL_ORDER:
        if model not in rows_by_model:
            continue
        info = params_payload["models"][model]
        model_row = rows_by_model[model][0]
        summary_rows.append(
            {
                "model": model,
                "study_name": info["study_name"],
                "best_validation_replay_trial": info["best_validation_replay_trial"],
                "best_validation_replay_balanced_rmsse": f"{info['best_validation_replay_balanced_rmsse']:.12g}",
                "final_test_balanced_rmsse": f"{info['final_test_balanced_rmsse']:.12g}",
                "overall_balanced_rmsse": f"{model_row['overall_balanced_rmsse']:.12g}",
                "short_avg_rmsse": f"{model_row['short_avg_rmsse']:.12g}",
                "middle_avg_rmsse": f"{model_row['middle_avg_rmsse']:.12g}",
                "long_avg_rmsse": f"{model_row['long_avg_rmsse']:.12g}",
                "overall_avg_rmse": f"{model_row['overall_avg_rmse']:.12g}",
                "overall_avg_mae": f"{model_row['overall_avg_mae']:.12g}",
                "params_json": json.dumps(info["params"], sort_keys=True),
                "params_compact": params_compact(info["params"]),
                "study_suffix": study_suffix,
            }
        )

    summary_rows.sort(key=lambda row: float(row["overall_balanced_rmsse"]))
    return summary_rows


def build_horizon_summary(best_rows):
    rows_by_horizon = defaultdict(list)
    for row in best_rows:
        rows_by_horizon[row["horizon"]].append(row)

    summary_rows = []
    for horizon in HORIZONS:
        horizon_rows = sorted(rows_by_horizon[horizon], key=lambda row: row["rmsse"])
        best = horizon_rows[0]
        runner_up = horizon_rows[1]
        summary_rows.append(
            {
                "horizon": horizon,
                "best_model": best["model"],
                "best_term": best["term"],
                "best_rmsse": f"{best['rmsse']:.12g}",
                "best_rmse": f"{best['rmse']:.12g}",
                "best_mae": f"{best['mae']:.12g}",
                "runner_up_model": runner_up["model"],
                "runner_up_term": runner_up["term"],
                "runner_up_rmsse": f"{runner_up['rmsse']:.12g}",
                "runner_up_rmse": f"{runner_up['rmse']:.12g}",
                "runner_up_mae": f"{runner_up['mae']:.12g}",
            }
        )
    return summary_rows


def build_reproduction_config(best_rows, params_payload, dataset_cfg, study_suffix, source_files, bundle_root):
    model_order = [row["model"] for row in sorted(
        {row["model"]: row for row in best_rows}.values(),
        key=lambda row: float(row["overall_balanced_rmsse"]),
    )]
    model_order = [model for model in MODEL_ORDER if model in model_order]

    full_command = [
        "conda",
        "run",
        "-n",
        "mamba",
        "python",
        "scripts/optuna/run_dataset_optuna.py",
        "--dataset",
        params_payload["dataset"],
        "--phase",
        params_payload["phase"],
        "--models",
        *MODEL_ORDER,
        "--trials",
        "20",
        "--study-suffix",
        study_suffix,
        "--calibration-horizons",
        *[str(h) for h in params_payload["calibration_horizons"]],
        "--full-horizons",
        *[str(h) for h in params_payload["full_horizons"]],
    ]

    models = {}
    for model in MODEL_ORDER:
        if model not in params_payload["models"]:
            continue
        info = params_payload["models"][model]
        per_model_command = [
            "conda",
            "run",
            "-n",
            "mamba",
            "python",
            "scripts/optuna/run_dataset_optuna.py",
            "--dataset",
            params_payload["dataset"],
            "--phase",
            params_payload["phase"],
            "--models",
            model,
            "--trials",
            "20",
            "--study-suffix",
            study_suffix,
            "--calibration-horizons",
            *[str(h) for h in params_payload["calibration_horizons"]],
            "--full-horizons",
            *[str(h) for h in params_payload["full_horizons"]],
        ]
        models[model] = {
            "study_name": info["study_name"],
            "best_calibration_trial": info["best_calibration_trial"],
            "best_calibration_objective": info["best_calibration_objective"],
            "best_validation_replay_trial": info["best_validation_replay_trial"],
            "best_validation_replay_balanced_rmsse": info["best_validation_replay_balanced_rmsse"],
            "final_test_balanced_rmsse": info["final_test_balanced_rmsse"],
            "params": info["params"],
            "params_compact": params_compact(info["params"]),
            "replay_command": shlex.join(per_model_command),
        }

    return {
        "dataset": params_payload["dataset"],
        "phase": params_payload["phase"],
        "objective_metric": params_payload["objective_metric"],
        "search_space_version": params_payload["search_space_version"],
        "study_suffix": study_suffix,
        "source_files": source_files,
        "dataset_config": dataset_cfg,
        "reproduction_command": shlex.join(full_command),
        "plot_ready": {
            "baseline_best_csv": str((bundle_root / "plot_ready" / "baseline_best.csv").relative_to(bundle_root)),
            "baseline_hyperparameters_csv": str((bundle_root / "plot_ready" / "baseline_hyperparameters.csv").relative_to(bundle_root)),
            "model_summary_csv": str((bundle_root / "plot_ready" / "model_summary.csv").relative_to(bundle_root)),
            "horizon_summary_csv": str((bundle_root / "plot_ready" / "horizon_summary.csv").relative_to(bundle_root)),
        },
        "models": models,
    }


def main():
    args = parse_args()
    best_rows = load_best_rows(args.best_csv)
    params_payload = load_params(args.best_params_json)
    dataset_cfg = load_manifest(args.manifest)

    if len(best_rows) != len(MODEL_ORDER) * len(HORIZONS):
        raise SystemExit(
            f"expected {len(MODEL_ORDER) * len(HORIZONS)} rows in {args.best_csv}, got {len(best_rows)}"
        )

    rows_by_horizon = defaultdict(list)
    rows_by_model = defaultdict(list)
    complete_count = 0
    for row in best_rows:
        rows_by_horizon[row["horizon"]].append(row)
        rows_by_model[row["model"]].append(row)
        if row["status"] == "complete":
            complete_count += 1

    if complete_count != len(best_rows):
        raise SystemExit(f"expected all rows complete, got {complete_count}/{len(best_rows)}")

    bundle_root = args.bundle_root
    plot_ready_dir = bundle_root / "plot_ready"
    config_dir = bundle_root / "configs"
    plot_ready_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)

    # Plot-ready copies.
    shutil.copyfile(args.best_csv, plot_ready_dir / "baseline_best.csv")

    model_summary_rows = build_model_summary(best_rows, params_payload, args.study_suffix)
    horizon_summary_rows = build_horizon_summary(best_rows)
    write_csv(
        plot_ready_dir / "model_summary.csv",
        model_summary_rows,
        [
            "model",
            "study_name",
            "best_validation_replay_trial",
            "best_validation_replay_balanced_rmsse",
            "final_test_balanced_rmsse",
            "overall_balanced_rmsse",
            "short_avg_rmsse",
            "middle_avg_rmsse",
            "long_avg_rmsse",
            "overall_avg_rmse",
            "overall_avg_mae",
            "params_json",
            "params_compact",
            "study_suffix",
        ],
    )
    write_csv(
        plot_ready_dir / "horizon_summary.csv",
        horizon_summary_rows,
        [
            "horizon",
            "best_model",
            "best_term",
            "best_rmsse",
            "best_rmse",
            "best_mae",
            "runner_up_model",
            "runner_up_term",
            "runner_up_rmsse",
            "runner_up_rmse",
            "runner_up_mae",
        ],
    )

    hyper_rows = []
    for model in MODEL_ORDER:
        if model not in params_payload["models"]:
            continue
        info = params_payload["models"][model]
        hyper_rows.append(
            {
                "model": model,
                "study_name": info["study_name"],
                "trial_number": info["best_validation_replay_trial"],
                "val_balanced_rmsse": f"{info['best_validation_replay_balanced_rmsse']:.12g}",
                "test_balanced_rmsse": f"{info['final_test_balanced_rmsse']:.12g}",
                "params_json": json.dumps(info["params"], sort_keys=True),
                "params_compact": params_compact(info["params"]),
            }
        )
    write_csv(
        plot_ready_dir / "baseline_hyperparameters.csv",
        hyper_rows,
        [
            "model",
            "study_name",
            "trial_number",
            "val_balanced_rmsse",
            "test_balanced_rmsse",
            "params_json",
            "params_compact",
        ],
    )

    # Config bundle for exact reproduction.
    source_files = {
        "best_csv": str(args.best_csv.relative_to(REPO_ROOT)),
        "best_params_json": str(args.best_params_json.relative_to(REPO_ROOT)),
    }
    reproduction_config = build_reproduction_config(
        best_rows=best_rows,
        params_payload=params_payload,
        dataset_cfg=dataset_cfg,
        study_suffix=args.study_suffix,
        source_files=source_files,
        bundle_root=bundle_root,
    )
    with (config_dir / "mamba_reproduction_config.json").open("w") as f:
        json.dump(reproduction_config, f, indent=2, sort_keys=True)

    with (config_dir / "mamba_best_params.json").open("w") as f:
        json.dump(params_payload, f, indent=2, sort_keys=True)

    bundle_manifest = {
        "bundle_root": str(bundle_root.relative_to(REPO_ROOT)),
        "plot_ready_files": [
            "plot_ready/baseline_best.csv",
            "plot_ready/model_summary.csv",
            "plot_ready/horizon_summary.csv",
            "plot_ready/baseline_hyperparameters.csv",
        ],
        "config_files": [
            "configs/mamba_reproduction_config.json",
            "configs/mamba_best_params.json",
        ],
        "rows": len(best_rows),
        "models": len(rows_by_model),
        "horizons": len(rows_by_horizon),
    }
    with (bundle_root / "manifest.json").open("w") as f:
        json.dump(bundle_manifest, f, indent=2, sort_keys=True)

    print(f"wrote {plot_ready_dir.relative_to(REPO_ROOT)}")
    print(f"wrote {config_dir.relative_to(REPO_ROOT)}")
    print(f"wrote {str((bundle_root / 'manifest.json').relative_to(REPO_ROOT))}")


if __name__ == "__main__":
    main()
