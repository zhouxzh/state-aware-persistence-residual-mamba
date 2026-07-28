# Nonstationary Financial Dataset and Evaluation Plan

## Purpose

This document defines the prospective dataset and evaluation plan for a manuscript on
nonstationary financial time-series forecasting. It replaces the earlier general
long-term forecasting benchmark proposal.

The target problem is not generic periodic forecasting. The study focuses on financial
nonstationarity expressed through stochastic trends, structural breaks, volatility
clustering, changing cross-market dependence, and market-regime shifts. Periodic
electricity, traffic, and meteorological benchmarks are therefore outside the planned
confirmatory scope.

This scope decision must not be justified by model performance. The manuscript must
state that ETTh1 and similar datasets are excluded because they do not represent the
target financial process, not because a Mamba variant performs poorly on them.

The plan is prospective. None of the proposed datasets or analyses may be described as
completed evidence until their source records, preprocessing artifacts, predictions,
metrics, and run metadata have been verified.

## Research Questions

The expanded evaluation should answer three bounded questions:

1. Does nonstationarity-aware normalization improve forecasting under changes in
   financial level, scale, and volatility?
2. Do decomposition and multiple temporal scales improve forecasting across natural
   financial horizons and market regimes?
3. Do variable-token Mamba encoders obtain useful information from multivariate
   financial panels that is unavailable in the current single-variable setting?

The study should not claim general superiority across all time-series domains, trading
profitability, market efficiency, or causal effects.

## Scope Boundaries

### Included

- financial prices, rates, yields, returns, and realized volatility;
- daily or higher-frequency series with documented timestamps and market calendars;
- univariate tasks that test temporal modeling;
- multivariate panels that test changing cross-market dependence;
- public or institutionally licensed sources with reproducible identifiers;
- negative, null, or inconclusive results from every frozen task.

### Excluded from the confirmatory benchmark

- ETT, Electricity, Traffic, ILI, Solar-Energy, and other general-domain benchmarks;
- the current unclean Weather experiment;
- datasets selected after inspecting whether the proposed model wins;
- sources without a recoverable series identifier, retrieval record, or usage terms;
- trading-strategy claims that require transaction costs, execution assumptions, and
  economic-utility evaluation.

The exploratory Weather run must remain disclosed in the research record. Its earlier
post hoc exclusion was caused by unhandled sentinel values. It is not part of the new
financial protocol and should not be used as supporting or opposing evidence.

## Dataset Eligibility Rules

Before downloading or training on a new dataset, record:

- the task-family ID and the scientific reason for inclusion;
- provider, series IDs or symbols, units, quote direction, frequency, and timezone;
- source URL, license or access conditions, retrieval date, and file checksum;
- a fixed data cutoff date and a versioned raw-data snapshot;
- enough observations for the maximum lookback, forecast horizon, validation replay,
  and final evaluation windows;
- missing-date, non-trading-day, corporate-action, and outlier policies;
- target transformations and whether they use levels, log levels, returns, or
  volatility;
- train, validation, rolling-origin, and untouched final-evaluation boundaries;
- all exclusions before model outcomes are inspected.

No unit-root test, change-point statistic, or model score may be used as an outcome-based
dataset inclusion rule. These analyses characterize the frozen datasets; they do not
decide which completed results are retained.

## Planned Financial Task Families

| Priority | Task family | Candidate series | Nonstationarity represented | Mode |
| --- | --- | --- | --- | --- |
| P0 | Existing development evidence | GLD and current U.K. Exchange target | Trending levels and exchange-rate drift | S |
| P0 | Foreign-exchange panel | A predeclared set of FRED H.10 major-currency series | Stochastic trends, policy shifts, and changing co-movement | S and M |
| P0 | Treasury yield curve | DGS2, DGS5, DGS10, and DGS30 | Monetary regimes and time-varying term-structure dependence | S and M |
| P0 | Cross-asset daily panel | Gold, equity, oil, and volatility indicators | Risk-on/risk-off transitions and structural breaks | M |
| P1 | Cryptoasset panel | Predeclared liquid spot pairs with OHLCV records | Jumps, volatility clustering, and continuous trading | S and M |
| P1 | Realized-volatility panel | Equity, foreign-exchange, and futures volatility measures | Long memory, clustering, jumps, and stress regimes | S and M |
| P2 | Macroeconomic context | A fixed FRED-MD or FRED-QD vintage | Low-frequency macroeconomic regime shifts | M or MS |
| P2 | External collection benchmark | M4 Finance or Monash Bitcoin | Cross-series and cross-frequency robustness | Separate global protocol |

The task families are the unit of design. Adding many nearly identical tickers from one
market does not substitute for coverage across foreign exchange, rates, cross-asset
prices, cryptoassets, and volatility.

## Task-Family Specifications

### Existing GLD and Exchange Results

The current GLD and Exchange runs remain development-period evidence. Earlier GLD test
outcomes influenced architecture promotion, and the current Exchange provenance lacks
the exact original series identifier. These results may motivate the new study but must
not be re-labelled as untouched confirmation.

The local Exchange preparation should be replaced prospectively by direct retrieval
from explicitly named FRED series. The existing United Kingdom target is consistent
with the FRED H.10 series DEXUSUK, but this mapping must be verified from the original
raw record before it is asserted as historical provenance.

### Foreign-Exchange Panel

Select six to eight major-currency series from one documented FRED H.10 release before
training. Candidate examples include DEXUSUK, DEXUSEU, and DEXCAUS. Because FRED quote
directions differ across currencies, retain the original units in the raw archive and
define one explicit transformation into a common orientation for modeling.

Run both:

- independent univariate forecasts for each currency; and
- a multivariate panel forecast over dates shared by the frozen currency set.

The multivariate panel is necessary to evaluate the variable-token Mamba encoder. A
single-currency S-mode task contains only one variable token and cannot demonstrate
cross-currency modeling.

### Treasury Yield-Curve Panel

Use constant-maturity Treasury yields at predeclared maturities, with DGS2, DGS5,
DGS10, and DGS30 as the initial panel. Record units as percentage yields and preserve
the official missing-date pattern.

Evaluate each maturity separately and jointly. The joint task should test whether the
model captures changing level, slope, and curvature relationships without claiming that
the latent factors are causally identified.

### Cross-Asset Daily Panel

Construct one predeclared daily panel spanning several asset classes, for example:

- gold or a gold-market proxy;
- a broad equity-market indicator;
- a crude-oil price indicator;
- a market-volatility indicator.

Check redistribution terms before archiving or releasing any source series. Traditional
asset panels should use a shared business-day calendar. Crypto observations must not be
silently merged into that calendar because crypto trades continuously.

The cross-asset panel should be evaluated as a separate task from its univariate member
series. Missing values must not be filled using future observations.

### Cryptoasset Panel

Use the official Binance public-data archive or another versioned primary source. Freeze
the exchange, market type, quote currency, symbols, bar interval, and start/end dates
before training. Verify every downloaded archive with its published checksum.

Prefer a small set of liquid pairs with sufficiently long common histories. Do not
select tokens based on retrospective model accuracy or survivorship alone. Record
listing dates, delistings, symbol changes, and unavailable intervals.

Daily bars support comparability with traditional assets. A separate four-hour task may
be added only if all models receive the same horizon and search protocol.

### Realized-Volatility Panel

Realized volatility is a distinct target and must not be evaluated as if it were a price
level. VOLARE is a candidate source for standardized realized measures over equities,
foreign exchange, and futures. Verify its processed-data availability and redistribution
conditions before inclusion.

Use a declared realized measure consistently across assets. Model log realized
volatility or another prespecified transformation, and include financial volatility
benchmarks such as HAR-RV. Do not use the discontinued Oxford-Man library unless a
legally shareable, versioned archive and its provenance can be documented.

### FRED-MD, FRED-QD, and Collection Benchmarks

FRED-MD and FRED-QD are optional context tasks rather than primary financial-market
targets. Freeze an exact vintage and apply the published transformation codes. Avoid
using the live `current.csv` endpoint as the only archived input because it changes
over time.

M4 Finance and Monash Bitcoin use collection-style forecasting protocols. They require
a new global-forecasting loader and a different unit of analysis, so their results must
not be pooled directly with the current single-series sliding-window cells.

## Target Definitions

Price, return, and volatility targets answer different questions and require separate
tables.

### Level Forecasting

- target: original level or prespecified log level;
- primary references: last value and random walk with drift;
- metrics: RMSSE, MAE, and skill relative to the random-walk reference;
- interpretation: statistical forecast accuracy only.

### Return Forecasting

- target: prespecified simple or log return;
- primary reference: zero return;
- metrics: MAE and RMSE, with directional accuracy as a secondary descriptive measure;
- interpretation: no profitability claim without a separate economic evaluation.

### Volatility Forecasting

- target: prespecified log realized volatility or another documented positive measure;
- primary references: HAR-RV and appropriate GARCH-family models;
- metrics: QLIKE and MSE on the declared transformed scale;
- interpretation: risk-forecast accuracy rather than price-direction accuracy.

The manuscript should choose one primary target family. Other target families are
secondary robustness analyses and must not be searched for the most favorable outcome.

## Forecast Horizons

For new daily financial tasks, use natural trading horizons selected before training:

- 1 observation: next session;
- 5 observations: approximately one trading week;
- 20 observations: approximately one trading month;
- 60 observations: approximately one quarter;
- 120 observations: approximately half a trading year;
- 252 observations: approximately one trading year.

Calendar interpretations are approximate and must not be applied to 24/7 crypto markets.
For each nominal horizon H, report whether a metric averages the full forecast path
(leads 1 through H) or evaluates only terminal lead H. Prefer reporting both path-average
and terminal-lead results rather than presenting one as the other.

The existing 12-horizon GLD and Exchange results remain development evidence under their
original protocol. They should not be silently mixed with the new six-horizon
confirmatory benchmark.

## Temporal Evaluation Design

Replace a single split as the only evaluation with a frozen walk-forward design:

1. an initial chronological training period;
2. a validation period used for hyperparameter selection;
3. multiple rolling forecast origins across the evaluation era;
4. a final contiguous period that remains untouched until the protocol and model set
   are frozen.

Report aggregate performance over the complete evaluation era. Secondary regime
analysis may compare calm and stress periods only when the classification rule and dates
are fixed without using test forecast errors. Data-driven change points may be estimated
from training data, but must not use future test observations to define favorable
subgroups.

Adjacent rolling origins and multiple leads are dependent. They must not be counted as
independent replications.

## Nonstationarity Characterization

For each frozen series or panel, report descriptive evidence such as:

- rolling mean and scale changes;
- rolling volatility and tail behavior;
- missingness and market-calendar structure;
- train-to-test distribution shift;
- prespecified unit-root and stationarity diagnostics;
- structural-break or change-point summaries;
- time-varying cross-series correlations for multivariate panels.

No single ADF, KPSS, or change-point test establishes the complete form of
nonstationarity. Diagnostics should describe the task and motivate bounded hypotheses,
not certify that a dataset is suitable only when a preferred model performs well.

## Comparator Requirements

### Statistical and financial references

- last value or random walk;
- random walk with drift;
- ARIMA or another documented autoregressive reference;
- VAR or VECM where justified for multivariate financial panels;
- HAR-RV and a GARCH-family reference for volatility tasks.

### Learned forecasting references

- DLinear and NLinear;
- PatchTST;
- TimesNet;
- iTransformer;
- S-Mamba;
- NS-Mamba-D;
- MS-Mamba-MD;
- PMS-Mamba-PD.

Autoformer, Informer, Reformer, and a plain Transformer may remain supplementary.
Compute should prioritize fair tuning and repeated runs of the strongest references
rather than additional weak single-seed baselines.

## Fairness, Uncertainty, and Reproducibility

Within every task family:

- use the same calibration horizons and trial budgets for competing learned models;
- keep model-specific search spaces bounded and document their dimensions;
- select configurations on validation data only;
- run the central learned models with multiple seeds, using five as a practical target
  when compute permits;
- store per-origin and per-lead predictions, targets, and losses;
- report training-seed variation separately from sampling uncertainty;
- use paired moving-block bootstrap intervals or an appropriately specified
  loss-differential procedure that respects temporal dependence;
- address multiple comparisons when making inferential claims across many models;
- record parameters, runtime, peak GPU memory, GPU model, package versions, and
  nondeterminism controls.

Negative and inconclusive results must remain in the result matrices. No dataset, horizon,
seed, or baseline may be removed because it reverses the preferred ranking.

## Execution Plan

### Phase 0: Freeze the protocol

1. Choose the primary target family.
2. Freeze the task families, series IDs, data cutoff, horizons, model list, metrics, and
   exclusion rules.
3. Record source terms and the intended release boundary for raw and processed data.

### Phase 1: Build versioned datasets

1. Download raw files from primary sources.
2. Preserve raw snapshots and checksums.
3. Generate processed CSV files through deterministic scripts.
4. Produce provenance manifests with units, quote directions, calendars, and split
   boundaries.
5. Validate missingness, duplicates, monotonic dates, and target finiteness.

### Phase 2: Validate model compatibility

1. Run S-mode smoke tests on representative univariate series.
2. Run M-mode smoke tests on each multivariate panel.
3. Verify output shapes, inverse scaling, metric units, and GPU memory.
4. Confirm that multivariate targets are evaluated consistently across models.

### Phase 3: Equal-budget selection

1. Run the same Optuna trial count and calibration horizons for central models.
2. Replay the same number of validation candidates.
3. Freeze selected configurations without inspecting the final evaluation period.

### Phase 4: Repeated final evaluation

1. Train the frozen central configurations across the declared seeds.
2. Generate walk-forward predictions.
3. Open the untouched final period only after all prior checks pass.
4. Archive run metadata and failures rather than silently replacing them.

### Phase 5: Analysis and manuscript integration

1. Compute primary metrics and reference-model skill.
2. Estimate dependence-aware uncertainty.
3. Characterize results by task family, horizon, and prespecified regime.
4. Update generated tables and figures from archived result files.
5. Revise the title, abstract, claims, and limitations only after the evidence is
   complete.

## Minimum and Preferred Portfolios

### Minimum defensible expansion

- current GLD and Exchange results as development evidence;
- one frozen multivariate FRED foreign-exchange panel;
- one frozen Treasury yield-curve panel;
- one frozen cross-asset panel;
- one additional volatility or cryptoasset task;
- equal-budget central baselines, repeated seeds, and walk-forward evaluation.

### Preferred expansion

- all minimum task families;
- independent univariate and multivariate versions of the foreign-exchange and
  yield-curve tasks;
- both a cryptoasset panel and a realized-volatility panel;
- one external robustness collection such as M4 Finance or Monash Bitcoin;
- controlled ablations for normalization, decomposition, temporal scales, and patch
  tokenization.

The preferred design supports conclusions about nonstationary financial forecasting
across market types. It does not support conclusions about periodic industrial,
meteorological, medical, or general-purpose time-series forecasting.

## Manuscript Consequences

After the new experiments are complete, the manuscript should:

- present financial nonstationarity as the primary scientific problem;
- explain why general periodic benchmarks are outside scope without citing poor model
  performance as the reason;
- distinguish current development evidence from newly frozen confirmatory evidence;
- explain why multivariate financial panels are required to test variable-token Mamba;
- compare against econometric and naive financial references, not only neural models;
- preserve failures and domains in which persistence remains strongest;
- avoid claims of trading utility or general time-series superiority.

A future title may emphasize nonstationarity-aware financial forecasting and evidence
across market regimes. The title must not be finalized until the expanded result pattern
is known.

## Candidate Source Records

- FRED H.10, United Kingdom exchange rate (DEXUSUK):
  <https://fred.stlouisfed.org/series/DEXUSUK>
- FRED H.10, euro exchange rate (DEXUSEU):
  <https://fred.stlouisfed.org/series/DEXUSEU>
- FRED H.10, Canadian exchange rate (DEXCAUS):
  <https://fred.stlouisfed.org/series/DEXCAUS>
- FRED H.15, 2-year Treasury yield (DGS2):
  <https://fred.stlouisfed.org/series/DGS2>
- FRED H.15, 5-year Treasury yield (DGS5):
  <https://fred.stlouisfed.org/series/DGS5>
- FRED H.15, 10-year Treasury yield (DGS10):
  <https://fred.stlouisfed.org/series/DGS10>
- FRED H.15, 30-year Treasury yield (DGS30):
  <https://fred.stlouisfed.org/series/DGS30>
- FRED-MD and FRED-QD:
  <https://www.stlouisfed.org/research/economists/mccracken/fred-databases>
- Binance public historical market data:
  <https://github.com/binance/binance-public-data>
- VOLARE realized-volatility archive:
  <https://volare.unime.it/documentation>
- M4 Competition:
  <https://www.unic.ac.cy/iff/research/forecasting/m-competitions/m4/>
- Monash Time Series Forecasting Repository:
  <https://forecastingdata.org/>

These are candidate sources, not verified manuscript evidence. Before use, the authors
must open the exact source, verify the downloaded version and proposition, record access
and redistribution conditions, and preserve the raw-to-processed transformation.
