#!/usr/bin/env python
"""Choose a BOCPD candidate using validation detector diagnostics only."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPLORATIONS = tuple(f"bocpd_e{index}" for index in range(1, 6))


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    candidates = []
    for study in EXPLORATIONS:
        protocol = read(REPO_ROOT / "configs" / f"sapr_mamba_{study}" / "protocol.json")
        audit = read(REPO_ROOT / "docs" / "analysis" / f"sapr_{study}" / "validation_detector_selection.json")
        rows = {row["mechanism"]: row for row in audit["rows"]}
        required = tuple(protocol["detector_discrimination"]["required_mechanisms"])
        lifts = [float(rows[item]["visible_minus_stable"]) for item in required]
        low_signal = [float(rows[item]["stable_rate"] or 0.0) for item in ("stable", "random_walk")]
        candidates.append({"study": study, "minimum_visible_lift": min(lifts), "mean_low_signal_rate": sum(low_signal) / len(low_signal), "required_mechanisms": list(required), "uses_test_results": False})
    eligible = [item for item in candidates if item["minimum_visible_lift"] >= 0.1]
    ranked = sorted(eligible or candidates, key=lambda item: (-item["minimum_visible_lift"], item["mean_low_signal_rate"], item["study"]))
    result = {"status": "selected" if eligible else "no_eligible_candidate", "selection_split": "validation", "uses_test_results": False, "ranking": ranked, "selected_study": ranked[0]["study"] if ranked else None}
    output = REPO_ROOT / "reproducibility" / "sapr_bocpd_selection" / "selection_lock.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
