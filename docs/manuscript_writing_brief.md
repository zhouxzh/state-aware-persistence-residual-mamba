# Manuscript Writing Brief

Updated: 2026-08-09

This document is the reusable writing scaffold for the PMS-Mamba paper. It is written
so that paragraphs, tables, and figure captions can be transferred into a manuscript
without mixing development evidence with the unopened final test. Replace every
`[FINAL ...]` placeholder only after the final protocol has been executed.

## Working title and one-sentence thesis

**Working title:** *PMS-Mamba: Efficient Regime-Aware Forecasting for Nonstationary
Financial Time Series*

**Thesis currently supported:** PMSV5_R6 is a compact regime-aware Mamba forecaster
whose persistence-change head improves the locked 2022 merge-gate score over the two
Mamba selection references while showing a provisional matched CUDA inference-efficiency
signal against PatchTST and TimesNet.

The word "provisional" must be removed only after the profile metadata is repaired and
the final comparison is regenerated.

## Abstract scaffold

Nonstationary financial series exhibit changing scale, cross-channel dependence, and
forecast horizons with very different error behavior. We introduce PMS-Mamba, a
compact regime-aware forecaster that summarizes cross-channel level and change signals
with a Mamba block and predicts channel-specific changes around the last observation.
We evaluate four financial panels using a chronological, leakage-controlled protocol,
scale-normalized path RMSSE, and horizon-resolved error analysis. On the locked 2022
merge gate, PMSV5_R6 obtains balanced RMSSE **6.0095**, improving **15.00%** over
PMSV3_B0 and **17.90%** over retuned NS-Mamba-D. The untouched 2023-2026 comparison
against the full baseline set is **[FINAL TEST RESULT]**. Under a matched float32 CUDA
forward-pass profile, R6 records **0.263 ms** median latency and **14.2 MB** allocated
memory, but the profile metadata requires repair before these values are final. These
results position PMS-Mamba as an efficiency-oriented approach whose final accuracy
claim depends on the preregistered financial test comparison.

## Introduction: argument order

1. Define the forecasting problem as nonstationary financial prediction, not generic
   benchmark chasing.
2. Explain why level persistence, changing volatility, cross-asset dependence, and
   horizon-specific degradation make a single static representation insufficient.
3. Motivate Mamba as a computationally compact temporal mechanism, while stating that
   the paper tests accuracy and efficiency jointly.
4. State the gap: existing comparisons often mix horizons, metrics, or data splits.
5. State the contributions with bounded verbs: "introduce," "evaluate," and
   "characterize," rather than "prove" or "guarantee."

## Contributions paragraph (draft)

This study makes four contributions. First, it introduces a compact PMS-Mamba design
that combines a global regime representation with channel-specific persistence-change
maps. Second, it defines a chronological evaluation protocol over cross-asset,
cryptocurrency, FX, and Treasury-yield panels, with training, validation, and test
periods kept separate. Third, it reports path RMSSE together with raw-unit and
horizon-specific diagnostics so that short- and long-horizon behavior are not hidden
by one aggregate. Fourth, it evaluates the accuracy-efficiency trade-off against
Mamba, transformer, temporal, linear, and statistical references. The fourth
contribution is complete only when the final test and repaired runtime profile are
available.

## Methods content checklist

### Model

Use Figure 1 and `docs/model_architecture_and_metrics.md` for the architecture text.
The exact R6 contract is `X: B x L x C -> Y_hat: B x H x C`, with per-window
normalization, four global regime features, one Mamba block (`d_model=64`, `d_state=8`,
`d_conv=2`, `expand=1`), a horizon gate, channel-specific affine change maps, and a
last-value persistence anchor. Cite `model/PMS_Mamba.py::_regime_linear_forecast` and
`configs/pms_mamba_v3.json` in the reproducibility statement.

### Data

Use `docs/current_data.md` and the manifests under `data/financial/manifests/`. Report
dataset identity, channels, date range, retained rows, missing-value policy, and hash.
Do not call the study "financial results" as a generic label; call it "nonstationary
financial forecasting using four financial panels."

The four panels provide adequate chronological coverage for the proposed benchmark,
but the eight `S`/`MS` tasks are views of four underlying target series rather than
eight independent markets. State this limitation and avoid extrapolating the results
to all financial assets.

### Protocol

State the train-through-2022-12-31 boundary, the untouched 2023-01-01 to 2026-06-30
test period, horizons 1/5/20/60/120/252, promotion seeds 2023-2027, and the full
baseline list. Explain that R6 was selected on the locked 2022 merge gate and that
horizon 252 is excluded from that gate because one validation year does not provide
enough complete observations.

### Metrics

Use path RMSSE as the primary scale-free measure. Report MAE and RMSE per task/channel
in native units, MSE as the optimization diagnostic, MAPE/MSPE only with a near-zero
caveat, and terminal RMSSE for the final step. Define balanced RMSSE as the equal mean
of short, middle, and long path-RMSSE groups. Never average raw MAE/RMSE across
heterogeneous financial targets as if their units were comparable.

## Results text that is ready now

On the locked 2022 merge gate, PMSV5_R6 achieved balanced RMSSE **6.0095**, compared
with **7.0701** for PMSV3_B0 and **7.3197** for retuned NS-Mamba-D. The corresponding
relative improvements were **15.00%** and **17.90%**. R6 was better on six of eight
tasks versus B0 and on all eight tasks versus retuned NS-Mamba-D; B0 remained better on
both FX tasks. R6 improved the short, middle, and long gate groups against both Mamba
references. These are merge-gate selection results, not final test results.

The historical common metric suite evaluated an earlier PMS-Mamba-PD configuration.
It therefore provides context for model families but must not be used as an R6
comparison against PatchTST or TimesNet. The final per-task and per-horizon table is
**[FINAL TABLE 3]**.

## Results that must remain placeholders

- R6 versus PatchTST and TimesNet on 2023-2026: **[FINAL TEST TABLE]**
- Horizon 252 and long-horizon ranking: **[FINAL H252 ANALYSIS]**
- Paired confidence intervals and effect sizes: **[FINAL UNCERTAINTY]**
- Repaired latency, throughput, memory, and parameter count: **[FINAL PROFILE TABLE]**
- Component ablation: **[FINAL ABLATION TABLE]**

## Figures and tables for the manuscript

| ID | Planned item | Evidence source |
| --- | --- | --- |
| Fig. 1 | Detailed PMSV5_R6 architecture | `docs/figures/pmsv5_r6_architecture_tikz_rgb.png` |
| Fig. 2 | Metric versus horizon, all models and tasks | Generate from final row-level predictions |
| Fig. 3 | R6 gaps, task wins, and FX contrast | Generate from final paired metrics |
| Fig. 4 | Accuracy-efficiency frontier | Final metrics plus repaired profile |
| Fig. 5 | Long-horizon and failure-case analysis | Final per-origin forecasts |
| Fig. S1 | Architecture gallery | `docs/figures/all_model_architecture_gallery_tikz_rgb.png` |
| Table 1 | Dataset and split audit | `docs/current_data.md` and manifests |
| Table 2 | Protocol and baseline definitions | `configs/pms_mamba_v3.json` |
| Table 3 | Final MAE, RMSE, path RMSSE, terminal RMSSE | Final test output |
| Table 4 | Horizon-band scores and uncertainty | Final test output |
| Table 5 | Runtime, memory, throughput, parameters | Repaired profile |
| Table 6 | R6 ablation | Development-gate ablation output |

## Discussion prompts

Discuss R6's current pattern as a hypothesis, not a causal conclusion: the global
regime gate and persistence-change formulation may help cross-asset, crypto, and yield
panels, while FX remains a stress case where B0 is better on both gate tasks. The
profile suggests lower batched forward-pass cost, but it does not establish lower
training cost, CPU cost, energy use, or deployment cost. Explain that long-horizon
performance must be evaluated explicitly rather than inferred from the 2022 gate.

## Limitations to state explicitly

- The R6 accuracy comparison with PatchTST and TimesNet on the untouched test is still
  pending.
- The current profile has inconsistent throughput metadata and a blank R6 sequence
  length.
- The historical common suite used an earlier PMS-Mamba configuration.
- Financial datasets are heterogeneous; raw-unit metrics are not directly comparable
  across panels.
- Forecast error does not measure trading profitability or economic utility.

## Reproducibility paragraph (draft)

All model, protocol, and metric definitions are versioned in the repository. The
frozen R6 recipe is in `configs/pms_mamba_v3.json`; the implementation is in
`model/PMS_Mamba.py`; data manifests and hashes are under
`data/financial/manifests/`; and the gate aggregates are under
`results/nonstationary_analysis_v5/gate/`. The release will add row-level final
predictions, environment metadata, repaired profile records, and SHA-256 checksums.
Large or restricted raw datasets should be distributed through documented download
instructions rather than committed to GitHub.
