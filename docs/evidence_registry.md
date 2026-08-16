# Technical Evidence Registry

This registry binds current technical statements to inspectable active artifacts.
Archived mixed S/MS files are not evidence for a new manuscript claim.

| ID | Statement supported | Artifact |
| --- | --- | --- |
| E01 | v1 S-only protocol, horizons, seeds, ablations, and retrospective label | `reproducibility/financial_s_only_v1/protocol.json` |
| E02 | v2 independent-target roster and protocol | `reproducibility/financial_s_only_v2/protocol.json` |
| E03 | Data paths, target identities, split counts, and SHA-256 hashes | each release's `training_datasets.json` |
| E04 | Active model identities and role assignments | `model/RegimeGatedMamba.py`, each release `model_identity_map.json` |
| E05 | Active proposed architecture and ungated ablation | `docs/figures/regime_gated_mamba_s_only.dot` |
| E06 | Frozen pre-2023 parameter selections | each release `selection_manifest.json` and `selection/` files |
| E07 | Complete v1 deterministic metrics | `financial_s_only_v1/metrics/deterministic_metrics.csv` |
| E08 | Complete v1 learned seed-level, aggregate, and rank metrics | `financial_s_only_v1/metrics/metrics_by_seed.csv`, `metrics_aggregate.csv` |
| E09 | v1 Regime-Gated Mamba paired contrasts and scale-normalized block bootstrap | `financial_s_only_v1/metrics/paired_contrasts.csv`, `paired_block_bootstrap.csv` |
| E10 | v1 runtime environment, claims boundary, completion status, and checksums | `financial_s_only_v1/runtime_environment.json`, `claim_evidence_map.json`, `release_status.json`, `SHA256SUMS.json` |
| E11 | Fixed-workload v1/v2 CUDA profiles | each release's `metrics/matched_cuda_microbenchmark.csv` and `.json` |
| E12 | Current figures and their source-table provenance | `docs/figures/financial_s_only_v1_figure_manifest.json` |
| E13 | Complete v2 deterministic references and incomplete learned state | `financial_s_only_v2/metrics/deterministic_metrics.csv`, `release_status.json` |
| E14 | Historical local artifact archive inventory | ignored `backup/legacy_s_ms_20260812/archive_manifest.json` |

## Claim Boundaries

E08 supports retrospective, S-only path MAE/RMSE/RMSSE comparisons across the four
named v1 targets. E09 supports the documented paired ablation and deterministic
reference contrasts, with the stated four-task cluster limitation. E11 supports
only the bounded CUDA workloads and recorded campaign-runtime table.

The evidence supports the narrow observation that Regime-Gated Mamba is rank 1 for
the two longest DGS10 yield horizons in v1 and has lower recorded campaign runtime
than PatchTST and TimesNet. It does not support a prospective-test claim, a trading
claim, economic causality, a broad financial-market generalization, or an
unqualified overall accuracy advantage.

Every numeric statement in a future manuscript should map to E01--E13 and retain
the retrospective label. New targets, a modified gate, or an untouched test period
need a separate release and new evidence IDs.
