# Repository Agent Rules

## Scope

- The active study is the independent SAPR-Mamba V3 confirmation protocol,
  including the additive V3.1 public-source amendment, under
  `docs/current/`, `configs/sapr_mamba_v3/`, `data/sapr_mamba_v3/`,
  `results/sapr_mamba_v3/`, and `reproducibility/sapr_mamba_v3/`.
- V2 is immutable development evidence. Never pool V2 estimates with V3
  confirmation estimates, and never change V2 artifacts to make V3 checks pass.
- Historical financial releases and all `sapr_mamba_v1` artifacts are audit
  records. Never select models, thresholds, sources, hyperparameters, or
  reporting subsets from them, and never overwrite them.
- Do not read or copy files from
  `~/Documents/Self-Supervised-Contrastive-Forecsating`.
- Preserve failed, negative, interrupted, and superseded-study artifacts. Label
  their protocol/version boundary rather than deleting or mixing them into V2.

## Python Environments

- `sci-agent` is the only Conda environment for new repository Python packages,
  experiments, validation, and scientific-agent-skill dependencies.
- Run new work with `conda run --no-capture-output -n sci-agent ...`.
- Do not install, upgrade, remove, or otherwise mutate packages in `mamba`.
  It is a legacy runtime that may host an already-running job. Never stop or
  restart an existing job without explicit user direction.
- Install only a skill's workflow-specific optional packages when the workflow
  is invoked. Install them in `sci-agent` unless their documented requirements
  are incompatible, in which case create a separately named environment and
  document it before use.

## Data And Results

- Raw/processed data, checkpoints, prediction arrays, TensorBoard files, and
  transient run output belong in ignored `data/` and `results/` paths.
- Before starting a batch, record preflight state. Every task must retain its
  atomic manifest, code/config/data hashes, output hashes, and failures.
- Do not report a numeric conclusion from logs. Recompute it from retained
  artifacts, verify checksums, and preserve the complete result matrix.

## Git, Skills, And Network

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

## Unattended V3 Continuation

- The resumable controller is `scripts/sapr_mamba_v3_pipeline.py`; it retries
  failures and records limitations without emitting a blocked state.
- When a long `real` run is active, keep it untouched and run
  `scripts/sapr_mamba_v3_autocontinue.py` in `sci-agent`. The supervisor waits
  for the exact real controller, then runs `real_extended`, `analysis`,
  `verify`, `release`, and the test suite in order. It writes half-hour
  progress snapshots to `docs/current/zhong3_runlog/sapr_mamba_v3/` and state
  to `results/sapr_mamba_v3/autocontinue_state.json`.
- A stage reported as `complete_with_limitations` is not a reason to stop the
  supervisor. Preserve its evidence, apply the recorded remediation, and
  continue all independent downstream checks.
- For the V3.1 external extension, use
  `scripts/sapr_mamba_v3_completion_guard.py` after the real-run. It waits for
  the frozen 950-task matrix with zero failed/invalid manifests, then runs
  external-aware analysis, manuscript generation, independent recomputation,
  compact release creation/verification, and the full test suite.
