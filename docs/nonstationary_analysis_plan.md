# Nonstationary Data and Model Analysis Plan

Updated: 2026-07-31

## Scope and terminology

This repository studies forecasting under nonstationarity. The current foreign
exchange, Treasury-yield, cross-asset, and cryptoasset panels are financial reference
datasets, not the boundary of the research domain. New artifacts should use
`nonstationary_analysis` terminology. The frozen identifier
`financial_confirmatory_v1` remains unchanged because renaming a frozen protocol would
invalidate its hashes.

## Evidence stages

### Stage A: selection-safe data analysis - complete

- Verify four processed panels, source hashes, chronological splits, missingness, and
  duplicate dates.
- Analyze train/validation level and difference stationarity with the frozen ADF/KPSS
  specifications.
- Quantify validation-era mean, level-scale, difference-scale, volatility, and
  target-feature correlation shifts.
- Do not read protected test targets.

Acceptance criteria: 4/4 panels pass integrity checks and the diagnostics manifest says
`scope=train_validation` and `test_targets_read=false`.

### Stage B: selection and architecture analysis - complete

- Audit 8 S/MS tasks, 9 learned models, 72 model/task selections, 864 budgeted Optuna
  trials, 2 recorded interrupted trials, and 216 full-horizon validation replays.
- Report validation-only task ranks, S/MS differences, proposed variants relative to
  S-Mamba, selected hyperparameter frequencies, and calibration/replay agreement.
- Treat these results as exploratory selection evidence. Do not compute inferential
  p-values from selected validation scores.

Acceptance criteria: every study has 12 COMPLETE+PRUNED trials, 3 validation replays,
`selection_eval_flag=val`, and `final_eval_flag=not_opened`.

### Stage C: restore the formal runtime - complete

The local `mamba` environment now uses Python 3.9.25, PyTorch 2.8.0/CUDA 12.8, and
`mamba-ssm==2.3.1`, built locally with CUDA 12.8. The preflight exits 0, all four
repository Mamba model modules import, and a CUDA Mamba layer completes finite forward
and backward passes on the RTX 5090 D. This is a documented replacement runtime rather
than a claim that the original host used the same package versions.

Acceptance criteria: `scripts/financial/preflight.py` exits 0 and all Mamba model
imports pass; the 8-task smoke stage then completes without shape, inverse-scaling,
thermal, or non-finite metric failures.

### Stage D: frozen final predictions - complete

The protected 2023-01-01 through 2026-06-30 period was explicitly authorized for
opening on 2026-07-31. After the eight-task smoke gate passes, run:

```bash
conda run --no-capture-output -n mamba python \
  scripts/financial/run_financial_benchmark.py --stage final --unlock-test
```

The runner is resumable. It must produce all 360 task/model/seed cells: 8 tasks x 9
learned models x 5 seeds. Do not replace failures silently or assemble a result table
from a task subset.

Acceptance criteria: `final_runs.json` contains exactly 360 complete cells bound to the
frozen protocol and data hashes, with per-origin predictions for all six horizons.

### Stage E: statistical references and final model analysis - complete

Run the 28 task/reference series, then the existing final analyzer:

```bash
conda run --no-capture-output -n mamba python \
  scripts/financial/run_statistical_baselines.py --unlock-test
conda run --no-capture-output -n mamba python \
  scripts/financial/analyze_financial_results.py
```

Required outputs include path and terminal MAE/MSE/RMSE/RMSSE, skill relative to last
value, S/MS comparisons, prespecified volatility-regime metrics, five-seed variation,
10,000-replicate moving-block bootstrap intervals, and Holm-adjusted comparisons.

Acceptance criteria: the final analyzer exits 0, reports 360 neural cells, validates
all expected origins, and produces no missing or non-finite primary metric cells.
Prespecified regime cells with zero eligible origins are retained with `origin_count=0`
and not-estimable metrics rather than imputed values. All selected ARIMA candidates and
test-preceding coefficient fits are required to report convergence.

### Stage F: release integration - complete; manuscript integration remains separate

- Freeze final parameters, manifests, input/output hashes, tables, and figures under
  `reproducibility/` without moving runtime files.
- Rewrite result claims from final evidence only.
- Describe current panels as financial reference datasets for nonstationary analysis.
- Preserve null, negative, and inconclusive outcomes and avoid trading-profit or
  general-purpose forecasting claims.

The Git-trackable final snapshot is generated under
`reproducibility/nonstationary_analysis_v1/final/`. Raw per-origin arrays remain in the
ignored runtime result tree because they are approximately 1.2 GB.

## Current result boundary

Stages A through F are complete for the current financial reference panels. The final
matrix contains all 360 task/model/seed cells and 2,160 horizon-specific learned-model
records. No Mamba variant has the best path RMSSE in any of the 48 task-horizon cells;
this negative result and the mixed paired contrasts must be preserved in any manuscript
integration.
