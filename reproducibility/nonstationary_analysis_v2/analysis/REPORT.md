# PMS-Mamba V2 validation analysis

This report is validation-only. The protected test targets were not read for screening,
confirmation, selection, or this analysis.

## Decision

The frozen decision is `baseline_retained` with `PMSV2_F04` selected.
Neither finalist met the predeclared requirement of at least 2% lower mean balanced RMSSE,
although neither violated the 5% term-level degradation guardrail.

| Candidate | Improvement vs F04 | 95% paired bootstrap interval | Better task-seed runs |
| --- | ---: | ---: | ---: |
| PMSV2_F01 | 1.79% | [1.51%, 2.02%] | 38/40 |
| PMSV2_F03 | 1.68% | [1.20%, 2.13%] | 28/40 |

The intervals are descriptive 95% percentile intervals from 10,000 paired task-seed
bootstrap resamples; the unit of replication is one task-seed validation summary (n=40).
No confirmatory p-values are claimed for this exploratory V2 analysis.

## Factor diagnosis

Factor effects are high minus low levels in the resolution-IV screen. Negative values
indicate lower (better) balanced RMSSE at the high level. Main effects remain aliased with
three-factor interactions under the D=ABC fractional design.

| Factor | High vs low effect | 95% paired bootstrap interval |
| --- | ---: | ---: |
| Forecast target | -1.77% | [-2.76%, -0.89%] |
| Training loss | 6.11% | [1.99%, 10.96%] |
| Multi-scale fusion | 0.52% | [-0.01%, 1.04%] |
| Step weighting | 0.21% | [0.05%, 0.37%] |

The dominant useful direction is residual anchoring. Scale-normalized MSE is unfavorable
in this screen, while gated fusion and late-step weighting show smaller average effects.
The next optimization cycle should therefore keep residual anchoring fixed and investigate
long-horizon capacity or regime conditioning with a new, separately frozen validation protocol.

## Figure description

Panel A shows the four high-minus-low screening effects on balanced RMSSE with descriptive
95% paired bootstrap intervals. Panel B shows task-level validation improvement over F04
for F01 and F03; points to the right of zero favor the candidate. The task table below the
figure is available in `confirmation_task_summary.csv`.

## Evidence files

- `screen_factor_effects.csv`: factor estimates for balanced, short, middle, and long RMSSE.
- `confirmation_paired_summary.csv`: five-seed paired candidate comparisons.
- `confirmation_task_summary.csv`: task-level candidate and F04 summaries.
- `pms_v2_validation_effects.pdf` and `.png`: provisional general manuscript figure.
- `analysis_manifest.json`: source hashes, transformations, bootstrap settings, and figure metadata.
