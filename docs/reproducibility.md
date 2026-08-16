# Reproducibility Workflow

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

## Deterministic References and Learned Matrix

The deterministic stage is resumable. It writes compact metrics to the tracked
release and retains forecast arrays in ignored local `results/` directories.

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
```

`replay` loads retained checkpoints and writes a new ignored replay tree without
training. For future replays it checks each regenerated prediction and truth array
against the retained bundle within an absolute tolerance of `1e-6`, and requires
exact origin and forecast dates. `replay-verify` performs the same comparison over
an existing replay tree without loading a model or requiring CUDA; it writes local
`replay_validation.json`.

`profile` is a fixed CUDA forward-pass microbenchmark. `report` is blocked until
the complete learned matrix validates, then writes metrics, scale-normalized paired
contrasts, block-bootstrap results, runtime metadata, claim map, and checksums.
After finalization, `verify` validates rather than rewrites the checksum-covered
status record.

## Public Entry Points

The four public scripts are intentionally flat:

```text
scripts/data.py       data preparation and release setup
scripts/evaluate.py   compatibility entry point for the S-only workflow
scripts/reproduce.py  S-only train, replay, report, and verification stages
scripts/analyze.py    compact report, profile, and figure rendering
```

`run.py` remains a low-level manual experiment interface. It is not the
reproducible release path. No user-facing subdirectory exists within `scripts/`.

## Archived Historical Material

Inactive mixed S/MS campaign roots are recoverably stored in the ignored
`backup/legacy_s_ms_20260812/` directory. The active workflow never reads it. Its
manifest records inventory hashes and restoration targets.
