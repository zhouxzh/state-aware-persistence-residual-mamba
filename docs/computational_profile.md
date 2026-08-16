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
target, and is kept as a data-expansion hardware reference only. Raw tables and
machine metadata are tracked in the release:

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

## Interpretation Limits

The fixed profile and campaign runtime are both bound to this GPU, batch shape,
software state, retained-artifact policy, early-stopping behavior, and the v1
series. They do not establish training-energy use, portability to other hardware,
or a universal Mamba advantage. Rerun `--stage profile` from a clean release commit
before using the microbenchmark in a submitted manuscript.
