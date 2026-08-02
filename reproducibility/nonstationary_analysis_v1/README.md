# Nonstationary Analysis V1

This directory stores Git-tracked analysis snapshots for the broader nonstationary
forecasting study. Financial panels are the current reference datasets, not the research
domain name.

`selection_safe/` contains analysis derived without reading protected test targets:

- data quality and train/validation nonstationarity summaries;
- validation-only model scores, ranks, S/MS comparisons, and proposal contrasts;
- selected hyperparameter frequencies and HPO audit summaries;
- two diagnostic figures, a human-readable report, and an input-hash manifest.

The selection results are exploratory and must not be presented as final-period model
performance.

`final/` contains the authorized test-period analysis after the frozen 360-cell neural
matrix and statistical references completed. It includes all small release tables,
completion and runtime metadata, convergence audits, a result report, one summary
figure, and SHA-256 hashes. Raw per-origin predictions remain in the ignored runtime
tree and are not duplicated into Git.

Regenerate from the runtime data and Optuna records with:

```bash
conda run --no-capture-output -n mamba python \
  scripts/financial/analyze_selection_evidence.py \
  --output-root reproducibility/nonstationary_analysis_v1/selection_safe
```

Runtime files under `data/financial/` and `results/optuna/` remain in place and are not
moved by the analyzer.

Regenerate the final Git snapshot after running the final analyzer with:

```bash
conda run --no-capture-output -n mamba python \
  scripts/financial/build_nonstationary_release.py
```
