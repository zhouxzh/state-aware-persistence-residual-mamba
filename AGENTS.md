# Repository Agent Rules

## Scope

- The active study is SAPR-Mamba V2 under `docs/current/`, `configs/sapr_mamba_v2/`,
  `data/sapr_mamba_v2/`, `results/sapr_mamba_v2/`, and
  `reproducibility/sapr_mamba_v2/`.
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
- Enable Clash only for a required GitHub push. Verify both functions exist,
  install an `EXIT` cleanup handler before the push, and turn Clash off even
  when the push fails:

```bash
export CLASHCTL_HOME=/home/zhong/clashctl
source "$CLASHCTL_HOME/scripts/cmd/clashctl.sh"
type clashon >/dev/null && type clashoff >/dev/null
clashon
trap 'clashoff' EXIT
git push origin main
```

- Do not fetch, pull, clone, or perform unrelated network work while Clash is
  enabled. Let the cleanup handler call `clashoff` immediately after the push.
- Before committing, inspect `git status`, stage only intended source,
  configuration, documentation, tests, and compact reproducibility evidence,
  then run the relevant test suite. Never force-push or rewrite history.
