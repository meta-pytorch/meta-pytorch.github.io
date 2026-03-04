#!/usr/bin/env python3
"""
Sitemap Generator for meta-pytorch.org

This script generates a unified sitemap by:
1. Reading projects from projects.yaml
2. Fetching individual project sitemaps
3. Generating a single sitemap.xml with all URLs

Can be run locally or via GitHub Actions.

Usage:
    python scripts/generate_sitemap.py

Options:
    --validate   Only validate that all project sitemaps exist
"""

import argparse
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional
from xml.dom import minidom
from xml.etree import ElementTree as ET

import yaml

# Configuration
BASE_URL = "https://meta-pytorch.org"
PROJECTS_YAML_PATH = "projects.yaml"
SITEMAP_OUTPUT_PATH = "sitemap.xml"

# URL normalization: map alternative domains to canonical domain
URL_REPLACEMENTS = {
    "https://meta-pytorch.github.io": "https://meta-pytorch.org",
}

# XML namespaces
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
ET.register_namespace("", SITEMAP_NS)


def normalize_url(url: str) -> str:
    """Normalize URL to use canonical domain."""
    if url:
        for old_domain, new_domain in URL_REPLACEMENTS.items():
            url = url.replace(old_domain, new_domain)
    return url


def prettify_xml(elem: ET.Element) -> str:
    """Return a pretty-printed XML string with proper indentation."""
    rough_string = ET.tostring(elem, encoding="unicode")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ", encoding=None)


def load_projects(projects_path: str) -> list:
    """Load projects from projects.yaml file."""
    with open(projects_path, "r") as f:
        return yaml.safe_load(f)


def fetch_sitemap(url: str, timeout: int = 10) -> Optional[ET.Element]:
    """Fetch and parse a sitemap from a URL."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            content = response.read()
            return ET.fromstring(content)
    except (urllib.error.URLError, urllib.error.HTTPError, ET.ParseError) as e:
        print(f"Warning: Could not fetch sitemap from {url}: {e}")
        return None


def get_project_sitemap_url(project: dict) -> Optional[str]:
    """Get the sitemap URL for a project.

    Uses the 'sitemap' field if specified, otherwise defaults to {docs}/sitemap.xml.
    Returns None if sitemap is explicitly set to null.
    """
    if "sitemap" in project:
        return project["sitemap"]  # Could be a URL or None
    docs_url = project.get("docs", "").rstrip("/")
    return f"{docs_url}/sitemap.xml"


def generate_sitemap(projects: list) -> str:
    """Generate a unified sitemap with all URLs from all projects."""
    root = ET.Element("urlset", xmlns=SITEMAP_NS)
    today = datetime.now().strftime("%Y-%m-%d")

    # Add main site URL
    url_elem = ET.SubElement(root, "url")
    loc = ET.SubElement(url_elem, "loc")
    loc.text = f"{BASE_URL}/"
    lastmod = ET.SubElement(url_elem, "lastmod")
    lastmod.text = today
    priority = ET.SubElement(url_elem, "priority")
    priority.text = "1.0"
    changefreq = ET.SubElement(url_elem, "changefreq")
    changefreq.text = "weekly"

    # Fetch and merge each project's sitemap
    for project in projects:
        sitemap_url = get_project_sitemap_url(project)
        if sitemap_url is None:
            # Project has no sitemap, just add the docs root URL
            url_elem = ET.SubElement(root, "url")
            loc = ET.SubElement(url_elem, "loc")
            loc.text = normalize_url(project.get("docs", "").rstrip("/") + "/")
            lastmod = ET.SubElement(url_elem, "lastmod")
            lastmod.text = today
            priority = ET.SubElement(url_elem, "priority")
            priority.text = "0.8"
            continue

        print(f"Fetching sitemap: {sitemap_url}")

        sitemap_root = fetch_sitemap(sitemap_url)
        if sitemap_root is None:
            # If sitemap doesn't exist, at least add the docs root
            url_elem = ET.SubElement(root, "url")
            loc = ET.SubElement(url_elem, "loc")
            loc.text = normalize_url(project.get("docs", "").rstrip("/") + "/")
            lastmod = ET.SubElement(url_elem, "lastmod")
            lastmod.text = today
            priority = ET.SubElement(url_elem, "priority")
            priority.text = "0.8"
            continue

        # Extract all URL entries from the project sitemap
        for url_entry in sitemap_root.findall(f".//{{{SITEMAP_NS}}}url"):
            # Clone the URL entry to our unified sitemap
            new_url = ET.SubElement(root, "url")
            has_lastmod = False
            for child in url_entry:
                tag_name = child.tag.replace(f"{{{SITEMAP_NS}}}", "")
                new_child = ET.SubElement(new_url, tag_name)
                # Normalize URLs in <loc> elements to use canonical domain
                if tag_name == "loc":
                    new_child.text = normalize_url(child.text)
                else:
                    new_child.text = child.text
                if tag_name == "lastmod":
                    has_lastmod = True
            # Add lastmod if not present in source sitemap
            if not has_lastmod:
                lastmod = ET.SubElement(new_url, "lastmod")
                lastmod.text = today

    return prettify_xml(root)


def validate_sitemaps(projects: list) -> bool:
    """Check that all project sitemaps are accessible."""
    all_valid = True
    for project in projects:
        sitemap_url = get_project_sitemap_url(project)
        if sitemap_url is None:
            print(f"Skipping {project.get('id', 'unknown')}: no sitemap configured")
            continue

        print(f"Validating: {sitemap_url} ... ", end="")

        if fetch_sitemap(sitemap_url) is not None:
            print("OK")
        else:
            print("MISSING or INVALID")
            all_valid = False

    return all_valid


def main():
    parser = argparse.ArgumentParser(
        description="Generate sitemap for meta-pytorch.org"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Only validate that all project sitemaps exist",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=".",
        help="Output directory for generated sitemap",
    )

    args = parser.parse_args()

    # Determine script directory and project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)

    # Load projects
    print(f"Loading projects from {PROJECTS_YAML_PATH}...")
    projects = load_projects(PROJECTS_YAML_PATH)
    print(f"Found {len(projects)} projects")

    if args.validate:
        print("\nValidating project sitemaps...")
        if validate_sitemaps(projects):
            print("\nAll sitemaps are valid!")
            sys.exit(0)
        else:
            print("\nSome sitemaps are missing or invalid.")
            sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate sitemap
    print("\nGenerating sitemap...")
    sitemap = generate_sitemap(projects)
    sitemap_path = output_dir / SITEMAP_OUTPUT_PATH
    with open(sitemap_path, "w") as f:
        f.write(sitemap)
    print(f"Saved sitemap to {sitemap_path}")

    print("\nDone!")


if __name__ == "__main__":
    main()
