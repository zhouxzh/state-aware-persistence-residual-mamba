# Paper Writing Direction

Updated: 2026-08-04

## Recommended positioning

The strongest defensible paper is an evaluation-and-method paper about forecasting
under nonstationarity, not a state-of-the-art victory paper. Its central contribution
is the combination of:

1. a patchwise, decomposition-aware, multi-scale Mamba design;
2. a strict comparison against persistence, statistical, linear, Transformer, and
   Mamba references;
3. a complete negative/mixed result showing where the architecture helps and where
   simple baselines remain stronger;
4. a validation-only follow-up that identifies residual anchoring as a useful direction
   without changing the frozen final conclusion.

Financial series should be described as reference panels that expose stochastic trends,
structural shifts, changing scale, volatility, and cross-market dependence. The title,
abstract, and conclusion must not imply that the method has been validated across all
nonstationary domains.

The positive result must be stated comparatively, not as a generic claim that the model
"performs well." PMS-Mamba has a broad descriptive accuracy advantage over TimesNet,
iTransformer, DLinear, and PatchTST, a stability advantage over every non-Mamba learned
model, and a long-horizon advantage over NLinear. These findings coexist with no primary
cell wins and a persistent deficit against naive/statistical references. That contrast
is the paper's central empirical result.

## Recommended title

Current evidence supports:

> Evaluating Patch Multi-Scale Mamba for Forecasting Under Nonstationarity: Evidence
> from Financial Reference Panels

Other defensible alternatives are:

- PMS-Mamba for Nonstationary Time-Series Forecasting: A Multi-Horizon Benchmark Study
- Patchwise Multi-Scale State-Space Forecasting Under Nonstationarity

Avoid titles containing "state of the art", "superior", "universal", or "long-term
solution". A title centered on residual anchoring should be used only after a future
residual model passes a frozen external evaluation.

## Research questions

1. How competitive is PMS-Mamba against the complete comparator set under a frozen
   nonstationary forecasting protocol?
2. How does performance change across dataset family, input mode, and forecast horizon?
3. Does multivariate input provide consistent benefit over target-only input?
4. Which architectural factors provide validation evidence for the next model version?

## Evidence hierarchy

| Evidence | Role in paper | Allowed interpretation |
| --- | --- | --- |
| V1 frozen 2023-2026 test matrix | Confirmatory result | Final comparison for current panels |
| V1 moving-block bootstrap + Holm | Confirmatory paired contrasts | Cell-specific evidence with multiplicity control |
| V1 S/MS and regime summaries | Prespecified secondary analysis | Bounded mechanism diagnostics |
| V2 screen and five-seed confirmation | Exploratory validation ablation | Optimization direction only |
| Future V3 | Prospective work | No current-result claim |

Do not mix V2 validation numbers into V1 test rankings. Do not describe V2 bootstrap
intervals as confirmatory p-values.

## Main story

### Observation

- PMS-Mamba has a low pooled mean path RMSSE, but no primary task-horizon win.
- By average task-horizon position it ranks 7/12 among full-coverage models and 4/9
  among learned models for RMSE/RMSSE.
- Naive/statistical references win 38/48 cells and non-Mamba learned models win 10/48.
- PMS-Mamba ranks second on both cross-asset tasks and is closest to winners at middle
  horizons.
- PMS-Mamba has lower descriptive five-seed mean RMSE than PatchTST in 42/48 cells,
  DLinear in 36/48, TimesNet in 43/48, and iTransformer in 44/48, but is lower than
  Last-value in only 8/48, ARIMA in 14/48, and Random-walk-drift in 2/48.
- FX exposes the failure to beat persistence. The largest long-horizon failures are
  cross-asset 252 and yields 120/252; crypto becomes comparatively close at long horizons.
- The advantage over TimesNet, iTransformer, DLinear, and PatchTST appears in short,
  middle, and long groups rather than in only one selected horizon.
- The comparison with NLinear reverses by horizon: PMS wins 2/16 short cells but 14/16
  long cells, with median signed RMSE differences of +5.36% and -4.83%, respectively.
- PMS has the third-lowest median seed CV among learned models (0.76%) but the
  third-highest peak memory and the second-slowest median runtime.
- V2 residual anchoring improves validation performance, especially at short horizons,
  but the finalists do not pass the frozen replacement rule.

### Interpretation

The result suggests that temporal patching and multi-scale state-space modeling are
useful in some cross-variable settings but do not by themselves solve persistence or
long-horizon cumulative-change forecasting. Strong naive references are part of the
scientific finding, not an obstacle to hide.

### Implication

Future model work should explicitly separate persistence from change and evaluate new
architectures on a new prospective period or external dataset set. The current paper's
conclusion remains bounded to the completed panels and protocol.

## Claims that are supported

- "PMS-Mamba is competitive among the evaluated learned models."
- "PMS-Mamba's descriptive pooled mean path RMSSE is 12.967, but it wins 0/48 primary
  task-horizon cells."
- "PMS-Mamba ranks 7/12 among full-coverage models and 4/9 among learned models by
  average RMSE/RMSSE cell rank."
- "The model ranks second on both cross-asset task summaries."
- "Middle horizons are within 5% of the cell winner in 14/16 cases."
- "PMS-Mamba has lower mean RMSE than TimesNet, iTransformer, DLinear, and PatchTST in
  43/48, 44/48, 36/48, and 42/48 cells, respectively."
- "PMS-Mamba beats NLinear in 14/16 long-horizon cells but only 2/16 short-horizon
  cells, demonstrating a horizon-dependent reversal rather than uniform superiority."
- "PMS-Mamba has the third-lowest median seed CV of the nine learned models, while its
  runtime and memory do not support a general efficiency claim."
- "PMS-Mamba has 75.48% lower median runtime and 72.21% lower median peak allocated GPU
  memory than TimesNet under the executed configurations."
- "PMS-Mamba is 6.04 times slower than PatchTST by median train/evaluation runtime, so
  the current operational profile does not establish a general Mamba efficiency advantage."
- "PMS-Mamba is the only evaluated Mamba variant with lower mean RMSSE in MS than S
  mode, but the reduction is small and occurs in 14/24 matched pairs."
- "PMS-Mamba has lower descriptive mean RMSE than PatchTST in 42/48 cells but loses
  the two cross-asset task-balanced summaries, showing that win counts and effect
  location differ."
- "Naive or statistical references win 38/48 primary cells."
- "Residual anchoring is the strongest favorable factor in the exploratory V2 screen."
- "Neither V2 finalist meets the prespecified 2% replacement threshold."

Every numeric version of these claims should cite the corresponding frozen table or
claim-evidence sidecar.

## Claims that are not supported

- PMS-Mamba is the overall best or state-of-the-art model.
- Mamba models outperform classical methods on these datasets.
- Multivariate inputs consistently improve forecasting.
- The model solves long-horizon nonstationarity.
- Validation-only V2 configurations improve final test performance.
- Forecast accuracy implies trading profit, market efficiency, or causal knowledge.
- Current financial reference panels establish cross-domain generalization.
- PMS-Mamba is faster than PatchTST, iTransformer, or Transformer models generally.
- The current end-to-end run timings prove Mamba's asymptotic linear complexity advantage.

## Proposed paper structure

### 1. Introduction

- Define the forecasting problem as changing level, scale, dependence, and regime.
- Explain why persistence is a difficult and scientifically necessary comparator.
- Motivate temporal patching, decomposition, and multi-scale processing without claiming
  they are already superior.
- State the four research questions and the bounded contribution.

### 2. Related work

- State-space/Mamba forecasting;
- patch-based long-horizon forecasting;
- normalization and decomposition under distribution shift;
- statistical and naive forecasting under stochastic trends.

References are not yet curated in this repository. Do not add citations from memory;
verify every bibliographic record and claim in the manuscript repository.

### 3. Method

- PMS-Mamba architecture and tensor shapes;
- reversible window normalization;
- additive decomposition;
- multi-scale temporal patches and fusion;
- training objective and inverse scaling;
- computational complexity and implementation boundary.

Separate the V1 model from exploratory V2 factors. Residual anchoring is not part of
the selected V1 PMS configuration.

### 4. Experimental protocol

- four reference panels and eight S/MS tasks, with exact rows, variables, shifts, and
  source constraints from `docs/current_data.md`;
- chronological splits and protected final period;
- six horizons and path-versus-terminal metrics;
- learned and statistical comparator sets;
- equal-budget validation selection and five final seeds;
- moving-block bootstrap, Holm families, missing regime cells, runtime, and checksums.

### 5. Results

Present results in this order:

1. complete task-horizon winner matrix;
2. all-model average rank and gap position across MAE/RMSE/RMSSE;
3. PMS-Mamba's 48-cell task-horizon gap and rank matrix;
4. separate short- (1, 5), middle- (20, 60), and long-term (120, 252)
   all-model comparisons, followed by the task-specific PMS-Mamba term matrix;
5. direct descriptive comparisons against every model, including the signed
   overall/short/middle/long RMSE matrix;
6. confirmatory paired contrasts with S-Mamba and selected learned comparators;
7. S/MS, regime, seed-stability, and runtime results;
8. validation-only V2 ablation in a separately labeled subsection.

### 6. Discussion

- cross-asset strength and possible changing-dependence interpretation;
- middle-horizon advantage;
- persistence failure on FX/yields;
- long-horizon cumulative-error limitation;
- why pooled means and isolated significant cells do not establish dominance;
- residual anchoring as a future hypothesis, not a completed test claim.

### 7. Limitations

- financial reference panels only;
- level-forecasting emphasis;
- one frozen temporal test era;
- no trading or utility evaluation;
- dependent origins and non-estimable regime cells;
- V2 is validation-only;
- no untouched period currently available for a newly designed V3 model.

### 8. Conclusion

Conclude that PMS-Mamba is stable and competitive in bounded settings, especially
cross-asset and middle-horizon forecasting, while persistence/statistical references
remain stronger overall. End with the prospective residual/persistence-change research
direction rather than a superiority claim.

## Figure plan

| Figure | Content | Evidence/source | Status |
| --- | --- | --- | --- |
| 1 | PMS-Mamba architecture | Implemented model code | To generate in manuscript repository |
| 2 | Dataset size, split, level shift, and volatility shift | V1 data manifests and diagnostics | Complete under `docs/figures/` |
| 3 | 48-cell task-horizon winner map | V1 final snapshot | Complete |
| 4 | PMS MAE/RMSE/RMSSE cell gap and rank matrix | V1 aggregate metrics | Complete under `docs/figures/` |
| 5 | Short-, middle-, and long-term all-model rank/gap panels | V1 aggregate metrics | Complete as three separate figures under `docs/figures/` |
| 6 | PMS signed RMSE comparison against every model by term | V1 aggregate metrics | Complete under `docs/figures/` |
| S1 | All-model average rank and median gap | V1 aggregate metrics | Complete under `docs/figures/` |
| S2 | All-model task-balanced RMSSE landscape | V1 aggregate metrics | Complete under `docs/figures/` |
| S3 | PMS task-by-term RMSSE gap, rank, and within-5% matrix | V1 aggregate metrics | Complete under `docs/figures/` |
| S4 | V2 factor effects and task improvements | V2 validation release | Complete |
| S5 | Runtime and peak-memory profile by model, horizon, and task | V1 run-level profiles | Complete under `docs/figures/` |

Figure 3 should establish the complete winner landscape. Figure 4 should show exactly
where PMS-Mamba is strong or weak. Figure 5 must keep short, middle, and long horizons
visually separate rather than collapsing their different behaviors into one average.
Figure 6 should explain which model families PMS-Mamba beats and which remain ahead.
The V2 figure must be labeled exploratory validation evidence. Do not duplicate every
value from these figures in prose.

## Table plan

| Table | Content |
| --- | --- |
| 1 | Dataset, target, mode, dates, frequency, and nonstationarity mechanism |
| 2 | Model components and tuning budget |
| 3 | Balanced task-level path RMSSE and rank |
| 4 | Signed PMS comparison against every model by short/middle/long term |
| 5 | Stability, runtime, and memory tradeoff |
| 6 | Paired bootstrap contrast counts and uncertainty |
| 7 | V2 validation finalists and frozen decision rule |

Use exact values from tracked CSV/JSON artifacts. Preserve explicit NA values for
regime cells with no eligible origins.

## Abstract direction

The abstract should contain five bounded elements:

1. problem: forecasting under nonstationary level, scale, and dependence;
2. method: patchwise decomposition-aware multi-scale Mamba;
3. protocol: eight S/MS tasks, six horizons, strong naive/statistical/learned baselines,
   and five training seeds;
4. result: 0/48 Mamba wins, PMS rank 4/9 among learned models, cross-asset/middle-
   horizon strengths, and the persistence/statistical deficit;
5. conclusion: competitive but not dominant, with residual anchoring as a validation
   direction.

Do not write the final abstract until the manuscript's citations, exact table numbering,
and human-approved contribution statement are available.

## Writing order and review gates

1. Import the frozen evidence tables and figures into the manuscript repository.
2. Write Methods and Experimental Protocol from executed artifacts.
3. Write Results directly from the claim-evidence mapping.
4. Write Discussion and Limitations after the results language is frozen.
5. Reconcile title, abstract, introduction, and conclusion last.
6. Verify every citation against an opened primary source.
7. Run numeric consistency, reference, figure, and LaTeX build checks.
8. Require human approval for authorship, declarations, AI disclosure, venue choice,
   and submission readiness.

The target journal and article type remain unresolved. Publisher-specific formatting,
word counts, data availability language, and AI disclosure must be verified after the
venue is selected.
