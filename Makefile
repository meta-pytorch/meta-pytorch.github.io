# Minimal makefile for Sphinx documentation

SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = source
BUILDDIR      = build

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile generate clean html

# Generate projects.json and search-index.json from projects.yaml
generate:
	@SPHINXPY=$$(head -1 "$$(which $(SPHINXBUILD))" | sed 's/^#!//') && \
	$$SPHINXPY generate.py

# Generate (offline, no sitemap crawling)
generate-offline:
	@SPHINXPY=$$(head -1 "$$(which $(SPHINXBUILD))" | sed 's/^#!//') && \
	$$SPHINXPY generate.py --offline

# Run generate before building HTML
html: generate
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

html-no-clean:
	@$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)/html" $(SPHINXOPTS) $(O)

clean:
	rm -rf $(BUILDDIR)/*

%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
