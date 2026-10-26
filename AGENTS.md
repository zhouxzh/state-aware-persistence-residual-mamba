# Repository Agent Rules

## Repository role

- This clone is the executable SAPR-Mamba code repository on zhong3:
  `~/Documents/state-aware-persistence-residual-mamba`.
- It corresponds to the SAPR paper workspace
  `state-aware-persistence-residual-mamba/` in the paper/evidence repository
  `nonstationary-mamba`. It is not the PMS or Regime-Gated paper.
- The paper/evidence workspace is a separate repository. Do not copy this
  runnable tree into the paper repository, and do not treat this clone as the
  manuscript workspace.
- Closed-protocol raw arrays (`predictions.npz`, checkpoints) for superseded
  versions must not be kept here after compact evidence is in the paper repo.
- Current HEAD at last paper-repo mapping: `82a74c2`. The working tree already
  contains pre-existing uncommitted research/evidence files. Do not commit,
  push, reset, or clean that state without explicit user instruction.

## Active protocol

- The active exploratory protocol is **OCRA-v1.2.r1** (Observability-Certified
  Residual Admission): a fresh, disjoint-seed recap of the `canonical_v2`
  nine-mechanism generator. It is not a V3/V3.1 real-source confirmation and
  not `sim_v5`.
- Its plan is `docs/OCRA_V1_2_PROTOCOL.md`; prior OCRA protocol directories are
  immutable evidence and must not be reused or pooled.
- Run products (checkpoints, forecasts, metrics, protocol hashes) live under
  ignored `results/ocra_v1_2_r1/` in this repository. Do not commit those files.
- Do not start OCRA backbone training until `protocol.json` exists and the
  canonical_v2 seed / `series_id` blacklist check passes. Test data must not be
  loaded before E1 and E2 pass.
- Do not revive the learned sigmoid state gate as the method. It remains a
  frozen negative control. Do not pursue generic residual admission; that
  direction is covered by RAEGL.

## Frozen evidence. Do not pool

These namespaces are closed estimands. Never average them, never retune one
with another, and never alter locks or artifacts after their decision is known:

- V2 development evidence
- V3 / V3.1 real/public-source confirmation
- `canonical_v2` mechanism simulation (the current SAPR manuscript estimand)
- `sim_v1`--`sim_v5`
- BOCPD experiment series
- historical financial releases and all `sapr_mamba_v1` artifacts

`canonical_v2` test `series_id` values and training seeds
`{20262201, 20262202, 20262203, 20262204, 20262205}` have been inspected. OCRA-v1
must use disjoint generator seeds, `series_id` prefix `ocra_v1_`, and training
seeds `{20261021, 20261022, 20261023, 20261024, 20261025}`.

V4 remains an immutable pre-training coverage-gate failure with no trained-model
evidence.

Do not read or copy files from
`~/Documents/Self-Supervised-Contrastive-Forecsating`.

Preserve failed, negative, interrupted, coverage-gate-failed, and superseded
artifacts with their protocol/version labels.

## Python environments

- `sci-agent` is the only Conda environment for new repository Python packages,
  experiments, validation, and scientific-agent-skill dependencies.
- Run new work with `conda run --no-capture-output -n sci-agent ...`.
- Do not install, upgrade, remove, or otherwise mutate packages in `mamba`.
  It is a legacy runtime that may host an already-running job. Never stop or
  restart an existing job without explicit user direction.
- Create a separate named environment for OCRA only if `sci-agent` cannot
  satisfy the frozen protocol; document it before use.

## Data and results

- Raw/processed data, checkpoints, prediction arrays, TensorBoard files, and
  transient run output belong in ignored `data/` and `results/` paths.
  OCRA artifacts use `results/ocra_v1_2_r1/`.
- Before starting a batch, record preflight state. Every task must retain its
  atomic manifest, code/config/data hashes, output hashes, and failures.
- Do not report a numeric conclusion from logs. Recompute it from retained
  artifacts, verify checksums, and preserve the complete result matrix.
- Compact OCRA tables, checksums, paper-used figures, and claim verdicts may
  later be copied to the paper repository. Full arrays stay on this server.

## Git, skills, and network

- Use a GitHub web proxy such as `gh-proxy.com` for public GitHub downloads,
  including third-party skill installation. Do not enable Clash for those
  downloads.
- `clashon` and `clashoff` are shell functions defined by
  `/home/zhong/clashctl/scripts/cmd/clashctl.sh`. In a non-interactive shell,
  set `CLASHCTL_HOME=/home/zhong/clashctl` and source that file directly;
  `~/.bashrc` may return before loading the functions.
- Every Git push must use the following Clash lifecycle. Enable Clash only for
  the push itself; verify both functions exist, install an `EXIT` cleanup
  handler before the push, and turn Clash off immediately after the push,
  including when authentication, TLS, or transfer fails:

```bash
export CLASHCTL_HOME=/home/zhong/clashctl
source "$CLASHCTL_HOME/scripts/cmd/clashctl.sh"
type clashon >/dev/null && type clashoff >/dev/null
clashon
trap 'clashoff' EXIT
git push origin main
```

- Do not fetch, pull, clone, or perform unrelated network work while Clash is
  enabled. Do not omit the cleanup handler or leave Clash enabled for any
  follow-up command; let it call `clashoff` immediately after every push.
- Before committing, inspect `git status`, stage only intended source,
  configuration, documentation, tests, and compact reproducibility evidence,
  then run the relevant test suite. Never force-push or rewrite history.
- Do not push this repository without explicit user instruction.

## Historical supervisors. Not the default

- `scripts/sapr_mamba_v3_pipeline.py`, `scripts/sapr_mamba_v3_autocontinue.py`,
  `scripts/sapr_mamba_v3_completion_guard.py`, and the `sim_v5` guard are frozen
  continuation tools for those namespaces. Do not launch them unless the user
  explicitly asks to resume V3/V3.1 or `sim_v5`.
- Default unattended work follows `docs/OCRA_V1_2_PROTOCOL.md`, with artifacts
  under `results/ocra_v1_2_r1/`: protocol seal, blacklist check, single-backbone
  preflight, then 20 backbone runs. Do not load the OCRA test split before E1
  and E2 pass.
