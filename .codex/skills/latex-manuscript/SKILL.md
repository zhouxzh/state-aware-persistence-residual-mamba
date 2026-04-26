---
name: latex-manuscript
description: "Use this skill when working on LaTeX manuscripts: rewriting sections, improving paper structure, inserting or captioning figures and tables, tightening scientific claims, and compiling the manuscript PDF. Especially useful in repos with a `manuscript/` directory, a `main.tex` entry file, figures under `manuscript/figures/`, and a `Makefile` or `latexmk`-based build."
---

# Latex Manuscript

## Overview
Use this skill for publication-facing LaTeX work. It is for scientific writing, figure integration, table cleanup, claim control, and PDF rebuilds. It is not for general prose editing outside a manuscript workflow.

## Workflow
1. Identify the manuscript entry file.
   Prefer `manuscript/main.tex`.
   If there is a `Makefile`, use it instead of inventing a custom build command.

2. Read before editing.
   Check:
   - title, abstract, introduction
   - result tables and figure references
   - whether claims match completed experiments
   - whether referenced figures actually exist

3. Keep figures evidential.
   Every inserted figure should:
   - live under `manuscript/figures/` when possible
   - have a caption and label
   - be referenced in the text
   - support a concrete scientific statement
   Avoid decorative figures.

4. Keep claims conservative.
   Distinguish clearly between:
   - completed results
   - partial results
   - planned experiments
   If an experiment is incomplete, say so directly in the manuscript.

5. Rebuild after edits.
   Prefer:
   ```bash
   make -C manuscript pdf
   ```
   Fallback:
   ```bash
   latexmk -pdf -interaction=nonstopmode -halt-on-error manuscript/main.tex
   ```

6. Report output status.
   After compiling, report:
   - whether the PDF built successfully
   - the output PDF path
   - any warnings that materially affect manuscript quality

## Editing Guidelines
- Prefer minimal structural edits that improve scientific clarity.
- Keep the abstract aligned with actual evidence.
- Do not turn hypotheses into results.
- When tables contain partial comparisons, label them explicitly as partial.
- When discussing metrics, name the horizon and the exact comparison baseline.
- Keep notation and terminology consistent across title, abstract, main text, and tables.

## Figure Handling
When adding or revising figures:
- use `\includegraphics[width=\linewidth]{...}` unless there is a clear reason not to
- add `\caption{...}` and `\label{...}`
- explain in surrounding text:
  - what the figure shows
  - what claim it supports
  - why it matters

Good figure explanation pattern:
- observation from the figure
- interpretation
- implication for the paper argument

## Result-Safety Checks
Before finalizing a manuscript edit, check:
- are all numeric claims traceable to logs, tables, or saved metrics?
- are "best" claims tied to the completed search space?
- are partial experiment blocks described as partial?
- is the title narrower than the strongest unsupported claim?

## Build Conventions
Preferred build path for repos like this one:
- manuscript entry: `manuscript/main.tex`
- figures: `manuscript/figures/`
- build command: `make -C manuscript pdf`
- output: `manuscript/main.pdf`

## Typical Uses
- Rewrite the abstract to match completed experiments.
- Insert manuscript figures and explain what they prove.
- Tighten a results section so it does not overclaim.
- Turn an outline into a coherent draft.
- Compile the PDF after changes and inspect build warnings.
