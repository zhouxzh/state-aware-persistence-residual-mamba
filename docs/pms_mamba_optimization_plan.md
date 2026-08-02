# PMS-Mamba Optimization and Paper Analysis Plan

Updated: 2026-08-02

## Objective

Improve PMS-Mamba for nonstationary time-series forecasting while preserving a
locked, auditable comparison. The current financial panels are reference datasets
for the broader nonstationarity study, not the scientific scope of the project.

## Frozen baseline and evidence boundary

The V1 confirmatory snapshot under
`reproducibility/nonstationary_analysis_v1/final/` is immutable. It contains:

- 4 panels, 8 S/MS tasks, 13 models, and 6 horizons (1, 5, 20, 60, 120, 252);
- 360 learned model/task/seed cells and 2,160 horizon-specific learned records;
- path and terminal MAE, MSE, RMSE, RMSSE, skill relative to Last-value, seed
  stability, volatility-regime summaries, and moving-block bootstrap contrasts.

The protected test period must not be used for architecture selection, loss
selection, hyperparameter tuning, or stopping decisions. Any new experiment is a
V2 validation-selected extension and must not overwrite the V1 snapshot.

## Work packages

### 0. Reproducibility lock (complete)

- Verify the V1 SHA-256 manifest, protocol hash, data manifest, and final run counts.
- Record the exact conda environment and Mamba runtime in the experiment manifest.
- Keep the current predictions and negative findings available as the reference arm.

Acceptance: all V1 hashes and existing analysis tests pass; no test-target access is
introduced into selection scripts.

### 1. Metric and failure-mode audit (complete)

- Use the common-metric suite to compare all models with MAE, MSE, RMSE, path-RMSSE,
  terminal RMSSE, and skill relative to Last-value.
- Report task-horizon winners, dataset-balanced short/middle/long summaries, seed
  coefficients of variation, regime-specific metrics, and paired bootstrap contrasts.
- Separate the three observed failure modes: short-horizon persistence, cross-asset
  252-day degradation, and FX/yield no-change dominance.

Acceptance: the report is generated from the frozen final snapshot, all expected rows
are present and finite where estimable, and zero-origin regime cells remain explicit
NA rather than being imputed.

### 2. Validation-only PMS screening (next)

Run a seeded resolution-IV fractional factorial screen over four prespecified factors:

| Factor | Low level | High level |
| --- | --- | --- |
| Forecast target | direct level | residual from the last observed value |
| Training loss | MSE | scale-normalized or baseline-relative MSE |
| Multi-scale fusion | fixed mean | learnable/volatility-conditioned gate |
| Selection calibration | balanced horizons [5, 60, 252] | long-horizon [60, 120, 252] |

- Use the same temporal splits, origins, input windows, and data hashes as V1.
- Archive the exact 8-run design matrix, seed list, commands, and validation outputs.
- Use three fixed training seeds for screening; do not inspect test predictions.
- Keep `S_Mamba` unchanged as the implementation baseline.

Primary screen objective: validation balanced RMSSE. Secondary diagnostics are
validation path-RMSSE by horizon term, skill versus Last-value, and training/runtime
stability. The screen is exploratory and does not create confirmatory p-values.

Acceptance: every run has complete validation metrics and finite outputs; the chosen
candidate is selected by the predeclared objective, not by a favorable test result.

### 3. Validation confirmation and implementation audit

- Refit the two best screening configurations with five seeds on all eight tasks.
- Check residual-target inverse scaling, gated-fusion shape invariants, loss scale
  behavior, and deterministic replay.
- Compare the finalists with the current PMS-Mamba-PD and the validation-selected
  non-Mamba learned comparator using paired validation origins.
- Retain the current PMS configuration if no candidate meets the practical success
  rule: at least 2% lower mean validation balanced RMSSE and no term-level degradation
  greater than 5%.

Acceptance: selected parameters and replay scores are frozen in a V2 selection
manifest; the implementation passes smoke tests, unit tests, and finite forward/
backward checks in the `mamba` conda environment.

### 4. Locked test evaluation (only after V2 selection is frozen)

- Evaluate the selected PMS candidate with five seeds on the unchanged test period.
- Compare it against all existing V1 models using the same path-RMSSE primary ranking
  and the common metric suite; existing V1 predictions are not replaced.
- Run 10,000-replicate moving-block bootstrap contrasts with Holm correction within
  each prespecified comparison family.
- Report point estimates, uncertainty, practical effect sizes, task-horizon wins,
  balanced dataset summaries, and regime-specific NA counts.

If the protocol or primary metric changes, create a separately labeled protocol
amendment and rerun the complete comparison matrix. Do not silently mix V1 and V2
claims.

### 5. Manuscript and release integration

- Describe the study as forecasting under nonstationarity with financial reference
  panels.
- State the mixed result accurately: PMS-Mamba-PD is competitive among learned models,
  but naive/statistical references remain strong and no Mamba variant wins a V1
  task-horizon cell.
- Present the long-horizon diagnosis and the validation-only V2 ablation as separate
  confirmatory versus exploratory evidence.
- Bind every numeric claim to a local evidence ID and reconcile tables, figures,
  methods, and result text before submission.
- Copy only the required V2 manifests, selected parameters, metric tables, figures,
  and scripts into `reproducibility/nonstationary_analysis_v2/`; leave raw runtime
  arrays and checkpoints outside Git unless specifically required for reruns.
- Generate SHA-256 sums and rerun repository tests, metric-suite checks, manuscript
  consistency checks, and `git diff --check`.

## Stop and reporting rules

- Do not cherry-pick horizons, datasets, seeds, or metrics after seeing test results.
- Do not call a candidate an overall winner unless it wins the prespecified
  task-horizon comparison with uncertainty reported.
- Report null, negative, non-significant, and non-estimable results.
- If no V2 candidate improves the validation objective, keep V1 as the final result and
  document the optimization attempt as a negative ablation.

## Planned artifacts

- `results/nonstationary_metric_suite/` for local exploratory metric tables and the
  PMS diagnostic report;
- `reproducibility/nonstationary_analysis_v2/` for the frozen V2 manifests, selected
  parameters, final metrics, bootstrap contrasts, figures, and checksums;
- `docs/pms_mamba_optimization_plan.md` (this document) as the protocol record.
