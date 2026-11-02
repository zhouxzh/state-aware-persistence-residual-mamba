# Risk-Controlled Residual v1.1 Amendment

`risk_controlled_residual_v1.0` was sealed and completed only its pilot. A
post-pilot implementation review found two execution defects before the main
grid was launched: cap cells consumed separate calibration draws despite the
declared common-random-numbers design, and analytic target risks were
recomputed for every chunk. No main calibration cell and no locked target-test
value was materialized under v1.0.

`risk_controlled_residual_v1.1` fixes both defects before any new run: it
shares each panel/repeat/group source draw across cap, K, n, and rho cells, and
caches each frozen analytic risk matrix by panel, cap, K, rho, and quadrature
rule. It has a new random seed, series-ID prefix, configuration directory and
ignored results root. The v1.0 seal, literature ledger and pilot remain
preserved under `results/risk_controlled_residual_v1/`; they are not pooled,
retuned, or reported as v1.1 evidence.

The statistical rule, grids, alpha, eta, candidate order, target-test size,
resource limits and Stage B prohibition are unchanged. The amended runner must
be committed and pushed before its own seal and pilot begin.
