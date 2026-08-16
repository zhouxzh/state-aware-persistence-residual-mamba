# Computational Profile

## Recorded Inference Profiles

The following matched CUDA forward-pass profiles were recorded for the two active
S-only releases. They are performance measurements, not trained-model accuracy
results. The metadata records that the working tree was dirty at measurement time;
rerun the profile from the release commit before making a final publication claim.

### v1: Original Four-Panel Release

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

### v2: Independent-Target Expansion

| Model | Median latency (ms) | Throughput (samples/s) | Peak allocated memory (MB) | Parameters |
| --- | ---: | ---: | ---: | ---: |
| Regime-Gated Mamba | 0.2709 | 118,125 | 14.15 | 30,644 |
| Ungated Regime-Linear Mamba | 0.0590 | 542,483 | 8.24 | 11,640 |
| PatchTST | 0.3987 | 80,263 | 19.76 | 1,155,132 |
| TimesNet | 10.4823 | 3,053 | 123.47 | 11,159,101 |

Conditions are identical except for the S-only task
`financial_cross_asset_gld_s` from the independent-target roster.

On both fixed workloads, Regime-Gated Mamba has lower measured median latency,
lower allocated memory, and fewer parameters than PatchTST and TimesNet. The
ungated ablation isolates the cost of the learned gate. These observations do not
imply faster training, better energy use, portability to other hardware, or a
universal accuracy-efficiency tradeoff.

The raw table and machine metadata are tracked in:

- [matched CUDA metrics](../reproducibility/financial_s_only_v1/metrics/matched_cuda_microbenchmark.csv)
- [profile metadata](../reproducibility/financial_s_only_v1/metrics/matched_cuda_microbenchmark.json)
- [v2 matched CUDA metrics](../reproducibility/financial_s_only_v2/metrics/matched_cuda_microbenchmark.csv)
- [v2 profile metadata](../reproducibility/financial_s_only_v2/metrics/matched_cuda_microbenchmark.json)

## Required Interpretation

No learned-model accuracy matrix currently exists in v1 or v2. The profile therefore
supports only the bounded inference statement above. Any future paper statement
linking speed and accuracy must wait for the completed S-only learned matrix and must
identify this exact workload separately from end-to-end training time. Before the
release is frozen, rerun the profile on the committed source tree and retain its new
metadata alongside the final checksums.

Run the active profile with:

```bash
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v1 --stage profile
conda run --no-capture-output -n mamba python scripts/reproduce.py \
  --workflow financial-s-only --release v2 --stage profile
```
