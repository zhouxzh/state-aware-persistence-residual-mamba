# Reproducibility Workflow

## Environment

Use the existing `mamba` Conda environment for this repository's CUDA-dependent
model code. It has a working `mamba-ssm` installation on this machine. `sci-agent`
is not the runtime environment for the active Mamba workflow.

```bash
conda run --no-capture-output -n mamba python scripts/data.py preflight
conda run --no-capture-output -n sci-agent python -m pytest -q
```

The preflight records Python, package, CUDA, GPU, disk, and Git state. The current
`mamba` environment is the validated training/profile environment; `sci-agent`
contains the test runner. A reviewer needs a CUDA-compatible PyTorch build and
`mamba-ssm` to run learned models; data and deterministic references can be checked
without retraining neural models.

## Data and Release Setup

Raw provider data is local and ignored. After obtaining sources under their terms,
build the two data views and release contracts:

```bash
conda run --no-capture-output -n mamba python scripts/data.py download
conda run --no-capture-output -n mamba python scripts/data.py prepare
conda run --no-capture-output -n mamba python scripts/data.py materialize-targets
conda run --no-capture-output -n mamba python scripts/data.py release-setup --release v1
conda run --no-capture-output -n mamba python scripts/data.py release-setup --release v2
```

`prepare` creates the four v1 wide-source panels but emits only active `S` task
entries. `materialize-targets` creates one independent target CSV for every v2 target.
`release-setup` validates data hashes and release-local frozen parameter selections.

## Deterministic References

The deterministic stage is resumable. It preserves compact CSV metrics in the tracked
release and keeps prediction arrays in local ignored `results/` directories.

```bash
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v1 --stage deterministic
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v2 --stage deterministic
```

## Learned Matrix

Inspect the exact planned scope first:

```bash
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v1 --stage plan
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v2 --stage plan
```

The training command is locked because it writes new retrospective test-result
artifacts. The active configuration does not silently reuse historical mixed S/MS
outputs.

```bash
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v1 --stage train \
  --unlock-retrospective-test
```

Use `--release v2` for the independent-target expansion. Optional selectors such as
`--tasks`, `--models`, `--horizons`, `--seeds`, and `--max-runs` support resumable,
bounded execution; do not use partial output for final claims.

Each completed learned unit retains its checkpoint and prediction, truth, origin-date,
forecast-date, metric, and metadata artifacts. The campaign summary and manifests
verify them before report generation.

## Replay, Profile, Report, Verify

```bash
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v1 --stage replay
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v1 --stage profile
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v2 --stage profile
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v1 --stage report
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v1 --stage verify
```

`replay` reads retained checkpoints and writes a new local replay tree without
training. `profile` performs a fixed S-only CUDA forward-pass microbenchmark.
`report` is intentionally blocked until the full learned matrix validates. `verify`
always writes a truthful release status and checks the deterministic matrix, required
release files, and checksums when a completed report exists.

Run `release-setup` only before report construction. A finalized release carries a
checksum manifest and is intentionally immutable; create a new versioned release
rather than rewriting its protocol, data manifest, or selection snapshot.

The four public script entry points are intentionally flat:

```text
scripts/data.py       data preparation and release setup
scripts/evaluate.py   compatibility entry point for the S-only workflow
scripts/reproduce.py  S-only training, replay, profile, report, and verification
scripts/analyze.py    direct profile or report invocation
```

## Archived Historical Material

The inactive mixed S/MS local campaigns were moved intact to
`backup/legacy_s_ms_20260812/`. That directory is ignored by Git and is not read by
the active workflow. Its manifest records inventory hashes and restoration paths.
