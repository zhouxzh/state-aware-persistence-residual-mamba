# PMS-Mamba for Nonstationary Financial Forecasting

Reference implementation for the paper *A Decomposition-Aware Multi-Scale Mamba Model for Nonstationary Financial Forecasting*.

PMS-Mamba applies reversible window normalization, additive moving-average decomposition, multi-scale temporal pooling, and bidirectional Mamba encoders over ordered temporal patches.  The implementation is designed for nonstationary daily financial level series.

## Scope and Status

The current study uses four financial panels: foreign exchange, U.S. Treasury yields, cross-asset prices, and cryptoassets.  Each panel has a target-only task and a multivariate task.

The data-preparation and validation-selection stages have completed under the versioned financial evaluation protocol.  The protected final 2023--2026 test period has not been analyzed in this repository version.  Consequently, this repository does not claim that PMS-Mamba outperforms any comparator.

Historical GLD, Exchange, Weather, ETT, Electricity, and Traffic artifacts are not part of the current study and are deliberately excluded from the working tree.

## Models

- `S_Mamba`: inverted variable-token baseline.
- `NS_Mamba-D`: additive decomposition variant.
- `MS_Mamba-MD`: multi-scale decomposition variant.
- `PMS_Mamba-PD`: the proposed temporal-patch, decomposition-aware, multi-scale model.

The principal implementation is in `model/PMS_Mamba.py`; reusable normalization and decomposition layers are in `layers/`.

## Environment

The project is developed in the `mamba` Conda environment.  Install the Python dependencies inside that environment:

```bash
conda run --no-capture-output -n mamba python -m pip install -r requirements.txt
```

PMS-Mamba experiments require a CUDA-capable PyTorch installation and `mamba-ssm`.  Check the local runtime before training:

```bash
conda run --no-capture-output -n mamba python scripts/financial/preflight.py
```

## Financial Data Workflow

Downloaded source data and derived panels are local, ignored files under `data/financial/`.  Their availability and redistribution conditions remain subject to the original data providers.

To retrieve and prepare a fresh permitted local copy, run:

```bash
conda run --no-capture-output -n mamba python scripts/financial/download_financial_data.py --proxy-first
conda run --no-capture-output -n mamba python scripts/financial/prepare_financial_data.py
conda run --no-capture-output -n mamba python -m unittest tests.test_financial_pipeline -v
```

The downloader can use a locally running Clash proxy at `http://127.0.0.1:7890` when direct access fails.  Do not use `--refresh` to overwrite a frozen dataset snapshot without creating and documenting a new protocol version.

## Evaluation Workflow

Run a small GPU validation smoke test over the financial tasks:

```bash
conda run --no-capture-output -n mamba python scripts/financial/run_financial_benchmark.py --stage smoke
```

Re-audit the frozen validation-selection records without opening final targets:

```bash
conda run --no-capture-output -n mamba python scripts/financial/run_financial_benchmark.py --stage selection
```

The final evaluation has an explicit `--unlock-test` guard.  It must only be run after the authors approve opening the final period:

```bash
conda run --no-capture-output -n mamba python scripts/financial/run_financial_benchmark.py --stage final --unlock-test
```

`docs/financial_benchmark_runbook.md` records the full recovery, analysis, and manuscript-generation sequence.

## Repository Layout

```text
model/                 PMS-Mamba and comparison model definitions
layers/                normalization, decomposition, and encoder layers
scripts/financial/     data, protocol, training, and analysis entry points
configs/               versioned financial evaluation configuration
tests/                 financial data and protocol checks
docs/                  evaluation and data-management notes
```

The manuscript source of record is maintained in a separate repository.  Generated datasets, checkpoints, intermediate predictions, TensorBoard traces, and local backups are ignored by Git.  Keep them outside commits and regenerate them from the recorded configuration when needed.

## Reproducibility Boundary

The repository contains code and configuration, not redistributed market-data archives or trained checkpoints.  Any release of data, final metrics, or manuscript tables must use the completed protocol records and respect each source provider's terms.
