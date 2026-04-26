TEX := main.tex
PDF := main.pdf
DOT_SOURCES := $(wildcard figures/*.dot)
DOT_FIGURES := $(DOT_SOURCES:.dot=.pdf)

.PHONY: pdf clean distclean watch help

pdf: $(PDF)

$(PDF): $(TEX) $(DOT_FIGURES)
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

distclean: clean
	rm -f $(PDF) $(DOT_FIGURES)

help:
	@echo "Targets:"
	@echo "  make pdf       Build $(PDF)"
	@echo "  make watch     Rebuild continuously with latexmk"
	@echo "  make clean     Remove auxiliary LaTeX files"
	@echo "  make distclean Remove auxiliary files and $(PDF)"
