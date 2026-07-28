# Figures and Tables

Read this reference when creating, editing, regenerating, captioning, or auditing figures and tables.

## Source and Provenance

- Keep data figures under `manuscript/figures/` and their generators beside them when practical.
- Preserve raw inputs, transformations, filters, aggregation, normalization, missing-value handling, and random seeds.
- Edit generator code or source data, not exported PDF or PNG files.
- Record the exact source CSV/JSON and generated outputs in the task report.
- Never alter, hide, smooth, crop, or rescale data to strengthen a conclusion.

## Figure Specification

Before coding, identify:

- audience, target venue, submission phase, and final physical width;
- variables, units, horizons, model variants, and comparison set;
- estimator and uncertainty definition;
- replicate unit and sample count, when applicable;
- missing, excluded, failed, or censored observations;
- source paths and transformations.

When venue requirements are unknown, produce a provisional general figure and mark publisher-specific choices as pending verification.

## Honest Encoding

- Prefer position on a common scale for quantitative comparisons.
- Use zero baselines for bars unless a clearly justified alternative preserves meaning.
- Label nonzero limits, log transforms, normalization, bins, and smoothing.
- Name uncertainty as SD, SE, CI, percentile, posterior interval, or another exact definition.
- Do not connect missing observations as if they were measured.
- Avoid dual axes, decorative 3D, misleading area/radius scaling, and axis choices that exaggerate differences.
- Keep limits and normalization consistent across panels intended for comparison.

## Accessibility and Delivery

- Encode groups with color plus marker, line style, hatch, label, or panel structure.
- Use a palette whose semantics match qualitative, sequential, diverging, or cyclic data.
- Inspect contrast and grayscale separation at final rendered size.
- Keep text, legends, and axes readable in `manuscript/main.pdf`.
- Prefer vector PDF for plots and retain a high-resolution PNG only when useful for inspection or other delivery channels.
- Inspect physical dimensions, embedded raster resolution, fonts, transparency, clipping, and file size after export.

## Captions and Narrative

Every retained figure or table must have a caption, label, and in-text reference. A caption should state:

- what is compared;
- dataset and evaluation scope;
- horizon or aggregation;
- metric and direction;
- uncertainty or lack of uncertainty;
- important transformation or exclusion;
- the bounded observation supported by the display.

Surrounding prose should separate observation, interpretation, and implication.

## Using `$scientific-visualization`

- Use its integrity, encoding, accessibility, and export rules for data plots.
- Preserve the repository's established generator scripts and Makefile dependencies.
- Use its pinned `uv` commands when `uv` is available and exact snapshot replay matters.
- Without `uv`, use an available Conda Python only after checking Python version and required imports. Record package versions and do not describe the environment as the upstream pinned snapshot.
- Run optional metadata or palette helpers only on compatible inputs and dependencies; their reports are screening aids, not accessibility or journal-compliance certificates.

## Architecture Figures

- Use `$tikz` when mathematical notation, equations, or precise LaTeX typography belongs inside the diagram.
- Use `$graphviz` for dependency or flow graphs whose automatic layout is useful.
- Keep architecture figures evidential: show implemented components and data flow, not speculative modules presented as completed work.
