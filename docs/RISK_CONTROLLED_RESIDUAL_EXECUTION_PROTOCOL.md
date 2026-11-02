# Risk-Controlled Residual Stage A Execution Protocol

This is the executable Stage A protocol for the approved
`RISK_CONTROLLED_RESIDUAL_RESEARCH_PLAN.md`. It is independent from all SAPR,
OCRA, encoder, and Study 3 namespaces. Stage B training is explicitly out of
scope.

## Fixed Decision Rule

For every frozen candidate and all four protection groups, the runner computes
the per-sequence path-RMSE difference from persistence. It applies a radial cap
to every residual output, computes the simultaneous Hoeffding radius over all
`K*G` candidate/group pairs, adds the `2*c*rho` total-variation penalty, and
accepts a candidate only if every protected-group upper bound is nonpositive.
The accepted candidate minimizes its worst-group bound; ties use candidate ID.
An empty accepted set returns persistence exactly.

## Gates

1. Seal verifies fresh seeds, IDs and hashes, then writes the complete protocol.
2. The literature gate produces a public-source evidence ledger but defaults to
   a non-novelty claim; no automated search may assert method novelty.
3. Pilot checks runtime, peak memory, numerical quadrature and data contracts.
4. The main 384-cell grid begins only if pilot estimates fit the fixed 48
   CPU-core-hour / 28 GiB operational envelope. The 28 GiB limit is a
   conservative run-time limit within the approved 32 GiB planning budget.
5. Independent target tests are generated only after all calibration decisions
   are frozen. Test results do not tune caps, K, rho, n, alpha or candidate order.

## Output

The ignored run root retains every chunk manifest, failure, cell summary, true
risk, target-test interval, resource measurement, decision ledger and checksum.
Compact evidence is eligible for later review only after hash verification.

## Execution Lifecycle

Run `seal`, `literature-gate`, `pilot`, `main`, `target-test`, `analyze`, and
`verify` in that order with `sci-agent`. `risk_controlled_monitor.py` writes a
host/GPU snapshot every 30 minutes and refreshes its live-process view every
minute. It records only the process carrying the matching `RCR_RUN_ID` and
never stops or changes any process. A failed gate leaves its artifacts in the
run root and prevents the next stage from unlocking.
