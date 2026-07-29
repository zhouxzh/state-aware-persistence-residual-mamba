# Protocol-Aligned Revision Record

Revision date: 2026-07-29  
Controlling review: `NSMAMBA-AUTHOR-LOCAL-20260728`

## Resolved in the interim manuscript

- Replaced the legacy two-series title and study framing with the frozen four-panel
  financial benchmark.
- Removed legacy GLD/Exchange performance values and all performance conclusions.
- Rewrote the task definition for paired S and MS single-target evaluation.
- Replaced the old 12-horizon, single-seed selection protocol with the frozen six-horizon,
  12-trial, top-three replay, five-seed workflow.
- Added all four financial panels, fixed calendar splits, complete-case rule, source
  provenance, data-rights caveats, and selection-safe diagnostics.
- Added path and terminal estimands, RMSSE, last-value skill, paired S/MS differences,
  moving-block bootstrap contrasts, Holm adjustment, and volatility-regime analysis.
- Rewrote Results, Discussion, and Conclusion to withhold confirmatory performance claims
  while the final period remains locked.
- Removed legacy generated result tables and figures from the default PDF dependency graph.
- Added primary references for ADF, KPSS, and the Binance archive.
- Added a separate author-verification checklist rather than inventing declarations.
- Compiled the revised 18-page PDF with no unresolved citations, references, or box warnings.

## Implementation clarification found during revision

ARIMA/VAR orders or lags are selected on training data, but coefficients are estimated once
from the full pre-test training-plus-validation history. Neural weights are fitted on training
observations while validation controls early stopping. This conservative information advantage
for the statistical references is now stated in Methods and Limitations and recorded in future
statistical-run metadata.

## Still blocking submission

- Validation-only HPO and the complete locked final matrix are unfinished.
- No final statistical-reference, bootstrap, S/MS, regime, or full-period diagnostic outputs
  exist yet.
- The target journal and its reporting, template, data, and AI policies are not selected.
- Authorship contributions, funding, competing interests, data/code availability, ethics
  applicability, and AI-use disclosure require accountable author confirmation.
- Dataset redistribution rights and a permanent code/artifact archive remain unresolved.
- Specialist financial-econometrics and final statistical review are still recommended.
