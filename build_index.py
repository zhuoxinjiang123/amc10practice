"""
Generate the canonical index of ALL AMC 10 problems (2000-2025).

URL patterns follow AoPS wiki conventions:
  2000-2001 (single version):   2000_AMC_10_Problems/Problem_N
  2002 (A/B/P):                 2002_AMC_10{A|B|P}_Problems/Problem_N
  2003-2020 (A/B):              {YEAR}_AMC_10{A|B}_Problems/Problem_N
  2021 Spring:                  2021_AMC_10{A|B}_Problems/Problem_N
  2021 Fall:                    2021_Fall_AMC_10{A|B}_Problems/Problem_N
  2022-2025 (A/B):              {YEAR}_AMC_10{A|B}_Problems/Problem_N

53 contests total x 25 problems = 1325 problems.
"""
import csv

BASE = "https://artofproblemsolving.com/wiki/index.php"

def make_url(slug: str, problem_n: int | None = None) -> str:
    path = f"{slug}_Problems" if problem_n is None else f"{slug}_Problems/Problem_{problem_n}"
    return f"{BASE}/{path}"

def contests():
    # (year, version_label, slug_prefix)
    # slug_prefix becomes "{slug_prefix}" in the URL before "_Problems"
    contests = []
    # 2000, 2001: single test
    for y in (2000, 2001):
        contests.append((y, "", f"{y}_AMC_10"))
    # 2002: A, B, P (pilot)
    for v in ("A", "B", "P"):
        contests.append((2002, v, f"2002_AMC_10{v}"))
    # 2003-2020: A, B
    for y in range(2003, 2021):
        for v in ("A", "B"):
            contests.append((y, v, f"{y}_AMC_10{v}"))
    # 2021 Spring: A, B
    for v in ("A", "B"):
        contests.append((2021, f"Spring {v}", f"2021_AMC_10{v}"))
    # 2021 Fall: A, B
    for v in ("A", "B"):
        contests.append((2021, f"Fall {v}", f"2021_Fall_AMC_10{v}"))
    # 2022-2025: A, B
    for y in range(2022, 2026):
        for v in ("A", "B"):
            contests.append((y, v, f"{y}_AMC_10{v}"))
    return contests

def make_label(year: int, version: str) -> str:
    """Match AoPS's own formatting: '2025 AMC 10B', '2021 Fall AMC 10A', etc."""
    if version == "":
        return f"{year} AMC 10"
    if version in ("A", "B", "P"):
        return f"{year} AMC 10{version}"
    parts = version.split()
    season, letter = parts[0], parts[1]  # "Spring" / "Fall", "A" / "B"
    return f"{year} {season} AMC 10{letter}"

def build_index():
    rows = []
    problem_id = 0
    for year, version, slug in contests():
        contest_page = make_url(slug)
        for n in range(1, 26):  # 25 problems per contest
            problem_id += 1
            rows.append({
                "problem_id": problem_id,
                "year": year,
                "version": version,
                "problem_num": n,
                "contest_label": make_label(year, version),
                "slug": slug,
                "problem_url": make_url(slug, n),
                "contest_url": contest_page,
                "category": "",  # filled in by scraper
            })
    return rows

if __name__ == "__main__":
    rows = build_index()
    import pathlib
    out = str(pathlib.Path(__file__).resolve().parent / "data" / "amc10_index.csv")
    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} problems across {len(contests())} contests to {out}")
    # Sanity print
    from collections import Counter
    by_year = Counter(r["year"] for r in rows)
    print("\nProblems per year:")
    for y in sorted(by_year):
        print(f"  {y}: {by_year[y]}")
