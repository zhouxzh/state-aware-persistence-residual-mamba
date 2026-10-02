# 历史金融发布物的可复现性边界

更新日期：2026-10-02。三套 `financial_s_only_*` 紧凑发布物和 SHA-256 清单仍可直接
核验；原始 `results/`、`checkpoints/`、回放树、TensorBoard 和日志已删除。因此下文所有
训练、回放和再生成命令都是**历史工作流记录**，不是当前新模型的运行授权，也不能在
不重新建立新版本化输出目录的情况下恢复旧运行。

当前状态感知持久性残差 Mamba 的训练前要求见 [current/README.md](current/README.md)。
没有明确用户授权，不应启动、停止、重跑或修改任何远端实验。

可优先执行只读完整性检查：

```bash
conda run --no-capture-output -n sci-agent python -m pytest -q
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v2 --stage verify
```

校验结果只能解释为历史金融发布物的完整性，不能形成新模型性能证据。

---

# Historical Financial Reproducibility Workflow

## Environments

Use the existing `mamba` Conda environment for CUDA-dependent training, checkpoint
replay, and report generation. It contains the working `mamba-ssm` installation on
this machine. Use `sci-agent` for tests and static figure rendering.

```bash
conda run --no-capture-output -n mamba python scripts/data.py preflight
conda run --no-capture-output -n sci-agent python -m pytest -q
```

A reviewer needs a CUDA-compatible PyTorch build and `mamba-ssm` to rerun learned
models. The data contracts, deterministic references, compact metrics, checksums,
and documentation can be inspected without retraining neural models.

## Data and Release Setup

Raw provider data is local and ignored. Obtain it under the applicable provider
terms, then build the two S-only data views and release contracts:

```bash
conda run --no-capture-output -n mamba python scripts/data.py download
conda run --no-capture-output -n mamba python scripts/data.py prepare
conda run --no-capture-output -n mamba python scripts/data.py materialize-targets
conda run --no-capture-output -n mamba python scripts/data.py release-setup --release v1
conda run --no-capture-output -n mamba python scripts/data.py release-setup --release v2
```

`prepare` creates four v1 wide-source panels but emits only active `S` task entries.
`materialize-targets` creates a separate date-plus-target CSV for each v2 series.
`release-setup` validates data hashes and copies frozen parameter selections into
the release contract. It rejects mutation after a checksum manifest exists; create
a new versioned release instead.

For the bounded V2 supplemental gate study, create the local-only release from the
already verified V2 inputs. This copies and rechecks the V2 files and selections;
it does not rematerialize or modify shared data:

```bash
conda run --no-capture-output -n mamba python scripts/data.py release-setup --release v2-supplement
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v2-supplement --stage plan
```

## Deterministic References and Learned Matrix

The deterministic stage is resumable. It writes compact metrics to the tracked
release and retains forecast arrays in ignored local `results/` directories.
The following uses v1 as an example; replace `v1` with `v2` to run the
independent-target expansion. The two releases are separate evidence records and
must not be pooled.

```bash
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v1 --stage deterministic
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v1 --stage plan
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v1 --stage train \
  --unlock-retrospective-test
```

The `train` command is locked because it creates retrospective test-result
artifacts. Selectors such as `--tasks`, `--models`, `--horizons`, `--seeds`, and
`--max-runs` support bounded resume work, but partial output must never be used for
final model claims.

Each completed learned unit retains a checkpoint, prediction, truth, origin-date,
forecast-date, metric, and metadata artifact. The campaign summary stores SHA-256
records for those files.

## Replay and Verification

```bash
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v1 --stage replay
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v1 --stage replay-verify
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v1 --stage profile
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v1 --stage report
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v1 --stage verify
conda run --no-capture-output -n sci-agent python scripts/analyze.py figures \
  --release financial_s_only_v1 --output-dir docs/figures
conda run --no-capture-output -n sci-agent python scripts/analyze.py analysis \
  --release financial_s_only_v2 --output-dir docs/analysis/financial_s_only_v2
```

Historically, `replay` loaded retained checkpoints and wrote a new ignored replay tree without
training. For future replays it checks each regenerated prediction and truth array
against the retained bundle within an absolute tolerance of `1e-6`, and requires
exact origin and forecast dates. `replay-verify` performs the same comparison over
an existing replay tree without loading a model or requiring CUDA; it writes local
`replay_validation.json`.

When a replay validation is already complete but its convenience index is partial,
rebuild that index from the equality-validation record without loading models:

```bash
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v2 --stage replay-summary
```

V1 completed this replay audit for all 1,320 learned bundles. V2 completed
the equivalent reload-and-array-equality replay audit for all 5,940 learned
bundles on 2026-08-21; `replay-verify --release v2` reports `verified` with no
problems and zero maximum prediction/truth differences. The validation record
is intentionally local because it contains bulk replay paths. Use the same
`replay` and `replay-verify` stages with `--release v2` to regenerate it.

`profile` is a fixed CUDA forward-pass microbenchmark. `report` is blocked until
the complete learned matrix validates, then writes metrics, scale-normalized paired
contrasts, block-bootstrap results, runtime metadata, claim map, and checksums.
After finalization, `verify` validates rather than rewrites the checksum-covered
status record.

`analysis` reads the verified V2 release tables and writes target-level, horizon,
family, pairwise, normalized-metric, and seed-stability summaries under
`docs/analysis/financial_s_only_v2/`. It does not retrain models or alter the
checksum-covered release.

The V2 supplement was deliberately narrower: 18 targets x 2 models x 5 seeds x
horizons 60/120/252 = 540 learned cells. It reuses frozen V2 selections, omits
deterministic and baseline reruns, and is marked as a retrospective supplement.
After training, replay, and report generation, render only the paired gate analysis:

```bash
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v2-supplement --stage train --unlock-retrospective-test
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v2-supplement --stage replay
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v2-supplement --stage replay-verify
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v2-supplement --stage report
conda run --no-capture-output -n sci-agent python scripts/analyze.py v2-supplement
```

V2-supplement results and checkpoints were ignored local artifacts and have now been
deleted from ace2. The tracked V2 release remains the historical authority for comparisons with
PatchTST, TimesNet, iTransformer, and deterministic references.

## Public Entry Points

The four public scripts are intentionally flat:

```text
scripts/data.py       data preparation and release setup
scripts/evaluate.py   compatibility entry point for the S-only workflow
scripts/reproduce.py  S-only train, replay, report, and verification stages
scripts/analyze.py    derived analysis, compact report, profile, and figure rendering
```

`run.py` remains a low-level manual experiment interface. It is not the
reproducible release path. No user-facing subdirectory exists within `scripts/`.

## Archived Historical Material

Inactive mixed S/MS campaign roots were stored in the ignored
`backup/legacy_s_ms_20260812/` directory. They were removed on 2026-10-02 after the
financial releases had been verified. The active workflow never read them.
