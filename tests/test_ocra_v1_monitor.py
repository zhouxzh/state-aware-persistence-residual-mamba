from __future__ import annotations

import json

from scripts.ocra_v1_monitor import temperatures
from scripts import ocra_v1_monitor


def test_temperatures_ignores_missing_or_non_numeric_values() -> None:
    values = temperatures([{"temperature_c": "40"}, {"temperature_c": "N/A"}, {"unavailable": "driver"}])
    assert values == [40.0]


def test_protocol_snapshot_reports_terminal_supervisor_state_when_e2_did_not_pass(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(ocra_v1_monitor, "RUN_ROOT", tmp_path)
    state = tmp_path / "supervisor" / "state.json"
    state.parent.mkdir()
    state.write_text(json.dumps({"status": "stopped_e2_failed", "test_loaded": False}), encoding="utf-8")

    assert ocra_v1_monitor.protocol_snapshot() == {
        "status": "stopped_e2_failed",
        "stage": "supervisor",
        "test_loaded": False,
        "test_numeric_materialized": False,
    }
