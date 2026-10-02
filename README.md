# 状态感知持久性残差 Mamba：历史代码与新研究设计

本仓库保留 Regime-Gated Mamba 金融 S-only 项目的可执行历史代码和紧凑、校验和覆盖的
发布物，同时为新的状态感知持久性残差 Mamba 研究设计提供受控起点。它不是大规模实验
输出归档库。

当前研究检验：在预先定义的变化状态中，学习型残差修正能否在不损害稳定状态预测的
前提下优于持久性与无门控残差模型。候选比较是 M0 持久性、M1 线性残差、M2 无门控
Mamba 残差和 M3 状态门控 Mamba 残差。新设计尚未训练，不能报告性能或显著性结论。
在实现前必须冻结数据、合成变化机制、因果状态规则、划分、预算和报告协议。详见
[docs/current/README.md](docs/current/README.md)。

金融 V1/V2/Supplement 发布物只用于审计已完成的历史研究，不能作为新模型结果、图表或
结论来源。历史导航见
[docs/archive/financial_s_only/README.md](docs/archive/financial_s_only/README.md)。

---

# Historical Regime-Gated Mamba Financial Study

The material below documents the archived target-only,
univariate financial forecasting study. The proposed model, **Regime-Gated
Mamba**, forecasts a normalized change from the latest level and uses a small
selective state-space gate to modulate that change across the forecast horizon.

All historical tasks were target-only (`S`): a model sees one target history and
forecasts that same target. No active `financial_*_ms` task, raw provider data,
trained weight, bulk forecast array, TensorBoard log, manuscript source, or
trading strategy is committed to Git.

## Historical Evidence Status

The 2023-01-01 through 2026-06-30 evaluation interval has already been
inspected. All results are therefore **retrospective**, not prospective or
untouched-test evidence.

| Release | Scope | Learned matrix | Deterministic references | Current state |
| --- | --- | ---: | ---: | --- |
| `financial_s_only_v1` | Four original target-only panels | 1,320 / 1,320 horizon rows | 72 / 72 rows | Verified, checksum-covered |
| `financial_s_only_v2` | Eighteen independently materialized targets | 5,940 / 5,940 horizon rows | 324 / 324 rows | Verified, checksum-covered |

The verified results are deliberately mixed rather than selectively positive.
Across the original four-panel v1 release, Regime-Gated Mamba is not the overall
path-RMSSE leader but ranks first in the two longest-horizon DGS10 cells. Across
the 18-target v2 release, it has a mean path-RMSSE rank of 6.25 across 108
target-horizon cells, four rank-1 cells, and a corrected gate-ablation advantage
through horizon 20. In both releases it has lower measured campaign runtime than
PatchTST and TimesNet. Read the separate [v1 evaluation record](docs/evaluation_record.md)
and [v2 evaluation record](docs/v2_evaluation_record.md) before using any number
in a manuscript.

## Historical Workflow

Use the `mamba` Conda environment for CUDA-dependent training and replay. It
contains the working `mamba-ssm` installation for this machine. Use `sci-agent`
for repository tests and figure generation.

```bash
conda run --no-capture-output -n mamba python scripts/data.py release-setup --release v1
conda run --no-capture-output -n mamba python scripts/reproduce.py --workflow financial-s-only --release v1 --stage plan
conda run --no-capture-output -n mamba python scripts/reproduce.py --workflow financial-s-only --release v1 --stage deterministic
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v1 --stage train \
  --unlock-retrospective-test
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v1 --stage replay
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v1 --stage replay-verify
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v1 --stage report
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v1 --stage verify
conda run --no-capture-output -n sci-agent python scripts/analyze.py figures \
  --release financial_s_only_v1
conda run --no-capture-output -n sci-agent python scripts/analyze.py analysis \
  --release financial_s_only_v2 \
  --output-dir docs/analysis/financial_s_only_v2
```

Training is intentionally locked because it writes a new retrospective
test-result release. The full command sequence, release boundaries, and
acceptance checks are in [docs/reproducibility.md](docs/reproducibility.md).
Use `--release v2` for the completed 18-target expansion; it is a separate
evidence record and must not be pooled with v1.
The detailed historical analysis is in
[docs/v2_evaluation_record.md](docs/v2_evaluation_record.md), with reproducible
derived tables under `docs/analysis/financial_s_only_v2/`.

## Historical Repository Map

| Path | Role |
| --- | --- |
| `model/` | Regime-Gated Mamba and comparison architectures. |
| `configs/` | Historical source-data and v1/v2 S-only release configurations. |
| `data/financial/` | Local raw data, processed panels, and independent targets; ignored by Git. |
| `experiments/financial/` | S-only deterministic, training, replay, and orchestration code. |
| `utils/financial/` | Release setup, data preparation, reporting, profiling, figures, and archive utilities. |
| `reproducibility/financial_s_only_v1/` | Tracked v1 protocol, hashes, frozen parameters, and compact verified metrics. |
| `reproducibility/financial_s_only_v2/` | Tracked v2 protocol, hashes, frozen parameters, compact verified metrics, profile, and claim map. |
| `docs/` | Technical documentation, figures, and evidence map. |

Read [docs/README.md](docs/README.md) first. The historical architecture is shown in
[docs/figures/regime_gated_mamba_s_only.svg](docs/figures/regime_gated_mamba_s_only.svg).

## License and Data

The MIT license covers original contributions in this repository. Inherited source
notices are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Provider
terms apply independently; source data and derived levels remain local unless their
redistribution rights have been checked.
