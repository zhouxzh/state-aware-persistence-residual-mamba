from __future__ import annotations

import unittest
import json
from pathlib import Path

import numpy as np
import pandas as pd

from manuscript.scripts.generate_financial_results import latex_escape
from scripts.financial.analyze_financial_results import (
    add_skill,
    aggregate_metrics,
    moving_block_bootstrap,
    regime_by_date,
    regime_metrics,
    s_ms_comparison,
)


METRIC_COLUMNS = [
    "path_mae",
    "path_mse",
    "path_rmse",
    "path_rmsse",
    "terminal_mae",
    "terminal_mse",
    "terminal_rmse",
    "terminal_rmsse",
]


class FinancialAnalysisTests(unittest.TestCase):
    def test_s_ms_skill_comparison(self) -> None:
        neural_rows = []
        for task, mse in (("financial_fx_s", 2.0), ("financial_fx_ms", 1.0)):
            for seed in (1, 2):
                neural_rows.append(
                    {
                        "dataset": task,
                        "model": "NLinear",
                        "seed": seed,
                        "horizon": 5,
                        **{column: mse for column in METRIC_COLUMNS},
                    }
                )
        statistical_rows = [
            {
                "dataset": task,
                "model": "Last-value",
                "seed": "deterministic",
                "horizon": 5,
                **{column: 4.0 for column in METRIC_COLUMNS},
            }
            for task in ("financial_fx_s", "financial_fx_ms")
        ]
        aggregate = add_skill(
            aggregate_metrics(pd.DataFrame(neural_rows), pd.DataFrame(statistical_rows))
        )
        comparison = s_ms_comparison(aggregate)
        row = comparison[comparison["model"] == "NLinear"].iloc[0]
        self.assertAlmostEqual(float(row["s_skill_vs_last_value"]), 0.5)
        self.assertAlmostEqual(float(row["ms_skill_vs_last_value"]), 0.75)
        self.assertAlmostEqual(float(row["ms_minus_s_skill"]), 0.25)

    def test_moving_block_bootstrap_is_reproducible(self) -> None:
        difference = np.linspace(-2.0, -0.5, 100)
        first = moving_block_bootstrap(difference, 5, 250, np.random.default_rng(123))
        second = moving_block_bootstrap(difference, 5, 250, np.random.default_rng(123))
        self.assertEqual(first, second)
        self.assertLess(first["ci_high"], 0.0)
        self.assertEqual(first["block_length"], 5)

    def test_latex_escape(self) -> None:
        self.assertEqual(latex_escape("financial_fx & 5%"), r"financial\_fx \& 5\%")

    def test_prespecified_regime_metrics(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        protocol = json.loads((repo_root / "configs" / "financial_benchmark.json").read_text())
        manifest = json.loads(
            (repo_root / "data" / "financial" / "manifests" / "training_datasets.json").read_text()
        )
        assignments = regime_by_date(manifest, protocol)["financial_fx_s"]
        selected_dates = []
        for label in protocol["regime_analysis"]["labels"]:
            selected_dates.append(
                next(date for date, value in assignments.items() if date >= "2023-01-01" and value == label)
            )
        origins = np.asarray(selected_dates, dtype="U10")
        store = {
            "losses": {
                ("financial_fx_s", "NLinear", 1, 2023): np.ones(3),
                ("financial_fx_s", "Last-value", 1, "deterministic"): np.full(3, 2.0),
            },
            "origins": {
                ("financial_fx_s", "NLinear", 1, 2023): origins,
                ("financial_fx_s", "Last-value", 1, "deterministic"): origins,
            },
        }
        output = regime_metrics(protocol, manifest, store)
        self.assertEqual(len(output), 6)
        learned = output[output["model"] == "NLinear"]
        np.testing.assert_allclose(learned["skill_vs_last_value"], 0.5)


if __name__ == "__main__":
    unittest.main()
