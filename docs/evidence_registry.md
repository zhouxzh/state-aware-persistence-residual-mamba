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
| E12 | Current v1 figures and their source-table provenance | `docs/figures/financial_s_only_v1_figure_manifest.json` |
| E13 | Complete v2 deterministic and learned seed-level, aggregate, and rank metrics | `financial_s_only_v2/metrics/deterministic_metrics.csv`, `metrics_by_seed.csv`, `metrics_aggregate.csv` |
| E14 | v2 paired contrasts, scale-normalized bootstrap, runtime metadata, verified completion status, and checksums | `financial_s_only_v2/metrics/paired_contrasts.csv`, `paired_block_bootstrap.csv`, `runtime_environment.json`, `claim_evidence_map.json`, `release_status.json`, `SHA256SUMS.json` |
| E15 | Current v2 figures and their source-table provenance | `docs/figures/financial_s_only_v2_figure_manifest.json` |
| E16 | V2 derived model, horizon, family, target, normalized-metric, and seed-stability analysis | `docs/analysis/financial_s_only_v2/analysis_manifest.json` and derived CSV/JSON tables |
| E17 | Historical local artifact archive inventory | ignored `backup/legacy_s_ms_20260812/archive_manifest.json` |
| E18 | Corrected audit response and V2 supplemental gate-ablation computation record | `docs/audit_response_and_computation_plan.md` |

## Claim Boundaries

E08 supports retrospective, S-only path MAE/RMSE/RMSSE comparisons across the four
named v1 targets. E09 supports the documented paired ablation and deterministic
reference contrasts, with the stated four-task cluster limitation. E13 and E14
support the corresponding 18-target v2 comparisons, including the corrected
gate-ablation result through horizon 20. E11 supports only the bounded CUDA
workloads and recorded campaign-runtime tables.

The evidence supports the narrow observations that Regime-Gated Mamba is rank 1
for the two longest DGS10 yield horizons in v1; has four rank-1 cells and a
corrected gate-ablation advantage through horizon 20 in v2; and has lower recorded
campaign runtime than PatchTST and TimesNet in both releases. It does not support
a prospective-test claim, a trading claim, economic causality, a broad
financial-market generalization, or an unqualified overall accuracy advantage.

Every numeric statement in a future manuscript should map to E01--E18 and retain
the retrospective label and release boundary. New targets, a modified gate, or an
untouched test period need a separate release and new evidence IDs.
