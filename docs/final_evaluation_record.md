# Final Evaluation Acceptance Record

## Active Releases

| Release | Purpose | Current status |
| --- | --- | --- |
| `financial_s_only_v1` | Four original target-only panels | Deterministic matrix complete; learned matrix in progress and not claim-eligible |
| `financial_s_only_v2` | Eighteen independent financial targets | Deterministic matrix complete; learned matrix pending |

These releases are separate evidence records. v2 expands the target roster and
maximizes per-series history; it does not replace v1 or permit pooled significance
claims across all targets.

## Frozen Protocol

- Input policy: target-only `S` input for every task.
- Splits: training through 2020-12-31; validation in 2021--2022; retrospective
  evaluation in 2023-01-01 through 2026-06-30.
- Horizons: 1, 5, 20, 60, 120, 252 retained observations.
- Seeds: 2023, 2024, 2025, 2026, 2027 for learned models.
- Learned roster: 11 models, including the full Regime-Gated Mamba and ungated
  ablation.
- Deterministic roster: Last-value, Random-walk-with-drift, ARIMA.
- Primary metric: path RMSSE; path and terminal MAE/RMSE/RMSSE are retained.
- Evidence label: `retrospective_protocol_matched`.

The authoritative protocol files are
[v1 protocol](../reproducibility/financial_s_only_v1/protocol.json) and
[v2 protocol](../reproducibility/financial_s_only_v2/protocol.json).

## Acceptance Criteria

A release may move from `incomplete` to `verified` only when all of the following
are true:

1. Every expected task-model-seed-horizon learned unit is complete.
2. Every checkpoint, prediction array, truth array, origin-date array, forecast-date
   array, and metadata file matches its recorded SHA-256.
3. The deterministic matrix matches every expected task-model-horizon cell.
4. Learned and deterministic outputs use identical rolling origins and the same
   training-window RMSSE denominator for each target.
5. The report writes per-seed metrics, aggregates, contrasts, block-bootstrap output,
   runtime environment, claim-evidence map, and valid `SHA256SUMS.json`.
6. No task, model, seed, horizon, excluded failure, or protocol deviation is hidden.

Only then may manuscript tables or figures use the released learned-model numbers.
The result remains retrospective and must not be relabeled as a clean prospective
test after completion.
