# Study 3 v2 Execution Protocol

`study3_v2` is an independent implementation of the approved revised Study 3
plan. It does not reuse arrays, rosters, checkpoints, test access, estimates,
or conclusions from `study3_v1` or `study3_v1_r1`.

## Fixed Safety Design

- The safety contrast is `d = RMSE(MambaPhi) - RMSE(Mamba0)`. Positive values
  mean the state summary increased error.
- The approved non-inferiority margin is `delta = 0.20` raw path RMSE, equal to
  20% of the generator's fixed innovation standard deviation of 1.0.
- Each safety comparison uses a paired percentile-bootstrap 97.5% one-sided
  upper confidence bound and a paired one-sided sign-flip test of `E[d] < delta`.
- Six safety comparisons, N2/N8 at L96/L384/L768, form one Holm-adjusted family.
  A non-inferiority statement requires both upper bound `< 0.20` and
  Holm-adjusted one-sided `p < 0.05`.

The runner locks these settings before training. Test numeric data remain absent
until all 40 cells complete and the release gate validates checkpoints, hashes,
coverage, and the absent test-access ledger.
