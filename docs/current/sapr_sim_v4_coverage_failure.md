# SAPR Sim V4 Coverage Failure

**Status:** immutable pre-training failure record.  
**Date:** 2026-10-09.

V4 generated independent synthetic data but did not start model training because
its frozen pre-training coverage gate failed.  Its global two-window detector
threshold was 4.8685, calibrated from training origins only.  That threshold
made the detector nearly inactive for trend-break visible changes while it was
strongly activated by random-walk accumulation.

- T4 trend break: visible-minus-stable trigger rate = -0.0017.
- T6 seasonal change: visible-minus-stable trigger rate = 0.7891.
- T8 random walk stable origins: trigger rate = 0.7418.

The protocol required at least a 0.10 visible-minus-stable lift for both T4 and
T6, so the gate correctly prevented V4 training.  No V4 threshold, generator,
or model was changed after this outcome.  V5 is a separately generated study
with a documented per-series causal-prefix calibration rule and a predeclared
T4-only gate claim.

Evidence: `docs/current/sapr_sim_v4_coverage.json` and
`reproducibility/sapr_sim_v4/configuration_lock.json`.
