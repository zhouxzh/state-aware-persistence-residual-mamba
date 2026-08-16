# Model Reference

## Active Proposed Model

The active proposed model is `RegimeGatedMamba`, displayed as **Regime-Gated
Mamba**. Its active recipe is the `regime_linear` branch in
[model/RegimeGatedMamba.py](../model/RegimeGatedMamba.py), not the file's optional
patch, decomposition, or multiscale branches.

![Active S-only architecture](figures/regime_gated_mamba_s_only.png)

The editable source is [regime_gated_mamba_s_only.dot](figures/regime_gated_mamba_s_only.dot);
SVG and PDF versions are beside it for manuscript preparation.

For a target window `x` of length `L` and a forecast horizon `H`, the active
branch:

1. standardizes each target window using its own temporal mean and standard
   deviation;
2. centers the standardized history on its final observation;
3. maps the centered single-channel history from `L` to `H` with a channelwise
   linear change path;
4. maps four timewise summaries through a 4-to-64 projection, one Mamba block
   (`d_state=8`), residual LayerNorm, and an `H`-output sigmoid gate;
5. multiplies the normalized change path by that horizon-wise gate, restores the
   temporal scale, and adds the final observed value as a persistence anchor.

The resulting forecast is `x_L + sigma * (g * delta_hat)`. The active proposed
configuration does not use moving-average decomposition, temporal patch encoding,
bidirectional patch Mamba, or the generic `persistence_change` head.

With exactly one target channel, the two cross-channel standard-deviation summary
features are identically zero. This is a known implementation limitation, not a
claimed nonstationarity mechanism. A temporal-statistic redesign needs a new model
identifier, pre-2023 development selection, and a separate release; it cannot be
silently folded into the verified v1 result.

## Ablation Sequence

`LastValue` is the persistence-only reference. `UngatedRegimeLinearMamba` retains
the normalization, linear change path, and persistence anchor, but fixes `g=1` and
does not instantiate the gate projection, Mamba block, normalization, or horizon
head. The full Regime-Gated Mamba is the third pre-specified point in the sequence:

```text
Last-value persistence -> Ungated linear change -> Regime-Gated Mamba
```

This makes the gate's added parameters and latency visible instead of attributing a
generic linear-persistence improvement to Mamba.

## Observed v1 Position

The completed v1 release does not support a broad accuracy-superiority claim.
Regime-Gated Mamba has a mean path-RMSSE rank of 7.42 across 24 task-horizon cells,
with two rank-1 cells. Both wins occur for the DGS10 Treasury-yield target at the
120 and 252 observation horizons. It ranks below the deterministic references and
several Mamba variants in the whole-matrix summary.

The gate lowers path RMSSE relative to the ungated ablation in 16 of 24 cells. The
paired, scale-normalized bootstrap differences favor the gate in point estimate at
each horizon, but none survive the prespecified Holm correction. The appropriate
statement is that the observed gate effect is bounded and hypothesis-generating,
not that it is established across financial series.

The model's mean end-to-end task-horizon-seed runtime is 3.09 s, compared with
3.58 s for PatchTST and 100.28 s for TimesNet. The fixed CUDA forward profile also
shows lower latency and allocated memory than those two models on the recorded
one-channel workload. These are hardware- and recipe-specific measurements; they
do not prove a universal speed or accuracy-efficiency advantage.

The trajectory examples in [evaluation_record.md](evaluation_record.md) are
consistent with a persistence-heavy forecast that can underreact to sustained
level shifts in GLD and BTCUSDT. They are illustrative, so they do not establish
that this is the causal reason for the aggregate ranks. The model's narrow long
yield result may instead reflect the DGS10 path in this fixed retrospective window.

## Comparison Roster

Both releases define 11 learned models and three deterministic references:

| ID | Display name | Role |
| --- | --- | --- |
| `RegimeGatedMamba` | Regime-Gated Mamba | Proposed model |
| `UngatedRegimeLinearMamba` | Ungated Regime-Linear Mamba | Gate ablation |
| `MultiScalePatchMamba` | Multi-Scale Patch Mamba | S-input architectural comparator |
| `InvertedMamba` | Inverted Mamba | Mamba baseline |
| `DecompositionMamba` | Decomposition Mamba | Mamba baseline |
| `MultiScaleDecompositionMamba` | Multi-Scale Decomposition Mamba | S-input architectural comparator |
| `DLinear` | DLinear | Learned baseline |
| `NLinear` | NLinear | Learned baseline |
| `PatchTST` | PatchTST | Learned baseline |
| `TimesNet` | TimesNet | Learned baseline |
| `iTransformer` | iTransformer | Learned baseline |
| `LastValue` | Last-value | Deterministic reference |
| `RandomWalkDrift` | Random-walk-with-drift | Deterministic reference |
| `ARIMA` | ARIMA | Deterministic reference |

`Multi-Scale` in a model name denotes an architecture. It does not mean that the
model was evaluated on a removed multivariate `financial_*_ms` task. Every row in
the active release manifest has `features: S`.

The source implementation identifiers remain only as `source_model_id` in each
release's `model_identity_map.json`. Public commands and documentation use the
canonical identifiers above.

## Frozen Training Recipe

The active v1 configuration sets `d_model=64`, `d_ff=128`, `d_state=8`, one layer,
MSE training loss, and balanced horizon weighting. Frozen family-level parameter
selections were made with data through 2022 and are copied into the release under
`selection_manifest.json`. Historical study names are provenance only; they do not
reactivate the removed mixed-protocol evidence.
