# PMS-Mamba V2 validation release

This snapshot records a validation-only optimization study for forecasting under
nonstationarity. Financial panels are reference datasets, not the scope label of the
method. The protected test targets were not read during V2 screening, confirmation,
selection, or analysis.

## Result

The resolution-IV screen compared eight configurations on eight S/MS tasks, three
seeds, and six horizons (1,152 horizon-level rows). F01 and F03 were then compared
with the current PMS configuration F04 using five seeds (720 rows). F01 improved
mean validation balanced RMSSE by 1.79% and F03 by 1.68%; neither reached the frozen
2% practical threshold, so F04 was retained and no new locked-test run was opened.

## Contents

- `validation/`: exact design, horizon metrics, task-seed summaries, and manifests.
- `selection/`: frozen decision, selected per-task parameters, and checksums.
- `analysis/`: factor effects, paired diagnostics, report, figure, and provenance.
- `analysis/pms_v2_results.tex`: evidence-bound LaTeX results fragment for later inclusion.
- `release_manifest.json`: source-code hashes and runtime versions.
- `SHA256SUMS`: checksums for every release file except the checksum file itself.

## Replay

Run commands from the repository root in the `mamba` conda environment:

```bash
conda run -n mamba python scripts/financial/merge_pms_v2_validation.py
conda run -n mamba python scripts/financial/freeze_pms_v2_selection.py
conda run -n mamba python scripts/financial/analyze_pms_v2_validation.py
conda run -n mamba python scripts/financial/build_pms_v2_release.py
```

Training replay uses `scripts/financial/run_pms_v2_screen.py`; exact configuration,
task, seed, horizon, protocol, and data hashes are recorded in the manifests. No
checkpoint is required to reproduce the reported aggregate metrics from the frozen
tables; retraining requires the tracked source and the documented `mamba` conda
environment.
