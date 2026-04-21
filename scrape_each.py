"""
Scrape each AMC 10 problem page individually to read its category tags.

AoPS wiki pages have category links at the bottom like:
  Category:Introductory_Algebra_Problems
  Category:Intermediate_Geometry_Problems
  etc.

We map those to our 4 topic buckets. This gives much better coverage
than only reading the category index pages.
"""

import csv
import re
import time
from pathlib import Path

import requests
from html.parser import HTMLParser

DATA_DIR = Path(__file__).resolve().parent / "data"
USER_AGENT = "amc10-research/0.1 (educational use)"
REQ_DELAY = 0.5  # be polite

# Map AoPS category slugs to our 4 topics
SLUG_TO_TOPIC = {}
for level in ("Introductory", "Intermediate", "Advanced"):
    SLUG_TO_TOPIC[f"{level}_Algebra_Problems"] = "Algebra"
    SLUG_TO_TOPIC[f"{level}_Geometry_Problems"] = "Geometry"
    SLUG_TO_TOPIC[f"{level}_Combinatorics_Problems"] = "Counting & Probability"
    SLUG_TO_TOPIC[f"{level}_Number_Theory_Problems"] = "Number Theory"
# Extra variants
SLUG_TO_TOPIC["Introductory_Counting_and_Probability_Problems"] = "Counting & Probability"
SLUG_TO_TOPIC["Intermediate_Counting_and_Probability_Problems"] = "Counting & Probability"


class CategoryExtractor(HTMLParser):
    """Extract category links from an AoPS problem page."""

    def __init__(self):
        super().__init__()
        self.categories = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href", "")
        # Category links look like: /wiki/index.php?title=Category:Introductory_Algebra_Problems
        # or /wiki/index.php/Category:...
        m = re.search(r"Category:(\w+)", href)
        if m:
            slug = m.group(1)
            if slug in SLUG_TO_TOPIC:
                topic = SLUG_TO_TOPIC[slug]
                if topic not in self.categories:
                    self.categories.append(topic)


def fetch(url: str) -> str | None:
    time.sleep(REQ_DELAY)
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        if r.status_code == 200:
            return r.text
        print(f"  HTTP {r.status_code}: {url}")
        return None
    except Exception as e:
        print(f"  ERROR: {url} -> {e}")
        return None


def scrape_problem_category(url: str) -> str:
    """Fetch one problem page and return its category string."""
    html = fetch(url)
    if not html:
        return "Uncategorized"
    parser = CategoryExtractor()
    parser.feed(html)
    if parser.categories:
        return "; ".join(sorted(parser.categories))
    return "Uncategorized"


def main():
    index_path = DATA_DIR / "amc10_index.csv"
    out_path = DATA_DIR / "amc10_categorized.csv"

    # Load existing categorized file if it exists (to resume)
    existing = {}
    if out_path.exists():
        with open(out_path, newline="") as f:
            for row in csv.DictReader(f):
                cat = (row.get("category") or "").strip()
                if cat and cat != "Uncategorized":
                    existing[row["problem_id"]] = cat

    with open(index_path, newline="") as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    print(f"Loaded {total} problems, {len(existing)} already categorized")

    for i, row in enumerate(rows):
        pid = row["problem_id"]
        # Skip if already categorized
        if pid in existing:
            row["category"] = existing[pid]
            continue

        url = row["problem_url"]
        cat = scrape_problem_category(url)
        row["category"] = cat

        status = "+" if cat != "Uncategorized" else "."
        if (i + 1) % 50 == 0 or i == 0:
            print(f"[{i+1}/{total}] {status} {row['contest_label']} #{row['problem_num']} -> {cat}")
        elif cat != "Uncategorized":
            print(f"[{i+1}/{total}] {status} {row['contest_label']} #{row['problem_num']} -> {cat}")

        # Save progress every 100 problems
        if (i + 1) % 100 == 0:
            _save(rows, out_path)
            print(f"  (checkpoint saved)")

    _save(rows, out_path)
    print(f"\nDone! Wrote {out_path}")

    from collections import Counter
    cats = Counter(r["category"] for r in rows)
    print("\nCategory distribution:")
    for cat, n in cats.most_common():
        print(f"  {cat}: {n}")


def _save(rows, path):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
