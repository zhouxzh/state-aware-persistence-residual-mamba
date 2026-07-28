# Review and Submission

Read this reference for formal manuscript review, reviewer responses, revision verification, and submission preparation.

## Choose the Mode

- Use an author self-check during normal editing. Keep it scoped to the changed claims and sections.
- Use `$peer-review` only when the user requests a formal review, critique, revision roadmap, or response plan.
- Keep formal review read-only. Write findings to a separate report only when requested; do not modify manuscript sources in the same review pass.
- Use a later revision pass to apply accepted comments, then verify each change against the original comment and evidence.

For the author's own local manuscript, record that the user controls the material. For third-party or confidential review material, follow `$peer-review` authorization, venue-policy, conflict, retention, and local-only gates before reading it.

## Pre-submission Gate

Review these dimensions without converting a checklist into an acceptance prediction:

1. Contribution and scope
   - State the research question, contribution, and comparison boundary consistently.
   - Keep novelty claims search-bounded and supported by verified literature.

2. Methods and evaluation
   - Report dataset provenance, target, preprocessing, splits, sequence lengths, horizons, and metric definitions.
   - Distinguish model selection from final evaluation.
   - Describe tuning budgets, seeds, repetitions, missing or failed runs, and hardware/software where available.

3. Forecasting validity
   - Check for temporal leakage and inappropriate random splitting.
   - State how scaling, inverse transforms, and horizon aggregation are handled.
   - Avoid significance or robustness claims when only point estimates or one dataset are available.

4. Reproducibility
   - Link model names to source files and registration points.
   - Preserve exact configs, best parameters, environment, run commands, and generator inputs.
   - Do not claim reproduction unless the documented command was actually run successfully.

5. Claims and citations
   - Apply [evidence-and-consistency.md](evidence-and-consistency.md).
   - Ensure limitations directly bound the abstract and conclusion.

6. Figures and tables
   - Apply [figures-and-tables.md](figures-and-tables.md).
   - Verify captions, labels, units, uncertainty, and consistency with prose.

7. Declarations and venue rules
   - Verify authorship, contributions, funding, conflicts, data/code availability, ethics applicability, and AI disclosure from known facts.
   - Never insert plausible boilerplate for missing declarations.
   - Check current official instructions for the exact venue and submission phase.

## Review Findings

Make every major or minor finding actionable:

- Location
- Observation
- Evidence or criterion
- Why it matters
- Requested action

Separate required corrections from optional polish. Request new experiments only when necessary for a central claim; otherwise prefer narrowing, clarification, sensitivity analysis, correction, or explicit limitation.

## Reviewer-response Workflow

1. Preserve each reviewer comment verbatim in a private working document.
2. Classify it as editorial, scientific, statistical, reproducibility, policy, or unresolved.
3. Map it to affected claims, evidence, sections, figures, and tables.
4. Decide whether to accept, partially accept, or respectfully disagree, with evidence.
5. Change authoritative data or generators before dependent prose.
6. State exactly what changed and where.
7. Rebuild and verify the revised manuscript against every response.

Do not claim a concern is resolved until the revised source and rendered PDF both contain the promised change.
