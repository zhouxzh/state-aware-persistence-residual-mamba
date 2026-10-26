# SAPR Simulation Evidence Synthesis

**Status:** evidence-bounded internal record, not a submission-ready manuscript.
**Date:** 2026-10-09.
**Scope:** independently executed simulation versions only. Estimates are never pooled across versions.

## Evidence Boundary

Each result below is bound to retained local artifacts, configuration locks, task manifests, and SHA-256 checksums. This record reports computational evidence; it does not supply authorship, declarations, venue selection, literature verification, or human approval required for submission.

## Version Decisions

| Version | Matrix / status | T0 | T2 | T8 | Residual patch | State-gate claim | Interpretation |
|---|---|---|---|---|---|---|---|
| V1 | 40 tasks complete | pass | fail | pass | fail | fail | Future-jump negative control was invalidated by predictable pre-jump dynamics. |
| V2 | 40 tasks complete | pass | fail | pass | fail | fail | Direction balancing alone did not remove that confound. |
| V3 | 40 tasks complete | pass | pass | pass | pass: T4, T6 | fail | Random-walk future-jump control repaired, but the full M3 gate also benefited low-signal groups. |
| V4 | no model training | n/a | n/a | n/a | n/a | n/a | Frozen pre-training detector-coverage gate failed; retained as a design failure. |
| V5 | 45 tasks complete | pass | pass | pass | pass: T4, T6 | fail | Explicit binary trigger did not outperform the matched constant gate at T4 and did not show attribution against hidden/no-state controls. |

V1/V2 decision artifact SHA-256: `0b35eb990158ce4e9fc88279abf07f9658ef8415bec7c05a0db9fa5d2c2a2388`.
V3 decision artifact SHA-256: `645f37d65a7eac0dbcd47f23b0ce6dbe91b17248fbd50af58a993db4c2497604`.
V5 decision artifact SHA-256: `38fa71d57be47128c2027dcadc1a7644b7268212d6f972b65d37b4d21050a725`.

## What The Completed Evidence Supports

1. In V3 and V5, a persistence-residual Mamba path met the preregistered residual-patch criterion on the trend-break (T4) and seasonal-change (T6) mechanisms, after passing the future-jump (T2) and random-walk (T8) safety controls.
2. The result is mechanism-bound. It does not establish that a residual network broadly solves nonstationarity, and it does not establish a real-data claim.
3. The tested state-gate formulations do not meet the stated causal-gating criterion. V3 failed the low-signal matched-control condition. V5 passed its pre-training detector-discrimination gate but did not show T4 benefit over a matched constant gate, and the trigger gate was worse than the hidden-only and no-state-feature controls at all T4 horizons.

## V5 Key Checks

V5 used 45 complete task manifests with no failures. Every task has the same configuration, runner, and code hashes, and every retained metric, prediction, and checkpoint artifact was checksum-verified.

- T2: no model was significantly favorable to persistence after Holm adjustment.
- T8: the trigger gate was significantly worse than persistence at every tested horizon, which satisfies the negative-control requirement.
- T4 trigger gate minus constant gate was positive at horizons 12, 24, and 48, and null at 96; it was never significantly favorable after Holm adjustment.
- T4 trigger gate minus hidden-only and no-state-feature controls was positive at every horizon. Thus there is no attribution evidence for the explicit binary trigger.

The V5 detector coverage record reports a T4 visible-minus-stable trigger-rate lift of 0.1927 (0.4762 versus 0.2835), exceeding its frozen 0.10 prerequisite. Detector discrimination was therefore adequate for the planned test, but the model result remained negative.

## Consequences For A Paper

The available evidence does not support a paper whose contribution is an effective state-aware gate. It can support a narrower, transparent negative or boundary-focused result only after a human decision about the target venue, authors, disclosures, and whether a mechanism-specific residual-patch study is scientifically sufficient. The existing V3 real-data manuscript is an older, distinct artifact and must not be relabeled as a V5 confirmation.

No further gate architecture should be selected by these V5 test outcomes. A future gate study would require an independently justified architecture and a new simulation version with new data, seeds, and a new pre-training protocol.

## Primary Artifacts

- `docs/analysis/sapr_sim_v1/decision.json`
- `docs/analysis/sapr_sim_v2/decision.json`
- `docs/analysis/sapr_sim_v3/analysis_manifest.json`
- `docs/current/sapr_sim_v3_interpretation.md`
- `docs/current/sapr_sim_v4_coverage_failure.md`
- `docs/analysis/sapr_sim_v5/analysis_manifest.json`
- `docs/analysis/sapr_sim_v5/frozen_comparisons.csv`
- `docs/analysis/sapr_sim_v5/detector_truth_audit.csv`
- `reproducibility/sapr_sim_v5/checksums.json`
