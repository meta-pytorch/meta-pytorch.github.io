import os

import pytorch_sphinx_theme2

project = "Meta-PyTorch"
copyright = "Meta Platforms, Inc"
author = "Meta Platforms, Inc"

extensions = [
    "myst_parser",
    "pytorch_sphinx_theme2",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

templates_path = [
    "_templates",
    os.path.join(os.path.dirname(pytorch_sphinx_theme2.__file__), "templates"),
]
exclude_patterns = []

html_theme = "pytorch_sphinx_theme2"
html_theme_path = [pytorch_sphinx_theme2.get_html_theme_path()]

html_theme_options = {
    "pytorch_project": "meta-pytorch",
    "display_version": False,
    "canonical_url": "https://meta-pytorch.org/",
    "navbar_start": ["navbar-logo"],
    "navbar_center": ["navbar-nav"],
    "navbar_end": ["theme-switcher", "navbar-icon-links"],
    "navbar_persistent": [],
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/meta-pytorch",
            "icon": "fa-brands fa-github",
        },
    ],
    "show_lf_header": False,
    "show_lf_footer": False,
    "show_prev_next": False,
    "use_edit_page_button": False,
    "show_pytorch_org_link": True,
    "secondary_sidebar_items": [],
    "article_header_end": "",
    "article_footer_items": [],
}

html_title = "Meta-PyTorch"
html_static_path = ["_static"]
html_css_files = ["css/custom.css"]
html_show_sourcelink = False
html_sidebars = {"**": []}
html_favicon = "_static/favicon.svg"
