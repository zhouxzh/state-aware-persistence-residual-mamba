# Results Inventory

## Active Evidence

| Location | Git status | Role |
| --- | --- | --- |
| `reproducibility/financial_s_only_v1/` | Tracked | v1 protocol, selections, data manifest, deterministic metrics, profile, and status. |
| `reproducibility/financial_s_only_v2/` | Tracked | v2 protocol, selections, data manifest, deterministic metrics, profile, and status. |
| `results/financial_s_only_retrospective_v1/` | Ignored local | Deterministic bundles plus the in-progress, restart-safe v1 learned campaign, retained forecasts, checkpoints, and summary. |
| `results/financial_s_only_retrospective_v2/` | Ignored local | v2 deterministic forecast bundles now; later learned forecasts and reports. |
| `checkpoints/financial_s_only_retrospective_v1/` | Ignored local | Retained checkpoints for completed v1 learned bundles. |
| `checkpoints/financial_s_only_retrospective_v2/` | Ignored local | Reserved for the v2 learned campaign, which has not started. |

The two tracked deterministic metric tables are compact release inputs. Their local
bundle fields point to prediction arrays that are intentionally not committed.

## Archived Historical Material

The mixed S/MS campaign roots and unused reference workspace were recoverably moved
on 2026-08-12 into `backup/legacy_s_ms_20260812/`:

| Original root | Files | Bytes |
| --- | ---: | ---: |
| `results/financial_mamba_rerun_v1` | 7,285 | 3,841,951,196 |
| `results/financial_baseline_rerun_v1` | 7,203 | 3,839,240,640 |
| `checkpoints/financial_mamba_rerun_v1` | 1,211 | 3,454,393,995 |
| `checkpoints/financial_baseline_rerun_v1` | 1,201 | 17,255,178,813 |
| `results/manuscript_evidence` | 23 | 771,323 |

Two empty legacy roots were archived with the same manifest. The archive contains
16,923 files totaling 28,391,535,967 bytes. Every root has an inventory SHA-256 and
explicit restoration target in `archive_manifest.json`. The active workflow never
reads it.

The historical source code, configurations, compact old results, and legacy figures
were removed from the active repository head. Git history retains them, but they must
not be reintroduced into a new S-only result table.

## Git Policy

`data/`, `results/`, `checkpoints/`, `backup/`, TensorBoard output, and source-provider
archives are ignored. Commit code, configurations, release contracts, compact metric
tables, documentation, and generated architecture figures only. Do not commit raw
financial series or bulk prediction/checkpoint artifacts without a separate rights and
repository-size review.
