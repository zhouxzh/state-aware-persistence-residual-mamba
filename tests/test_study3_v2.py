from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

from scripts import study3_v2


ROOT = Path(__file__).resolve().parents[1]


def test_v2_protocol_locks_correct_noninferiority_direction_and_family() -> None:
    protocol, synthetic, _ = study3_v2.configs()

    assert len(study3_v2.registered_cells(protocol)) == 40
    assert protocol["evaluation"]["summary_noninferiority_difference"] == "RMSE(summary-on) - RMSE(summary-off)"
    assert protocol["evaluation"]["summary_noninferiority_margin_raw_path_rmse"] == 0.2
    assert protocol["evaluation"]["summary_noninferiority_confidence"]["level"] == 0.975
    assert "six" in protocol["evaluation"]["families"]["P2_summary_safety"]
    assert synthetic["base"]["future_jump_offset"] == 12


def test_noninferiority_uses_upper_bound_and_one_sided_holm_p_value() -> None:
    benign = np.full(100, 0.05)
    harmful = np.full(100, 0.25)

    assert study3_v2.one_sided_upper_bound(benign, 2000, 17, 0.975) < 0.2
    assert study3_v2.noninferiority_sign_flip(benign, 0.2, 2000, 18) < 0.05
    assert study3_v2.one_sided_upper_bound(harmful, 2000, 19, 0.975) > 0.2
    assert study3_v2.noninferiority_sign_flip(harmful, 0.2, 2000, 20) > 0.05


def test_v2_runner_is_directly_executable() -> None:
    completed = subprocess.run([sys.executable, "scripts/study3_v2.py", "--help"], cwd=ROOT, text=True, capture_output=True, check=False)

    assert completed.returncode == 0, completed.stderr
    assert "evaluate-once" in completed.stdout


def test_monitor_uses_configured_v2_runner(monkeypatch) -> None:
    from importlib import reload
    from scripts import study3_monitor

    monkeypatch.setenv("STUDY3_RUNNER", "scripts/study3_v2.py")
    reloaded = reload(study3_monitor)
    assert reloaded.RUNNER == "scripts/study3_v2.py"
