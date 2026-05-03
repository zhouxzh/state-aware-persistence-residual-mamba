#!/usr/bin/env python
import csv
import importlib
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SETTING_ID = "A"
DATASET = "GLD"
TARGET = "close"
MODELS = [
    "S_Mamba",
    "Transformer",
    "Informer",
    "Reformer",
    "Autoformer",
    "iTransformer",
    "Nonstationary_Transformer",
    "DLinear",
    "NLinear",
    "PatchTST",
    "TimesNet",
]
HORIZONS = [1, 3, 5, 7, 14, 30, 60, 90, 120, 180, 270, 360]
SETTING = {
    "seq_len": 360,
    "label_len": 180,
    "d_model": 64,
    "d_ff": 128,
    "e_layers": 2,
    "d_layers": 1,
    "batch_size": 16,
    "train_epochs": 10,
    "patience": 3,
    "seed": 2023,
}


def term_for_horizon(horizon):
    if horizon <= 7:
        return "short"
    if horizon <= 90:
        return "middle"
    return "long"


def parse_result_dir(path):
    name = path.name
    patterns = [
        re.compile(r"^GLD_A_(?P<model>.+?)_pl(?P<horizon>\d+)_"),
        re.compile(r"^GLD_calib_A_(?P<model>.+?)_pl(?P<horizon>\d+)_"),
    ]
    for pattern in patterns:
        match = pattern.match(name)
        if match:
            return match.group("model"), int(match.group("horizon"))
    return None, None


def load_completed_metrics():
    completed = {}
    for metrics_path in Path("results").glob("GLD*_*/metrics.npy"):
        model, horizon = parse_result_dir(metrics_path.parent)
        if model is None:
            continue
        if model not in MODELS or horizon not in HORIZONS:
            continue
        metrics = np.load(metrics_path)
        mae, mse, rmse, mape, mspe = [float(x) for x in metrics[:5]]
        rmsse = float(metrics[5]) if metrics.shape[0] > 5 else ""
        current = completed.get((model, horizon))
        meta_path = metrics_path.parent / "meta.json"
        inverse = None
        if meta_path.exists():
            with meta_path.open() as f:
                inverse = bool(json.load(f).get("inverse", False))
        candidate = {
            "mse": mse,
            "mae": mae,
            "rmse": rmse,
            "mape": mape,
            "mspe": mspe,
            "rmsse": rmsse,
            "inverse": inverse,
            "run": metrics_path.parent.name,
        }
        # Prefer full baseline runs over calibration runs when both exist.
        if current is None or current["run"].startswith("GLD_calib_A_"):
            completed[(model, horizon)] = candidate
    return completed


def parameter_count(model_name):
    args = SimpleNamespace(
        seq_len=SETTING["seq_len"],
        label_len=SETTING["label_len"],
        pred_len=1,
        task_name="long_term_forecast",
        enc_in=1,
        dec_in=1,
        c_out=1,
        d_model=SETTING["d_model"],
        n_heads=8,
        e_layers=SETTING["e_layers"],
        d_layers=SETTING["d_layers"],
        d_ff=SETTING["d_ff"],
        moving_avg=25,
        individual=False,
        top_k=5,
        num_kernels=6,
        patch_len=16,
        stride=8,
        factor=1,
        distil=True,
        dropout=0.1,
        embed="timeF",
        freq="d",
        activation="gelu",
        output_attention=False,
        channel_independence=False,
        class_strategy="projection",
        use_norm=True,
        d_state=16,
        p_hidden_dims=[128, 128],
        p_hidden_layers=2,
    )
    module = importlib.import_module(f"model.{model_name}")
    model = module.Model(args)
    return sum(p.numel() for p in model.parameters())


def main():
    completed = load_completed_metrics()
    param_counts = {model: parameter_count(model) for model in MODELS}

    rows = []
    for model in MODELS:
        for horizon in HORIZONS:
            metrics = completed.get((model, horizon))
            row = {
                "dataset": DATASET,
                "target": TARGET,
                "model": model,
                "horizon": horizon,
                "term": term_for_horizon(horizon),
                "setting_id": SETTING_ID,
                "seq_len": SETTING["seq_len"],
                "label_len": SETTING["label_len"],
                "pred_len": horizon,
                "d_model": SETTING["d_model"],
                "d_ff": SETTING["d_ff"],
                "e_layers": SETTING["e_layers"],
                "d_layers": SETTING["d_layers"],
                "batch_size": SETTING["batch_size"],
                "train_epochs": SETTING["train_epochs"],
                "patience": SETTING["patience"],
                "seed": SETTING["seed"],
                "mse": "",
                "mae": "",
                "rmse": "",
                "mape": "",
                "mspe": "",
                "rmsse": "",
                "best_val_loss": "",
                "train_time_sec": "",
                "param_count": param_counts[model],
                "gpu_memory_mb": "",
                "status": "pending",
                "notes": "",
                "run": "",
            }
            if metrics is not None:
                status = "complete"
                notes = ""
                if metrics["inverse"] is False:
                    status = "legacy_scaled"
                    notes = "run saved before inverse=True default; rerun for price-scale baseline"
                elif metrics["inverse"] is None:
                    status = "legacy_unknown"
                    notes = "missing meta.json; scale of saved metrics is unknown"
                row.update(
                    {
                        "mse": metrics["mse"],
                        "mae": metrics["mae"],
                        "rmse": metrics["rmse"],
                        "mape": metrics["mape"],
                        "mspe": metrics["mspe"],
                        "rmsse": metrics["rmsse"],
                        "status": status,
                        "notes": notes,
                        "run": metrics["run"],
                    }
                )
                if status == "complete" and metrics["run"].startswith("GLD_calib_A_"):
                    row["notes"] = "seeded from calibration run"
            rows.append(row)

    out = Path("results/gld_baselines.csv")
    out.parent.mkdir(exist_ok=True)
    fieldnames = [
        "dataset",
        "target",
        "model",
        "horizon",
        "term",
        "setting_id",
        "seq_len",
        "label_len",
        "pred_len",
        "d_model",
        "d_ff",
        "e_layers",
        "d_layers",
        "batch_size",
        "train_epochs",
        "patience",
        "seed",
        "mse",
        "mae",
        "rmse",
        "mape",
        "mspe",
        "rmsse",
        "best_val_loss",
        "train_time_sec",
        "param_count",
        "gpu_memory_mb",
        "status",
        "notes",
        "run",
    ]
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    complete = sum(row["status"] == "complete" for row in rows)
    print(f"wrote {out}")
    print(f"complete rows: {complete}/{len(rows)}")


if __name__ == "__main__":
    main()
