# Manuscript Publication Gap Plan for the ace2 Agent

Date: 2026-09-14 (Asia/Shanghai)

## Purpose

This document records the analysis still needed after the completed 18-target
retrospective benchmark. It is an instruction for evidence preparation, not
authorization to restart training, change the protocol, or overwrite a frozen release.

## Current Verified State

- The main compact release is complete: 5,940/5,940 learned rows, 324/324 deterministic
  rows, 18 targets, 108 target--horizon cells, and 25/25 valid checksum entries.
- The checkpoint-reload replay covers all 5,940 learned entries with exact prediction
  and truth equality and matching dates.
- The long-horizon supplement is complete (540/540 rows and 21/21 checksums) but reuses
  the same targets, data, selections, seeds, horizons, and retrospective window. It is
  an audit-only consistency replay and must not be pooled with the main rankings or
  treated as independent evidence.
- No new model training is required for the manuscript's current bounded retrospective
  claim.

## Priority 0: Correct the Inference Boundary

The current `p_value_descriptive` is computed from the fraction of an uncentered nested
bootstrap distribution on either side of zero. It is useful descriptively but is not a
calibrated null-hypothesis p value. The pointwise percentile intervals are unadjusted,
while Holm is applied to all 24 model--reference--horizon tail quantities.

Before any formal significance claim is used, create a new versioned analysis directory
without modifying `reproducibility/financial_s_only_v2/` and do the following:

1. Write and freeze the estimand, experimental unit, null hypothesis, resampling unit,
   comparison family, RNG seed, replicate count, and acceptance checks before producing
   the new outputs.
2. Obtain statistical review of a target-cluster paired randomization/sign-flip test or
   a properly null-centered hierarchical bootstrap. Do not assume target independence
   without documenting the limitation.
3. Apply a finite-replicate correction so no Monte Carlo probability is reported as
   zero. Preserve the 24-comparison family unless a broader, outcome-independent
   protocol is approved before computation.
4. Add block-length sensitivity and a stationary-bootstrap alternative. The existing
   horizon-1 block length of one does not address serial dependence beyond overlap.
5. Report robust target-level summaries (median, IQR, trimmed mean, win count) and all
   four family strata. The existing mean gate difference is concentrated in crypto and
   cross assets; foreign exchange is slightly unfavorable.
6. If formal simultaneous claims are desired, produce multiplicity-compatible
   intervals rather than displaying unadjusted intervals beside adjusted quantities.
7. Record inputs and outputs in a checksum manifest and add a claim--evidence map.

Until that work is complete, retain the manuscript's current phrase “Holm-adjusted
descriptive bootstrap sign-tail probability” and do not use “significant,”
“establishes an effect,” or “confirmatory.”

## Priority 1: Existing-Artifact Analyses

These tasks use retained arrays/checkpoints and do not require retraining:

- Add cluster-aware uncertainty for the 14-model ranking or a model-confidence-set
  analysis, after the statistical procedure is reviewed and frozen.
- Produce a compact selection/fairness table covering candidate search size,
  validation objective, calibration horizons, family input lengths, training budget,
  parameter counts, and matched hardware/runtime protocol.
- If the architectural name `Regime-Gated` is to carry mechanistic meaning, export gate
  values from retained checkpoints and compare them with pre-defined input-window state
  summaries. Treat this as post hoc diagnostic evidence. Otherwise retain the paper's
  explicit statement that the name does not identify an economic regime.
- If “distribution shift” is to return to the title, first freeze outcome-independent
  train/validation/evaluation shift diagnostics for levels, first differences, and
  volatility. Otherwise keep the current title without that claim.

The balanced forecast-trajectory task is complete in the paper repository. The figure
uses the four Regime-Gated Mamba rank-1 cells and its worst numerical rank (13; GLD,
horizon 120), records source and prediction hashes, and is explicitly labelled illustrative.
Do not replace it with a favorable-only selection.

## Priority 2: Reproducibility and Submission Package

- Publish the synchronized code snapshot and compact checksum release at an immutable,
  citable DOI or permanent URL. Record the exact commit and release checksum.
- Resolve redistribution terms for Yahoo Finance, FRED, and Binance source snapshots;
  when redistribution is not permitted, publish retrieval code, identifiers, cutoffs,
  transformations, and hashes rather than the restricted values.
- Complete primary-source metadata checks for the remaining conference references.
  The manuscript currently contains ten uncited bibliography records; remove them from
  the submission bibliography unless they become substantively cited.
- Prepare the LaTeX source, review PDF, individual figures, appendix, and supporting
  information as separate revision-ready files without changing frozen evidence.

## Priority 3: Stronger Generalization

A prospective or broad-market claim requires a new, separately locked future boundary
or external panel. Before any run, freeze sources, target definitions, cutoff,
preprocessing, horizons, models, selection rules, metrics, multiplicity family, and
release name. Do not use the already viewed 2023--2026 period as prospective evidence.
Starting such an experiment requires explicit user authorization.

## Human and Submission Tasks

The server agent cannot resolve author-controlled facts. The authors must provide and
approve funding, conflicts, CRediT roles, ethics or exemption wording, sponsor roles,
corresponding authors, all emails and ORCIDs, data redistribution terms, an immutable
archive DOI/URL, and the final AI-assisted-tools disclosure.

## Completion Criteria

Any new analysis is complete only when its protocol is frozen, inputs are stable,
outputs and counts are complete, checksums pass, negative/null results are retained,
and every manuscript-ready number has a claim--evidence locator. Do not start, stop, or
rerun training solely because this document exists.
