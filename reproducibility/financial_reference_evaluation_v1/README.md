# Financial Reference Evaluation V1

This directory contains the compact, reviewer-facing evidence for the selected
Regime-Gated Mamba configuration and its Multi-Scale Patch Mamba ablation.

## Contents

- `candidate_selection/`: the eight frozen selected-model parameter snapshots.
- `selection/`: the original baseline and Mamba parameter snapshots for eight tasks.
- `training_datasets.json`: the task manifest and data hashes.
- `audit/`: the strict audit of imported historical baseline rows.
- `metrics/`: canonical metrics, descriptive contrasts, and inference profile.
- `model_identity_map.json`: source-run to canonical-model mapping.

Source-run identifiers are retained only for audit. The public mapping is:

| Source identifier | Canonical ID | Public name |
| --- | --- | --- |
| `PMSV5_R6` | `RegimeGatedMamba` | Regime-Gated Mamba |
| `PMSV3_B0` | `MultiScalePatchMamba` | Multi-Scale Patch Mamba |

The archived baseline source protocol is `protocol/financial_confirmatory_source.json`.
The selected-model evaluation protocol is
`configs/financial_reference_evaluation_v1.json`.

## Evidence boundary

Historical baseline work had already opened the 2023-2026 target period. Candidate
comparisons are therefore marked `retrospective_protocol_matched`, not as untouched
test results. The selected configuration was chosen separately on the 2022 merge gate.

The full workflow is documented in [docs/reproducibility.md](../../docs/reproducibility.md).
Do not publish raw provider archives, processed panels without source-rights review,
checkpoints, predictions, or TensorBoard traces.
