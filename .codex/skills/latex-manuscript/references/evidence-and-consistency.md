# Evidence and Consistency

Read this reference for numeric claims, citations, result sections, abstract or conclusion updates, and submission audits.

## Repository Evidence Order

Prefer evidence in this order:

1. Completed run artifacts and saved metrics under `results/`.
2. Bundle manifests, reproduction configurations, best-parameter files, and plot-ready tables under `manuscript/data/`.
3. Generator scripts that define transformations and aggregation.
4. Generated result sections, appendix tables, and figures.
5. Narrative prose that interprets those artifacts.

Never use a downstream narrative or rendered PDF to override an upstream metric or configuration.

## Claim Record

For each material claim, identify:

- claim text and manuscript location;
- dataset and target;
- train, validation, test, or promoted evaluation scope;
- model and exact variant;
- horizon or horizon aggregation;
- metric, units, direction, and scaling;
- comparator and whether tuning budgets are comparable;
- source artifact and generator, when applicable;
- uncertainty, replicate count, or an explicit statement that neither is available;
- verification state: verified, partial, missing, or not applicable.

Use this record in working notes or a sidecar audit file. Do not expose audit IDs in publication prose.

## Result Gate

Before accepting a result edit, check:

- The metric value matches its source with the same rounding policy.
- Percentage improvements use the stated baseline and correct direction.
- "Best" is limited to the completed, named search space.
- Hyperparameter search and evaluation horizons are not conflated.
- Baselines and Mamba variants received clearly described tuning treatment.
- Model names and suffixes match configs, tables, figures, and prose.
- Results, discussion, abstract, and conclusion use the same comparison boundary.
- Single-asset GLD evidence is not generalized to all assets or datasets.
- Incomplete, failed, or excluded runs remain visible where they affect interpretation.

## Citation Gate

- Confirm that each citation key resolves in `manuscript/references.bib`.
- Open the primary source when support for a substantive claim matters.
- Verify the exact proposition, not only title or abstract similarity.
- Keep discovery, bibliographic validity, and claim support as separate states.
- Never invent a DOI, URL, author, year, quotation, or BibTeX field.
- Use current official venue guidance for submission rules; record the access date.

## Using `$scientific-writing`

Use its evidence, consistency, and authorship concepts without replacing the LaTeX project:

- Do not run `scaffold_manuscript.py` over this existing manuscript.
- Do not run `audit_claims.py` or `lint_manuscript.py` directly on `.tex`; they expect tagged Markdown and would produce misleading results.
- Use `check_consistency.py` only when a compatible JSON consistency sidecar exists.
- Use `validate_manifest.py`, `check_references.py`, or `validate_authorship.py` only with their documented JSON templates.
- Keep optional manifests under a separate location such as `manuscript/audit/`; create them only for an explicit provenance or submission-audit task.
- Treat a passing local script as structural validation, never proof that a claim or citation is scientifically correct.

## Generated Artifacts

When evidence changes:

1. Update the authoritative result/configuration input only when the user requested that data change.
2. Update the generator when the transformation, table, or visualization logic must change.
3. Regenerate the derived `.tex`, PDF, or PNG through the Makefile or documented generator.
4. Review the diff for unexpected numeric or formatting changes.
5. Rebuild the manuscript and recheck every narrative claim that depends on the output.

Do not hand-edit generated result sections or figures to force agreement with prose.
