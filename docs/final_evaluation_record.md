# Final Evaluation Acceptance Record

## Active Releases

| Release | Purpose | Current status |
| --- | --- | --- |
| `financial_s_only_v1` | Four original target-only panels | Verified retrospective release: 1,320 learned and 72 deterministic rows |
| `financial_s_only_v2` | Eighteen independent financial targets | Deterministic matrix complete; learned matrix pending |

The releases are separate evidence records. v2 expands the target roster and does
not replace v1, pool with v1, or permit pooled significance claims across targets.

## Verified v1 Acceptance Checks

The v1 release satisfies the result-release checks below:

1. All 4 x 11 x 5 x 6 = 1,320 learned task-model-seed-horizon rows are complete.
2. All 4 x 3 x 6 = 72 deterministic rows are complete.
3. Every completed learned unit records a checkpoint, prediction, truth, origin
   dates, forecast dates, metadata, and SHA-256 values; the release verifier reports
   no missing or mismatched artifacts.
4. Learned and deterministic outputs use the same rolling origins and the same
   target-specific training-window RMSSE denominator.
5. The release contains seed-level and aggregate metrics, paired contrasts,
   scale-normalized block-bootstrap output, the runtime environment, claim map, and
   a checksum manifest.
6. The verifier result is `verified` with an empty `problems` list in
   [release_status.json](../reproducibility/financial_s_only_v1/release_status.json).
7. A complete checkpoint replay audit on 2026-08-14 regenerated all 1,320 learned
   bundles. `--stage replay-verify` found zero problems: replayed predictions and
   truths had maximum absolute differences of `0.0`, and all origin and forecast
   date indices matched their source artifacts.

The replay validation record is intentionally not committed because it contains
bulk local replay paths. It remains available at
`results/financial_s_only_retrospective_v1/replay/replay_validation.json` on this
machine; the frozen compact release remains the citation source.

## Frozen Protocol

- Input policy: target-only `S` input for every task.
- Splits: training through 2020-12-31; validation in 2021--2022; retrospective
  evaluation in 2023-01-01 through 2026-06-30.
- Horizons: 1, 5, 20, 60, 120, 252 retained observations.
- Seeds: 2023, 2024, 2025, 2026, 2027 for learned models.
- Learned roster: 11 models, including full Regime-Gated Mamba and its ungated
  ablation.
- Deterministic roster: Last-value, Random-walk-with-drift, and ARIMA.
- Primary metric: path RMSSE; path and terminal MAE/RMSE/RMSSE are retained.
- Evidence label: `retrospective_protocol_matched`.

The authoritative protocol files are the [v1 protocol](../reproducibility/financial_s_only_v1/protocol.json)
and [v2 protocol](../reproducibility/financial_s_only_v2/protocol.json).

## Manuscript Boundary

Only v1 numbers cited from its checksum-covered aggregate tables are ready for a
technical report or manuscript draft. They must retain the retrospective label and
the four-series scope. v2 learned results, a redesigned non-degenerate gate, or a
new untouched test period require a new versioned release rather than an update to
this one.
