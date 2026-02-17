# meta-pytorch.github.io

Landing page and project hub for the [meta-pytorch](https://github.com/meta-pytorch) GitHub organization.

**Live site:** [meta-pytorch.org](https://meta-pytorch.org/)

## Quick start

```bash
pip install -r requirements.txt
make html
# Open build/html/index.html in a browser
```

`make html` automatically runs `generate.py` which:
1. Reads **`projects.yaml`** (the single source of truth for all projects)
2. Crawls each project's docs sitemap to discover pages
3. Generates `source/_static/projects.json` (powers project cards)
4. Generates `source/_static/search-index.json` (powers Lunr.js search)
5. Builds the Sphinx site

For faster builds without network access:
```bash
make generate-offline  # use only YAML data, skip sitemap crawling
make html-no-clean     # build without re-generating
```

## Adding a new project

Edit **`projects.yaml`** at the repo root. Add a new entry like:

```yaml
- id: myproject
  title: MyProject
  repo: myproject            # GitHub repo name under meta-pytorch org
  category: Training         # Category label shown on the card
  description: >-
    One-line description of the project.
  docs: https://meta-pytorch.org/myproject/   # optional, defaults to this
  keywords: >-                                # optional, improves search
    keyword1 keyword2 keyword3
  pages:                                      # optional, manual search entries
    - title: Getting Started
      url: https://meta-pytorch.org/myproject/getting-started.html
      content: How to install and use MyProject
```

Then run `make html` — the project card and search index are generated automatically.

> **Tip:** If the project's docs site has a `sitemap.xml`, the generator will
> automatically discover all pages and add them to the search index. Manual
> `pages` entries are only needed for sites without a sitemap (e.g. GitHub READMEs).

## Project structure

```
projects.yaml                   ← SINGLE SOURCE OF TRUTH (edit this!)
generate.py                     ← Reads YAML, crawls sitemaps, writes JSON
Makefile                        ← Build orchestration
requirements.txt                ← Python dependencies
index.html                      ← Legacy redirect (GitHub Pages root)
CNAME                           ← Custom domain for GitHub Pages
404.html                        ← Custom 404 with project-aware redirects
source/
├── conf.py                     ← Sphinx configuration
├── index.md                    ← Landing page content (Markdown)
├── _templates/
│   ├── page.html               ← Custom template (hero banner for index page)
│   └── search-field.html       ← Cross-project Lunr.js search component
└── _static/
    ├── css/custom.css           ← All custom styles
    ├── js/
    │   ├── project-cards.js     ← Renders cards from projects.json
    │   └── search.js            ← Lunr.js search engine
    ├── projects.json            ← (generated) card data
    ├── search-index.json        ← (generated) search index
    └── favicon.svg              ← PyTorch flame logo
build/html/                     ← (generated) final site output
```

## How each file works

### Root-level files

#### `projects.yaml`

The **single source of truth** for every project listed on the site. Each entry
defines an `id`, `title`, `repo`, `category`, `description`, and optional fields
like `docs` (URL), `keywords` (for search relevance), and `pages` (manual search
entries for sites without a sitemap). Both project cards and the search index are
generated from this file — you never need to touch HTML or JSON directly.

#### `generate.py`

A standalone Python script that reads `projects.yaml` and produces two JSON files
in `source/_static/`:

- **`projects.json`** — a flat list of project metadata (id, title, repo,
  category, description, docs URL, GitHub URL) consumed by `project-cards.js` to
  render the card grid.
- **`search-index.json`** — a richer structure that includes each project's
  metadata *plus* individual sub-pages (title, URL, content snippet) consumed by
  `search.js` to power Lunr.js search.

When run **online** (the default), the script crawls each project's docs site for
a `sitemap.xml`, fetches every discovered page, and extracts its `<title>` and
`<meta name="description">` to populate the search index automatically. Sphinx
build artifacts (e.g. `_modules/`, `genindex`) are filtered out.
When run with `--offline`, it skips all network requests and uses only the data
already present in the YAML (useful for fast local iteration).

#### `Makefile`

Orchestrates the build. Key targets:

| Target              | What it does |
|---------------------|-------------|
| `make html`         | Runs `generate.py` (online) then `sphinx-build -M html` |
| `make generate`     | Runs `generate.py` alone (online) |
| `make generate-offline` | Runs `generate.py --offline` |
| `make html-no-clean`| Sphinx build only — skips regeneration |
| `make clean`        | Deletes `build/` |

The Makefile discovers the Python interpreter from the `sphinx-build` shebang
line so the generate script runs in the same virtual environment as Sphinx.

#### `requirements.txt`

Python dependencies: `sphinx`, `pytorch_sphinx_theme2` (the PyTorch docs theme),
`myst-parser` (Markdown support for Sphinx), and `pyyaml` (for reading
`projects.yaml`).

#### `index.html`

A **legacy redirect page** at the repo root. Before the Sphinx site existed,
this was the GitHub Pages entry point. It simply redirects visitors to the
GitHub organization page (`https://github.com/meta-pytorch`). Once `build/html/`
is deployed, this file is only reached if someone accesses the raw repo root
on a misconfigured setup.

#### `CNAME`

Contains the custom domain `meta-pytorch.org`. GitHub Pages reads this file to
configure DNS for the custom domain.

#### `404.html`

A **project-aware 404 handler** at the repo root. When a visitor hits a
non-existent URL, this page inspects the first path segment (e.g. `/forge/...`)
and checks a `PROJECTS` mapping. If a redirect rule exists for that project, the
visitor is forwarded to the new location (useful for project renames — e.g.
`/forge/` → `/torchforge/`). Unrecognized paths fall back to the site root.

### `source/` — Sphinx source tree

#### `source/conf.py`

Sphinx configuration. Highlights:

- Uses `pytorch_sphinx_theme2` as the HTML theme with Meta-PyTorch branding.
- Enables `myst_parser` so pages can be written in Markdown.
- Disables sidebars, version display, prev/next navigation, and source links for
  a clean landing-page feel.
- Registers `_static/css/custom.css` as an extra stylesheet.
- Sets Open Graph / Twitter card metadata through `html_theme_options`.

#### `source/index.md`

The landing page content in MyST Markdown. It contains:

1. A raw HTML block with an empty `<div id="project-grid">` — the project cards
   are injected here at runtime by `project-cards.js`.
2. A **Getting started** section pointing visitors to individual project docs.
3. A **Contributing** section linking to the org-wide contribution guide.

#### `source/_templates/page.html`

A Jinja2 template that extends the theme's `layout.html`. On the **index page
only**, it:

- Injects Open Graph and Twitter Card `<meta>` tags for social sharing.
- Replaces the default navbar with a **hero banner** containing the site title,
  tagline, a "GitHub" CTA button, and an inline search bar.
- Loads `project-cards.js`, `search.js`, and the Lunr.js library via `<script>`
  tags.
- Sets `window.__projectsURL` and `window.__searchIndexURL` so the JS files
  resolve the correct paths to the generated JSON files regardless of deploy
  context.

On all other pages it falls back to the default theme layout (`{{ super() }}`).

#### `source/_templates/search-field.html`

A reusable Jinja2 partial that renders a standalone search input wired to
Lunr.js. It loads the Lunr library, sets the search index URL, and includes
`search.js`. This template can be included on any page to add cross-project
search (currently used in the hero banner via `page.html`).

### `source/_static/` — Static assets

#### `source/_static/css/custom.css`

All custom styles for the site, organized into sections:

- **Hero** — gradient banner, title, tagline, CTA button, and inline search bar
  (with focus states that transition from translucent to opaque).
- **Project grid & cards** — responsive CSS Grid layout
  (`repeat(auto-fill, minmax(280px, 1fr))`), card borders, category tags, star
  count badges, and GitHub/Docs link row.
- **Search dropdown** — absolutely positioned results panel with result items,
  URL previews, "no results" state, and a Google fallback link.
- **Dark mode** — every component has a `html[data-theme="dark"]` variant that
  adjusts colors for the theme switcher.

#### `source/_static/js/project-cards.js`

Runs on `DOMContentLoaded`. Fetches `projects.json`, creates a `<div>` card for
each project (category tag, title, description, GitHub/Docs links), and appends
them to `#project-grid`. After rendering, it makes parallel GitHub API requests
(`/repos/meta-pytorch/<repo>`) to fetch live star counts, appends a ★ badge to
each card title, and **re-sorts the grid by stars descending** so the most
popular projects appear first.

#### `source/_static/js/search.js`

Implements cross-project search in the browser:

1. **Initialization** — Fetches `search-index.json`, flattens it into one entry
   per project + one entry per sub-page, and builds a Lunr.js index with boosted
   fields (`title` ×10, `category` ×2, `body` ×1).
2. **Search** — On each keystroke (debounced 150 ms), runs a wildcard query
   (`query*`) combined with an exact-match query, deduplicates by URL, and
   returns the top 10 results.
3. **Rendering** — Displays results in a dropdown with title, URL preview, and a
   "More results on Google" fallback link (scoped to
   `site:github.com/meta-pytorch OR site:meta-pytorch.org`).
4. **UX** — Handles focus/blur, `Escape` to close, and form submission (opens
   the first result or falls back to Google).

#### `source/_static/projects.json` *(generated)*

A flat JSON array produced by `generate.py`. Each element contains `id`, `title`,
`repo`, `category`, `description`, `docs`, and `github` URLs. Consumed by
`project-cards.js`.

#### `source/_static/search-index.json` *(generated)*

A JSON array produced by `generate.py`. Each element contains a project's
metadata plus a `pages` array of `{ title, url, content }` objects for every
discovered sub-page. Consumed by `search.js` to build the Lunr index.

#### `source/_static/favicon.svg`

The PyTorch flame logo used as the browser tab icon.

### CI / Deployment

#### `.github/workflows/build-and-deploy.yml`

A GitHub Actions workflow that:

1. **On every push to `main` and every PR** — checks out the repo, installs
   Python 3.12 and dependencies, runs `make html`.
2. **On PR** — uploads the built site to an S3 bucket for doc previews.
3. **On push to `main`** — uploads `build/html/` as a GitHub Pages artifact and
   deploys it via `actions/deploy-pages`.

## Built with

- [Sphinx](https://www.sphinx-doc.org/) with [MyST-Parser](https://myst-parser.readthedocs.io/) (Markdown)
- [pytorch_sphinx_theme2](https://github.com/pytorch/pytorch_sphinx_theme) (PyTorch documentation theme)
- [Lunr.js](https://lunrjs.com/) (client-side search)

## Deployment

The site is deployed to GitHub Pages. The `build/html/` directory is published
to the `gh-pages` branch.
