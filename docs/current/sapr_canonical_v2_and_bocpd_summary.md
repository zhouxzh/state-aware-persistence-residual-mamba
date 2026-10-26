# Canonical V2 And BOCPD Summary

## Canonical T0-T8 Matrix

`canonical_v2` is the completed, hash-consistent canonical execution of the
frozen T0-T8 question protocol after `canonical_v1` was retained as an invalid
interrupted audit. All 40 planned task manifests completed without failure.

- Coverage gate: passed.
- T0 safety, T2 future-jump leakage, and T8 random-walk controls: passed.
- Residual-patch combination: passed on T4 trend break and T6 seasonal change.
- State-gate claim: failed. The original `phi` gate improved relative to the
  constant-gate control in low-signal groups, so the gate-close condition was
  not met.

The canonical evidence supports only the mechanism-specific residual-patch
boundary. It does not support a state-aware gate claim.

## BOCPD Exploration Termination

Five predeclared BOCPD detector variants were evaluated independently before
model training. All failed their frozen coverage or detector-discrimination
gate, so none trained a model and no confirmation matrix was started.

| Variant | Pre-training outcome |
|---|---|
| E1 | Exact-current posterior was constant under fixed hazard. |
| E2 | Corrected recent-run posterior failed T4 discrimination. |
| E3 | Seasonal-residual posterior failed T4 and T6 discrimination. |
| E4 | Dual posterior passed T6 but failed T4 discrimination. |
| E5 | Lower-hazard long-window posterior passed T6 but failed T4 discrimination. |

The final selector lock is `no_eligible_candidate`; it used no validation or
test outcome to select a model, and it did not start confirmation. The planned
five-version exploration budget is exhausted. A future detector study requires
a newly justified protocol and a new independent namespace.

## Evidence

- `docs/analysis/sapr_canonical_v2/analysis_manifest.json`
- `docs/analysis/sapr_canonical_v2/decision.json`
- `reproducibility/sapr_canonical_v2/checksums.json`
- `docs/current/sapr_bocpd_e1_coverage.json`
- `docs/current/sapr_bocpd_e2_coverage_failure.md`
- `docs/current/sapr_bocpd_e3_coverage_failure.md`
- `docs/current/sapr_bocpd_e4_coverage_failure.md`
- `docs/current/sapr_bocpd_e5_coverage_failure.md`
- `reproducibility/sapr_bocpd_selection/selection_lock.json`
