# Journal of Forecasting Submission Audit

Date: 2026-09-14 (Asia/Shanghai)

## Verdict

The scientific core can support a bounded retrospective evaluation paper, but the
manuscript is not submission-ready. The complete benchmark and replay evidence are
available; the remaining blockers are statistical interpretation, declarations,
permanent data/code availability, final citation verification, and submission-package
preparation. No further model training is required for the current narrow claim.

## Evidence Reviewed

- Remote preflight: `zhong@ace2:/home/zhong/Documents/pms-mamba-financial-forecasting`
  on branch `main`, commit `67558ba34c7e2ffae12dea0f9d3ff5cdffeb5c77`, clean at
  2026-09-14 09:42:35 CST. No project training or analysis process was active.
- Frozen main release: 25/25 checksums valid; 5,940/5,940 learned rows and 324/324
  deterministic rows; 18 targets and 108 target--horizon cells.
- Replay: 5,940/5,940 learned entries reproduce predictions and truth exactly with
  matching dates.
- Long-horizon consistency supplement: 21/21 checksums valid and 540/540 replay rows;
  same targets, data, selections, seeds, and retrospective window, so it adds no
  independent evidence and is excluded from rankings and inference.

## Scientific Assessment

The main positive result is a matched architecture comparison: the gated model is
lower than its ungated ablation in 71/108 cells. The equal-cell mean difference is
mostly driven by crypto and cross-asset cells; foreign exchange has a slightly
unfavorable mean gate difference even though the complete model ranks relatively well
there. The paper must keep overall competitiveness separate from gate contribution.

The proposed model is not the overall winner. Its mean rank is 6.25 among 14 methods,
with four rank-1 and 24 top-three cells. Last-value leads 42 cells, and the proposed
model loses to Last-value in 86/108 cells. The strongest descriptive families are
Treasury yields and foreign exchange; crypto is the weakest.

The frozen bootstrap implementation yields an uncentered descriptive sign-tail
probability, not a calibrated null-hypothesis p value. Holm is applied to all 24
model--reference--horizon quantities, while the displayed percentile intervals are
pointwise and unadjusted. The manuscript now labels this correctly. Formal
significance language must not be restored without a new, versioned analysis.

The title no longer claims measured distribution shift. `Regime-Gated` is treated as
an architectural name rather than an identified economic state. A quantified shift or
gate-validity claim would require additional frozen diagnostics.

## Journal and Package Requirements

The official author page checked on 2026-09-14 allows Free Format submission and a
LaTeX main document accompanied by a review PDF. It requires a readable manuscript,
figure legends, up to six keywords, consistent references (APA is the journal style),
ORCID, coauthor affiliations and emails, and applicable data, funding, conflict,
ethics, and permissions statements. Figures, appendices, and supporting information
must be supplied separately at revision. The current KOMA-Script two-column layout is
therefore a working approximation, not an official production template.

## Submission Blockers

1. Authors must approve funding, conflicts of interest, CRediT contributions, ethics or
   exemption language, sponsor roles, corresponding authors, all emails and ORCIDs,
   and the AI-assisted-tools disclosure.
2. A citable immutable code and compact-evidence archive needs a DOI or permanent URL.
   Data-provider redistribution terms and restrictions must be confirmed.
3. The three cited Mamba forecasting papers with verified formal versions have been
   updated (`MambaTS`, `ms-Mamba`, and `KARMA`), and arXiv DOIs were added for Mamba and
   Bi-Mamba+. A final primary-source pass is still needed for conference metadata and
   the ten currently uncited bibliography entries should be removed or cited on merit.
4. A specialist should review the financial-econometric estimand and bootstrap design.
   For formal inference, create a new analysis release with a defensible null procedure,
   finite-replicate correction, multiplicity-compatible intervals, and block-length
   sensitivity.
5. Recompile after all factual declarations are supplied, inspect every page at final
   size, verify embedded fonts and cross-references, and prepare separate figure and
   supporting-information files.

The trajectory figure now includes all four Regime-Gated Mamba rank-1 cells plus the
model's worst numerical rank (13; GLD, horizon 120) under an explicit rule. It remains
illustrative; the complete 108-cell rank heatmap carries the comparative evidence.

## Optional Stronger Evidence

A separately locked future period or external panel would materially strengthen
generalization, but it is not required for the narrowed retrospective paper. It is
required before making prospective or broad market-generalization claims. The known
2023--2026 period must not be relabeled as untouched evidence.

Official sources checked:

- <https://onlinelibrary.wiley.com/page/journal/1099131x/homepage/forauthors.html>
- <https://onlinelibrary.wiley.com/journal/1099131X>
