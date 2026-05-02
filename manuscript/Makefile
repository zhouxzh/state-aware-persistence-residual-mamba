TEX := main.tex
PDF := main.pdf
PYTHON ?= python
ARCH_TEX := $(wildcard arch/*.tex)
DOT_SOURCES := $(wildcard figures/*.dot)
DOT_FIGURES := $(DOT_SOURCES:.dot=.pdf)
SECTION_TEX := $(wildcard sections/*.tex)
RESULT_SECTION_TEX := \
	sections/results_baselines.tex \
	sections/results_ns_mamba_diagnostic.tex \
	sections/results_ns_mamba_vs_all.tex \
	sections/results_source_optimized.tex \
	sections/results_mamba_hpo.tex \
	sections/results_overview_figure.tex
FIGURE_DATA := figures/gld_baselines.csv figures/gld_source_optimized_best.csv figures/gld_mamba_hpo_best.csv
FIGURE_OUTPUTS := figures/gld_result_overview.pdf figures/gld_result_overview.png

.PHONY: pdf clean distclean watch help

pdf: $(PDF)

$(PDF): $(TEX) $(ARCH_TEX) $(DOT_FIGURES) $(SECTION_TEX) $(RESULT_SECTION_TEX) $(FIGURE_OUTPUTS)
	@if command -v latexmk >/dev/null 2>&1; then \
		latexmk -pdf -interaction=nonstopmode -halt-on-error $(TEX); \
	elif command -v pdflatex >/dev/null 2>&1; then \
		pdflatex -interaction=nonstopmode -halt-on-error $(TEX); \
		pdflatex -interaction=nonstopmode -halt-on-error $(TEX); \
	else \
		echo "No LaTeX compiler found. Install latexmk or pdflatex to build $(PDF)."; \
		exit 127; \
	fi

figures/%.pdf: figures/%.dot
	@if command -v dot >/dev/null 2>&1; then \
		dot -Tpdf $< -o $@; \
	elif command -v fdp >/dev/null 2>&1; then \
		fdp -Tpdf $< -o $@; \
	elif command -v neato >/dev/null 2>&1; then \
		neato -n2 -Tpdf $< -o $@; \
	else \
		echo "No Graphviz renderer found. Install dot, fdp, or neato to build $@."; \
		exit 127; \
	fi

sections/results_baselines.tex: scripts/generate_gld_baseline_results.py data/gld_baselines.csv
	$(PYTHON) $<

sections/results_ns_mamba_diagnostic.tex: scripts/generate_gld_ns_mamba_diagnostic_results.py data/gld_ns_mamba_ablation.csv
	$(PYTHON) $<

sections/results_ns_mamba_vs_all.tex: scripts/generate_gld_ns_mamba_vs_all.py data/gld_baselines.csv data/gld_ns_mamba_ablation.csv data/gld_source_optimized_best.csv
	$(PYTHON) $<

sections/results_source_optimized.tex: scripts/generate_gld_source_optimized_partial_results.py data/gld_source_optimized_all.csv data/gld_source_optimized_best.csv data/gld_baselines.csv
	$(PYTHON) $<

sections/results_mamba_hpo.tex: scripts/generate_gld_mamba_hpo_results.py data/gld_mamba_hpo_best.csv data/gld_source_optimized_best.csv
	$(PYTHON) $<

sections/results_overview_figure.tex: scripts/generate_gld_complete_metrics_figure_tex.py $(FIGURE_OUTPUTS)
	$(PYTHON) $<

$(FIGURE_OUTPUTS): figures/generate_gld_result_overview.py $(FIGURE_DATA)
	$(PYTHON) figures/generate_gld_result_overview.py

watch:
	@if command -v latexmk >/dev/null 2>&1; then \
		latexmk -pdf -pvc -interaction=nonstopmode -halt-on-error $(TEX); \
	else \
		echo "latexmk is required for watch mode."; \
		exit 127; \
	fi

clean:
	@if command -v latexmk >/dev/null 2>&1; then \
		latexmk -c $(TEX); \
	else \
		rm -f *.aux *.bbl *.blg *.fdb_latexmk *.fls *.log *.out *.toc *.synctex.gz; \
	fi
	rm -rf figures/__pycache__ scripts/__pycache__

distclean: clean
	rm -f $(PDF) $(DOT_FIGURES) $(FIGURE_OUTPUTS) $(RESULT_SECTION_TEX)

help:
	@echo "Targets:"
	@echo "  make pdf       Build $(PDF)"
	@echo "  make watch     Rebuild continuously with latexmk"
	@echo "  make clean     Remove auxiliary LaTeX files"
	@echo "  make distclean Remove auxiliary files and $(PDF)"
