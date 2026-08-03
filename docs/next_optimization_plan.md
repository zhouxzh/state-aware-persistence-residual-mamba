# Next PMS-Mamba Optimization Plan

Status: prospective V3 protocol draft

Updated: 2026-08-03

## Objective

The next cycle should not perform a broad hyperparameter search. It should answer one
specific question: can residual-anchored PMS-Mamba retain its short-horizon validation
gain while producing a material improvement at 120 and 252 steps?

Financial panels remain the development reference case. Cross-domain claims require
new datasets selected for their nonstationary mechanisms before model outcomes are
inspected.

## Diagnosis carried forward

- Current PMS-Mamba is strongest at 20 and 60 steps and weakest at 120 and 252 steps.
- FX and yields are dominated by persistence; cross-asset is the strongest model family.
- V2 residual anchoring was favorable, especially at short horizons.
- V2 `SCALE_MSE` was materially unfavorable and must not be reused unchanged.
- The current volatility gate and late-step weighting did not solve long-horizon error.
- The V1 test period is already known. It cannot serve as an untouched confirmatory
  period for a newly designed V3 architecture.

## Model priorities

### 1. Isolate residual anchoring

The fractional V2 design did not contain the clean combination residual target + MSE +
mean fusion + uniform step weighting. V3 must test this configuration directly before
adding another mechanism. This separates the residual-target effect from the late-step
weighting used by F01.

### 2. Persistence-change decomposition

Use an explicit forecast form:

```text
forecast_h = last_value + alpha_h * predicted_change_h
```

`alpha_h` may depend on the input window and horizon, but it must be bounded and
regularized toward persistence. The intent is to avoid unnecessary movement at short
horizons while allowing larger cumulative change at long horizons.

### 3. Cumulative increment head

Evaluate a head that predicts per-step increments and reconstructs the level path by a
cumulative sum from the last observation. This makes long-horizon error accumulation
explicit and allows a secondary increment-consistency loss. It must be compared with
the existing direct residual head using identical encoders and budgets.

### 4. Long-range receptive field

Test one bounded architectural change, not a new collection of loosely motivated
modules. The preferred candidate is a coarse patch branch whose effective lookback
extends beyond the current short patch layout. Preserve the existing fine branch and
mean fusion so the experiment isolates receptive-field scale.

### 5. Input-conditioned regime features

If a regime feature is used, compute it only from the encoder window. Candidate features
are recent/full volatility ratio, normalized slope, and last-value z-score. Do not
define regimes from validation or test forecast errors. A regime module must demonstrate
incremental value beyond the simpler persistence-change head.

## Loss and selection alignment

The metric roles must be explicit:

- training loss: standard MSE as the reference;
- optional auxiliary loss: increment MSE with one frozen coefficient;
- validation selection: balanced path RMSSE across short, middle, and long terms;
- final reporting: path RMSSE primary, with path MAE/RMSE, terminal RMSSE, and skill
  versus Last-value as supporting metrics.

Do not optimize one configuration on balanced RMSSE and another on a different horizon
set. Do not reuse the failed local `SCALE_MSE` definition. If a fixed training scale is
tested later, derive it from training data only and create a new named protocol.

## Prespecified V3 screen

| ID | Residual anchor | Forecast head | Receptive field | Purpose |
| --- | --- | --- | --- | --- |
| V3-B0 | No | Direct level | Current | Frozen F04 reference |
| V3-B1 | Yes | Direct residual | Current | Isolated residual effect |
| V3-C1 | Yes | Cumulative increments | Current | Long-path consistency |
| V3-C2 | Yes | Persistence-change blend | Current | Short/long adaptation |
| V3-C3 | Yes | Best of C1/C2 | Coarse branch | Long-range capacity |

Run B0 through C2 first. Promote only the better of C1 and C2 into C3; do not combine
both after inspecting individual task wins.

### Screening stage

- 8 current S/MS tasks;
- horizons 1, 5, 20, 60, 120, and 252;
- seeds 2023, 2024, and 2025;
- identical base hyperparameters, epochs, early stopping, and data hashes;
- validation targets only;
- atomic, resumable horizon records.

### Confirmation stage

Refit the best candidate and B0 with seeds 2023 through 2027. Confirm inverse scaling,
output shapes, deterministic replay, finite gradients, and loss behavior before
interpreting scores.

## Practical success rule

A V3 candidate is eligible for external evaluation only if all conditions hold:

1. at least 2% lower mean validation balanced path RMSSE than B0;
2. at least 2% lower mean long-term RMSSE;
3. no short-, middle-, or long-term degradation greater than 5%;
4. improvement in at least 5 of the 8 current tasks;
5. median seed RMSSE coefficient of variation no greater than 1%;
6. median runtime no greater than 1.5 times B0 unless the accuracy gain exceeds 5%.

If no candidate meets every rule, retain B0 and report another negative ablation.

## Evaluation boundary

The 2023-2026 V1 test period has already been analyzed and must not be treated as a new
untouched test set. V3 can remain validation-only until one of these confirmatory
options is available:

- a later out-of-time period long enough to support the 252-step horizon;
- a prospectively frozen set of new datasets with untouched final periods;
- an external benchmark protocol selected before V3 outcomes are inspected.

Only one frozen V3 candidate may enter that evaluation. Existing V1 results remain
unchanged and must not be overwritten.

## Dataset expansion

Select datasets by nonstationary mechanism rather than by domain label or model score.
The minimum next portfolio should add at least three non-financial families:

| Mechanism | Candidate domain | Required property |
| --- | --- | --- |
| Structural break | Energy demand/price or mobility | Documented policy, shock, or regime eras |
| Sensor drift and scale change | Industrial condition monitoring | Calibrated timestamps and nonstationary operating regimes |
| Seasonal distribution shift | Weather, climate, or environmental monitoring | Long record with changing seasonal level or variance |

Optional robustness families include macroeconomic vintages, realized volatility, and
external forecasting collections. Exact providers, licenses, identifiers, frequencies,
cutoffs, target transformations, and split dates must be frozen before download or
training. Do not drop a completed dataset because PMS-Mamba loses on it.

## Baselines

Every level-forecasting task must retain Last-value and Random-walk-drift. Add ARIMA or
an appropriate autoregressive reference, NLinear, DLinear, PatchTST, S-Mamba, and the
frozen PMS baseline. Domain-specific references should be added when justified, such as
HAR-RV for realized volatility. Equal validation budgets matter more than adding many
weak neural baselines.

## Required outputs

- versioned V3 protocol and data manifests;
- exact configuration matrix and source hashes;
- horizon-level MAE, MSE, RMSE, RMSSE, and runtime;
- task-seed-term summaries and paired validation comparisons;
- selection manifest with an explicit test-access flag;
- implementation tests for every new head;
- Git-trackable parameters, summary tables, figures, and SHA-256 sums;
- checkpoints only outside Git unless required for an explicit release.

## Stop rules

- Do not alter the success rule after seeing validation results.
- Do not search additional losses, gates, or horizon weights because a candidate is
  just below the threshold.
- Do not inspect an external final period until the candidate and protocol are frozen.
- Preserve failed, null, and unfavorable tasks in every summary.
- Do not describe validation improvements as final generalization.

