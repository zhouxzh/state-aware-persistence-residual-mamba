# Audit Response and Computation Plan

## Scope

This document replaces the two temporary ACE2 notes. It records the corrective
actions from the independent audit and the only additional computation authorized
for this release family. The repository is a program and evidence package; it does
not contain manuscript source.

## Corrected V2 Interpretation

The V2 confirmatory-comparison release is the publication authority for the current
18-target S-only study. It contains 5,940 learned horizon rows and 324 deterministic
rows. The full checkpoint reload audit is authoritative at
`results/financial_s_only_retrospective_v2/replay/replay_validation.json`: it
validated all 5,940 learned bundles, found no problems, reported zero maximum
prediction and truth differences, and matched origin and forecast dates exactly.
The regenerated `replay_summary.json` is now a complete 5,940-entry verified index;
both files are retained in the external archive and the compact release remains the
tracked evidence contract.

## Targeted V3 Computation

The audit identified a specific question: whether the regime gate helps the Mamba
branch at the long horizons where V2 is weaker. A full baseline rerun is not
justified. The bounded exploratory design is:

| Factor | Frozen choice |
| --- | --- |
| Targets | all 18 V2 target-only financial series |
| Learned models | Regime-Gated Mamba and Ungated Regime-Linear Mamba |
| Seeds | 2023, 2024, 2025, 2026, 2027 |
| Horizons | 60, 120, 252 |
| Selection | exact V2 family selections; no Optuna rerun |
| Training | V2 MSE, balanced horizon weighting, 10 epochs, patience 3 |
| Evaluation | same 2023-01-01 to 2026-06-30 retrospective test window |
| Planned cells | 18 x 2 x 5 x 3 = 540 learned cells |

V3 is marked `exploratory_retrospective`, stored under ignored local `results/`,
`checkpoints/`, `docs/analysis/`, and figure paths, and is never merged into V2
metrics. It is allowed to answer a mechanism question, not to create a new
confirmatory accuracy claim.

## Execution

Use the CUDA `mamba` environment for the release, training, replay, and report;
use `sci-agent` for analysis and tests.

The executed commands were:

```bash
conda run --no-capture-output -n mamba python scripts/data.py release-setup --release v3
conda run --no-capture-output -n mamba python scripts/reproduce.py --workflow financial-s-only --release v3 --stage plan
conda run --no-capture-output -n mamba python scripts/reproduce.py --workflow financial-s-only --release v3 --stage train --unlock-retrospective-test
conda run --no-capture-output -n mamba python scripts/reproduce.py --workflow financial-s-only --release v3 --stage report
conda run --no-capture-output -n mamba python scripts/reproduce.py --workflow financial-s-only --release v3 --stage replay
conda run --no-capture-output -n mamba python scripts/reproduce.py --workflow financial-s-only --release v3 --stage replay-verify
conda run --no-capture-output -n sci-agent python scripts/analyze.py exploratory-v3
```

The run completed on 2026-08-21. The release verifier reports `540/540` learned
rows with no problems, and checkpoint replay reports `540/540` valid entries with
zero maximum prediction/truth differences and exact date matches. The paired mean
path-RMSSE differences (gated minus ungated) are -0.1494 at h=60 (bootstrap 95%
CI [-0.3392, -0.0216], Holm-adjusted descriptive p=0.0264), -0.0978 at h=120
(CI [-0.2592, 0.0177]), and -0.0433 at h=252 (CI [-0.0930, 0.0037]). These are
exploratory gate-ablation results, not comparisons with V2 baselines. Mean runtime
per retained horizon run was 6.28 s for the gated model and 2.38 s for the ungated
ablation, so this V3 run does not support a speed advantage for the gate itself.

## Claim Boundary

The manuscript may cite V2 for the baseline comparison and V3 only for an explicitly
exploratory gate-ablation observation after V3 is complete and verified. It must not
describe V3 as a fresh test set, prospective evidence, a replacement for V2, or proof
that Mamba beats PatchTST or TimesNet. Any future untouched-period evaluation requires
a new versioned release.
