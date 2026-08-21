# Results Inventory

## Active Evidence

| Location | Git status | Role |
| --- | --- | --- |
| `reproducibility/financial_s_only_v1/` | Tracked | Verified v1 protocol, selections, data manifest, compact metrics, profile, claim map, runtime metadata, and checksums. |
| `reproducibility/financial_s_only_v2/` | Tracked | Verified v2 protocol, selections, data manifest, compact metrics, paired comparisons, profile, claim map, runtime metadata, and checksums. |
| `results/financial_s_only_retrospective_v1/` | Ignored local | Complete v1 deterministic and learned forecast bundles, aggregate build inputs, campaign summary, and a 1,320-bundle exact-match checkpoint replay audit. |
| `checkpoints/financial_s_only_retrospective_v1/` | Ignored local | One retained checkpoint for every v1 learned task-model-seed-horizon unit. |
| `results/financial_s_only_retrospective_v2/` | Ignored local | Complete v2 deterministic and learned forecast bundles, aggregate build inputs, and campaign summary. |
| `checkpoints/financial_s_only_retrospective_v2/` | Ignored local | One retained checkpoint for every v2 learned task-model-seed-horizon unit. |
| `results/financial_s_only_exploratory_v3/` | Ignored local | Exploratory two-model long-horizon gate-ablation forecasts, reports, and replay validation. |
| `checkpoints/financial_s_only_exploratory_v3/` | Ignored local | Retained V3 checkpoints for 18 targets, 2 models, 5 seeds, and horizons 60/120/252. |
| `docs/figures/financial_s_only_v1_*` | Tracked | Figures rendered from checksum-covered v1 tables, with source and output hashes in the figure manifest. |
| `docs/figures/financial_s_only_v2_*` | Tracked | Figures rendered from checksum-covered v2 tables, with source and output hashes in the figure manifest. |
| `docs/analysis/financial_s_only_v2/` | Tracked | Derived V2 model, horizon, family, target, normalized-metric, seed-stability, summary, and provenance tables. |

Each compact release is its own citation source. Local forecast and checkpoint
files are the regeneration source: they are needed to rerun checkpoint evaluation
and to rebuild compact tables, but remain untracked because of size and
source-data rights. V1 retains 1,320 and V2 retains 5,940 learned
task-model-seed-horizon outputs, each with prediction, truth, origin-date,
forecast-date, metric, metadata, and checkpoint artifacts.

The derived V2 analysis directory is reproducible from the compact release tables;
it is a reporting layer, not a replacement for the release contract.

## Checkpoint Replay Boundary

`--stage replay` reloads local v1 checkpoints and writes a separate ignored
`results/financial_s_only_retrospective_v1/replay/` tree. `--stage replay-verify`
then compares each replayed prediction and truth array with its source artifact at
absolute tolerance `1e-6`, and requires exact origin and forecast dates. The local
`replay_validation.json` is a validation record, not a tracked evidence table. On
2026-08-14, the completed v1 audit validated all 1,320 bundles with zero problems,
zero maximum prediction/truth differences, and matching date arrays throughout.

The completed v2 campaign retains the same classes of local artifacts and uses
the same replay commands. On 2026-08-21, its complete checkpoint reload and
array-equality audit validated all 5,940 learned bundles with zero problems,
zero maximum prediction/truth differences, and matching date arrays. The local
validation record remains an ignored artifact rather than a tracked evidence
table.

V3 is intentionally local-only and contains 540 learned cells. Its paired tables
compare Regime-Gated Mamba with Ungated Regime-Linear Mamba only; no baseline or
Optuna rerun is represented there.

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
