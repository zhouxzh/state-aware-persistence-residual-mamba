from __future__ import annotations

import json
import inspect
import subprocess
import sys
from pathlib import Path

import numpy as np

from scripts import study3_v1


ROOT = Path(__file__).resolve().parents[1]


def test_study3_protocol_has_the_registered_40_cell_matrix_and_locked_margin() -> None:
    protocol, synthetic, _ = study3_v1.configs()
    cells = study3_v1.registered_cells(protocol)

    assert len(cells) == 40
    assert len({(cell["lookback"], cell["model"], cell["seed"]) for cell in cells}) == 40
    assert protocol["evaluation"]["summary_noninferiority_margin_raw_path_rmse"] == 0.2
    assert protocol["evaluation"]["future_jump_offset"] == synthetic["base"]["future_jump_offset"] == 12
    first = cells[0]
    inspect.signature(study3_v1.train_cell).bind(first["lookback"], first["model"], first["seed"])


def test_study3_primary_groups_have_exactly_100_test_sequences_and_n2_is_in_horizon() -> None:
    protocol, synthetic, _ = study3_v1.configs()
    records = study3_v1.make_records("test", synthetic, protocol["series_id_prefix"])
    origins = study3_v1.origins_for(records, protocol, synthetic)
    groups = study3_v1.origin_groups(records, origins, protocol, synthetic)

    counts = {
        group: {records[int(series)]["series_id"] for (series, _), value in zip(origins, groups) if value == group}
        for group in ("N2", "N8", "S4", "S6")
    }
    assert {group: len(identifiers) for group, identifiers in counts.items()} == {"N2": 100, "N8": 100, "S4": 100, "S6": 100}
    for (series, origin), group in zip(origins, groups):
        if group == "N2":
            point = records[int(series)]["change_point"]
            assert 0 < point - int(origin) <= protocol["horizon"]
            assert point - int(origin) == 12


def test_study3_summary_off_dataset_contains_no_state_summary() -> None:
    protocol, synthetic, _ = study3_v1.configs()
    records = study3_v1.make_records("train", synthetic, protocol["series_id_prefix"])
    values = study3_v1.materialize(records[:2], synthetic, "train")
    origins = np.asarray([[0, 768], [1, 768]], dtype=np.int64)
    dataset = study3_v1.OriginDataset(values, origins, 96, protocol["horizon"], summary_on=False)

    assert np.array_equal(dataset.features, np.zeros((2, 9), dtype=np.float32))


def test_study3_monitor_reports_unsealed_test_as_locked(tmp_path, monkeypatch) -> None:
    from scripts import study3_monitor

    monkeypatch.setattr(study3_monitor, "RUN_ROOT", tmp_path)
    (tmp_path / "protocol").mkdir()
    (tmp_path / "protocol" / "protocol.json").write_text(json.dumps({"status": "sealed_before_training"}), encoding="utf-8")

    assert study3_monitor.protocol_snapshot() == {
        "status": "sealed_before_training",
        "release_gate": "not_run",
        "test_access": "locked",
        "test_numeric_materialized": False,
    }


def test_study3_monitor_uses_study_run_root_when_dedicated_root_is_not_set(monkeypatch) -> None:
    from importlib import reload
    from scripts import study3_monitor

    monkeypatch.setenv("STUDY3_RUN_ROOT", "results/study3_v1_r1")
    monkeypatch.delenv("STUDY3_MONITOR_RUN_ROOT", raising=False)
    reloaded = reload(study3_monitor)
    assert reloaded.RUN_ROOT.name == "study3_v1_r1"


def test_study3_runner_help_is_directly_executable() -> None:
    completed = subprocess.run([sys.executable, "scripts/study3_v1.py", "--help"], cwd=ROOT, text=True, capture_output=True, check=False)

    assert completed.returncode == 0, completed.stderr
    assert "evaluate-once" in completed.stdout
