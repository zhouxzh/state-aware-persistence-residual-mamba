# Regime-Gated Mamba for Financial Time-Series Forecasting

This repository contains the code and evidence contracts for a target-only,
univariate financial forecasting study. The proposed model, **Regime-Gated
Mamba**, forecasts a normalized change from the latest level and uses a small
selective state-space gate to modulate that change across the forecast horizon.

All active tasks are target-only (`S`): a model sees one target history and
forecasts that same target. No active `financial_*_ms` task, raw provider data,
trained weight, bulk forecast array, TensorBoard log, manuscript source, or
trading strategy is committed to Git.

## Evidence Status

The 2023-01-01 through 2026-06-30 evaluation interval has already been
inspected. All results are therefore **retrospective**, not prospective or
untouched-test evidence.

| Release | Scope | Learned matrix | Deterministic references | Current state |
| --- | --- | ---: | ---: | --- |
| `financial_s_only_v1` | Four original target-only panels | 1,320 / 1,320 horizon rows | 72 / 72 rows | Verified, checksum-covered |
| `financial_s_only_v2` | Eighteen independently materialized targets | 5,940 rows planned | 324 / 324 rows | Learned matrix not started |

The verified v1 result is deliberately mixed rather than selectively positive:
Regime-Gated Mamba is not the overall path-RMSSE leader, but it ranks first in
the two longest-horizon Treasury-yield cells and has lower measured campaign
runtime than PatchTST and TimesNet on this release. See
[the detailed evaluation record](docs/evaluation_record.md) before using any
number in a manuscript.

## Active Workflow

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
```

Training is intentionally locked because it writes a new retrospective
test-result release. The full command sequence, release boundaries, and
acceptance checks are in [docs/reproducibility.md](docs/reproducibility.md).

## Repository Map

| Path | Role |
| --- | --- |
| `model/` | Regime-Gated Mamba and comparison architectures. |
| `configs/` | Active source-data and v1/v2 S-only release configurations. |
| `data/financial/` | Local raw data, processed panels, and independent targets; ignored by Git. |
| `experiments/financial/` | S-only deterministic, training, replay, and orchestration code. |
| `utils/financial/` | Release setup, data preparation, reporting, profiling, figures, and archive utilities. |
| `reproducibility/financial_s_only_v1/` | Tracked v1 protocol, hashes, frozen parameters, and compact verified metrics. |
| `reproducibility/financial_s_only_v2/` | Tracked v2 protocol, hashes, frozen parameters, and deterministic metrics. |
| `docs/` | Technical documentation, figures, and evidence map. |

Read [docs/README.md](docs/README.md) first. The active architecture is shown in
[docs/figures/regime_gated_mamba_s_only.svg](docs/figures/regime_gated_mamba_s_only.svg).

## License and Data

The MIT license covers original contributions in this repository. Inherited source
notices are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Provider
terms apply independently; source data and derived levels remain local unless their
redistribution rights have been checked.
