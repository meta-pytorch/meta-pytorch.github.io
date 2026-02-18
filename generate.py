#!/usr/bin/env python3
"""Generate search-index.json and projects.json from projects.yaml.

Crawls each project's docs sitemap to discover pages, extracts titles and
descriptions, and writes the JSON files that power the site's cards and
Lunr.js search.

Usage:
    python generate.py            # crawl sitemaps and generate JSON
    python generate.py --offline  # skip crawling, use only YAML data
"""

import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECTS_YAML = os.path.join(ROOT, "projects.yaml")
STATIC_DIR = os.path.join(ROOT, "source", "_static")
SEARCH_INDEX_JSON = os.path.join(STATIC_DIR, "search-index.json")
PROJECTS_JSON = os.path.join(STATIC_DIR, "projects.json")

GITHUB_ORG = "meta-pytorch"
USER_AGENT = "meta-pytorch-site-generator/1.0"
TIMEOUT = 15  # seconds per request


# ---------------------------------------------------------------------------
# HTML title + description extractor
# ---------------------------------------------------------------------------
class _MetaExtractor(HTMLParser):
    """Extract <title> and <meta name="description"> from HTML."""

    def __init__(self):
        super().__init__()
        self.title = ""
        self.description = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            d = dict(attrs)
            if d.get("name", "").lower() == "description":
                self.description = d.get("content", "")

    def handle_data(self, data):
        if self._in_title:
            self.title += data

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False


def _fetch(url):
    """Fetch a URL and return (status_code, body_text). Returns (0, '') on error."""
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, OSError, Exception):
        return 0, ""


def _fetch_sitemap_urls(docs_url):
    """Try to fetch sitemap.xml and return a list of page URLs."""
    base = docs_url.rstrip("/")
    urls = []

    # Sitemaps can live at different paths depending on Sphinx config
    sitemap_paths = [
        "/sitemap.xml",
        "/stable/sitemap.xml",
        "/main/sitemap.xml",
        "/latest/sitemap.xml",
        "/en/stable/sitemap.xml",
        "/en/latest/sitemap.xml",
        "/sitemap_index.xml",
    ]

    for sitemap_path in sitemap_paths:
        status, body = _fetch(base + sitemap_path)
        if status != 200 or not body.strip():
            continue

        # Strip XML namespace to simplify parsing
        body = re.sub(r'\s+xmlns\s*=\s*"[^"]*"', "", body, count=1)
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            continue

        # Handle sitemap index (contains <sitemap><loc>...)
        for sitemap_el in root.iter("sitemap"):
            loc = sitemap_el.findtext("loc")
            if loc:
                sub_status, sub_body = _fetch(loc)
                if sub_status == 200 and sub_body:
                    sub_body = re.sub(r'\s+xmlns\s*=\s*"[^"]*"', "", sub_body, count=1)
                    try:
                        sub_root = ET.fromstring(sub_body)
                        for url_el in sub_root.iter("url"):
                            page_loc = url_el.findtext("loc")
                            if page_loc:
                                urls.append(page_loc)
                    except ET.ParseError:
                        pass

        # Handle regular sitemap (contains <url><loc>...)
        for url_el in root.iter("url"):
            loc = url_el.findtext("loc")
            if loc:
                urls.append(loc)

        if urls:
            break

    return urls


def _extract_page_info(url):
    """Fetch a page and extract its title and description."""
    status, body = _fetch(url)
    if status != 200:
        return None, None

    parser = _MetaExtractor()
    try:
        parser.feed(body)
    except Exception:
        pass

    title = parser.title.strip()
    desc = parser.description.strip()

    # Clean up common Sphinx title patterns like "Page — Project vX.Y docs"
    # but keep the project name portion (strip only version/docs suffix)
    if " — " in title:
        parts = title.split(" — ", 1)
        page_part = parts[0].strip()
        suffix = parts[1].strip() if len(parts) > 1 else ""
        # Remove version numbers and "documentation"/"docs" from suffix
        # e.g. "TorchComms 0.1 documentation" → "TorchComms"
        suffix = re.sub(r"\s+v?\d[\d.]*\s*", " ", suffix)
        suffix = re.sub(r"\s*(documentation|docs)\s*$", "", suffix, flags=re.IGNORECASE)
        suffix = suffix.strip()
        if suffix and suffix.lower() != page_part.lower():
            title = f"{page_part} - {suffix}"
        else:
            title = page_part

    return title or None, desc or None


def _is_crawlable(url):
    """Return True if this is a docs site we should crawl (not GitHub, HF, etc.)."""
    return not any(
        host in url for host in ["github.com", "huggingface.co", "gitlab.com"]
    )


# Paths to skip when crawling sitemaps (Sphinx build artifacts, not real content)
_SKIP_PATTERNS = [
    "/_sources/",
    "/_source/",
    "/_static/",
    "/_modules/",
    "/_downloads/",
    "/_images/",
    "/genindex",
    "/py-modindex",
    "/search.html",
    "/404.html",
    "/sg_execution_times",
    "/objects.inv",
]


def _should_skip_url(url):
    """Return True if this URL should be excluded from the search index."""
    return any(pat in url for pat in _SKIP_PATTERNS)


# ---------------------------------------------------------------------------
# Main generation logic
# ---------------------------------------------------------------------------
def generate(offline=False):
    with open(PROJECTS_YAML, "r") as f:
        projects = yaml.safe_load(f)

    search_index = []
    projects_out = []

    for proj in projects:
        pid = proj["id"]
        repo = proj["repo"]
        docs_url = proj.get("docs", f"https://meta-pytorch.org/{repo}/")
        github_url = f"https://github.com/{GITHUB_ORG}/{repo}"
        keywords = proj.get("keywords", "")
        category = proj.get("category", "")
        description = proj.get("description", "")

        # Output for project cards
        projects_out.append(
            {
                "id": pid,
                "title": proj["title"],
                "repo": repo,
                "category": category,
                "description": description,
                "docs": docs_url,
                "github": github_url,
            }
        )

        # Start building search pages from manual YAML entries
        manual_urls = set()
        pages = []
        for pg in proj.get("pages", []):
            pages.append(
                {
                    "title": pg["title"],
                    "url": pg["url"],
                    "content": pg.get("content", ""),
                }
            )
            manual_urls.add(pg["url"].rstrip("/"))

        # Crawl sitemap if online and the docs URL is crawlable
        if not offline and _is_crawlable(docs_url):
            print(f"  [{pid}] Crawling {docs_url} ...")
            sitemap_urls = _fetch_sitemap_urls(docs_url)

            if sitemap_urls:
                print(f"  [{pid}] Found {len(sitemap_urls)} pages in sitemap")
            else:
                print(f"  [{pid}] No sitemap found, skipping crawl")

            for page_url in sitemap_urls:
                if page_url.rstrip("/") in manual_urls:
                    continue  # manual entry takes priority
                if _should_skip_url(page_url):
                    continue  # skip build artifacts

                title, desc = _extract_page_info(page_url)
                if not title:
                    continue

                # Ensure project name appears in the title for search relevance
                proj_title = proj["title"]
                if proj_title.lower() not in title.lower():
                    title = f"{title} - {proj_title}"

                pages.append(
                    {
                        "title": title,
                        "url": page_url,
                        "content": desc or "",
                    }
                )

            # Deduplicate by URL
            seen = set()
            deduped = []
            for pg in pages:
                key = pg["url"].rstrip("/")
                if key not in seen:
                    seen.add(key)
                    deduped.append(pg)
            pages = deduped

        # Build search index entry for this project
        search_entry = {
            "id": pid,
            "title": proj["title"],
            "category": category,
            "description": description,
            "keywords": keywords,
            "url": docs_url,
            "pages": pages,
        }
        search_index.append(search_entry)

        print(f"  [{pid}] {len(pages)} search pages")

    # Write output files
    os.makedirs(STATIC_DIR, exist_ok=True)

    with open(SEARCH_INDEX_JSON, "w") as f:
        json.dump(search_index, f, indent=2)
    print(f"\n✓ Wrote {SEARCH_INDEX_JSON} ({len(search_index)} projects)")

    with open(PROJECTS_JSON, "w") as f:
        json.dump(projects_out, f, indent=2)
    print(f"✓ Wrote {PROJECTS_JSON} ({len(projects_out)} projects)")


if __name__ == "__main__":
    offline = "--offline" in sys.argv
    print(
        "Generating site data from projects.yaml"
        + (" (offline)" if offline else "")
        + "\n"
    )
    generate(offline=offline)
