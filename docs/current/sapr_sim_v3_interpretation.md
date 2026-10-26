# SAPR Sim V3 Interpretation

**Status:** complete, immutable audit record.  
**Completed:** 2026-10-09.  
**Scope:** this note interprets only `sapr_sim_v3`; it does not pool V1, V2, real-data, or future-study estimates.

## Verified Evidence

- The full frozen matrix completed: 40 of 40 task manifests are `complete`, with no task failure.
- The pre-training coverage gate passed.
- Artifact verification passed for the analysis manifest and its retained files.
- Simulation-specific tests passed (7 passed), and the default suite passed (49 passed, 7 skipped).
- The unseen future-jump control passed: no model was significantly better than persistence after family-wise Holm adjustment.
- The random-walk control passed: no model was significantly better than persistence.
- The residual-patch criterion passed on the predeclared T4 trend-break and T6 seasonal-change groups.

## Rejected Claim

The state-gate claim is rejected for V3.  Although M3 outperformed the
constant-gate control on predeclared visible-change groups, it also significantly
outperformed that control on low-signal groups where the state-specific claim
requires no such advantage:

- T0 stable at all four horizons;
- T7 variance-only change at all four horizons; and
- T8 random walk at horizons 12, 24, 48, and 96 after Holm adjustment.

Consequently `state_gate_claim_pass` is `false`.  The result cannot be repaired
by changing a V3 threshold, architecture, outcome grouping, or statistical rule.

## Causal Diagnosis

V3 M3 computes its gate from both explicit causal state features and the Mamba
hidden representation.  Its improvement over a constant gate on low-signal
groups can therefore be a history-adaptive residual scaling effect rather than
evidence that the explicit state detector selectively opens a gate.  The
detector audit also shows that the frozen max-absolute-feature score has limited
discrimination for several visible-change mechanisms.  In particular, a detector
coverage count is not evidence of detector selectivity.

## Constraint On Follow-up Work

Any successor must be a new namespace with newly generated sequences, seeds,
configuration lock, and result root.  It must keep V3 untouched and predeclare:

1. a gate whose state-only path is separable from a hidden-history gate;
2. matched constant, hidden-only, and shuffled-state controls;
3. a detector-discrimination gate evaluated before model training; and
4. a state-gate decision requiring both signal-group benefit and no low-signal
   advantage relative to the matched constant gate.

Until such an independent study passes, the supported claim is limited to the
mechanism-specific residual-patch result, not a state-gating effect.

## Evidence Paths

- `docs/analysis/sapr_sim_v3/analysis_manifest.json`
- `docs/analysis/sapr_sim_v3/decision.json`
- `docs/analysis/sapr_sim_v3/frozen_comparisons.csv`
- `docs/analysis/sapr_sim_v3/detector_truth_audit.csv`
- `reproducibility/sapr_sim_v3/checksums.json`
