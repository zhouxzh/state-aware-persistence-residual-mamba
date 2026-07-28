# Financial Confirmatory Benchmark Runbook

## Current Handoff State

The code and data preparation phases are complete. The frozen protocol is
`financial_confirmatory_v1`, with a data cutoff of 2026-06-30. Raw source files,
checksums, processed panels, and manifests are stored under `data/financial/`.

Prepared panels:

| Panel | Rows | Date range | Train / validation / test |
| --- | ---: | --- | ---: |
| Foreign exchange | 6,894 | 1999-01-04 to 2026-06-30 | 5,521 / 499 / 874 |
| Treasury yields | 5,101 | 2006-02-09 to 2026-06-30 | 3,728 / 500 / 873 |
| Cross asset | 2,483 | 2016-07-25 to 2026-06-30 | 1,112 / 502 / 869 |
| Cryptoasset | 2,980 | 2018-05-04 to 2026-06-30 | 973 / 730 / 1,277 |

Each panel has an S task and an MS task. The confirmatory matrix contains eight tasks,
nine learned models, six horizons, and five final seeds. Weather, ETT, Electricity, and
Traffic are outside this manuscript's confirmatory scope. Legacy GLD and Exchange runs
remain development evidence only.

The current machine state blocks formal training: CUDA is unavailable and `nvidia-smi`
reports an NVIDIA driver/library mismatch. Do not start formal training until the first
preflight command below returns success.

## After Reboot

Run all commands from the repository root, `/data/zhong/mamba`.

1. Verify CUDA, the NVIDIA driver, disk space, and the optional Clash endpoint:

   ```bash
   conda run --no-capture-output -n mamba python scripts/financial/preflight.py --output results/financial_confirmatory/environment_preflight.json
   ```

   The command must exit with status 0, report `"available": true`, list at least one
   CUDA device, and show a successful `nvidia-smi` query. A nonzero exit blocks formal
   training.

2. Revalidate every source checksum, processed-data hash, split, and target layout:

   ```bash
   conda run --no-capture-output -n mamba python -m unittest tests.test_financial_pipeline -v
   ```

   The selection-safe nonstationarity diagnostics can also be regenerated without
   reading final-period targets:

   ```bash
   python scripts/financial/analyze_financial_data.py
   python manuscript/figures/generate_financial_data_diagnostics.py
   ```

3. Run GPU smoke tests. These train NLinear plus S-Mamba, NS-Mamba-D, MS-Mamba-MD, and
   PMS-Mamba-PD for one epoch on all eight tasks and evaluate validation data only:

   ```bash
   conda run --no-capture-output -n mamba python scripts/financial/run_financial_benchmark.py --stage smoke
   ```

4. Run validation-only hyperparameter selection. Optuna studies are persisted in
   `results/optuna/`, so rerunning the same command resumes interrupted studies:

   ```bash
   conda run --no-capture-output -n mamba python scripts/financial/run_financial_benchmark.py --stage hpo
   ```

5. Audit the complete frozen selection before any test evaluation:

   ```bash
   conda run --no-capture-output -n mamba python scripts/financial/run_financial_benchmark.py --stage selection
   ```

   This checks model coverage, protocol version, data hashes, horizons, and that every
   selection record still has `final_eval_flag=not_opened`.

6. Run the five-seed final neural evaluation. `--unlock-test` is deliberately required.
   Completed task/model/seed cells are recorded atomically and skipped on restart:

   ```bash
   conda run --no-capture-output -n mamba python scripts/financial/run_financial_benchmark.py --stage final --unlock-test
   ```

7. After all 360 neural configurations complete, run deterministic and statistical
   references. This command refuses to run if the neural matrix is incomplete:

   ```bash
   python scripts/financial/run_statistical_baselines.py --unlock-test
   ```

8. Validate artifacts and compute path/terminal metrics, last-value skill, S-versus-MS
   comparisons, 10,000-replicate moving-block bootstrap intervals, and Holm-adjusted
   p-values:

   ```bash
   python scripts/financial/analyze_financial_results.py
   ```

   Once the final period has already been unlocked, generate the full-period descriptive
   diagnostics with the frozen rule:

   ```bash
   python scripts/financial/analyze_financial_data.py --include-test
   python manuscript/figures/generate_financial_data_diagnostics.py --include-test
   ```

9. Generate evidence-bound LaTeX tables and publication figures:

   ```bash
   make -C manuscript financial-assets
   ```

   This target fails unless the complete result matrix exists. It generates new
   financial result assets but does not silently splice them into the legacy manuscript.
   The manuscript should then be rewritten against these artifacts using the
   `scientific-writing` and `latex-manuscript` skills and compiled with:

   ```bash
   make -C manuscript pdf
   ```

## Recovery and Partial Runs

Use `--tasks` to diagnose a named task during smoke testing, for example:

```bash
conda run --no-capture-output -n mamba python scripts/financial/run_financial_benchmark.py --stage smoke --tasks financial_fx_s
```

Do not use a task subset to assemble the paper's confirmatory result table. The analysis
and manuscript generators require the full frozen matrix.

If raw files ever need to be recovered, the downloaders first try direct access and can
use Clash explicitly at `http://127.0.0.1:7890`:

```bash
python scripts/financial/download_financial_data.py --proxy-first --skip-yahoo
conda run --no-capture-output -n mamba python scripts/financial/download_financial_data.py --only-yahoo --proxy-first --skip-binance
conda run --no-capture-output -n mamba python scripts/financial/prepare_financial_data.py
```

Do not use `--refresh` unless intentionally creating and documenting a new data snapshot.
Any source or protocol change requires a new protocol version rather than overwriting the
confirmatory evidence.
