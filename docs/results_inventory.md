# 历史金融结果清单与保留边界

更新日期：2026-10-02。本文件描述已完成的 Regime-Gated Mamba 金融 S-only 研究，
不描述或支撑当前状态感知持久性残差 Mamba 的新实验。

2026-10-02，在三套冻结发布物完成 SHA-256 校验、且无训练或分析进程运行后，服务器已
删除所有历史 `results/`、`checkpoints/`、回放树、旧 S/MS 归档、旧备份结果、TensorBoard、
日志和缓存。下方出现这些路径的文字是**历史记录**，不表示路径仍存在或可用于重跑。
保留范围是 `reproducibility/`、源代码、配置、`data/` 和 `backup/data/`；后者尚未纳入
新研究协议。

新研究不得从这些金融材料选择数据、阈值、模型或有利结论。历史发布物的完整性校验通过：
V1 25/25、V2 25/25、V2 supplement 21/21。

---

# Historical Results Inventory

## Preserved Historical Evidence

| Location | Git status | Role |
| --- | --- | --- |
| `reproducibility/financial_s_only_v1/` | Tracked | Verified v1 protocol, selections, data manifest, compact metrics, profile, claim map, runtime metadata, and checksums. |
| `reproducibility/financial_s_only_v2/` | Tracked | Verified v2 protocol, selections, data manifest, compact metrics, paired comparisons, profile, claim map, runtime metadata, and checksums. |
| Historical `results/financial_s_only_*` trees | Deleted 2026-10-02 | Original forecast arrays, reports, and replay trees were removed after release verification. |
| Historical `checkpoints/financial_s_only_*` trees | Deleted 2026-10-02 | Original per-run checkpoints were removed after release verification. |
| `docs/figures/financial_s_only_v1_*` | Tracked | Figures rendered from checksum-covered v1 tables, with source and output hashes in the figure manifest. |
| `docs/figures/financial_s_only_v2_*` | Tracked | Figures rendered from checksum-covered v2 tables, with source and output hashes in the figure manifest. |
| `docs/analysis/financial_s_only_v2/` | Tracked | Derived V2 model, horizon, family, target, normalized-metric, seed-stability, summary, and provenance tables. |

Each compact release is its own historical citation source. The original forecast and
checkpoint files were intentionally removed from this server after verification; they
cannot now be used for replay or regeneration. Recreating them requires explicit
authorization, source-data review, and a new versioned output directory.

The derived V2 analysis directory is reproducible from the compact release tables;
it is a reporting layer, not a replacement for the release contract.

## Historical Replay Boundary

Before deletion, `--stage replay` reloaded local v1 checkpoints and wrote a separate ignored
`results/financial_s_only_retrospective_v1/replay/` tree. `--stage replay-verify`
then compares each replayed prediction and truth array with its source artifact at
absolute tolerance `1e-6`, and requires exact origin and forecast dates. The local
`replay_validation.json` is a validation record, not a tracked evidence table. On
2026-08-14, the completed v1 audit validated all 1,320 bundles with zero problems,
zero maximum prediction/truth differences, and matching date arrays throughout.

The completed v2 campaign retained the same classes of local artifacts and used
the same replay commands. On 2026-08-21, its complete checkpoint reload and
array-equality audit validated all 5,940 learned bundles with zero problems,
zero maximum prediction/truth differences, and matching date arrays. The local
validation record remains an ignored artifact rather than a tracked evidence
table.

The V2 supplement was intentionally local-only and contained 540 learned cells. Its
paired tables compare Regime-Gated Mamba with Ungated Regime-Linear Mamba only;
no baseline or Optuna rerun is represented there.

## Removed Historical Material

Mixed S/MS campaign roots and the unused reference workspace were moved on 2026-08-12
into `backup/legacy_s_ms_20260812/`, then deleted on 2026-10-02 after the financial
releases had been verified:

| Original root | Files | Bytes |
| --- | ---: | ---: |
| `results/financial_mamba_rerun_v1` | 7,285 | 3,841,951,196 |
| `results/financial_baseline_rerun_v1` | 7,203 | 3,839,240,640 |
| `checkpoints/financial_mamba_rerun_v1` | 1,211 | 3,454,393,995 |
| `checkpoints/financial_baseline_rerun_v1` | 1,201 | 17,255,178,813 |
| `results/manuscript_evidence` | 23 | 771,323 |

The archive contained 16,923 files totaling 28,391,535,967 bytes. It is no longer
available on ace2. Its historical inventory was retained only in prior audit records;
the active workflow never read it.

## Git Policy

`data/`, `results/`, `checkpoints/`, `backup/`, TensorBoard output, and
source-provider archives are ignored. Commit code, configurations, release
contracts, compact metric tables, documentation, and generated figures. Do not
commit raw financial levels or bulk forecast/checkpoint artifacts without a separate
rights and repository-size review.
