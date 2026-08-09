# Current Model Results

Updated: 2026-08-09

## Result in one sentence

`PMSV5_R6` is the selected PMS-Mamba model because it passed the locked 2022 financial
merge gate with mean balanced RMSSE 6.0095. A matched CUDA profile provides a
provisional forward-pass latency and memory advantage, but its metadata must be
repaired; final accuracy against PatchTST and TimesNet on the untouched 2023-2026
financial period has not yet been measured.

For manuscript reuse, see the [publication plan](publication_plan.md),
[manuscript writing brief](manuscript_writing_brief.md), and
[evidence manifest](manuscript_evidence_manifest.md).

## Which result is current?

| Evidence layer | PMS model | Evaluation period | Scientific use |
| --- | --- | --- | --- |
| Development | R6, R5, C3 | 2021 | Architecture selection only |
| Merge gate | PMSV5_R6 | 2022 | Current promotion evidence |
| Historical common suite | Earlier PMS_Mamba-PD | Previously evaluated frozen test | Baseline context only |
| Final financial test | PMSV5_R6 | 2023-2026 | Not yet opened |

## Merge-gate accuracy

The gate contains eight tasks, five selection horizons, five seeds, and three models,
for 600 completed metric rows. Lower RMSSE is better.

| Model | Short RMSSE | Medium RMSSE | Long RMSSE | Balanced RMSSE |
| --- | ---: | ---: | ---: | ---: |
| PMSV5_R6 | **1.5993** | **5.3724** | **11.0567** | **6.0095** |
| PMSV3_B0 | 1.8890 | 6.1731 | 13.1483 | 7.0701 |
| Retuned NS-Mamba-D | 1.9208 | 6.5225 | 13.5159 | 7.3197 |

Relative to B0, R6 improves balanced RMSSE by 15.00%. Relative to retuned NS-Mamba-D,
the improvement is 17.90%. R6 improves all three gate horizon groups against both
references. The gate's long group contains horizon 120 only, not 252.

## Task-level result

| Task | R6 | B0 | Retuned NS-D | R6 position |
| --- | ---: | ---: | ---: | --- |
| Cross-asset MS | **5.4958** | 6.2245 | 6.2293 | Best |
| Cross-asset S | **5.5327** | 6.1924 | 6.2290 | Best |
| Cryptoasset MS | **5.5152** | 8.8209 | 9.4265 | Best |
| Cryptoasset S | **5.8704** | 9.3165 | 8.9998 | Best |
| FX MS | 5.1721 | **4.7027** | 5.6307 | Second; B0 is better |
| FX S | 4.9429 | **4.7196** | 5.4109 | Second; B0 is better |
| Yields MS | **7.7785** | 8.2933 | 8.2467 | Best |
| Yields S | **7.7684** | 8.2911 | 8.3850 | Best |

R6 wins six of eight tasks against B0 and all eight against NS-Mamba-D. Its unresolved
weakness is foreign exchange, where the simpler B0 configuration remains stronger.

## Broader baseline context

The historical common metric suite evaluates an earlier PMS-Mamba configuration over
48 task-horizon cells. It does not evaluate R6 and cannot answer whether R6 is more
accurate than PatchTST or TimesNet.

| Model | Mean path MAE | Mean path RMSE | Mean path RMSSE | Mean RMSSE rank |
| --- | ---: | ---: | ---: | ---: |
| Random-walk drift | 1,602.61 | 2,242.91 | **12.6767** | **3.02** |
| Earlier PMS_Mamba-PD | 1,673.41 | 2,300.09 | 12.9669 | 6.63 |
| Last-value | 1,629.22 | 2,253.62 | 13.0323 | 3.19 |
| Retuned NS-Mamba-D | 1,646.36 | 2,273.29 | 13.0514 | 5.96 |
| PatchTST | 1,809.37 | 2,434.28 | 13.5955 | 9.35 |
| TimesNet | 2,366.12 | 3,133.72 | 16.3875 | 10.92 |

The earlier PMS model has a better aggregate path RMSSE than PatchTST and TimesNet but
zero individual path-RMSSE cell wins. Random-walk drift has the strongest aggregate
RMSSE in this subset. The paper must therefore report both aggregate performance and
cell-level ranks rather than claim broad dominance from one mean.

The existing all-model horizon figures under `docs/figures/` belong to this historical
suite. They are useful for diagnosing persistence, dataset, and horizon effects, but
they are not figures of R6.

## Metric interpretation

MAE and RMSE remain in the target's units. RMSSE is scale-normalized within each task.
Balanced RMSSE gives equal weight to short, medium, and long horizon groups. Path
metrics evaluate the full forecast trajectory; terminal metrics evaluate only the last
forecasted step. The final paper should name one primary metric and report the others
as complementary outcomes.

## Current conclusion

R6 is convincingly better than the two Mamba references on the selection gate and is
particularly strong on crypto. It is not the best configuration for FX. Its accuracy
against PatchTST, TimesNet, statistical baselines, and horizon 252 under the final
financial protocol remains an open empirical question.

Evidence: `results/nonstationary_analysis_v5/gate/`,
`results/nonstationary_metric_suite/`, and `configs/pms_mamba_v3.json`.
