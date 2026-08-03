# Current Nonstationary Forecasting Results

Updated: 2026-08-03

## Direct conclusion

PMS-Mamba is a competitive but not dominant forecasting model. Its strongest evidence
is on the cross-asset tasks and at middle horizons. It is stable across training seeds,
but it does not beat the strongest naive, statistical, or learned comparator in any of
the 48 primary task-horizon path-RMSSE cells.

The paper must therefore present PMS-Mamba as a bounded mixed result, not as a new
state-of-the-art winner.

## Evidence boundary

The immutable V1 final analysis covers the protected 2023-01-01 through 2026-06-30
period and contains:

- 4 financial reference panels and 8 target-only/multivariate tasks;
- 9 learned models, up to 4 deterministic statistical or naive references, and 6
  horizons: 1, 5, 20, 60, 120, and 252;
- 360 learned model-task-seed cells and 2,160 learned horizon records;
- path and terminal MAE, MSE, RMSE, and RMSSE; five-seed variation; runtime;
  regime summaries; and 10,000-replicate moving-block bootstrap contrasts with Holm
  correction.

V2 is a separate validation-only optimization study. It did not reopen the protected
test targets and must not be described as confirmatory test performance.

## PMS-Mamba overall performance

| Quantity | PMS-Mamba result | Interpretation |
| --- | ---: | --- |
| Mean path RMSSE across 48 cells | 12.967 | Descriptive pooled value only |
| Median path RMSSE | 6.023 | Descriptive pooled value only |
| Average cell rank | 6.625 | Middle of the full comparison set |
| Path-RMSSE wins | 0/48 | No primary cell win |
| Path-RMSSE top-three cells | 3/48 | Concentrated at middle horizons |
| Terminal-RMSSE wins | 1/48 | One terminal-lead win does not change the primary result |
| Positive skill versus Last-value | 8/48 | Persistence remains difficult to beat |
| Median seed coefficient of variation | 0.76% | Training is comparatively stable |
| Maximum seed coefficient of variation | 7.58% | No pervasive seed-instability failure |

The pooled mean path RMSSE of 12.967 is the second-lowest descriptive mean among
models evaluated in all 48 cells, behind Random-walk-drift at 12.677. This is not a
valid "second place" claim: pooling mixes heterogeneous tasks and horizons, whereas
the prespecified primary comparison is the winner within each task-horizon cell.

PMS-Mamba obtained no path MAE, MSE, RMSE, or RMSSE cell wins. It obtained one
terminal-metric win. Naive or statistical references won 38/48 path-RMSSE cells and
non-Mamba learned models won 10/48; all Mamba variants together won 0/48.

## Performance by task

Balanced path RMSSE is the unweighted mean of short-, middle-, and long-term mean
path RMSSE within a task. Lower is better.

| Task | PMS-Mamba | Winner | Winner score | PMS rank | Gap |
| --- | ---: | --- | ---: | ---: | ---: |
| Cross-asset MS | 17.254 | PatchTST | 15.744 | 2/13 | 9.59% |
| Cross-asset S | 17.255 | PatchTST | 15.698 | 2/12 | 9.92% |
| Crypto MS | 26.788 | ARIMA | 26.215 | 7/13 | 2.18% |
| Crypto S | 27.053 | ARIMA | 26.215 | 8/12 | 3.20% |
| FX MS | 2.985 | Last-value | 2.625 | 7/13 | 13.72% |
| FX S | 2.997 | Last-value | 2.625 | 8/12 | 14.16% |
| Yields MS | 4.695 | Last-value | 4.315 | 5/13 | 8.82% |
| Yields S | 4.707 | Last-value | 4.315 | 6/12 | 9.10% |

Cross-asset is PMS-Mamba's clearest task-level strength. Crypto is numerically close
to the winner but ranks behind several simple references. FX is the weakest task family
because Last-value remains substantially better. Yields is intermediate, but the same
persistence problem remains.

![PMS-Mamba task and horizon performance](figures/pms_mamba_performance_summary.png)

Figure 1. Panel A reports the percentage gap between PMS-Mamba and each task's balanced
path-RMSSE winner. Panel B reports the mean gap to the winner over the 16 cells in each
horizon group. These are descriptive five-seed test means; no uncertainty interval is
shown. Underlying values and provenance are in `docs/figures/`.

## Performance by horizon

| Horizon group | Cells | Mean gap to winner | Median gap | Within 5% | Top three |
| --- | ---: | ---: | ---: | ---: | ---: |
| Short: 1, 5 | 16 | 9.34% | 7.72% | 4/16 | 0/16 |
| Middle: 20, 60 | 16 | 4.49% | 3.36% | 14/16 | 3/16 |
| Long: 120, 252 | 16 | 14.69% | 12.82% | 4/16 | 0/16 |

The middle horizon is the model's strongest region. The short-horizon problem is
competition from persistence and low-order statistical models. The long-horizon
problem is larger in magnitude: error accumulation and insufficient long-range trend
control produce the largest average gap.

## Pairwise and multivariate evidence

Against S-Mamba, PMS-Mamba has 9 significantly favorable cells, 13 significantly
unfavorable cells, and 26 cells without a Holm-adjusted significant difference.
Against the validation-selected non-Mamba learned comparator, the counts are 15
favorable, 6 unfavorable, and 27 not significant.

These paired results show that PMS-Mamba adds value in some cells, but they do not
overturn the full-comparator winner matrix because naive and statistical references
remain part of the benchmark.

Multivariate input lowers PMS-Mamba RMSSE in 14/24 matched S/MS family-horizon pairs,
with a mean MS-minus-S RMSSE of -0.073. The effect is modest and inconsistent; the
current evidence does not justify a general claim that additional covariates always
help.

![V1 task-horizon winners](../reproducibility/nonstationary_analysis_v1/final/task_horizon_winners.png)

Figure 2. Lowest five-seed mean path RMSSE in each V1 task-horizon cell. The absence of
a Mamba label is the central negative result: naive/statistical models win 38 cells and
non-Mamba learned models win 10.

## V2 validation-only optimization

V2 screened 8 configurations over 8 tasks, 3 seeds, and 6 horizons, producing 1,152
complete validation records. F01 and F03 were then compared with the current F04
configuration over five seeds, producing 720 complete records.

| Candidate | Overall improvement vs F04 | Short | Middle | Long | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| F01 | 1.79% | 7.06% | 2.04% | 0.84% | Below 2% threshold |
| F03 | 1.68% | 7.29% | 1.92% | 0.70% | Below 2% threshold |

F01's descriptive 95% paired task-seed bootstrap interval for overall improvement was
1.51% to 2.02%; F03's was 1.20% to 2.13%. Selection used the prespecified point-estimate
rule, not whether an interval crossed 2%. Neither finalist achieved at least 2% lower
mean balanced RMSSE, so F04 was retained and no new locked-test run was opened.

| Screen factor, high minus low | Effect on balanced RMSSE | Direction |
| --- | ---: | --- |
| Residual target minus direct level | -1.77% | Favorable |
| Scale MSE minus MSE | +6.11% | Unfavorable |
| Gate minus mean fusion | +0.52% | Slightly unfavorable |
| Late-step minus uniform weighting | +0.21% | Slightly unfavorable |

The V2 fractional design aliases main effects with three-factor interactions, so these
factor effects are diagnostic rather than confirmatory. The reliable design signal is
to continue investigating residual anchoring; the current `SCALE_MSE`, gate, and
late-step weighting should not be promoted unchanged.

![V2 validation effects](../reproducibility/nonstationary_analysis_v2/analysis/pms_v2_validation_effects.png)

Figure 3. Panel A shows descriptive high-minus-low screen effects with paired bootstrap
intervals. Panel B shows five-seed task-level improvements of F01 and F03 over F04.
This is validation-only evidence.

## Current scientific interpretation

1. PMS-Mamba is competitive among learned models but not superior to the complete
   baseline set.
2. Patch multi-scale modeling appears most useful when cross-variable structure matters,
   particularly in cross-asset tasks.
3. Middle horizons are the strongest operating range.
4. Short horizons require an explicit persistence-aware design.
5. Long horizons require better control of cumulative change and regime-dependent trend.
6. Residual anchoring is the only favorable V2 factor worth carrying forward directly.

## Evidence links

- V1 final report: `reproducibility/nonstationary_analysis_v1/final/REPORT.md`
- V1 aggregate metrics: `reproducibility/nonstationary_analysis_v1/final/aggregate_metrics.csv`
- V1 bootstrap contrasts: `reproducibility/nonstationary_analysis_v1/final/bootstrap_contrasts.csv`
- V2 analysis report: `reproducibility/nonstationary_analysis_v2/analysis/REPORT.md`
- V2 frozen selection: `reproducibility/nonstationary_analysis_v2/selection/selection_manifest.json`
- Documentation figure manifest: `docs/figures/pms_mamba_performance_summary.manifest.json`

