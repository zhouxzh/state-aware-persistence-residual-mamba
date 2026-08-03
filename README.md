# PMS-Mamba for Forecasting Under Nonstationarity

Reference implementation and frozen experiment evidence for PMS-Mamba, a
decomposition-aware multi-scale state-space model for nonstationary time-series
forecasting.

PMS-Mamba applies reversible window normalization, additive moving-average
decomposition, multi-scale temporal pooling, and bidirectional Mamba encoders over
ordered temporal patches. The current experiments use daily financial panels as
reference datasets; the research question is broader forecasting under
nonstationarity.

## Scope and Status

The current study uses four financial reference panels: foreign exchange, U.S.
Treasury yields, cross-asset prices, and cryptoassets. Each panel has a target-only
task and a multivariate task.

V1 final evaluation and V2 validation-only optimization are complete. On the frozen
2023-01-01 through 2026-06-30 V1 test period, PMS-Mamba wins 0 of 48 primary
task-horizon path-RMSSE cells. It is most competitive on cross-asset tasks and middle
horizons; persistence and statistical references remain stronger overall. Neither V2
finalist met the prespecified 2% validation replacement threshold, so the existing F04
configuration was retained and the V1 test was not reopened.

Historical GLD, Exchange, Weather, ETT, Electricity, and Traffic artifacts are not part of the current study and are deliberately excluded from the working tree.

Start with the [documentation index](docs/README.md), then see the
[current result report](docs/current_results.md),
[next optimization plan](docs/next_optimization_plan.md), and
[paper writing direction](docs/paper_writing_direction.md).

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

## Reference Data Workflow

Downloaded source data and derived panels are local, ignored files under `data/financial/`.  Their availability and redistribution conditions remain subject to the original data providers.

To retrieve and prepare a fresh permitted local copy, run:

```bash
conda run --no-capture-output -n mamba python scripts/financial/download_financial_data.py --proxy-first
conda run --no-capture-output -n mamba python scripts/financial/prepare_financial_data.py
conda run --no-capture-output -n mamba python -m unittest tests.test_financial_pipeline -v
```

The downloader can use a locally running Clash proxy at `http://127.0.0.1:7890` when direct access fails.  Do not use `--refresh` to overwrite a frozen dataset snapshot without creating and documenting a new protocol version.

## Development Workflow

Run a small GPU validation smoke test over the financial tasks:

```bash
conda run --no-capture-output -n mamba python scripts/financial/run_financial_benchmark.py --stage smoke
```

Re-audit the frozen validation-selection records:

```bash
conda run --no-capture-output -n mamba python scripts/financial/run_financial_benchmark.py --stage selection
```

The V1 final period has already been analyzed. Do not rerun it to select or revise a
model. New model development must follow the prospective evaluation boundary in
`docs/next_optimization_plan.md`.

## Repository Layout

```text
model/                 PMS-Mamba and comparison model definitions
layers/                normalization, decomposition, and encoder layers
scripts/financial/     data, protocol, training, and analysis entry points
configs/               versioned financial evaluation configuration
tests/                 financial data and protocol checks
docs/                  current results, optimization, and writing direction
reproducibility/       frozen V1/V2 metrics, manifests, figures, and checksums
```

The manuscript source of record is maintained in a separate repository. Generated
datasets, checkpoints, intermediate predictions, TensorBoard traces, and local backups
are ignored by Git. Keep them outside commits and regenerate them from the recorded
configuration when needed.

## Reproducibility Boundary

The repository contains code, frozen metrics, manifests, figures, and configuration,
but not redistributed market-data archives or trained checkpoints. Manuscript tables
and claims must use the completed protocol records and respect each source provider's
terms.
