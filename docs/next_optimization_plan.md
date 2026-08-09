# Final Financial Evaluation Plan

Updated: 2026-08-09

The architecture search is closed. `PMSV5_R6` is the selected model. The remaining
priority is a clean final financial evaluation, not additional tuning on the 2022 gate
or unrelated engineering datasets.

The submission sequence and claim restrictions are maintained in the
[publication plan](publication_plan.md); this document is the execution checklist for
the final evaluation itself.

## Step 1: freeze the comparison

Freeze the R6 recipe already stored in `configs/pms_mamba_v3.json`. Freeze baseline
recipes before reading the final targets:

- Mamba family: S-Mamba, retuned NS-Mamba-D, MS-Mamba-MD, and PMSV3_B0;
- neural forecasting: PatchTST, TimesNet, and NLinear;
- financial/statistical: last-value, random-walk drift, ARIMA, and VAR-difference for
  multivariate tasks.

R5 may appear as a development ablation, but it must not replace R6 after inspecting
the final test.

## Step 2: repair the runtime profile

Run one matched profiler for R6, PatchTST, and TimesNet with identical input window,
batch size, precision, warm-up, iteration count, and device. Record latency,
throughput, peak memory, parameter count, CUDA, PyTorch, GPU model, and driver version.

## Step 3: open the final financial test once

Train using data through 2022-12-31 and evaluate from 2023-01-01 through 2026-06-30.
Use seeds 2023-2027 and horizons 1, 5, 20, 60, 120, and 252. Save per-origin forecasts
so every aggregate and paired comparison can be regenerated.

The primary outcome should remain task-balanced path RMSSE. Report path MAE, path
RMSE, terminal MAE, terminal RMSE, and terminal RMSSE as secondary outcomes. Report
short, medium, and long horizons separately.

## Step 4: analyze uncertainty and failure modes

Use paired resampling over matched forecast origins and report confidence intervals,
effect sizes, task wins, and horizon-group wins. Analyze FX separately because R6 lost
both FX gate tasks to B0. Report statistical or persistence baselines even when they
beat learned models.

## Step 5: produce final figures

Regenerate all model-versus-horizon figures from the final R6 evaluation. The existing
all-model figures describe the earlier PMS model and must not be relabeled as R6.
Required final displays are:

- RMSSE by model, financial panel, task mode, and horizon;
- R6 percentage gap to each major baseline;
- short, medium, and long horizon summaries with uncertainty;
- latency versus balanced RMSSE and memory versus balanced RMSSE;
- an FX-focused failure analysis.

## Optional supplementary data

The public Exchange dataset is a relevant optional robustness test. ETT, Electricity,
Traffic, and Weather are not required for a finance-specific paper. Run them only if
the manuscript claims cross-domain generalization.

## Completion rule

The paper result becomes final only when the financial holdout is evaluated, the R6
comparison includes PatchTST and TimesNet under the same protocol, the profile metadata
is corrected, and all tables and figures can be regenerated from frozen artifacts.
