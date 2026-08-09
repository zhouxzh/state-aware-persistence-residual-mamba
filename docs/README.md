# Documentation

Updated: 2026-08-09

This directory describes the current state of the PMS-Mamba study. The intended paper
is about forecasting nonstationary financial time series. Public engineering datasets
such as ETT, Electricity, Traffic, and Weather are optional supplementary tests, not
requirements for the main paper.

## Current model

`PMSV5_R6` is the selected PMS-Mamba configuration. It passed the locked 2022
validation gate against `PMSV3_B0` and retuned `NS-Mamba-D`. The financial test period
from 2023-01-01 through 2026-06-30 remains unopened for R6, so the documentation calls
R6 the selected model rather than the final test winner.

## Canonical documents

| Document | Question answered |
| --- | --- |
| [Current data](current_data.md) | Which financial datasets, splits, tasks, and horizons are used? |
| [Model architecture and metrics](model_architecture_and_metrics.md) | How does R6 work, which metrics are used, and how do the models compare? |
| [Current results](current_results.md) | What does R6 currently beat, and what is not yet established? |
| [Computational profile](computational_profile.md) | How fast and memory-efficient is R6? |
| [Next evaluation plan](next_optimization_plan.md) | What must be completed before the paper result is final? |
| [Manuscript writing brief](manuscript_writing_brief.md) | Which manuscript paragraphs, tables, and figures can be reused? |
| [Publication plan](publication_plan.md) | What remains before the results are ready for submission? |
| [Evidence manifest](manuscript_evidence_manifest.md) | Which artifact supports each claim? |
| [Paper writing direction](paper_writing_direction.md) | What wording and evidence boundaries must the paper follow? |

The selected recipe is frozen in `configs/pms_mamba_v3.json`, and the decision evidence
is stored under `results/nonstationary_analysis_v5/`.

## Evidence hierarchy

1. Development results are used only to choose an architecture.
2. The 2022 merge gate confirms the selected architecture against Mamba references.
3. The untouched 2023-2026 financial period will provide the final paper comparison.
4. The older common metric suite provides context but evaluates an earlier
   `PMS_Mamba-PD`, not R6.

Do not combine values from different evidence layers into one model ranking.

## Primary artifacts

- R6 gate: `results/nonstationary_analysis_v5/gate/`
- R6 inference profile: `results/nonstationary_analysis_v5/profile/`
- Historical common metric suite: `results/nonstationary_metric_suite/`
- Financial data manifests: `data/financial/manifests/`
- Frozen protocol and R6 recipe: `configs/pms_mamba_v3.json`
