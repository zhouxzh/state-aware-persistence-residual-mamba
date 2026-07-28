TEX := main.tex
PDF := main.pdf
PYTHON ?= python
ARCH_TEX := $(wildcard arch/*.tex)
DOT_SOURCES := $(wildcard figures/*.dot)
DOT_FIGURES := $(DOT_SOURCES:.dot=.pdf)
SECTION_TEX := $(wildcard sections/*.tex)
APPENDIX_TEX := $(wildcard sections/appendix/*.tex)
RESULT_SECTION_TEX := \
	sections/results_benchmark_summary.tex \
	sections/results_model_ranking.tex
APPENDIX_RESULT_TEX := \
	sections/appendix/benchmark_protocol.tex
BENCHMARK_DATA := \
	../results/gld_baseline_optuna_best.csv \
	../results/gld_mamba_optuna_best.csv \
	../results/exchange_baseline_optuna_best.csv \
	../results/exchange_mamba_optuna_best.csv
BENCHMARK_METADATA := \
	../configs/optuna_datasets.json \
	$(wildcard ../results/optuna/gld/*_best_params.json) \
	$(wildcard ../results/optuna/gld/*_trials.csv) \
	$(wildcard ../results/optuna/exchange/*_best_params.json) \
	$(wildcard ../results/optuna/exchange/*_trials.csv)
BENCHMARK_SOURCE_DATA := \
	../data/GLD/GLD.csv \
	../data/Exchange/exchange_rate.csv
LAST_VALUE_DATA := data/last_value_baseline.csv
FIGURE_OUTPUTS := figures/benchmark_family_comparison.pdf figures/benchmark_family_comparison.png

.PHONY: pdf financial-assets clean distclean watch help

pdf: $(PDF)

financial-assets:
	$(PYTHON) ../scripts/financial/analyze_financial_results.py
	$(PYTHON) ../scripts/financial/analyze_financial_data.py --include-test
	$(PYTHON) scripts/generate_financial_results.py
	$(PYTHON) figures/generate_financial_results.py
	$(PYTHON) figures/generate_financial_data_diagnostics.py --include-test

$(PDF): $(TEX) $(ARCH_TEX) $(DOT_FIGURES) $(SECTION_TEX) $(APPENDIX_TEX) $(RESULT_SECTION_TEX) $(APPENDIX_RESULT_TEX) $(FIGURE_OUTPUTS)
	@if command -v latexmk >/dev/null 2>&1; then \
		latexmk -pdf -interaction=nonstopmode -halt-on-error $(TEX); \
	elif command -v pdflatex >/dev/null 2>&1 && command -v bibtex >/dev/null 2>&1; then \
		pdflatex -interaction=nonstopmode -halt-on-error $(TEX); \
		bibtex $(basename $(TEX)); \
		pdflatex -interaction=nonstopmode -halt-on-error $(TEX); \
		pdflatex -interaction=nonstopmode -halt-on-error $(TEX); \
	else \
		echo "No suitable LaTeX toolchain found. Install latexmk, or install both pdflatex and bibtex to build $(PDF)."; \
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

$(RESULT_SECTION_TEX) $(APPENDIX_RESULT_TEX) data/benchmark_summary.csv $(LAST_VALUE_DATA) &: scripts/generate_benchmark_results.py $(BENCHMARK_DATA) $(BENCHMARK_METADATA) $(BENCHMARK_SOURCE_DATA)
	$(PYTHON) scripts/generate_benchmark_results.py

$(FIGURE_OUTPUTS) &: figures/generate_benchmark_overview.py $(BENCHMARK_DATA) $(LAST_VALUE_DATA)
	$(PYTHON) figures/generate_benchmark_overview.py

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
	rm -f $(PDF) $(DOT_FIGURES) $(FIGURE_OUTPUTS) $(RESULT_SECTION_TEX) $(APPENDIX_RESULT_TEX)

help:
	@echo "Targets:"
	@echo "  make pdf       Build $(PDF)"
	@echo "  make financial-assets Validate complete financial evidence and generate tables/figures"
	@echo "  make watch     Rebuild continuously with latexmk"
	@echo "  make clean     Remove auxiliary LaTeX files"
	@echo "  make distclean Remove auxiliary files and $(PDF)"
