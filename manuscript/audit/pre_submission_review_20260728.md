# Author-Requested Pre-Submission Review

Status: working review draft for accountable human verification  
Review date: 2026-07-28  
Review ID: `NSMAMBA-AUTHOR-LOCAL-20260728`

## Scope and Boundary

This is an author-requested, local-only review of the repository manuscript. It is not
an editorial decision or a certification of submission readiness. The target journal
has not been selected, so journal-specific format, AI-disclosure, data-policy, and
retention requirements remain unresolved. Specialist review is still advisable for
financial-econometrics claims and the final statistical analysis.

Evidence inspected includes the LaTeX sources and build log, the manuscript Makefile,
`configs/financial_benchmark.json`, the financial benchmark runbook, generated legacy
tables, and current training-process metadata. No locked final-period outcome was
opened for this review.

## Overall Assessment

The current 16-page PDF builds without unresolved LaTeX citations or references, and
the legacy GLD/Exchange manuscript is unusually explicit about persistence, test-period
reuse, unequal search budgets, and single-seed limitations. However, it describes a
different study from the frozen `financial_confirmatory_v1` protocol. It therefore
cannot serve as the submission manuscript for the current project without a structural
rewrite. The correct interim deliverable is a protocol-aligned manuscript with final
performance claims withheld until the locked evaluation and statistical analysis are
complete.

## Major Findings

### M1. The manuscript and frozen protocol define different studies

- **Location:** `main.tex` title and metadata; Abstract; Introduction lines 21--32;
  Forecasting Models lines 3--11; Experimental Setup; Results; Conclusion.
- **Observation:** The manuscript reports two univariate legacy series, 14 neural
  models, 12 horizons, one seed, and chronological 70/10/20 splits. The frozen protocol
  specifies four financial panels, paired S/MS tasks, nine learned models, six horizons,
  five final seeds, and fixed calendar splits.
- **Evidence/criterion:** `configs/financial_benchmark.json` and
  `docs/financial_benchmark_runbook.md` are the controlling prospective artifacts.
- **Why it matters:** Dataset, method, and result claims currently refer to an obsolete
  evaluation and cannot be reconciled by copy-editing.
- **Requested action:** Rewrite the title, abstract, introduction, task definition,
  experimental setup, results structure, discussion, conclusion, and appendix around
  `financial_confirmatory_v1`.

### M2. Legacy test results are outside the confirmatory evidence boundary

- **Location:** Abstract lines 3--9; Results lines 7--34; Discussion; Conclusion.
- **Observation:** Final claims center on GLD and the old Exchange series.
- **Evidence/criterion:** The frozen protocol labels both legacy benchmarks as
  development-only and excludes them from the confirmatory manuscript evidence.
- **Why it matters:** Retaining these point estimates as principal results would mix
  architecture-development evidence with a prospectively locked study.
- **Requested action:** Remove legacy performance numbers from the main paper. At most,
  mention them as motivation without using their outcomes to support the new model.

### M3. The reported training and selection protocol is obsolete

- **Location:** Experimental Setup lines 78--99 and Appendix optimization tables.
- **Observation:** The manuscript reports 20/24 archived trials, up to five replays,
  family-dependent calibration horizons, and seed 2023.
- **Evidence/criterion:** The frozen design uses 12 effective trials per model/task,
  calibration horizons 5/60/252, top-three full validation replays, and final seeds
  2023--2027. The test split must remain unopened throughout model selection.
- **Why it matters:** Tuning fairness, leakage control, and uncertainty statements depend
  on the exact protocol actually run.
- **Requested action:** Replace the legacy HPO description and generated appendix with
  the frozen selection and final-evaluation workflow, including interruption recovery
  and the distinction between validation replay and test evaluation.

### M4. S/MS task design and multivariate interpretation are absent

- **Location:** Forecasting Models lines 5--11 and 67--69; Experimental Setup datasets.
- **Observation:** The manuscript fixes `C=C_o=1` and treats the inverted Mamba encoder
  as a one-token model. The frozen benchmark has both univariate S tasks and
  multivariate-to-single-target MS tasks.
- **Evidence/criterion:** `training_datasets.json` and the frozen dataset configuration
  define paired S/MS tasks for every panel.
- **Why it matters:** The MS tasks are the direct test of whether cross-series inputs
  improve the target forecast and change the interpretation of variable-token Mamba.
- **Requested action:** Define S as `C=1, C_o=1` and MS as `C>1, C_o=1`; state input
  columns and target for each panel; prespecify paired S-versus-MS comparisons without
  claiming that cross-series dependence is causal.

### M5. The confirmatory statistical analysis is not represented

- **Location:** Metrics section, Results, and Discussion.
- **Observation:** The current paper reports single-seed balanced RMSSE point estimates
  and explicitly has no inferential intervals.
- **Evidence/criterion:** The new analysis plan includes five seeds, deterministic and
  statistical references, path/terminal metrics, last-value skill, paired S/MS
  comparisons, moving-block bootstrap intervals, Holm adjustment, and a prespecified
  volatility-regime analysis.
- **Why it matters:** The new paper's central contribution depends on uncertainty-aware,
  dependence-conscious comparison rather than selected point estimates.
- **Requested action:** Rewrite the metric and analysis methods from the implemented
  analysis code, define the resampling unit and estimands exactly, and reserve all
  numeric conclusions until the complete locked matrix passes validation.

### M6. Dataset provenance and nonstationarity characterization must be rebuilt

- **Location:** Experimental Setup lines 3--43.
- **Observation:** Only GLD and a provenance-limited legacy Exchange series are described.
- **Evidence/criterion:** The frozen data assets contain FRED foreign-exchange and yield
  panels, a cross-asset panel, and Binance cryptoasset data with fixed cutoffs,
  complete-case calendars, checksums, targets, and selection-safe diagnostics.
- **Why it matters:** A paper about nonstationary financial forecasting must define the
  target, units, calendar alignment, missingness rule, source rights, and the evidence
  used to characterize nonstationarity.
- **Requested action:** Replace the dataset table and provenance text; distinguish
  selection-safe train/validation diagnostics from final-period descriptive analysis;
  avoid treating unit-root tests as proof of a single data-generating mechanism.

### M7. Final results are not yet available and must not be inferred from HPO

- **Location:** Abstract, Results, Discussion, and Conclusion.
- **Observation:** The current training process is still in validation-only HPO. The
  final command requires an explicit `--unlock-test` gate after selection audit.
- **Evidence/criterion:** Model-selection scores are not test evidence, and incomplete
  task subsets cannot populate the manuscript result matrix.
- **Why it matters:** Writing performance rankings now would create unsupported or
  leakage-prone claims.
- **Requested action:** Produce an interim protocol-aligned draft whose performance
  sections state that confirmatory outcomes are pending. Populate them only through the
  validated result generators after all neural and statistical references complete.

### M8. Submission declarations and venue controls are incomplete

- **Location:** End matter after the appendix and bibliography setup.
- **Observation:** Author names and affiliations are present, but there is no verified
  CRediT statement, funding/sponsor role, competing-interest statement, data/code
  availability statement, AI-use disclosure, or selected journal template.
- **Evidence/criterion:** These statements must be supplied as facts by accountable
  authors and checked against the target venue; plausible boilerplate is not evidence.
- **Why it matters:** The manuscript cannot be submission-ready without verified end
  matter and venue-specific policy review.
- **Requested action:** Add an explicit author-verification checklist outside the
  submission prose. Insert declarations only after the authors confirm their content.

### M9. The Makefile still regenerates the obsolete benchmark

- **Location:** `manuscript/Makefile`, generated legacy tables, and legacy comparison
  figure.
- **Observation:** The default PDF target depends on GLD/Exchange CSVs and regenerates
  legacy result sections and the old family-comparison figure.
- **Evidence/criterion:** `financial-assets` correctly fails closed until the complete
  confirmatory matrix exists, but the default manuscript still includes old outputs.
- **Why it matters:** A rebuild could silently restore obsolete evidence after prose is
  rewritten.
- **Requested action:** Separate legacy artifacts from the new default manuscript;
  preserve fail-closed generation and make the final financial result assets the only
  performance source for the new paper.

## Minor Findings

1. The current title accurately bounds the legacy study but is unsuitable for the new
   question. The replacement should name nonstationary financial level forecasting and
   the S/MS comparison without claiming superiority.
2. Current bibliography keys resolve internally, but the new manuscript needs verified
   primary citations for each dataset source and any statistical method added.
3. The old test-selected comparison figure is transparent about its post hoc selection,
   but it cannot be reused in the confirmatory paper. New figures should show frozen
   comparisons with five-seed uncertainty and redundant non-color encoding.
4. Page size is currently US Letter under a generic `article` class. This is acceptable
   for an internal draft; the final class, dimensions, abstract format, and reference
   style depend on the selected venue.

## Strengths to Preserve

- Explicit use of a persistence reference rather than neural-only ranking.
- Clear disclosure of prior test-period reuse and optimization-budget asymmetry.
- Separation of observation from mechanism claims.
- Generated result tables and figures with fail-closed checks.
- Repository-level protocol, data hashes, resumable studies, and an explicit test gate.

## Revision Decision for This Local Workflow

Proceed with a full protocol-aligned rewrite now. Keep the manuscript explicitly
non-submission-ready until the selection audit, locked five-seed evaluation,
statistical baselines, uncertainty analysis, and human declaration review are complete.
