# Financial Benchmark Power-Outage Handoff

Prepared: 2026-07-31

## Completed Before Shutdown

- The frozen protocol remains `financial_confirmatory_v1` with SHA-256
  `1b1a8d94847ab2296dec0db9a5cbe596836aae15fd8e7d88c1e4082e178d5963`.
- All eight validation-selection records passed
  `scripts/financial/run_financial_benchmark.py --stage selection`.
- Every selection record has `selection_eval_flag=val` and
  `final_eval_flag=not_opened`.
- Raw-source, processed-data, split, and target-layout checks passed through
  `tests.test_financial_pipeline`.
- Analysis-unit tests passed through `tests.test_financial_analysis`.
- The `mamba` environment contains `statsmodels 0.14.6`, required by the later
  ARIMA and VAR reference stage.

## No Further Downloads Needed

The frozen raw archives, processed panels, manifests, and checksums are already local.
Do not refresh data, rerun downloaders, or fetch newer observations after power returns.
No further Python packages are currently required for the planned pipeline.

## Resume After Power Returns

Run from `/data/zhong/mamba`:

```bash
conda run --no-capture-output -n mamba python scripts/financial/preflight.py --output results/financial_confirmatory/environment_preflight.json
conda run --no-capture-output -n mamba python -m unittest tests.test_financial_pipeline -v
conda run --no-capture-output -n mamba python scripts/financial/run_financial_benchmark.py --stage selection
```

Do not run `--stage hpo` unless the selection audit fails. A successful selection audit
does not open the final test split.

Only after an explicit decision to open the protected final period, run:

```bash
conda run --no-capture-output -n mamba python scripts/financial/run_financial_benchmark.py --stage final --unlock-test
```

The final runner writes completed task/model/seed cells atomically to
`results/financial_confirmatory/final_runs.json` and skips those cells on restart.
After all 360 neural cells finish, run the statistical references, analysis, and
manuscript asset generation in the order recorded in `docs/financial_benchmark_runbook.md`.

## Evidence Boundary

The 2023-01-01 to 2026-06-30 final period remains unopened at this handoff. The interim
manuscript may report only protocol, provenance, and selection-safe characterization;
it must not report validation rankings as confirmatory performance results.
