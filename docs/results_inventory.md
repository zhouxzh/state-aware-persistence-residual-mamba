# Results Inventory

## Active Evidence

| Location | Git status | Role |
| --- | --- | --- |
| `reproducibility/financial_s_only_v1/` | Tracked | Verified v1 protocol, selections, data manifest, compact metrics, profile, claim map, runtime metadata, and checksums. |
| `reproducibility/financial_s_only_v2/` | Tracked | v2 protocol, selections, data manifest, deterministic metrics, profile, and incomplete learned status. |
| `results/financial_s_only_retrospective_v1/` | Ignored local | Complete v1 deterministic and learned forecast bundles, aggregate build inputs, campaign summary, and a 1,320-bundle exact-match checkpoint replay audit. |
| `checkpoints/financial_s_only_retrospective_v1/` | Ignored local | One retained checkpoint for every v1 learned task-model-seed-horizon unit. |
| `results/financial_s_only_retrospective_v2/` | Ignored local | v2 deterministic bundles only; learned output has not started. |
| `checkpoints/financial_s_only_retrospective_v2/` | Ignored local | Reserved for a future v2 learned release. |
| `docs/figures/financial_s_only_v1_*` | Tracked | Figures rendered from checksum-covered v1 tables, with source and output hashes in the figure manifest. |

The v1 compact release is the citation source. Local forecast and checkpoint files
are the regeneration source: they are needed to rerun checkpoint evaluation and to
rebuild compact tables, but remain untracked because of size and source-data rights.
The campaign has 1,320 learned task-model-seed-horizon outputs and retains the
corresponding prediction, truth, origin-date, forecast-date, metric, and metadata
files.

## Checkpoint Replay Boundary

`--stage replay` reloads local v1 checkpoints and writes a separate ignored
`results/financial_s_only_retrospective_v1/replay/` tree. `--stage replay-verify`
then compares each replayed prediction and truth array with its source artifact at
absolute tolerance `1e-6`, and requires exact origin and forecast dates. The local
`replay_validation.json` is a validation record, not a tracked evidence table. On
2026-08-14, the completed v1 audit validated all 1,320 bundles with zero problems,
zero maximum prediction/truth differences, and matching date arrays throughout.

## Archived Historical Material

Mixed S/MS campaign roots and the unused reference workspace were recoverably moved
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
reads this archive.

## Git Policy

`data/`, `results/`, `checkpoints/`, `backup/`, TensorBoard output, and
source-provider archives are ignored. Commit code, configurations, release
contracts, compact metric tables, documentation, and generated figures. Do not
commit raw financial levels or bulk forecast/checkpoint artifacts without a separate
rights and repository-size review.
