# Author-requested publication-readiness review -- NSMAMBA-AUTHOR-LOCAL-20260731

> Local working review for the authors. This is not an editorial decision, an
> external peer-review report, or a certification that Wiley will send the paper
> for review. The authors control the material. The assessment concerns an initial
> research-article submission to *Journal of Forecasting*, checked on 2026-07-31.

## Intake record

- Reviewer capacity: `author_requested_reader`
- Target: *Journal of Forecasting*, initial research-article submission in LaTeX
- Official source checked: https://onlinelibrary.wiley.com/page/journal/1099131x/homepage/forauthors.html
- Peer-review model: `single_anonymized`
- Scope: claims, methods, statistics, reproducibility, reporting, citations, and venue readiness
- Boundary: no locked 2023--2026 target outcome was opened, and no forecast result was reproduced in this review.

# Comments to authors

## Evidence-bounded summary

The manuscript defines a prospectively frozen benchmark of four daily financial panels,
paired univariate and multivariate-input tasks, six horizons, learned and statistical
references, five final neural seeds, and dependence-aware inference. The selection audit
and selection-safe nonstationarity characterization are complete. The confirmatory
2023--2026 evaluation is deliberately still locked, so the paper currently reports a
protocol and descriptive diagnostics rather than forecast-performance evidence.

## Strengths

- The chronological split, validation-only selection, protected final period, and
  explicit evidence-status table establish a clear separation between model development
  and final evaluation (Introduction; Results, ``Locked Outcome Status'').
- The study includes persistence, drift, ARIMA, and VAR-on-differences references rather
  than treating a neural-to-neural comparison as sufficient (Abstract; Experimental Setup).
- The paired S/MS design and planned moving-block bootstrap address two common weaknesses
  in financial forecasting studies: unexamined multivariate-input value and dependence
  across forecast origins (Introduction; Experimental Setup).
- The Discussion names important interpretation limits, including that level accuracy is
  not evidence of trading profitability or market inefficiency (Discussion, lines 7--11).

## Major comments

### Major comment M1

- Location: Abstract lines 6--9; Results lines 18--54; Discussion lines 37--40; Conclusion lines 3--9.
- Observation: The complete 2023--2026 neural matrix, statistical-reference forecasts, bootstrap contrasts, and final-period diagnostics are absent by design.
- Evidence or criterion: The manuscript labels these artifacts as locked or not generated, while its three research questions require comparative out-of-period forecast evidence.
- Why it matters: The paper cannot yet answer its central questions about Mamba performance, cross-market stability, or the value of multivariate inputs; protocol quality cannot substitute for empirical results in a research-article submission.
- Requested action: Complete the gated final evaluation for every prespecified task, model, horizon, seed, and reference; generate the evidence tables and revise the Abstract, Results, Discussion, and Conclusion strictly from those artifacts.

### Major comment M2

- Location: Introduction lines 8--11 and 25--30; Discussion lines 13--16.
- Observation: The proposed decomposition and multi-scale Mamba variants overlap conceptually with cited Mamba forecasting adaptations, and the manuscript states that no factorial ablation isolates tokenization, decomposition, scale construction, or parameter count.
- Evidence or criterion: A method paper needs either evidence that isolates the added design choices or a contribution framed as a bounded comparative benchmark rather than as a general architectural advance.
- Why it matters: Without component-level evidence or appropriately limited claims, reviewers cannot determine whether a final difference is attributable to the proposed architecture rather than capacity, tuning choices, or an existing design pattern.
- Requested action: Before submission, add parameter-aware ablations for the components used in the final proposed model, or narrow the novelty and conclusion language to the observed benchmark comparison only.

### Major comment M3

- Location: Experimental Setup, ``Financial Panels and Data Provenance''; Discussion lines 18--22.
- Observation: The design contains four daily targets and one fixed 2023--2026 terminal evaluation interval; the shortest training segment has 973 observations.
- Evidence or criterion: Forecasting generalization depends on market, frequency, regime, and forecast-origin choice, and one terminal interval does not establish stability across historical regimes.
- Why it matters: A favorable result in the protected interval would support a carefully bounded out-of-period claim, but not broad superiority across financial forecasting settings.
- Requested action: Add a rolling-origin or multiple-terminal-period sensitivity analysis when feasible; otherwise keep every abstract and conclusion claim explicitly limited to the four panels, daily frequency, six horizons, and fixed final interval.

### Major comment M4

- Location: Experimental Setup lines 8--12; Discussion lines 24--35; Appendix, ``Frozen Protocol and Reproducibility Details''.
- Observation: The planned moving-block bootstrap and Holm procedure are specified, but final implementations, block-length sensitivity, complete loss records, and statistical-reference outputs are unavailable for inspection.
- Evidence or criterion: Inferential claims in dependent multi-horizon forecast comparisons require a documented analysis unit, implementable resampling procedure, complete contrast family, and reproducible result provenance.
- Why it matters: Intervals and adjusted p-values could otherwise be difficult to interpret, especially because horizons overlap and the neural and statistical workflows use validation data differently.
- Requested action: Archive the final origin-level loss inputs, exact bootstrap configuration and seed, contrast-family definition, block-length sensitivity results, and generated statistical output; obtain financial-econometrics review of the final inferential interpretation.

### Major comment M5

- Location: Experimental Setup lines 8--12; Discussion lines 37--40; `manuscript/audit/manuscript_manifest.json`.
- Observation: The manuscript records unresolved redistribution terms for Yahoo Finance and Binance data and contains no verified public code/data archive, data-availability statement, code-availability statement, funding statement, competing-interest statement, author-contribution statement, ethics applicability statement, or AI-use statement.
- Evidence or criterion: *Journal of Forecasting* expects data sharing and requests title-page statements on data availability, funding, conflicts, and relevant ethics or permissions; its authorship policy also requires that all authors agree to the submitted version.
- Why it matters: These omissions block a complete submission package and prevent readers from assessing whether the reported results can be accessed or reproduced lawfully.
- Requested action: Obtain accountable-author confirmation for every declaration; deposit only data and code that may lawfully be shared, cite versioned archives with persistent identifiers, and state any source-license restrictions and access process precisely.

### Major comment M6

- Location: `main.tex` lines 23--28 and 44--46; Abstract; `main.tex` line 59.
- Observation: The visible title contains internal workflow wording (``Locked''), there is no running title or visible keyword list, the interim status banner states that there are no confirmatory outcomes, and the bibliography uses `unsrt` rather than the journal's APA style.
- Evidence or criterion: The journal's current author guidelines request a brief informative title with major keywords and no abbreviations, a running title under 40 characters, up to six keywords, and APA references; its Free Format policy permits consistent references at initial submission.
- Why it matters: The current title and status notice correctly describe the draft but signal an unfinished protocol rather than a completed forecasting contribution. The reference style is not an initial-submission blocker, but it will create avoidable revision work.
- Requested action: Use the revised informative title and running title implemented in this revision, add a visible keyword list, remove the interim banner only after the final evidence exists, and convert the bibliography to APA during submission preparation.

## Minor comments

### Minor comment m1

- Location: Abstract lines 5--8.
- Observation: The abstract allocates substantial space to future-tense procedures and selection-safe diagnostics but has no final forecast result.
- Evidence or criterion: A research-article abstract should summarize completed methods, principal results, and a bounded implication.
- Why it matters: Readers and editors cannot assess the contribution from a protocol-only abstract.
- Requested action: Rewrite the abstract after final generation to report the primary metric, named comparators, uncertainty, scope, and any null or unfavorable outcomes without selectively reporting favorable cells.

### Minor comment m2

- Location: Experimental Setup, ``Financial Panels and Data Provenance''.
- Observation: Source URLs, retrieval dates, and hashes are retained locally but are not presented as a citable public provenance record.
- Evidence or criterion: Reproducible financial-data studies should identify immutable or versioned inputs and transformations to the extent permitted by source terms.
- Why it matters: A reader cannot independently reconstruct the exact data release from the current narrative alone.
- Requested action: Add a supplementary provenance table or archive manifest containing source identifiers, retrieval dates, transformations, checksums, split boundaries, and the permitted access route.

### Minor comment m3

- Location: Discussion lines 30--35.
- Observation: The paper notes that the statistical references are practical rather than exhaustive, but it does not predefine how an unfavorable outcome versus those references will alter the claimed contribution.
- Evidence or criterion: Interpretation should be determined by the final comparison boundary rather than by whether neural-to-neural results are favorable.
- Why it matters: Explicitly retaining null and negative outcomes reduces the risk of post hoc framing.
- Requested action: In the final Discussion, organize conclusions around comparisons with persistence and named statistical references first, then neural baselines, and state where conclusions differ by panel or horizon.

## Methods, statistics, and reproducibility

The protocol is stronger than a typical single-split neural benchmark because it separates
selection from final evaluation and prespecifies five neural seeds and dependence-aware
contrasts. Its current limitation is incompleteness rather than a demonstrated statistical
error. No final result, bootstrap, source-data reconstruction, or code run was independently
reproduced here. A financial-econometrics review remains needed for final choices about
statistical references, temporal sensitivity, and the interpretation of overlapping-horizon
inference.

## Venue compliance notes

For the current *Journal of Forecasting* initial-submission guidance checked on 2026-07-31,
the manuscript may be submitted in LaTeX under Free Format and author identities remain in
the file because review is single-anonymized. The initial submission still needs an editable
manuscript/PDF pair, title-page information, abstract, up to six keywords, readable figures
and tables, and the relevant data, funding, conflict, ethics, and permission statements.
ORCID is required by the journal. The authors must verify these portal and policy requirements
again immediately before submitting.

## Limitations of this review

This local review does not predict an editorial outcome. It is based on repository sources,
the current compiled PDF metadata, and the official journal page checked on the stated date.
It does not independently reproduce forecast experiments, assess all bibliography records
against their primary sources, validate external data licenses, or replace an accountable
financial-econometrics or author-declaration review.

# Confidential comments to editor

## Reviewer disclosures

Not applicable. This is an author-requested local review, not a journal assignment. No
confidential editor communication has been prepared.

## Editorial-process or integrity concerns

None identified from the materials reviewed. The outstanding issues are incomplete evidence
and unverified submission declarations, not an allegation of research misconduct.
