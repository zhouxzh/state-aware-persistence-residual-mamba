# Final Evaluation Acceptance Record

## Active Releases

| Release | Purpose | Current status |
| --- | --- | --- |
| `financial_s_only_v1` | Four original target-only panels | Verified retrospective release: 1,320 learned and 72 deterministic rows |
| `financial_s_only_v2` | Eighteen independently materialized financial targets | Verified retrospective release: 5,940 learned and 324 deterministic rows |
| `financial_s_only_v2_supplement` | Long-horizon two-model gate ablation supplement | Completed local V2 supplement: 540 learned rows; not a new publication comparison release |

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

## Verified v2 Acceptance Checks

The v2 release extends the target roster while retaining the same S-only,
retrospective protocol. It satisfies the following result-release checks:

1. All 18 x 11 x 5 x 6 = 5,940 learned task-model-seed-horizon rows are complete.
2. All 18 x 3 x 6 = 324 deterministic rows are complete.
3. All 5,940 learned units retain a checkpoint, prediction, truth, origin dates,
   forecast dates, metadata, and SHA-256 records; the release verifier reports no
   missing or mismatched artifacts.
4. The tracked compact release includes seed-level and aggregate metrics, paired
   contrasts, scale-normalized block-bootstrap output, runtime metadata, a claim
   map, the fixed CUDA profile, and a checksum manifest.
5. The verifier result is `verified` with an empty `problems` list in
   [the v2 release status](../reproducibility/financial_s_only_v2/release_status.json).
6. The detailed derived analysis validates the same release tables and records
   source/output hashes in
   [analysis_manifest.json](analysis/financial_s_only_v2/analysis_manifest.json).

V2 completed the full checkpoint reload and array-equality replay audit on
2026-08-21. The local validation record at
`results/financial_s_only_retrospective_v2/replay/replay_validation.json` reports
`status=verified`, `expected_entries=5940`, `validated_entries=5940`, and an empty
`problems` list. All prediction and truth maximum absolute differences are `0.0`,
and origin and forecast dates match exactly. The bulk validation record remains
local rather than tracked; the compact release and replay command remain the
reproducibility contract.

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

The checksum-covered v1 and v2 compact tables are ready for a technical report or
manuscript draft, provided they retain their retrospective labels and separate
target rosters. They must not be pooled for significance claims. The completed v2
gate result supports a corrected ablation claim through horizon 20, not a broad
accuracy-superiority claim; its replay-audit boundary must also be disclosed. A
redesigned gate or a new untouched test period requires a new versioned release
rather than an update to either release.

The detailed V2 interpretation and machine-readable tables are maintained in
[v2_evaluation_record.md](v2_evaluation_record.md) and
[analysis/financial_s_only_v2/README.md](analysis/financial_s_only_v2/README.md).

## V2 Supplement Boundary

The V2 supplement is a targeted retrospective diagnostic for the long-horizon
weakness observed in V2. It retains only Regime-Gated Mamba and Ungated
Regime-Linear Mamba at horizons 60, 120, and 252 over the same 18 targets and
five seeds. The design is therefore 540 learned cells, with frozen V2 selections
and no new Optuna search. Its paired bootstrap and runtime figures can support a
gate-mechanism discussion, but cannot establish superiority over PatchTST,
TimesNet, or any other baseline. Supplement artifacts are ignored; the tracked
V2 compact tables remain the reproducibility and manuscript evidence source.
