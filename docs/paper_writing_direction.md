# Paper Writing Direction

Updated: 2026-08-09

This document is the short writing policy for the PMS-Mamba manuscript. The detailed
section scaffold is in [Manuscript Writing Brief](manuscript_writing_brief.md), the
publication sequence is in [Publication Plan](publication_plan.md), and every current
claim is mapped in [Manuscript Evidence Manifest](manuscript_evidence_manifest.md).

## Scope

Frame the work as **nonstationary financial time-series forecasting** using four
financial panels: cross-asset, cryptocurrency, foreign exchange, and Treasury yields.
The title can be:

> PMS-Mamba: Efficient Regime-Aware Forecasting for Nonstationary Financial Time Series

ETT, Electricity, Traffic, and Weather are optional robustness datasets. They should
not displace the financial protocol or be implied to be necessary for the main claim.

## Evidence boundary

`PMSV5_R6` is the selected model from the locked 2022 merge gate. It reaches balanced
RMSSE 6.0095, a 15.00% improvement over PMSV3_B0 and a 17.90% improvement over
retuned NS-Mamba-D. It wins six of eight tasks against B0 and all eight against the
retuned NS-Mamba-D reference; B0 remains better on both FX tasks.

These values are selection evidence. The direct R6 accuracy comparison with PatchTST,
TimesNet, statistical baselines, and horizon 252 on the untouched 2023-2026 financial
test is still pending. The historical common suite used an earlier PMS-Mamba-PD
configuration and must remain contextual rather than being relabeled as R6 evidence.

The matched CUDA profile currently reports lower R6 latency and allocated memory than
PatchTST and TimesNet, but throughput and R6 sequence-length metadata are inconsistent.
Use the profile only as provisional evidence until it is regenerated with complete
hardware and software metadata.

## Writing rules

- Use "selected model" for R6 until the final test is complete.
- Report absolute values, relative differences, tasks, horizons, seeds, and evidence
  periods together.
- Use path RMSSE for cross-panel comparisons; keep MAE and RMSE per task because the
  financial targets have different units.
- Separate short, middle, and long horizons; do not infer long-horizon behavior from a
  balanced score alone.
- Describe FX as a current stress case, not as an explanation of mechanism.
- Distinguish forward-pass latency from training cost, CPU cost, energy, and asymptotic
  complexity.
- Do not claim state-of-the-art, universal superiority, profitability, or causality
  without new evidence.

## Draft order

Write Methods and Data first, then the gate selection result, then the final untouched
test result, then efficiency and ablations. Draft the Abstract and Conclusion last.
Use the architecture and metrics document for Figure 1 and metric definitions. Use the
publication plan as the completion checklist before submission.
