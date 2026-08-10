# Reproducibility Workflow

## Environment

Create the recorded Conda environment, then run every command through `sci-agent`.

```bash
conda env create -f environment.yml
conda run --no-capture-output -n sci-agent python -m pip install -r requirements.txt
conda run --no-capture-output -n sci-agent python scripts/financial/preflight.py
```

The environment must include a CUDA-compatible PyTorch build and `mamba-ssm`. The
preflight command reports the locally detected runtime before any evaluation starts.

## Data preparation

Raw downloads are excluded from Git. On a machine permitted to retrieve the source
data, construct a local copy and validate its manifests:

```bash
conda run --no-capture-output -n sci-agent python scripts/financial/download_financial_data.py
conda run --no-capture-output -n sci-agent python scripts/financial/prepare_financial_data.py
conda run --no-capture-output -n sci-agent python scripts/financial/preflight.py
```

Do not overwrite a recorded local data snapshot without creating a new protocol
version and manifest.

## Audit and evaluation

Audit the supplied historical baseline evidence before invoking the candidate runner:

```bash
conda run --no-capture-output -n sci-agent python scripts/publication/audit_legacy_baselines.py
conda run --no-capture-output -n sci-agent python scripts/publication/run_financial_reference_evaluation.py --stage dry-run
```

The complete comparison is explicitly retrospective. Execute it only with that
interpretation accepted:

```bash
conda run --no-capture-output -n sci-agent python scripts/publication/run_financial_reference_evaluation.py --stage final --unlock-retrospective-test
conda run --no-capture-output -n sci-agent python scripts/publication/analyze_publication_results.py --require-complete
conda run --no-capture-output -n sci-agent python scripts/publication/normalize_release_identifiers.py
conda run --no-capture-output -n sci-agent python scripts/publication/profile_final_models.py
conda run --no-capture-output -n sci-agent python scripts/publication/build_final_evaluation_report.py
```

The normalizer preserves `source_model_id` and writes canonical `model_id` and
reader-facing `model` columns. It must run before the profile/report commands when
evaluations have been regenerated.

## Validation

```bash
conda run --no-capture-output -n sci-agent pytest -q
```

Generated raw data, checkpoints, predictions, and TensorBoard traces remain local and
ignored. Commit code, configuration, technical documentation, and frozen
reproducibility artifacts only.
