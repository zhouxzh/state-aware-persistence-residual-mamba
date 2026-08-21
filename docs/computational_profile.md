# Computational Profile

## Fixed CUDA Forward Profile

The following matched CUDA forward-pass profile is recorded for the v1 S-only
release. It is a model-forward workload, not an end-to-end training measurement or
an accuracy result.

| Model | Median latency (ms) | Throughput (samples/s) | Peak allocated memory (MB) | Parameters |
| --- | ---: | ---: | ---: | ---: |
| Regime-Gated Mamba | 0.2658 | 120,375 | 14.15 | 30,644 |
| Ungated Regime-Linear Mamba | 0.0583 | 548,486 | 8.24 | 11,640 |
| PatchTST | 0.3913 | 81,774 | 19.76 | 1,155,132 |
| TimesNet | 10.3980 | 3,078 | 122.73 | 11,159,101 |

Conditions: `financial_cross_asset_s`, one target channel, input length 96,
horizon 60, batch size 32, float32, 10 warm-up iterations, three repeats of 30
timed iterations, PyTorch 2.8.0 with CUDA 12.8, `mamba-ssm` 2.3.1, and an NVIDIA
GeForce RTX 5090 D.

The recorded v2 profile uses the same workload except for the independent GLD
target. It is a completed release-specific measurement, not a pooled comparison
with v1:

| Model | Median latency (ms) | Throughput (samples/s) | Peak allocated memory (MB) | Parameters |
| --- | ---: | ---: | ---: | ---: |
| Regime-Gated Mamba | 0.2665 | 120,086 | 14.15 | 30,644 |
| Ungated Regime-Linear Mamba | 0.0588 | 544,440 | 8.24 | 11,640 |
| PatchTST | 0.3838 | 83,386 | 19.76 | 1,155,132 |
| TimesNet | 10.6316 | 3,010 | 122.65 | 11,159,101 |

Raw tables and machine metadata are tracked in the releases:

- [v1 matched CUDA metrics](../reproducibility/financial_s_only_v1/metrics/matched_cuda_microbenchmark.csv)
- [v1 profile metadata](../reproducibility/financial_s_only_v1/metrics/matched_cuda_microbenchmark.json)
- [v2 matched CUDA metrics](../reproducibility/financial_s_only_v2/metrics/matched_cuda_microbenchmark.csv)
- [v2 profile metadata](../reproducibility/financial_s_only_v2/metrics/matched_cuda_microbenchmark.json)

## Observed Campaign Runtime

The completed v1 matrix provides a separate end-to-end runtime observation. Each
learned task-horizon-seed unit includes training and evaluation time:

| Model | Mean seconds per bundle | Mean path-RMSSE rank across 24 cells |
| --- | ---: | ---: |
| Regime-Gated Mamba | 3.09 | 7.42 |
| Ungated Regime-Linear Mamba | 1.13 | 7.71 |
| PatchTST | 3.58 | 10.54 |
| TimesNet | 100.28 | 12.21 |
| NLinear | 0.64 | 6.88 |
| DLinear | 0.82 | 10.50 |

Regime-Gated Mamba is 13.7% faster than PatchTST and 96.9% faster than TimesNet
under this measured workflow. The proposed model is not the overall accuracy
leader, so this is an observed speed-position tradeoff rather than a combined
accuracy-and-efficiency victory. The full learned-model scatter is in
[financial_s_only_v1_accuracy_efficiency.png](figures/financial_s_only_v1_accuracy_efficiency.png).

The completed v2 matrix provides a second, separate end-to-end observation over
18 independent target files and 108 target-horizon cells:

| Model | Mean seconds per bundle | Mean path-RMSSE rank across 108 cells |
| --- | ---: | ---: |
| Regime-Gated Mamba | 6.74 | 6.25 |
| Ungated Regime-Linear Mamba | 2.54 | 6.82 |
| PatchTST | 7.67 | 10.15 |
| TimesNet | 231.16 | 12.33 |
| iTransformer | 12.44 | 12.00 |

Regime-Gated Mamba is 12.2% faster than PatchTST and 97.1% faster than TimesNet
under the v2 campaign recipe. It is again a speed-position tradeoff, not proof of
overall accuracy superiority. The corresponding scatter is in
[financial_s_only_v2_accuracy_efficiency.png](figures/financial_s_only_v2_accuracy_efficiency.png).
The normalized metric and seed-stability tables used alongside this runtime
comparison are in [the V2 analysis bundle](analysis/financial_s_only_v2/README.md).

## Interpretation Limits

The fixed profiles and campaign runtimes are bound to this GPU, batch shape,
software state, retained-artifact policy, early-stopping behavior, and their
respective release target rosters. They do not establish training-energy use,
portability to other hardware, or a universal Mamba advantage. Rerun
`--stage profile` from a clean release commit before using either microbenchmark
in a submitted manuscript.
