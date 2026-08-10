# Repository Structure

This repository separates forecasting implementation, local research data, frozen
evidence, and runnable workflows. The financial panels are the current reference
benchmark; the structure supports adding other nonstationary datasets later.

| Location | Ownership |
| --- | --- |
| `data/` | Local datasets, raw provider files, processed panels, and manifests. Only `data/financial/` is active for the current reference evaluation. |
| `model/` | Regime-Gated Mamba, its ablation, Mamba baselines, and audited external baselines. |
| `layers/` | Embedding, decomposition, normalization, gating, attention, and Mamba building blocks. |
| `data_provider/` | Dataset classes and DataLoader construction. |
| `experiments/` | Generic experiment classes plus financial reference evaluation and checkpoint replay workflows. |
| `utils/` | Shared metrics, data preparation, audit, provenance, reporting, and runtime helpers. |
| `scripts/` | The four supported user commands described below. |
| `reproducibility/` | Committed frozen protocol, selected parameters, metrics, profiles, and evidence hashes. |
| `backup/` | Ignored local archive of superseded data, training outputs, checkpoints, logs, and historical Optuna code. |

## Supported Commands

```bash
python scripts/data.py {download,prepare,preflight,diagnose}
python scripts/evaluate.py --stage {preflight,dry-run,smoke,final}
python scripts/analyze.py {audit,metrics,normalize,profile,report,runtime}
python scripts/reproduce.py [--workflow {reference,mamba-rerun}] --mode {train,replay,verify}
```

`run.py` remains available for a manually specified single experiment. The historical
Optuna workflow is archived because parameter selection is complete; the frozen
selected parameters remain part of the committed reproducibility record.
