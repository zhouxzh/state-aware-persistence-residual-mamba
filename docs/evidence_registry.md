# Technical Evidence Registry

This registry binds current technical statements to active, inspectable artifacts.
It does not treat archived mixed S/MS files as evidence for new manuscript claims.

| ID | Statement supported | Artifact |
| --- | --- | --- |
| E01 | v1 S-only protocol, horizons, seeds, ablations, and retrospective label | `reproducibility/financial_s_only_v1/protocol.json` |
| E02 | v2 independent-target roster and protocol | `reproducibility/financial_s_only_v2/protocol.json` |
| E03 | Data paths, counts, split counts, and SHA-256 hashes | `reproducibility/financial_s_only_v1/training_datasets.json`, `financial_s_only_v2/training_datasets.json` |
| E04 | Active model identities and role assignments | `model/RegimeGatedMamba.py`, each release `model_identity_map.json` |
| E05 | Active proposed architecture and ungated ablation | `docs/figures/regime_gated_mamba_s_only.dot` |
| E06 | Frozen pre-2023 model selections | each release `selection/` and `selection_manifest.json` |
| E07 | Complete v1 deterministic references | `financial_s_only_v1/metrics/deterministic_metrics.csv` |
| E08 | Complete v2 deterministic references | `financial_s_only_v2/metrics/deterministic_metrics.csv` |
| E09 | Fixed-workload v1/v2 CUDA profiles | each release's `metrics/matched_cuda_microbenchmark.csv` and `.json` |
| E10 | Current completion gap and acceptance state | each release `release_status.json` |
| E11 | Historical local artifact archive inventory | ignored `backup/legacy_s_ms_20260812/archive_manifest.json` |

## Claim Boundaries

At present, E07 and E08 support only deterministic-reference metrics. E09 supports
only bounded forward-pass profiles recorded on a dirty working tree, not a final
release-commit benchmark. No active artifact supports a learned-model
accuracy ranking, a Regime-Gated Mamba advantage, a long-horizon advantage, a
prospective-test claim, trading performance, or economic causality.

After all learned artifacts validate, the report builder will create per-seed metrics,
aggregates, contrasts, block-bootstrap tables, a runtime environment, a claim map,
and SHA-256 checksums. Those new files, rather than narrative memory or historic
tables, must support any manuscript number.
