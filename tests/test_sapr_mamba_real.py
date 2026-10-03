from __future__ import annotations

import io
import zipfile

import numpy as np
import pandas as pd
import torch

from experiments.sapr_mamba.run import evaluate_model
from model.StateAwarePersistenceResidualMamba import PersistenceModel
from utils.sapr_mamba.data import SeriesInfo, WindowDataset
from utils.sapr_mamba.real import _prepare_beijing
from utils.sapr_mamba.real import _panel_series


def test_beijing_parser_uses_nested_station_archive(tmp_path, monkeypatch) -> None:
    from utils.sapr_mamba import real

    raw = tmp_path / "raw"
    nested = io.BytesIO()
    with zipfile.ZipFile(nested, "w") as archive:
        archive.writestr("PRSA_Data_Aotizhongxin_20130301-20170228.csv", "No,year,month,day,hour,PM2.5,station\n1,2013,3,1,0,12,Aotizhongxin\n2,2013,3,1,1,13,Aotizhongxin\n")
    raw_file = raw / "beijing_air_quality" / "source.zip"
    raw_file.parent.mkdir(parents=True)
    with zipfile.ZipFile(raw_file, "w") as archive:
        archive.writestr("PRSA2017_Data_20130301-20170228.zip", nested.getvalue())
        archive.writestr("data.csv", "Date,Close\n2018-01-01,1\n")
    monkeypatch.setattr(real, "RAW_ROOT", raw)
    monkeypatch.setattr(real, "PROCESSED_ROOT", tmp_path / "processed")
    config = {"period": 1, "short_gap_limit": 1, "minimum_nonmissing_fraction": 0.0, "input_length": 1, "horizons": [1], "minimum_eligible_test_origins": 0}
    # The miniature input cannot meet production split constraints; confirm the parser reaches the nested station frame instead of outer data.csv.
    try:
        _prepare_beijing(config)
    except ValueError as exc:
        assert "too short" in str(exc)


def test_evaluation_inverts_real_panel_scaling_before_metrics(tmp_path) -> None:
    values = np.array([[0.0, 1.0, 2.0, 3.0, 4.0]], dtype=np.float32)
    info = [SeriesInfo("a", period=2, train_end=3, valid_end=4, source="test")]
    dataset = WindowDataset(values, info, np.array([[0, 4]]), 4, 1, 1e-6, 2.5)
    rows, _ = evaluate_model(
        PersistenceModel(1), dataset,
        [{"series_id": "a", "mechanism": "real", "strength": float("nan"), "training_mean": 10.0, "training_std": 2.0}],
        torch.device("cpu"), "M0", 1, [1], tmp_path / "prediction.npz", "test", inverse_to_raw=True,
    )
    overall = next(row for row in rows if row["state"] == "all")
    assert overall["mae"] == 2.0
    with np.load(tmp_path / "prediction.npz") as result:
        assert result["prediction"][0, 0] == 16.0
        assert result["target"][0, 0] == 18.0


def test_training_scaler_uses_only_finite_training_observations() -> None:
    values, _, _, quality = _panel_series(
        [np.array([1.0, 2.0, np.nan, np.nan, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])],
        ["a"], period=1, source="test", max_gap=1, minimum_fraction=0.0, cap=None,
        input_length=1, horizon=1, minimum_test_origins=0,
    )
    included = next(item for item in quality if item["included"])
    assert np.isfinite(included["training_mean"])
    assert np.isfinite(included["training_std"])
