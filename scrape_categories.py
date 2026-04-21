"""
Scrape AoPS wiki category pages to classify AMC 10 problems.

Fetches ~4 category index pages (with pagination) instead of 1300+
individual problem pages. Writes data/amc10_categorized.csv.
"""

import csv
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from html.parser import HTMLParser

AOPS_BASE = "https://artofproblemsolving.com/wiki/index.php"
USER_AGENT = "amc10-research/0.1 (educational use)"
REQ_DELAY = 1.0

CATEGORIES = {
    "Algebra": [
        "Introductory_Algebra_Problems",
        "Intermediate_Algebra_Problems",
    ],
    "Geometry": [
        "Introductory_Geometry_Problems",
        "Intermediate_Geometry_Problems",
    ],
    "Counting & Probability": [
        "Introductory_Combinatorics_Problems",
        "Intermediate_Combinatorics_Problems",
    ],
    "Number Theory": [
        "Introductory_Number_Theory_Problems",
        "Intermediate_Number_Theory_Problems",
    ],
}

DATA_DIR = Path(__file__).resolve().parent / "data"

# Regex matching AMC 10 problem URLs (both /wiki/index.php/... and ?title=... forms)
AMC10_RE = re.compile(r"AMC_10[ABP]?_Problems/Problem_\d+$")


class CategoryPageParser(HTMLParser):
    """Extract links from #mw-pages section of an AoPS category page."""

    def __init__(self):
        super().__init__()
        self.in_mw_pages = False
        self.links = []
        self.next_page_url = None
        self._current_href = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "div" and attrs_dict.get("id") == "mw-pages":
            self.in_mw_pages = True
        if self.in_mw_pages and tag == "a":
            self._current_href = attrs_dict.get("href", "")

    def handle_data(self, data):
        if self.in_mw_pages and self._current_href:
            href = self._current_href
            # Check if it's an AMC 10 problem link
            if AMC10_RE.search(href):
                self.links.append(href)
            # Check for pagination ("next page" or "next 200")
            if re.search(r"(?i)next (page|\d+)", data):
                self.next_page_url = href
            self._current_href = None

    def handle_endtag(self, tag):
        if tag == "a":
            self._current_href = None


def fetch(url: str) -> str | None:
    time.sleep(REQ_DELAY)
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  ERROR fetching {url}: {e}")
        return None


def scrape_category(slug: str) -> list[str]:
    """Scrape all AMC 10 problem URLs from one AoPS category (with pagination)."""
    url = f"{AOPS_BASE}?title=Category:{slug}"
    all_urls = []
    visited = set()
    page = 0

    while url and url not in visited:
        visited.add(url)
        page += 1
        print(f"  page {page}: {url}")
        html = fetch(url)
        if not html:
            break

        parser = CategoryPageParser()
        parser.feed(html)

        for href in parser.links:
            # Normalize to canonical form: /wiki/index.php/SLUG
            # Category pages link as ?title=SLUG, index uses /SLUG
            slug = href.split("title=")[-1] if "title=" in href else href.split("/wiki/index.php/")[-1]
            canonical = f"https://artofproblemsolving.com/wiki/index.php/{slug}"
            if canonical not in all_urls:
                all_urls.append(canonical)

        if parser.next_page_url:
            url = f"https://artofproblemsolving.com{parser.next_page_url}"
        else:
            url = None

    print(f"  -> {len(all_urls)} problems")
    return all_urls


def build_category_lookup() -> dict[str, str]:
    """Returns {problem_url: category} mapping."""
    url_to_cats: dict[str, list[str]] = {}

    for cat_name, slugs in CATEGORIES.items():
        print(f"\n== {cat_name} ==")
        for slug in slugs:
            urls = scrape_category(slug)
            for u in urls:
                url_to_cats.setdefault(u, []).append(cat_name)

    # Join multiple categories with "; "
    return {url: "; ".join(sorted(set(cats))) for url, cats in url_to_cats.items()}


def main():
    index_path = DATA_DIR / "amc10_index.csv"
    out_path = DATA_DIR / "amc10_categorized.csv"

    with open(index_path, newline="") as f:
        rows = list(csv.DictReader(f))
    print(f"Loaded {len(rows)} problems from index")

    lookup = build_category_lookup()
    print(f"\nMatched {len(lookup)} problem URLs to categories")

    # Merge
    for row in rows:
        row["category"] = lookup.get(row["problem_url"], "Uncategorized")

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {out_path}")

    # Stats
    from collections import Counter
    cats = Counter(r["category"] for r in rows)
    print("\nCategory distribution:")
    for cat, n in cats.most_common():
        print(f"  {cat}: {n}")


if __name__ == "__main__":
    main()
