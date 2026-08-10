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
conda run --no-capture-output -n sci-agent python scripts/financial/preflight.py
```

The environment requires CUDA-compatible PyTorch and `mamba-ssm` for Mamba models.

## Reproduce the supplied record

Raw financial data, checkpoints, predictions, and TensorBoard logs remain local and are excluded from Git. Follow source-provider terms before downloading data.

```bash
conda run --no-capture-output -n sci-agent python scripts/financial/download_financial_data.py
conda run --no-capture-output -n sci-agent python scripts/financial/prepare_financial_data.py
conda run --no-capture-output -n sci-agent python scripts/publication/audit_legacy_baselines.py
conda run --no-capture-output -n sci-agent python scripts/publication/run_financial_reference_evaluation.py --stage dry-run
```

The complete candidate comparison is retrospective because the baseline suite had already opened the 2023-2026 target period.

```bash
conda run --no-capture-output -n sci-agent python scripts/publication/run_financial_reference_evaluation.py --stage final --unlock-retrospective-test
conda run --no-capture-output -n sci-agent python scripts/publication/analyze_publication_results.py --require-complete
conda run --no-capture-output -n sci-agent python scripts/publication/normalize_release_identifiers.py
conda run --no-capture-output -n sci-agent python scripts/publication/profile_final_models.py
conda run --no-capture-output -n sci-agent python scripts/publication/build_final_evaluation_report.py
conda run --no-capture-output -n sci-agent pytest -q
```

## Repository layout

```text
model/                 Active models and canonical model wrappers
layers/                Normalization, decomposition, and encoder layers
scripts/financial/     Data acquisition, preparation, and preflight checks
scripts/evaluation/    Frozen task evaluator
scripts/publication/   Audit, comparison, normalization, analysis, and profiling
scripts/reproducibility/  Checkpoint retention, hashing, and forecast replay
configs/               Versioned evaluation configurations
reproducibility/       Metrics, manifests, selection snapshots, and provenance
docs/                  Technical data, model, evaluation, and reproduction record
tests/                 Release-level validation
```

No manuscript source is included in this repository. It is restricted to software, documentation, configurations, and reproducibility artifacts.
