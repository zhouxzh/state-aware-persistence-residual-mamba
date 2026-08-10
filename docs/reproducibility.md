# Reproducibility Workflow

## Environment

Create the recorded Conda environment, then run every command through `sci-agent`.

```bash
conda env create -f environment.yml
conda run --no-capture-output -n sci-agent python -m pip install -r requirements.txt
conda run --no-capture-output -n sci-agent python scripts/data.py preflight
```

The environment must include a CUDA-compatible PyTorch build and `mamba-ssm`. The
preflight command reports the locally detected runtime before any evaluation starts.

## Data preparation

Raw downloads are excluded from Git. On a machine permitted to retrieve the source
data, construct a local copy and validate its manifests:

```bash
conda run --no-capture-output -n sci-agent python scripts/data.py download
conda run --no-capture-output -n sci-agent python scripts/data.py prepare
conda run --no-capture-output -n sci-agent python scripts/data.py preflight
```

Do not overwrite a recorded local data snapshot without creating a new protocol
version and manifest.

## Audit and evaluation

Audit the supplied historical baseline evidence before invoking the candidate runner:

```bash
conda run --no-capture-output -n sci-agent python scripts/analyze.py audit
conda run --no-capture-output -n sci-agent python scripts/evaluate.py --stage dry-run
```

The complete comparison is explicitly retrospective. Execute it only with that
interpretation accepted:

```bash
conda run --no-capture-output -n sci-agent python scripts/evaluate.py --stage final --unlock-retrospective-test
conda run --no-capture-output -n sci-agent python scripts/analyze.py metrics --require-complete
conda run --no-capture-output -n sci-agent python scripts/analyze.py normalize
conda run --no-capture-output -n sci-agent python scripts/analyze.py profile
conda run --no-capture-output -n sci-agent python scripts/analyze.py report
```

The normalizer preserves `source_model_id` and writes canonical `model_id` and
reader-facing `model` columns. It must run before the profile/report commands when
evaluations have been regenerated.

## Checkpoint replay

Checkpoint-based reproduction is kept separate from publication analysis. The
workflow below trains the selected candidate models with retained weights, hashes
every checkpoint, and then replays forecasts without retraining:

```bash
conda run --no-capture-output -n sci-agent python scripts/reproduce.py --mode train
conda run --no-capture-output -n sci-agent python scripts/reproduce.py --mode replay
conda run --no-capture-output -n sci-agent python scripts/reproduce.py --mode verify
```

The baseline results remain reproducible from the frozen prediction and metric
snapshots; their historical training weights were not retained.

## Retained Five-Model Mamba Rerun

The separate `financial_mamba_rerun_v1` workflow retrains Regime-Gated Mamba,
Multi-Scale Patch Mamba, Inverted Mamba, Decomposition Mamba, and Multi-Scale
Decomposition Mamba. It uses the same eight financial tasks, six horizons, and five
fixed seeds, while keeping all checkpoints and raw forecasts in a new ignored local
archive. It remains a retrospective, protocol-matched evaluation.

```bash
conda run --no-capture-output -n sci-agent python scripts/reproduce.py --workflow mamba-rerun --mode train
conda run --no-capture-output -n sci-agent python scripts/reproduce.py --workflow mamba-rerun --mode verify
conda run --no-capture-output -n sci-agent python scripts/analyze.py mamba-report
conda run --no-capture-output -n sci-agent python scripts/analyze.py forecast-plots
```

The full campaign creates 1,200 horizon-specific training/evaluation runs under
`results/financial_mamba_rerun_v1/` and
`checkpoints/financial_mamba_rerun_v1/`. Each saved run includes a checkpoint,
prediction and target arrays, origin and target-date arrays, metrics, metadata, and
SHA-256 manifests. The plotting command creates one seed-aggregated rolling
forecast-versus-observed figure for each model/task/horizon combination plus summary
comparison panels for horizons 60 and 252.

## Validation

```bash
conda run --no-capture-output -n sci-agent pytest -q
```

Generated raw data, checkpoints, predictions, and TensorBoard traces remain local and
ignored. Commit code, configuration, technical documentation, and frozen
reproducibility artifacts only.
