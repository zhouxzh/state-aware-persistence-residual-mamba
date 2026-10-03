from __future__ import annotations

from pathlib import Path

from experiments.sapr_mamba.run import verify_synthetic


def test_verify_accepts_scalar_artifact_metadata(tmp_path, monkeypatch) -> None:
    from experiments.sapr_mamba import run
    from utils.sapr_mamba.io import atomic_write_json, sha256_path

    root = tmp_path / "synthetic"
    payload = root / "M0_seed1" / "predictions.npz"
    payload.parent.mkdir(parents=True)
    payload.write_bytes(b"artifact")
    atomic_write_json(payload.parent / "task_manifest.json", {"status": "complete", "artifacts": {"prediction_archive": {"path": str(payload), "sha256": sha256_path(payload)}, "origins": 42}})
    monkeypatch.setattr(run, "RESULT_ROOT", tmp_path)
    result = verify_synthetic()
    assert result["tasks"] == 1
    assert result["failures"] == []
