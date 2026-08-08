# Documentation Index

Updated: 2026-08-04

This directory contains only current project documentation. Completed protocols and
immutable result evidence live under `reproducibility/`; local runtime outputs remain
under ignored `results/` directories.

## Current documents

- [Current reference data](current_data.md): exact datasets, variables, targets, dates,
  splits, quality checks, hashes, distribution shifts, and publication constraints.
- [Current results](current_results.md): direct PMS-Mamba advantage and non-advantage
  statement, every-model comparison, term-specific results, exact V1 test evidence,
  V2 validation optimization, stability, compute cost, and figures.
- [Computational profile](computational_profile.md): all 2,160 learned-model runtime
  and GPU-memory records summarized by model, horizon, and task, with measurement
  limits and exact PMS-Mamba efficiency comparisons.
- [Next optimization plan](next_optimization_plan.md): prospective V3 architecture,
  dataset-expansion, validation, stopping, and release protocol.
- [Paper writing direction](paper_writing_direction.md): paper positioning, evidence
  hierarchy, permitted claims, section structure, and figure/table plan.

## Evidence of record

- `../reproducibility/nonstationary_analysis_v1/final/`: immutable V1 final-test
  metrics, bootstrap contrasts, manifests, runtime records, and checksums.
- `../reproducibility/nonstationary_analysis_v2/`: validation-only V2 screening,
  five-seed confirmation, frozen selection, analysis, and checksums.
- `../results/nonstationary_metric_suite/`: local derived metric suite and PMS-Mamba
  diagnostics; these are reproducible from the frozen V1 snapshot.

## Terminology

The project studies forecasting under nonstationarity. The current foreign-exchange,
Treasury-yield, cross-asset, and cryptoasset panels are financial reference datasets,
not the scientific boundary of the work. Use "nonstationary forecasting results on
financial reference datasets" rather than the generic phrase "financial results".

The frozen internal identifier `financial_confirmatory_v1` must not be renamed because
it is bound to published hashes. New protocols and outputs use
`nonstationary_analysis_vN` terminology.
