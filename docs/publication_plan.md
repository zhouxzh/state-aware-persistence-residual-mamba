# Publication Plan

Updated: 2026-08-09

## Objective and recommended scope

The publishable study is a method paper on nonstationary financial time-series
forecasting. Financial datasets are the primary evidence domain; ETT, Electricity,
Traffic, and Weather are optional robustness studies and should not be presented as
requirements for the central claim.

Recommended working title:

> PMS-Mamba: Efficient Regime-Aware Forecasting for Nonstationary Financial Time Series

The paper should present `PMSV5_R6` as the selected configuration until its untouched
financial test result is available. The current evidence supports a promising
accuracy-efficiency result against Mamba references, not a final claim of superiority
over every baseline.

## Is the data sufficient?

**For a focused nonstationary financial forecasting paper: yes. For a universal claim
about financial markets: no.** The current data have enough chronological coverage and
forecast origins for a rigorous model comparison, but their scientific scope must be
stated accurately.

| Question | Assessment |
| --- | --- |
| Financial coverage | Four daily panels: cross-asset, crypto, FX, and Treasury yields |
| Task views | Eight tasks: one `S` and one `MS` task per panel; these are not eight independent datasets |
| Raw rows | 2,483 cross-asset; 2,980 crypto; 6,894 FX; 5,101 yields |
| Training rows | 973-5,521 per panel, depending on history and availability |
| Validation rows | 499-730 per panel |
| Final-test rows | 869-1,277 per panel from 2023-01-01 to 2026-06-30 |
| Horizon 252 | Supported by the multi-year final test; excluded from the one-year merge gate for protocol reasons |
| Data quality | The quality report records zero duplicate dates and zero missing cells in the processed panels; market calendar gaps remain expected |
| Stochastic replication | Five promotion seeds are specified; rolling origins are paired but overlapping, so they are not independent samples |
| Breadth limitation | Only one named target per panel is currently used: GLD, BTCUSDT, GBPUSD, and DGS10 |

The repository also contains a complete older confirmatory suite: 360 model-task-seed
bundles, 2,160 neural metric rows, six horizons, nine models, and five seeds. That suite
is useful evidence only after provenance audit because it uses `financial_confirmatory_v1`
and evaluates `PMS_Mamba-PD`, not `PMSV5_R6`. It cannot by itself establish the R6
paper result.

The correct conclusion is therefore: the data volume is sufficient to publish a
carefully scoped financial forecasting study, but the current R6 manuscript still needs
an R6 run under the frozen protocol and should avoid claims of universal financial
superiority. Adding several additional assets per panel would strengthen external
validity, but it is not required if the paper explicitly presents these four panels as
representative case studies.

## Current readiness

| Evidence component | Status | What can be written now | What is still required |
| --- | --- | --- | --- |
| R6 architecture and implementation | Ready | Method, tensor contract, and complexity description | Code audit after final freeze |
| 2022 merge-gate selection | Ready | R6 beats PMSV3_B0 and retuned NS-Mamba-D | Report as development/selection evidence |
| Historical common metric suite | Context only | Earlier PMS-Mamba-PD benchmark context | Never relabel it as R6 evidence |
| R6 vs PatchTST/TimesNet accuracy | Blocked | Motivate the comparison | Run the untouched 2023-2026 test once |
| Runtime and memory comparison | Provisional | Forward-pass efficiency under recorded CUDA setup | Repair metadata and rerun uniformly |
| Uncertainty and statistical comparison | Blocked | Specify paired analysis | Compute confidence intervals and effect sizes |
| Final abstract, results, conclusion | Blocked | Use the merge-gate paragraph with caveats | Freeze only after final test and profile |
| Reproducibility package | Partial | Frozen config, manifests, and source links | Add final predictions, seeds, environment, and checksums |

## Publication sequence

### 1. Freeze the study protocol

Treat `configs/pms_mamba_v3.json` as the protocol authority. Record its SHA-256 hash
and the repository commit used for the final run. The final protocol must state:

- training through 2022-12-31, with no use of the 2023-01-01 to 2026-06-30 period for
  model selection;
- eight financial tasks: cross-asset, cryptocurrency, FX, and Treasury yields, each
  in multivariate (`MS`) and single-target (`S`) form;
- horizons 1, 5, 20, 60, 120, and 252;
- promotion seeds 2023, 2024, 2025, 2026, and 2027;
- the complete comparison set: R6, S-Mamba, retuned NS-Mamba-D, MS-Mamba-MD,
  PMSV3_B0, PatchTST, TimesNet, NLinear, Last-value, random-walk drift, ARIMA,
  and VAR-difference;
- path RMSSE as the primary scale-free metric, with MAE, RMSE, MSE, MAPE/MSPE, and
  terminal RMSSE reported as secondary or diagnostic metrics.

Do not change the test horizon, seeds, baselines, or metric definition after opening
the final test. Any exploratory change belongs in a new development experiment.

### 2. Audit the existing result tree

Before using `results/financial_confirmatory/`, build a provenance table containing the
config hash, code commit, dataset manifest hash, seed, date, and whether a run is
marked `FIN_SMOKE`. Smoke or provenance-unknown artifacts must be excluded from the
paper tables. Do not rename a historical or smoke result to make it look like a final
R6 run.

The 2022 gate files under `results/nonstationary_analysis_v5/gate/` are valid selection
evidence and should remain separate from the final test directory.

### 3. Open the final financial test once

For every model, task, seed, and horizon, save per-origin forecasts and the exact
evaluation inputs. The final test should be evaluated only after training/selection is
complete. At minimum retain:

- predictions and targets indexed by task, origin, horizon, channel, and seed;
- per-task and per-horizon metric rows, not only aggregate means;
- failed-run logs and excluded-origin reasons;
- the training, validation, and test manifest hashes;
- the command line and environment metadata.

The final table must allow a reader to recompute every aggregate from the stored rows.

### 4. Add uncertainty and paired comparisons

Use matched forecast origins when comparing models. Report seed-aware distributions and
paired bootstrap confidence intervals for metric differences. Include:

- R6 minus each baseline for every task and horizon group;
- the number and fraction of task-level wins;
- median and interquartile range across origins/seeds;
- an effect size for the primary metric;
- a separate FX analysis, because R6 currently loses to B0 on both FX gate tasks.

Do not use an unpaired average across datasets with different units. Raw MAE and RMSE
belong in per-task tables; RMSSE is the appropriate macro-comparison metric.

### 5. Repair and rerun the efficiency profile

Regenerate the matched inference profile for all compared neural models using identical
hardware, software, batch size, sequence length, warm-up count, measured iterations,
and synchronization rules. Record:

- median and tail latency;
- samples per second computed from the same batch definition;
- peak allocated and reserved GPU memory;
- parameter count;
- PyTorch, CUDA, driver, GPU model, precision, and sequence length.

The current profile is useful as a provisional signal: R6 has 0.263 ms median latency
and 14.2 MB allocated memory, versus 0.399 ms and 26.7 MB for PatchTST and 12.120 ms
and 159.7 MB for TimesNet. Its throughput and sequence-length metadata are currently
inconsistent, so these values must not appear in the final manuscript until repaired.

### 6. Run targeted ablations on development data

To support a mechanistic discussion, evaluate on the locked development gate only:

- remove the global regime path;
- replace the persistence-change head with a direct level head;
- replace channel-specific affine maps with a shared map;
- vary the Mamba state width and depth around R6;
- compare normalization and no-normalization controls.

The untouched test set must remain reserved for the frozen final comparison. Ablations
are evidence about design choices, not additional opportunities to tune the test.

### 7. Produce the manuscript result package

Generate these tables and figures from versioned scripts and saved row-level outputs:

| Item | Content | Current source or pending source |
| --- | --- | --- |
| Table 1 | Dataset panels, variables, dates, rows, and manifest hashes | `docs/current_data.md`, `data/financial/manifests/` |
| Table 2 | Chronological split, horizons, seeds, metrics, and baselines | `configs/pms_mamba_v3.json` |
| Table 3 | Final per-task MAE, RMSE, path RMSSE, terminal RMSSE | Pending final test |
| Table 4 | Short/middle/long horizon comparison and confidence intervals | Pending final test |
| Table 5 | Latency, throughput, memory, and parameter count | Pending repaired profile |
| Table 6 | R6 component ablation | Pending development ablation |
| Figure 1 | Detailed R6 architecture | `docs/figures/pmsv5_r6_architecture_tikz_rgb.png` |
| Figure 2 | Metric versus horizon for all models and tasks | Pending final test |
| Figure 3 | Task-level R6 gaps and win counts | Pending final test |
| Figure 4 | Accuracy-efficiency frontier | Pending final test/profile |
| Figure 5 | FX and long-horizon failure analysis | Pending final test |
| Figure S1 | Architecture gallery and additional diagnostics | `docs/figures/all_model_architecture_gallery_tikz_rgb.png` |

### 8. Draft the paper in evidence order

Use `docs/manuscript_writing_brief.md` as the section scaffold and
`docs/manuscript_evidence_manifest.md` as the claim-to-artifact map. Draft Methods and
Data first, then the selection result, then the final test result. Write the Abstract
and Conclusion last.

### 9. Prepare the reproducibility release

The release should contain the source code, frozen configuration, data manifests and
hashes, environment specification for the `sci-agent`/Anaconda workflow, final model
checkpoints if redistribution is permitted, row-level predictions, metric scripts,
profile metadata, and a README that reproduces each table and figure. Keep large or
restricted raw data outside GitHub and publish download instructions plus hashes.

### 10. Pre-submission audit

Run a claim audit, figure/table regeneration check, leakage check, and manuscript build
from a clean checkout. Confirm that every number in the manuscript has a source file,
that no `FIN_SMOKE` output is included, that test data were opened only once, and that
the paper distinguishes forecast accuracy from trading profitability.

## Claims allowed at the current stage

The following statement is supported by the existing evidence:

> On the locked 2022 financial merge gate, PMSV5_R6 achieved balanced RMSSE of 6.0095,
> improving 15.00% over PMSV3_B0 and 17.90% over retuned NS-Mamba-D. It won six of
> eight tasks against B0 and all eight against the retuned NS-Mamba-D reference.

The following statements must wait for the final test and repaired profile:

- R6 is more accurate than PatchTST, TimesNet, persistence, ARIMA, or VAR-difference.
- R6 is the best long-horizon model.
- R6 is universally superior or state of the art.
- R6 is faster in training, on CPU, or in energy consumption.
- Forecast-error improvements imply trading profitability.

## Stop conditions

Pause publication drafting and resolve the issue if any final run lacks a manifest hash,
uses a changed test protocol, contains a smoke label, cannot reproduce its metric rows,
or reports profile values without hardware/software metadata. These are evidence
integrity failures, not cosmetic documentation issues.
