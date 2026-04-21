"""
Classify AMC 10 problems by scraping contest pages for problem text,
then applying keyword-based classification.

Only ~53 HTTP requests (one per contest page, each has 25 problems).
"""

import csv
import re
import time
from pathlib import Path
from html.parser import HTMLParser

import requests

DATA_DIR = Path(__file__).resolve().parent / "data"
USER_AGENT = "amc10-research/0.1 (educational use)"
REQ_DELAY = 1.0


# ── Keyword rules ────────────────────────────────────────────────

GEOMETRY_KW = [
    r"\btriangle\b", r"\bcircle\b", r"\bsquare\b", r"\brectangle\b",
    r"\bangle\b", r"\bpolygon\b", r"\barea\b", r"\bperimeter\b",
    r"\bradius\b", r"\bdiameter\b", r"\bparallel\b", r"\bperpendicular\b",
    r"\bmidpoint\b", r"\bbisect", r"\bchord\b", r"\btangent\b",
    r"\bcircumscrib", r"\binscrib", r"\bhypotenuse\b", r"\bquadrilateral\b",
    r"\brhombus\b", r"\btrapezoid\b", r"\bparallelogram\b", r"\bcube\b",
    r"\bsphere\b", r"\bcylinder\b", r"\bcone\b", r"\bpyramid\b",
    r"\bdiagonal\b", r"\bcongruent\b", r"\bsimilar\b", r"\bisosceles\b",
    r"\bequilateral\b", r"\bright angle\b", r"\bvertex\b", r"\bvertices\b",
    r"\barc\b", r"\bsector\b", r"\bhexagon\b", r"\bpentagon\b",
    r"\boctagon\b", r"\brectangular\b", r"\bcircular\b",
    r"\bAB\b.*=.*\d", r"\bBC\b.*=.*\d", r"\bAC\b.*=.*\d",
    r"\bline\b.*\bsegment\b", r"\bcoordinate\b",
    r"\bslope\b", r"\bdistance\b.*\bpoint",
]

NUMBER_THEORY_KW = [
    r"\bprime\b", r"\bdivisor\b", r"\bfactor\b", r"\bremainder\b",
    r"\bdivisible\b", r"\bdigit\b", r"\bgcd\b", r"\blcm\b",
    r"\bmodulo\b", r"\bmod\b", r"\binteger\b.*\bdivid",
    r"\bperfect square\b", r"\bperfect cube\b",
    r"\beven\b.*\bodd\b", r"\bodd\b.*\beven\b",
    r"\bmultiple\b.*\bof\b", r"\bbase\b.*\b\d+\b.*\brepresent",
    r"\bcoprime\b", r"\brelatively prime\b",
    r"\beuler\b", r"\bphi\b.*\bfunction\b",
    r"\bcongruent\b.*\bmod", r"\bdivides\b",
    r"\bpositive divisor", r"\bnumber of divisor",
    r"\bsum of digits\b", r"\bproduct of digits\b",
    r"\brepresent.*base\b",
]

COUNTING_KW = [
    r"\bhow many\b", r"\bprobability\b", r"\bcombination\b",
    r"\bpermutation\b", r"\barrange\b", r"\bchoose\b", r"\bchoices\b",
    r"\bways\b", r"\bselect\b.*\bfrom\b",
    r"\brandom\b", r"\bdice\b", r"\bdie\b", r"\bcoin\b",
    r"\bdeck\b", r"\bcard\b", r"\bdrawn\b",
    r"\bcommittee\b", r"\bsubset\b", r"\bpath\b.*\bgrid\b",
    r"\blicense plate\b", r"\bnumber of ways\b",
    r"\bat least one\b", r"\bexactly\b.*\bof\b.*\bare\b",
    r"\bindistinguishable\b", r"\bdistinguishable\b",
    r"\b\d+!\b", r"\bbinom\b", r"\bcounted\b",
    r"\bfavorable\b", r"\boutcome\b",
    r"\bhow many.*integers\b",
]

ALGEBRA_KW = [
    r"\bequation\b", r"\bsolve\b", r"\bfunction\b",
    r"\bsequence\b", r"\bpolynomial\b", r"\broot\b",
    r"\binequality\b", r"\bvariable\b",
    r"\barithmetic\b.*\b(sequence|progression|mean)\b",
    r"\bgeometric\b.*\b(sequence|progression|mean)\b",
    r"\bquadratic\b", r"\blinear\b",
    r"\blog\b", r"\blogarithm\b", r"\bexponent\b",
    r"\bratio\b", r"\bproportion\b",
    r"\baverage\b", r"\bmean\b", r"\bmedian\b",
    r"\bmaximum\b", r"\bminimum\b",
    r"\bf\(x\)", r"\bg\(x\)", r"\bf\(", r"\bg\(",
    r"\bx\s*=\b", r"\by\s*=\b",
    r"\breal number\b", r"\bpositive integer\b",
    r"\bx\^2\b", r"\bx\^3\b",
    r"\bsystem\b.*\bequation\b",
    r"\bsum\b.*\bseries\b", r"\brecursive\b", r"\brecurrence\b",
    r"\bpercent\b", r"\bratio\b",
    r"\bincrease\b", r"\bdecrease\b",
    r"\bprofit\b", r"\bcost\b", r"\bprice\b", r"\bdiscount\b",
    r"\bspeed\b", r"\brate\b", r"\bwork\b.*\btogether\b",
    r"\bage\b.*\byears\b",
    r"\bset\b.*\b(of|contains)\b", r"\bvalue of\b",
    r"\bsimplif", r"\bexpression\b", r"\bevaluat",
    r"\bfraction\b", r"\bnumerator\b", r"\bdenominator\b",
    r"\blargest\b", r"\bsmallest\b", r"\bgreater\b", r"\bless\b",
    r"\bdollar\b", r"\bmoney\b", r"\bpaid\b", r"\bearns?\b",
    r"\bmiles?\b.*\bhour\b", r"\bminutes?\b",
    r"\boperations?\b", r"\bcompute\b",
    r"\bwhat is\b", r"\bfind\b.*\bvalue\b",
    r"\bsatisf(y|ies)\b",
    r"\breciprocal\b", r"\babsolute value\b",
    r"\bfloor\b", r"\bceiling\b", r"\bceil\b",
]


def classify_text(text: str) -> str:
    """Classify problem text into a topic using keyword matching."""
    text_lower = text.lower()

    scores = {
        "Geometry": 0,
        "Number Theory": 0,
        "Counting & Probability": 0,
        "Algebra": 0,
    }

    for pat in GEOMETRY_KW:
        if re.search(pat, text_lower):
            scores["Geometry"] += 1

    for pat in NUMBER_THEORY_KW:
        if re.search(pat, text_lower):
            scores["Number Theory"] += 1

    for pat in COUNTING_KW:
        if re.search(pat, text_lower):
            scores["Counting & Probability"] += 1

    for pat in ALGEBRA_KW:
        if re.search(pat, text_lower):
            scores["Algebra"] += 1

    # Disambiguate: "how many integers" with "divisor" -> Number Theory
    if scores["Number Theory"] > 0 and scores["Counting & Probability"] > 0:
        # If strong NT signal, prefer NT
        if scores["Number Theory"] >= scores["Counting & Probability"]:
            scores["Counting & Probability"] = max(0, scores["Counting & Probability"] - 1)

    best = max(scores, key=scores.get)
    if scores[best] == 0:
        # Last-resort: default to Algebra (most general AMC topic)
        return "Algebra"
    return best


# ── HTML parsing (regex-based, much more reliable) ───────────────

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


def strip_html(html_fragment: str) -> str:
    """Remove HTML tags, keep LaTeX ($...$) and plain text."""
    # Keep content inside <img alt="..."> as text (LaTeX renders)
    text = re.sub(r'<img[^>]*alt="([^"]*)"[^>]*>', r' \1 ', html_fragment)
    # Remove all other tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def scrape_contest_page(url: str) -> dict[int, str]:
    """Fetch a contest page and return {problem_num: problem_text}."""
    html = fetch(url)
    if not html:
        return {}

    problems = {}

    # Split by Problem N headings: <span class="mw-headline" id="Problem_N">
    # or <h2> containing "Problem N"
    pattern = r'id="Problem_(\d+)"'
    splits = list(re.finditer(pattern, html))

    for i, m in enumerate(splits):
        pnum = int(m.group(1))
        start = m.end()
        # End at the next heading or next Problem_N or "Solution" or "See Also"
        if i + 1 < len(splits):
            end = splits[i + 1].start()
        else:
            end = len(html)
        chunk = html[start:end]

        # Cut at "Solution" heading if present
        sol_match = re.search(r'id="Solution', chunk)
        if sol_match:
            chunk = chunk[:sol_match.start()]
        # Also cut at "See Also"
        see_match = re.search(r'id="See_Also', chunk)
        if see_match:
            chunk = chunk[:see_match.start()]

        text = strip_html(chunk)

        # Remove "Problem N" prefix if it got included
        text = re.sub(r'^Problem\s+\d+\s*', '', text)

        if text:
            problems[pnum] = text

    return problems


def main():
    index_path = DATA_DIR / "amc10_index.csv"
    out_path = DATA_DIR / "amc10_categorized.csv"

    with open(index_path, newline="") as f:
        rows = list(csv.DictReader(f))

    # Group by contest_url
    contests = {}
    for row in rows:
        cu = row["contest_url"]
        if cu not in contests:
            contests[cu] = []
        contests[cu].append(row)

    print(f"Loaded {len(rows)} problems across {len(contests)} contests")
    print(f"Scraping {len(contests)} contest pages...\n")

    classified = 0
    unclassified = 0

    for i, (contest_url, contest_rows) in enumerate(contests.items()):
        label = contest_rows[0]["contest_label"]
        print(f"[{i+1}/{len(contests)}] {label}")

        problems = scrape_contest_page(contest_url)

        for row in contest_rows:
            pnum = int(row["problem_num"])
            text = problems.get(pnum, "")
            if text:
                cat = classify_text(text)
                row["category"] = cat
                if cat != "Uncategorized":
                    classified += 1
                else:
                    unclassified += 1
            else:
                row["category"] = "Uncategorized"
                unclassified += 1

    # Save
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone! Classified: {classified}, Uncategorized: {unclassified}")
    print(f"Wrote {out_path}")

    from collections import Counter
    cats = Counter(r["category"] for r in rows)
    print("\nCategory distribution:")
    for cat, n in cats.most_common():
        print(f"  {cat}: {n}")


if __name__ == "__main__":
    main()
