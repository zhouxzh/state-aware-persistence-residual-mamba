# Regime-Gated Mamba for Financial Time-Series Forecasting

This repository contains the software and evidence contracts for a target-only,
univariate financial forecasting study. The proposed model is **Regime-Gated
Mamba**. It predicts a linear change from the last observed level and uses a
small selective state-space gate to attenuate or retain that change across the
forecast horizon.

The public workflow is deliberately S-only: every active task supplies one target
history and forecasts that same target. The repository does not contain manuscript
source, raw provider data, trained weights, forecast arrays, TensorBoard logs, or
trading code.

## Evidence Status

The 2023-01-01 through 2026-06-30 evaluation interval has already been inspected.
All active results are therefore **retrospective**, not untouched prospective-test
evidence.

Two release contracts are tracked:

| Release | Scope | Learned matrix | Deterministic references | Current state |
| --- | --- | ---: | ---: | --- |
| `financial_s_only_v1` | Four original target-only panels | 1,320 horizon rows planned | 72 / 72 complete | Learned matrix not run |
| `financial_s_only_v2` | Eighteen independently materialized targets | 5,940 horizon rows planned | 324 / 324 complete | Learned matrix not run |

The v1 CUDA microbenchmark is complete, but it is a fixed forward-pass workload
and is not an accuracy result. No learned-model accuracy ranking or superiority
claim is supported until the matching learned matrix is complete and verified.

## Active Workflow

Use the `mamba` Conda environment for training and profiling. It contains the
working `mamba-ssm` installation for this machine.

```bash
conda run --no-capture-output -n mamba python scripts/data.py release-setup --release v1
conda run --no-capture-output -n mamba python scripts/reproduce.py --workflow financial-s-only --release v1 --stage plan
conda run --no-capture-output -n mamba python scripts/reproduce.py --workflow financial-s-only --release v1 --stage deterministic
```

Training writes a retrospective test-result release and is deliberately locked:

```bash
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v1 --stage train \
  --unlock-retrospective-test
```

After the full learned matrix is complete, run `profile`, `report`, and `verify`.
The complete command sequence and acceptance criteria are in
[docs/reproducibility.md](docs/reproducibility.md).

## Repository Map

| Path | Role |
| --- | --- |
| `model/` | Regime-Gated Mamba and comparison architectures. |
| `configs/` | Active source-data and v1/v2 release configurations. |
| `data/financial/` | Local raw data, processed panels, and independent targets; ignored by Git. |
| `experiments/financial/` | S-only deterministic, training, replay, and orchestration code. |
| `utils/financial/` | Release setup, data preparation, reporting, profiling, and archive utilities. |
| `reproducibility/financial_s_only_v1/` | Tracked v1 protocol, hashes, frozen parameters, and compact metrics. |
| `reproducibility/financial_s_only_v2/` | Tracked v2 protocol, hashes, frozen parameters, and compact metrics. |
| `docs/` | Technical documentation and evidence map. |

Read [docs/README.md](docs/README.md) first. The active architecture is shown in
[docs/figures/regime_gated_mamba_s_only.svg](docs/figures/regime_gated_mamba_s_only.svg).

## License and Data

The MIT license covers original contributions in this repository. Inherited source
notices are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Source-data
terms apply independently; provider data and derived levels remain local unless
their redistribution rights have been checked.
