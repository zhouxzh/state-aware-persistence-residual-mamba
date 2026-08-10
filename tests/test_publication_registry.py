import json
import unittest
from pathlib import Path

from scripts.registry import (
    canonical_model_id,
    public_name,
    runtime_model_name,
    source_model_id,
)
from scripts.run_financial_reference_evaluation import compact_stage_tag


REPO_ROOT = Path(__file__).resolve().parents[1]


class PublicationRegistryTests(unittest.TestCase):
    def test_canonical_names_preserve_frozen_source_ids(self):
        self.assertEqual(canonical_model_id("PMSV5_R6"), "RegimeGatedMamba")
        self.assertEqual(canonical_model_id("PMSV3_B0"), "MultiScalePatchMamba")
        self.assertEqual(public_name("PMS_Mamba-PD"), "Legacy Patch-Decomposition Mamba")
        self.assertEqual(source_model_id("RegimeGatedMamba"), "PMSV5_R6")
        self.assertEqual(runtime_model_name("RegimeGatedMamba"), "RegimeGatedMamba")

    def test_publication_config_uses_tracked_selection_snapshots(self):
        config = json.loads((REPO_ROOT / "configs" / "financial_reference_evaluation_v1.json").read_text())
        root = REPO_ROOT / config["candidate_parameter_selection_snapshot"]
        tasks = json.loads((REPO_ROOT / config["base_protocol"]["training_manifest"]).read_text())
        for task in tasks:
            self.assertTrue((root / task / "mamba_best_params.json").is_file())
            self.assertTrue(
                (REPO_ROOT / "reproducibility" / "financial_reference_evaluation_v1" / "selection" / task / "baseline_best_params.json").is_file()
            )

    def test_publication_stage_tags_are_compact_and_deterministic(self):
        self.assertEqual(compact_stage_tag("RegimeGatedMamba", 2023), "pub_rgm_s2023")
        self.assertEqual(compact_stage_tag("MultiScalePatchMamba", 2027, smoke=True), "smk_msp_s2027")


if __name__ == "__main__":
    unittest.main()
