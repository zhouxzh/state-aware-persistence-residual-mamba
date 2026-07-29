TEX := main.tex
PDF := main.pdf
PYTHON ?= conda run --no-capture-output -n mamba python
ARCH_TEX := $(wildcard arch/*.tex)
DOT_SOURCES := $(wildcard figures/*.dot)
DOT_FIGURES := $(DOT_SOURCES:.dot=.pdf)
SECTION_TEX := $(wildcard sections/*.tex)
APPENDIX_TEX := $(wildcard sections/appendix/*.tex)
SELECTION_DIAGNOSTICS := \
	../data/financial/manifests/nonstationarity_diagnostics_selection_safe.json \
	../data/financial/manifests/quality_report.json \
	../configs/financial_benchmark.json
SELECTION_FIGURES := \
	figures/financial_nonstationarity_selection_safe.pdf \
	figures/financial_nonstationarity_selection_safe.png
FINAL_GENERATED_TEX := \
	sections/results_financial_confirmatory.tex \
	sections/appendix/financial_protocol.tex

.PHONY: pdf selection-assets financial-assets clean distclean watch help

pdf: $(PDF)

financial-assets:
	$(PYTHON) ../scripts/financial/analyze_financial_results.py
	$(PYTHON) ../scripts/financial/analyze_financial_data.py --include-test
	$(PYTHON) scripts/generate_financial_results.py
	$(PYTHON) figures/generate_financial_results.py
	$(PYTHON) figures/generate_financial_data_diagnostics.py --include-test

selection-assets: $(SELECTION_FIGURES)

$(PDF): $(TEX) references.bib $(ARCH_TEX) $(DOT_FIGURES) $(SECTION_TEX) $(APPENDIX_TEX) $(SELECTION_FIGURES)
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

$(SELECTION_FIGURES) &: figures/generate_financial_data_diagnostics.py $(SELECTION_DIAGNOSTICS)
	$(PYTHON) figures/generate_financial_data_diagnostics.py

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
	rm -f $(PDF) $(DOT_FIGURES) $(SELECTION_FIGURES) $(FINAL_GENERATED_TEX)

help:
	@echo "Targets:"
	@echo "  make pdf       Build the protocol-aligned interim $(PDF)"
	@echo "  make selection-assets Regenerate train/validation-only diagnostics"
	@echo "  make financial-assets Validate complete financial evidence and generate tables/figures"
	@echo "  make watch     Rebuild continuously with latexmk"
	@echo "  make clean     Remove auxiliary LaTeX files"
	@echo "  make distclean Remove auxiliary files and $(PDF)"
