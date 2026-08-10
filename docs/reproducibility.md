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

## Validation

```bash
conda run --no-capture-output -n sci-agent pytest -q
```

Generated raw data, checkpoints, predictions, and TensorBoard traces remain local and
ignored. Commit code, configuration, technical documentation, and frozen
reproducibility artifacts only.
