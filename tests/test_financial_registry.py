import json
import unittest
from pathlib import Path

from utils.financial.registry import (
    canonical_model_id,
    public_name,
    runtime_model_name,
    source_model_id,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class FinancialRegistryTests(unittest.TestCase):
    def test_canonical_names_preserve_provenance_without_exposing_legacy_ids(self):
        self.assertEqual(canonical_model_id("PMSV5_R6"), "RegimeGatedMamba")
        self.assertEqual(public_name("RegimeGatedMamba"), "Regime-Gated Mamba")
        self.assertEqual(source_model_id("RegimeGatedMamba"), "PMSV5_R6")
        self.assertEqual(runtime_model_name("RegimeGatedMamba"), "RegimeGatedMamba")
        self.assertEqual(
            public_name("UngatedRegimeLinearMamba"),
            "Ungated Regime-Linear Mamba",
        )

    def test_active_releases_use_release_local_selection_snapshots(self):
        for release in ("v1", "v2"):
            config = json.loads(
                (REPO_ROOT / "configs" / f"financial_s_only_{release}.json").read_text()
            )
            root = REPO_ROOT / config["selection_snapshot"]
            self.assertTrue(root.is_dir())
            for task in json.loads(
                (REPO_ROOT / config["base_protocol"]["training_manifest"]).read_text()
            ):
                selection_task = task
                for family, mapped in config.get("selection_task_map", {}).items():
                    if task.startswith(f"financial_{family}_"):
                        selection_task = mapped
                        break
                self.assertTrue((root / selection_task / "mamba_best_params.json").is_file())
                self.assertTrue((root / selection_task / "baseline_best_params.json").is_file())


if __name__ == "__main__":
    unittest.main()
