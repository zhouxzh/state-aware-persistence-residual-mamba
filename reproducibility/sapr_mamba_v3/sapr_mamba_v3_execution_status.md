# SAPR-Mamba V3 Automated Execution

V3 is an independent confirmation protocol layered on the immutable V2 release.
The pipeline entry point is `scripts/sapr_mamba_v3_pipeline.py`; it records every
attempt in `results/sapr_mamba_v3/pipeline_state.json` and never emits a blocked
state. Failures trigger identical retry, resource remediation, source-pool
expansion, or estimand downgrade while retaining the original evidence.

Current automated artifacts:

- `configs/sapr_mamba_v3/protocol.lock.json`: frozen V3 protocol and hashes.
- `data/sapr_mamba_v3/source_pool_audit.json`: deterministic source candidate order.
- `docs/analysis/sapr_mamba_v3/v3_plan_audit.json`: protocol feasibility audit.
- `manuscript/sapr_mamba_v3/`: generated manuscript scaffold and submission manifest.
- `reproducibility/sapr_mamba_v3/`: checksum-covered automated bundle.
- `scripts/sapr_mamba_v3_autocontinue.py`: resumable follow-on supervisor;
  it waits for the active real run and then executes external integration,
  analysis, verification, release, and tests with half-hour progress events.

V2 remains read-only development evidence. V3 numerical conclusions are generated
only after the full synthetic, real, external, robustness, verification, and
release stages complete. A `complete_with_limitations` result is valid and must
carry its limitation manifest into the manuscript.

The V3.1 amendment is source-additive: its panel geometry is resolved from
`configs/sapr_mamba_v3/amendments/v3.1_public_multiseries_sources.json`, while
the V3.0 top-level configuration remains hash-stable for already completed
tasks.

The base six-panel matrix has completed. The four-panel V3.1 extension is
running independently under the explicit `SAPR_MAMBA_VERSION=v3` environment;
the final completion guard requires 950 complete task manifests before it
rebuilds analysis, verification, manuscript, and release artifacts.
