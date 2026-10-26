# SAPR Sim V5 Protocol

**Status:** frozen before training.  
**Relationship:** an independent successor to V1-V4; no prior simulation data,
seeds, configurations, outputs, or decisions are modified.

## Question

Can an explicit causal binary trigger improve a residual forecast on a type for
which the trigger demonstrably distinguishes visible change from its own stable
windows, without improving relative to a matched constant gate in low-signal
controls?

## Pre-training Gate

For every series, the AR-plus-season residual-shift threshold is calibrated
only from origins through time 672.  Evaluation starts at time 768.  The
threshold is the 0.80 calibration-prefix quantile, bounded to [0.5, 50].

Training is permitted only if T4 trend-break visible origins have at least a
0.10 higher trigger rate than T4 stable origins and every mechanism meets the
existing coverage counts.  The generated V5 coverage audit passed: T4 has a
0.193 visible-minus-stable trigger-rate lift.

## Matched Models

- `M3-trigger-gate`: residual gate receives only the frozen binary trigger.
- `M3-constant-gate`: same residual backbone with a learned constant gate.
- `M3-hidden-only`: same residual backbone with a hidden-history gate.
- `M3-no-state-feature`: same residual backbone with state features removed.

The state-gate claim requires all four T4 horizons to favor the trigger gate
over the constant gate after Holm adjustment, no significant trigger-gate
advantage over the constant gate on T0/T2/T7/T8, and T4 attribution evidence
against at least one hidden-only or no-state-feature control.  T2 and T8 must
also remain non-favorable relative to persistence.

See `configs/sapr_mamba_sim_v5/` and
`docs/current/sapr_sim_v5_coverage.json` for the machine-readable lock and
coverage audit.
