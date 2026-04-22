# AMC 10 Problem Browser

Classifies every AMC 10 problem from 2000 through 2025 (53 contests, 1,325
problems total) into one of four topic areas — **Algebra**, **Geometry**,
**Counting & Probability**, **Number Theory** — and serves the result as a
Shiny app.

## Why this design

The obvious approach — fetch every problem page on the AoPS wiki and parse
the `Category:` tag — needs ~1,300 HTTP requests and gets rate-limited fast.
Instead we exploit the other direction of the MediaWiki index: AoPS has four
category pages (e.g. `Category:Introductory_Algebra_Problems`) that each list
*every* problem tagged into that category, across all contests. Walking those
four pages with pagination is ~25 requests total and yields a complete
URL → category mapping, which we then inner-join against a deterministically
generated index of AMC 10 problem URLs.

## Files

```
amc10/
├── build_index.py           # generates data/amc10_index.csv (no HTTP)
├── R/
│   └── scrape_amc10.R       # fetches AoPS category pages, writes categorized CSV
├── app.R                    # Shiny browser
├── data/
│   ├── amc10_index.csv      # 1,325 rows, always present
│   └── amc10_categorized.csv  # produced by the scraper
└── README.md
```

## One-time setup

Install R packages:

```r
install.packages(c("httr2", "rvest", "dplyr", "stringr", "tidyr",
                   "readr", "purrr", "shiny", "bslib", "DT",
                   "ggplot2", "scales"))
```

## Usage

1. **Generate the problem index** (fast, no network):

   ```bash
   python3 build_index.py
   ```

2. **Scrape AoPS categories** (~30–60 seconds with the 1s polite delay):

   ```bash
   Rscript R/scrape_amc10.R
   ```

3. **Launch the app**:

   ```r
   shiny::runApp()
   ```

## Caveats

- AoPS category tags are crowd-maintained on the wiki. Some recent problems
  (especially 2024–2025) may still be uncategorized — they show up as
  `Uncategorized` in the app. You can rerun the scraper periodically.
- A small number of problems carry multiple category tags (e.g. a geometry
  problem that reduces to an algebra problem). Those appear as
  `Algebra; Geometry` in the `category` column; the plot panel shows each
  problem under its first-listed primary category.
- The wiki URL convention for 2021 changed mid-stream: Spring 2021 A/B are at
  `/2021_AMC_10A_Problems` etc., and Fall 2021 A/B are at
  `/2021_Fall_AMC_10A_Problems`. The index handles both.
- Problem text and solutions are copyrighted by the MAA. The app stores URLs
  and classifications only, and links out to AoPS for the actual problem.

## Extending

- **Add difficulty estimates**: join in AoPS community rating or historical
  answer-distribution data.
- **Fetch problem text locally**: uncomment the per-problem fetch loop in
  `scrape_amc10.R` (left commented-out by default — adds 1,300 requests).
- **Swap in AMC 12 / AIME**: same pattern. Change `build_index.py` to enumerate
  the relevant slugs and adjust the category slug list.
# amc10
