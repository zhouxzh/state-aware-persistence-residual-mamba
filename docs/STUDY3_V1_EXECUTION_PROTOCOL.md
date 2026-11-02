# Study 3 Execution Protocol

This is the executable, independent realization of
`ENCODER_L_V1_FOLLOWUP_V2_RESEARCH_PLAN.md`. It does not change or reuse the
test data, locks, estimates, or model checkpoints from Study 1, Study 2, OCRA,
or prior encoder runs.

## Questions and Units

- P1 asks whether a residual forecaster improves on persistence when an unseen
  random-walk jump occurs 12 steps into the H=24 forecast window. The analysis
  unit is an independent test sequence, not its repeated origins or seeds.
- P2 compares Mamba0 minus MambaPhi. Positive values favour the state summary.
  S4/S6 are visible-change groups; N2/N8 are negative-control safety groups.
- Five fitted seeds are averaged within each sequence before paired inference.
  Bootstrap and sign-flip resampling operate only across independent sequences.

## Locked Design

The original `study3_v1.0` was sealed and stopped before its first model fit
because the matrix controller passed its model registry field with an unsupported
keyword argument. It has a retained failure record and no test numeric array.
The active independent execution is `study3_v1.r1`; its new seeds and series
prefix prevent reuse of the failed attempt's data or training seeds.

- Namespace: `study3_v1`; data and transient outputs: `results/study3_v1/`.
- Generator seed: `20261620`; training seeds: `20261621`--`20261625`.
- T=2048, H=24, period=48, origin stride=96, common legal-origin basis L=768.
- Train/validation/test contain 2,000/550/1,100 sequences respectively.
- Primary test groups N2, N8, S4, and S6 each contain exactly 100 sequences.
- N2 uses random-walk background and future-jump offset=12. N8 uses a near
  random walk with increment AR coefficient 0.05.
- The 40 training cells are all eight registered condition/lookback pairs times
  five independent training seeds.
- The N2/N8 non-inferiority contrast is `Mamba0 - MambaPhi`; the fixed margin is
  -0.20 raw path RMSE. This is 20% of the generator's unit innovation standard
  deviation and is not calibrated from prior test outcomes.

## Execution Gates

1. `seal` materializes only train/validation arrays, records test roster and all
   hashes, proves seed/series disjointness, and locks test numeric data.
2. `preflight` proves dimensions, causal features, common origins, coverage and
   a forward/backward GPU smoke operation without reading test numeric values.
3. Training records one atomic manifest per cell. The supervisor accepts only
   40 complete manifests with no recorded failures.
4. `release-gate` strict-loads every checkpoint, checks finite tensors and
   parameter counts, verifies all roster/config/source hashes and primary-group
   coverage, and requires the test array and one-time ledger to be absent.
5. Only after that gate passes does `evaluate-once` generate the test array,
   write its one-time ledger, and produce per-seed/per-sequence RMSE tables.
6. `analyze` writes paired percentile intervals, sign-flip p-values, Holm
   adjustments, safety/leakage flags, resource records, output hashes, and a
   release binding. It never refits or selects a model.

## Operational Safety

`study3_monitor.py` samples GPU and host state every 60 seconds while the
protocol is active, stores a complete snapshot every 30 minutes, warns at 80 C,
and terminates only Study 3 processes after three consecutive samples at or
above 85 C. `study3_supervisor.py` advances only after all gates pass; it never
restarts failed cells or bypasses a failed release gate.
