# 仓库结构与目录职责

更新日期：2026-10-02。此仓库的当前研究入口是 `docs/current/README.md`。历史金融输出
目录 `results/` 与 `checkpoints/` 已删除；其余下文涉及 V1/V2 的说明均是历史代码和冻结
证据的结构记录，不能作为新状态感知持久性残差 Mamba 的实现或实验授权。

---

# Historical Financial Repository Structure

| Location | Ownership |
| --- | --- |
| `data/financial/` | Local raw sources, v1 panels, v2 target files, and data manifests. Ignored by Git. |
| `model/` | Proposed Regime-Gated Mamba and comparison model implementations. |
| `layers/` | Shared Mamba, embedding, normalization, decomposition, and attention layers. |
| `data_provider/` | Dataset classes and DataLoader construction. |
| `experiments/financial/` | Active S-only orchestration, learned runner, deterministic references, and evaluation helpers. |
| `utils/financial/` | Data, release, evidence, report, profile, figure, and archive utilities. |
| `configs/` | Three active configurations: provider sources, v1 release, and v2 release. |
| `reproducibility/financial_s_only_v1/` | Tracked, checksum-covered v1 evidence contract. |
| `reproducibility/financial_s_only_v2/` | Tracked, checksum-covered v2 evidence contract. |
| `docs/` | Technical reference, figures, and manuscript-supporting evidence map. |
| `docs/analysis/financial_s_only_v2/` | Derived, hash-manifested V2 analysis tables; regenerated from the compact release. |
| `backup/data/` | 保留的公开候选数据；尚未纳入新研究协议。其他历史 `backup/` 内容已于 2026-10-02 删除。 |

Historical `results/` and `checkpoints/` roots were deleted after frozen-release
verification. A future authorized run may create ignored output directories, but it
must use a new versioned release and must not overwrite `financial_s_only_*`.

## Supported Commands

```text
python scripts/data.py {download,prepare,preflight,materialize-targets,release-setup}
python scripts/evaluate.py --release {v1,v2} --stage {setup,plan,deterministic,train,replay,replay-verify,profile,report,verify}
python scripts/reproduce.py --workflow financial-s-only --release {v1,v2} --stage ...
python scripts/analyze.py {figures,profile,report}
```

`run.py` is a low-level manual experiment interface, not the reproducible release
path. The intended public workflow is `scripts/reproduce.py` with the single
`financial-s-only` workflow. There are no user-facing subdirectories inside
`scripts/`; old mixed S/MS and publication-specific entry points were removed
rather than left as competing interfaces.
