# Computational Profile of the Selected Model

Updated: 2026-08-09

## Matched inference result

The current profile covers eight financial tasks and five selection horizons at batch
size 32 in float32 CUDA inference. It uses 20 warm-up iterations and 100 measured
iterations for each task-horizon cell.

| Model | Cells | Median latency (ms) | Median peak allocated GPU memory (MB) |
| --- | ---: | ---: | ---: |
| PMSV5_R6 | 40 | **0.263** | **14.2** |
| PatchTST | 40 | 0.399 | 26.7 |
| TimesNet | 40 | 12.120 | 159.7 |

PatchTST's median latency is 1.52 times R6's latency, and TimesNet's is 46.10 times
R6's latency. R6 also uses 46.6% less peak allocated memory than PatchTST and 91.1%
less than TimesNet.

## What the profile supports

The result supports a bounded claim: the selected R6 implementation has lower batched
CUDA forward-pass latency and allocated memory than the two neural references under
the recorded protocol. It does not establish lower training cost, end-to-end pipeline
latency, CPU latency, energy use, or asymptotic complexity.

R6 obtains this profile with a compact 64-dimensional representation, one Mamba layer,
one global regime scan, and individual linear channel forecasts without the previous
per-channel neural gate.

## Profile metadata issue

The R6 rows in the consolidated profile have a blank `seq_len`, and their stored
`throughput_samples_per_second` values are inconsistent with batch size divided by the
reported latency. Those throughput values must not be cited. Before manuscript
submission, regenerate the profile from one script so model name, sequence length,
iterations, latency, throughput, memory, hardware, and software versions are recorded
uniformly for all three models.

The directly measured latency and memory columns are retained as current engineering
evidence, but the speed table should be regenerated for the final paper.

## Evidence boundary

Current profile: `results/nonstationary_analysis_v5/profile/matched_inference_profile.csv`.
Older operational profiling figures under `docs/figures/` use a different model and
workflow and should not be used for the R6 runtime claim.
