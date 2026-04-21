# =====================================================================
#  scrape_amc10.R
#  -----------------------------------------------------------------
#  Categorizes every AMC 10 problem (2000-2025) into one of:
#      Algebra | Geometry | Counting & Probability | Number Theory
#  -----------------------------------------------------------------
#  Strategy: instead of scraping ~1300 individual problem pages, we
#  fetch the 4 AoPS category index pages (with pagination).  Each
#  page lists every problem classified into that category, so a
#  single pass gives us a URL -> category mapping for the entire
#  AoPS wiki.  We then inner-join that mapping against our
#  pre-generated AMC 10 problem index.
#
#  Total HTTP requests: ~25-30 (vs 1300+ the naive way).
# =====================================================================

suppressPackageStartupMessages({
  library(httr2)
  library(rvest)
  library(dplyr)
  library(stringr)
  library(tidyr)
  library(readr)
  library(purrr)
})

# --- Config ---------------------------------------------------------
AOPS_BASE  <- "https://artofproblemsolving.com/wiki/index.php"
USER_AGENT <- "amc10-research/0.1 (educational use; contact: local)"
REQ_DELAY  <- 1.0   # seconds between requests -- be polite to AoPS

# AoPS category slugs. If a slug returns empty, we try the fallback.
CATEGORIES <- list(
  "Algebra"                = c("Introductory_Algebra_Problems"),
  "Geometry"               = c("Introductory_Geometry_Problems"),
  "Counting & Probability" = c("Introductory_Combinatorics_Problems",
                               "Introductory_Counting_and_Probability_Problems"),
  "Number Theory"          = c("Introductory_Number_Theory_Problems")
)

# --- Polite HTTP helper --------------------------------------------
fetch_html <- function(url) {
  Sys.sleep(REQ_DELAY)
  resp <- request(url) |>
    req_user_agent(USER_AGENT) |>
    req_retry(max_tries = 3, backoff = \(i) 2^i) |>
    req_error(is_error = \(r) FALSE) |>
    req_perform()
  if (resp_status(resp) >= 400) {
    warning(sprintf("HTTP %d on %s", resp_status(resp), url))
    return(NULL)
  }
  resp |> resp_body_html()
}

# --- Parse one category page (with pagination follow) --------------
# Returns character vector of full problem-page URLs belonging to
# this category.  Handles MediaWiki pagination ("next page", "next 200").
parse_category_page <- function(slug) {
  url <- sprintf("%s?title=Category:%s", AOPS_BASE, slug)
  all_urls <- character()
  visited  <- character()
  page_num <- 0L

  while (!is.null(url) && !(url %in% visited)) {
    visited  <- c(visited, url)
    page_num <- page_num + 1L
    message("  page ", page_num, ": ", url)
    doc <- fetch_html(url)
    if (is.null(doc)) break

    # Category member links live in #mw-pages -> ul > li > a
    links <- doc |>
      html_elements("#mw-pages a") |>
      html_attr("href")
    links <- links[!is.na(links)]
    links <- unique(links)

    # Keep only AMC 10 problem pages (exclude pagination links which
    # point back to Category:... URLs). Matches:
    #   2000_AMC_10_Problems/Problem_N         (2000, 2001)
    #   2003_AMC_10A_Problems/Problem_N        (A / B / P)
    #   2021_Fall_AMC_10A_Problems/Problem_N   (Fall 2021)
    member_re <- "^/wiki/index\\.php/.+AMC_10[ABP]?_Problems/Problem_\\d+$"
    keep <- str_detect(links, member_re)
    all_urls <- c(all_urls, paste0("https://artofproblemsolving.com", links[keep]))

    # Follow pagination: MediaWiki renders "(next page)" or "next 200" etc.
    next_href <- doc |>
      html_elements("#mw-pages a") |>
      keep(\(a) str_detect(html_text(a), "(?i)next (page|\\d+)")) |>
      html_attr("href") |>
      unique() |>
      first()
    url <- if (!is.na(next_href))
             paste0("https://artofproblemsolving.com", next_href) else NULL
  }
  message("  total so far: ", length(unique(all_urls)), " problems")
  unique(all_urls)
}

# --- Build the URL -> category lookup ------------------------------
build_category_lookup <- function() {
  out <- list()
  for (cat_name in names(CATEGORIES)) {
    message("\n== Category: ", cat_name, " ==")
    urls <- character()
    for (slug in CATEGORIES[[cat_name]]) {
      urls <- c(urls, parse_category_page(slug))
      if (length(urls)) break   # first slug that works, use it
    }
    message("  -> ", length(urls), " problems tagged as ", cat_name)
    if (length(urls)) {
      out[[cat_name]] <- tibble(problem_url = urls, category = cat_name)
    }
  }
  bind_rows(out)
}

# --- Merge into the index ------------------------------------------
classify_amc10 <- function(index_csv = "data/amc10_index.csv",
                           out_csv   = "data/amc10_categorized.csv") {
  stopifnot(file.exists(index_csv))
  idx <- read_csv(index_csv, show_col_types = FALSE)
  message("Loaded index: ", nrow(idx), " AMC 10 problems")

  lookup <- build_category_lookup()
  # A problem may appear in multiple categories (rare).  Concatenate.
  lookup_uniq <- lookup |>
    group_by(problem_url) |>
    summarise(category = paste(sort(unique(category)), collapse = "; "),
              .groups = "drop")

  enriched <- idx |>
    select(-any_of("category")) |>
    left_join(lookup_uniq, by = "problem_url") |>
    mutate(category = replace_na(category, "Uncategorized"))

  dir.create(dirname(out_csv), showWarnings = FALSE, recursive = TRUE)
  write_csv(enriched, out_csv)

  message("\nWrote ", out_csv)
  message("\nCategory distribution:")
  print(enriched |> count(category, sort = TRUE))
  invisible(enriched)
}

# --- Entry point ----------------------------------------------------
if (sys.nframe() == 0L) {
  # Run from the repo root so relative paths resolve
  classify_amc10()
}
