LATEXMK ?= latexmk
LATEXFLAGS := -pdf -interaction=nonstopmode -halt-on-error -file-line-error
BUILD_DIR := build
FIGURES := pmsv5_r6_architecture all_model_architecture_gallery
FIGURE_PDFS := $(addprefix $(BUILD_DIR)/,$(addsuffix .pdf,$(FIGURES)))

.PHONY: pdf watch clean distclean

pdf: $(BUILD_DIR)/main.pdf $(FIGURE_PDFS)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/main.pdf: main.tex figure_preamble.tex \
	figures/pmsv5_r6_architecture.tex \
	figures/all_model_architecture_gallery.tex | $(BUILD_DIR)
	$(LATEXMK) $(LATEXFLAGS) -output-directory=$(BUILD_DIR) main.tex

$(BUILD_DIR)/%.pdf: previews/%.tex figures/%.tex figure_preamble.tex | $(BUILD_DIR)
	$(LATEXMK) $(LATEXFLAGS) -output-directory=$(BUILD_DIR) $<

watch:
	$(LATEXMK) -pdf -pvc -interaction=nonstopmode -output-directory=$(BUILD_DIR) main.tex

clean:
	$(LATEXMK) -C -output-directory=$(BUILD_DIR) main.tex
	$(LATEXMK) -C -output-directory=$(BUILD_DIR) previews/pmsv5_r6_architecture.tex
	$(LATEXMK) -C -output-directory=$(BUILD_DIR) previews/all_model_architecture_gallery.tex

distclean: clean
	rm -f $(BUILD_DIR)/main.pdf $(FIGURE_PDFS)

