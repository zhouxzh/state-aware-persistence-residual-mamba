from __future__ import annotations

import unittest
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from scripts.financial.analyze_financial_results import (
    add_skill,
    aggregate_metrics,
    latex_escape,
    moving_block_bootstrap,
    regime_by_date,
    regime_metrics,
    s_ms_comparison,
)
from scripts.financial.run_statistical_baselines import select_arima_order


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
    def test_arima_selection_excludes_nonconverged_candidates(self) -> None:
        class FakeFit:
            def __init__(self, order: tuple[int, int, int]) -> None:
                self.aic = 1.0 if order == (3, 1, 3) else 10.0
                self.mle_retvals = {"converged": order == (1, 0, 0)}

        class FakeARIMA:
            def __init__(
                self,
                _target: np.ndarray,
                order: tuple[int, int, int],
                trend: str,
            ) -> None:
                self.order = order
                self.trend = trend

            def fit(self) -> FakeFit:
                return FakeFit(self.order)

        with patch("statsmodels.tsa.arima.model.ARIMA", FakeARIMA):
            order, audit = select_arima_order(np.arange(20, dtype=float))

        self.assertEqual(order, (1, 0, 0))
        self.assertEqual(audit["attempted_candidate_count"], 31)
        self.assertEqual(audit["converged_candidate_count"], 1)
        self.assertEqual(audit["nonconverged_candidate_count"], 30)
        self.assertTrue(audit["selected_converged"])

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

    def test_empty_prespecified_regime_is_reported_as_not_estimable(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        protocol = json.loads((repo_root / "configs" / "financial_benchmark.json").read_text())
        manifest = json.loads(
            (repo_root / "data" / "financial" / "manifests" / "training_datasets.json").read_text()
        )
        assignments = regime_by_date(manifest, protocol)["financial_fx_s"]
        middle_label = protocol["regime_analysis"]["labels"][1]
        origin = next(
            date for date, value in assignments.items() if date >= "2023-01-01" and value == middle_label
        )
        origins = np.asarray([origin], dtype="U10")
        store = {
            "losses": {
                ("financial_fx_s", "NLinear", 1, 2023): np.ones(1),
                ("financial_fx_s", "Last-value", 1, "deterministic"): np.full(1, 2.0),
            },
            "origins": {
                ("financial_fx_s", "NLinear", 1, 2023): origins,
                ("financial_fx_s", "Last-value", 1, "deterministic"): origins,
            },
        }

        output = regime_metrics(protocol, manifest, store)

        self.assertEqual(len(output), 6)
        empty = output[output["regime"] != middle_label]
        self.assertTrue((empty["origin_count"] == 0).all())
        self.assertTrue(empty["origin_mse_mean"].isna().all())
        self.assertTrue(empty["skill_vs_last_value"].isna().all())


if __name__ == "__main__":
    unittest.main()
