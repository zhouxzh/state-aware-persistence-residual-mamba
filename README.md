# Regime-Gated Mamba for Nonstationary Forecasting

This repository is the reviewer-facing reference implementation for Regime-Gated Mamba, a state-space forecaster for nonstationary time series.

The completed evidence uses daily financial panels as reference data: foreign exchange, Treasury yields, cross-asset prices, and cryptoassets.

Regime-Gated Mamba combines reversible normalization, moving-average decomposition, temporal patch encoding, bidirectional Mamba encoders, and a regime-gated change head.

The selected recipe emphasizes short-horizon path-RMSSE accuracy and low-latency inference. It is not presented as the leading model at every long horizon.

The financial results do not support trading or economic claims.

Start with the [technical documentation](docs/README.md), then read the [data reference](docs/data_reference.md), [model reference](docs/model_reference.md), [evaluation record](docs/evaluation_record.md), and [reproducibility workflow](docs/reproducibility.md).

## Canonical models

| Identifier | Reader-facing name | Role |
| --- | --- | --- |
| `RegimeGatedMamba` | Regime-Gated Mamba | Selected proposed model. |
| `MultiScalePatchMamba` | Multi-Scale Patch Mamba | Architectural ablation. |
| `InvertedMamba` | Inverted Mamba | Mamba baseline. |
| `DecompositionMamba` | Decomposition Mamba | Mamba baseline. |
| `MultiScaleDecompositionMamba` | Multi-Scale Decomposition Mamba | Mamba baseline. |
| `PatchTST`, `TimesNet`, `DLinear`, `NLinear`, `iTransformer` | Unchanged | Audited external baselines. |

Historical result rows retain `source_model_id`, but active code, configuration, and documentation use the canonical identifiers above.

The complete mapping is in [`model_identity_map.json`](reproducibility/financial_reference_evaluation_v1/model_identity_map.json).

## Setup

```bash
conda env create -f environment.yml
conda run --no-capture-output -n sci-agent python -m pip install -r requirements.txt
conda run --no-capture-output -n sci-agent python scripts/data.py preflight
```

The environment requires CUDA-compatible PyTorch and `mamba-ssm` for Mamba models.

## Reproduce the supplied record

Raw financial data, checkpoints, predictions, and TensorBoard logs remain local and are excluded from Git. Follow source-provider terms before downloading data.

```bash
conda run --no-capture-output -n sci-agent python scripts/data.py download
conda run --no-capture-output -n sci-agent python scripts/data.py prepare
conda run --no-capture-output -n sci-agent python scripts/analyze.py audit
conda run --no-capture-output -n sci-agent python scripts/evaluate.py --stage dry-run
```

The complete candidate comparison is retrospective because the baseline suite had already opened the 2023-2026 target period.

```bash
conda run --no-capture-output -n sci-agent python scripts/evaluate.py --stage final --unlock-retrospective-test
conda run --no-capture-output -n sci-agent python scripts/analyze.py metrics --require-complete
conda run --no-capture-output -n sci-agent python scripts/analyze.py normalize
conda run --no-capture-output -n sci-agent python scripts/analyze.py profile
conda run --no-capture-output -n sci-agent python scripts/analyze.py report
conda run --no-capture-output -n sci-agent pytest -q
```

## Repository layout

```text
data/                  Local financial reference data and manifests
model/                 Forecasting model architectures and baselines
layers/                Neural network layers and normalization components
data_provider/         Dataset and DataLoader implementations
experiments/           Training, evaluation, and checkpoint-replay workflows
utils/                 Shared data, metrics, audit, and reporting utilities
scripts/               Four user-facing commands: data, evaluate, analyze, reproduce
configs/               Versioned evaluation configurations
reproducibility/       Frozen metrics, manifests, selection snapshots, and provenance
docs/                  Technical reference and repository structure guide
tests/                 Release-level validation
```

See [docs/repository_structure.md](docs/repository_structure.md) for the ownership
and command map.

No manuscript source is included in this repository. It is restricted to software, documentation, configurations, and reproducibility artifacts.
