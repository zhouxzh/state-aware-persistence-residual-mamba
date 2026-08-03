# Agent Guide

## Research Position

This repository studies nonstationary time-series forecasting. Financial panels are
the current reference case, not the sole research domain or the final scope of the
work. Treat the four current financial panels as evidence about nonstationarity under
a documented protocol, rather than as a claim that this is only a financial-forecasting
project.

## Language and Claims

- Do not refer to subsequent outputs generically as "financial results".
  Prefer "nonstationary forecasting results on financial reference datasets" or name
  the exact dataset family and evaluation stage.
- Keep development, validation-selection, and untouched final-test evidence separate.
  Validation Optuna scores are not confirmatory final results.
- Do not claim cross-domain generalization, trading performance, market efficiency, or
  causal conclusions from the financial reference datasets alone.

## Dataset Expansion

- Continue expanding evaluation beyond the current financial reference panels.
  Follow `docs/next_optimization_plan.md` when proposing new task families or a V3
  evaluation.
- Prioritize diverse nonstationary mechanisms and domains, such as realized-volatility,
  macroeconomic, and external collection benchmarks, instead of adding many near-
  duplicate financial tickers.
- Before any new training, freeze the dataset rationale, provider and license, series
  identifiers, timestamp/frequency conventions, preprocessing, data cutoff, checksums,
  split boundaries, horizons, and target transformation.
- Select datasets before inspecting model outcomes. Do not use model performance or
  stationarity-test results to decide whether a completed dataset remains in scope.

## Preservation Rules

- Preserve the frozen `financial_confirmatory_v1` protocol and its local data, Optuna
  records, and provenance artifacts unless the user explicitly requests a new version.
- Keep raw and processed data subject to source redistribution terms. Publish manifests,
  checksums, and reproducibility parameters rather than restricted source data.

## Documentation and Paper Direction

- Treat `docs/current_results.md` as the current human-readable result summary and
  verify numeric claims against the frozen `reproducibility/` artifacts.
- Follow `docs/paper_writing_direction.md` for positioning, evidence boundaries, and
  supported claims. The present evidence supports a bounded mixed-result paper, not a
  state-of-the-art superiority claim.
- Keep executed protocols with their matching reproducibility release. Put only active,
  prospective plans under `docs/`.
