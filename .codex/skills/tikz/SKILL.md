---
name: tikz
description: "Use this skill when creating publication-quality LaTeX/TikZ diagrams, especially architecture figures that need native LaTeX math, equations, subscripts, Greek symbols, or precise panel layouts inside manuscripts."
---

# TikZ Figure Authoring

Use this skill for LaTeX-native diagrams where mathematical notation must render correctly.
Prefer TikZ over Graphviz when node labels or edge annotations require equations, subscripts, Greek symbols, or aligned mathematical expressions.

## Workflow

1. Put reusable figure sources under `manuscript/figures/*.tex`.
   Include them from `manuscript/main.tex` with `\input{figures/name}`.

2. Ensure the manuscript preamble has:
   ```latex
   \usepackage{tikz}
   \usetikzlibrary{arrows.meta,positioning,calc,fit}
   ```

3. Keep diagrams compact.
   Split complex architecture figures into panels such as A and B.
   Use short text in nodes and reserve dense derivations for the surrounding manuscript text.

4. Define TikZ styles locally near the figure source.
   Use consistent styles for:
   - process nodes
   - state nodes
   - gate/control nodes
   - output nodes
   - arrows

5. Use native LaTeX math in nodes when needed:
   ```latex
   $\mathbf{h}_t=\bar{\mathbf{A}}_t\mathbf{h}_{t-1}+\bar{\mathbf{B}}_t\mathbf{x}_t$
   ```

6. Build after every figure edit:
   ```bash
   make -C manuscript pdf
   ```

## Design Rules

- Use `font=\small` or `font=\scriptsize` for node text in dense figures.
- Prefer `align=center` inside nodes with math.
- Avoid negative spacing hacks unless required for fitting.
- Do not put too many equations in one panel.
- If the figure becomes wider than the text column, split it into panels or stack panels vertically.
- If a diagram needs automatic graph layout without formulas, Graphviz is still acceptable.

## Typical Uses

- Mamba block diagrams with state-update equations.
- Neural network architecture diagrams with tensor notation.
- Ablation or module-flow diagrams with mathematical labels.
- Paper figures that need formulas inside boxes.
