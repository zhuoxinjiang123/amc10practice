# =====================================================================
#  AMC 10 Problem Browser -- Shiny app
#  -----------------------------------------------------------------
#  Loads data/amc10_categorized.csv (produced by R/scrape_amc10.R)
#  and lets you filter/browse problems by category, year, contest.
#  Falls back to data/amc10_index.csv if the categorized file isn't
#  there yet (all problems show as "Uncategorized").
# =====================================================================

suppressPackageStartupMessages({
  library(shiny)
  library(bslib)
  library(DT)
  library(dplyr)
  library(readr)
  library(stringr)
  library(ggplot2)
  library(tidyr)
})

# --- Data loader ----------------------------------------------------
load_data <- function() {
  path_cat <- "data/amc10_categorized.csv"
  path_idx <- "data/amc10_index.csv"
  if (file.exists(path_cat)) {
    df <- read_csv(path_cat, show_col_types = FALSE)
    attr(df, "source") <- "categorized"
  } else if (file.exists(path_idx)) {
    df <- read_csv(path_idx, show_col_types = FALSE) |>
      mutate(category = "Uncategorized (run scraper first)")
    attr(df, "source") <- "index-only"
  } else {
    stop("No data found. Run build_index.py then R/scrape_amc10.R first.")
  }
  # Ensure expected columns
  df |>
    mutate(
      category      = ifelse(is.na(category) | category == "",
                             "Uncategorized", category),
      contest_label = factor(contest_label, levels = unique(contest_label)),
      year          = as.integer(year)
    )
}

CAT_LEVELS <- c("Algebra", "Geometry", "Counting & Probability",
                "Number Theory", "Uncategorized")

cat_color <- c(
  "Algebra"                = "#2E86AB",
  "Geometry"               = "#E07A5F",
  "Counting & Probability" = "#81B29A",
  "Number Theory"          = "#F2CC8F",
  "Uncategorized"          = "#9A9A9A"
)

# --- UI -------------------------------------------------------------
ui <- page_sidebar(
  title = "AMC 10 Problem Browser",
  theme = bs_theme(version = 5, bootswatch = "flatly"),

  sidebar = sidebar(
    width = 320,
    title = "Filters",
    checkboxGroupInput("cat", "Category",
                       choices  = CAT_LEVELS,
                       selected = CAT_LEVELS[1:4]),
    sliderInput("year_range", "Year",
                min = 2000, max = 2025,
                value = c(2000, 2025), step = 1, sep = ""),
    selectizeInput("version", "Version",
                   choices = c("All", "A", "B", "P",
                               "Spring A", "Spring B",
                               "Fall A", "Fall B", "(single)"),
                   selected = "All", multiple = FALSE),
    hr(),
    uiOutput("summary_box")
  ),

  navset_card_tab(
    nav_panel(
      "Problems",
      card(
        card_header("Matching problems"),
        DTOutput("tbl"),
        tags$small(class = "text-muted px-3 pb-2",
                   "Click a row to open the AoPS page in a new tab.")
      )
    ),
    nav_panel(
      "Category distribution",
      layout_column_wrap(
        width = 1/2,
        card(card_header("By year"),
             plotOutput("plot_year", height = "420px")),
        card(card_header("By problem number (position in test)"),
             plotOutput("plot_pos", height = "420px"))
      ),
      card(card_header("Counts"),
           DTOutput("tbl_counts"))
    ),
    nav_panel(
      "About",
      card(
        card_body(
          h4("About this app"),
          p("Classifies every AMC 10 problem (2000-2025, 53 contests,",
            "1,325 problems) into one of four topic areas using the",
            tags$b("AoPS wiki's own category tags"), "."),
          h5("Data pipeline"),
          tags$ol(
            tags$li(code("build_index.py"),
                    " -- generates ",
                    code("data/amc10_index.csv"),
                    " with every problem URL (deterministic, no HTTP)."),
            tags$li(code("R/scrape_amc10.R"),
                    " -- fetches the 4 AoPS category pages (~25",
                    " requests with pagination) and writes ",
                    code("data/amc10_categorized.csv"), ".")
          ),
          h5("Caveats"),
          tags$ul(
            tags$li("AoPS category tags are crowd-maintained. Some",
                    " recent problems may be uncategorized."),
            tags$li("A few problems carry multiple tags (e.g. geometry",
                    " + algebra); those appear as",
                    code("Algebra; Geometry"), "."),
            tags$li("Problem text and solutions are copyrighted by the MAA.",
                    " This app links out to AoPS rather than reproducing them.")
          )
        )
      )
    )
  )
)

# --- Server ---------------------------------------------------------
server <- function(input, output, session) {
  data_all <- reactive(load_data())

  data_filtered <- reactive({
    df   <- data_all()
    cats <- input$cat
    # Guard: nothing selected -> empty result
    if (!length(cats)) return(df[0, ])

    # Match either a single-tag equality or any token of a multi-tag
    # problem like "Algebra; Geometry".
    pat <- paste(paste0("(?:^|; )", cats, "(?:$|;)"), collapse = "|")

    df |>
      filter(
        year >= input$year_range[1],
        year <= input$year_range[2],
        if (input$version == "All")        TRUE
        else if (input$version == "(single)") version == ""
        else                                  version == input$version,
        str_detect(category, pat) | (category %in% cats)
      )
  })

  # --- Summary box in sidebar -------------------------------------
  output$summary_box <- renderUI({
    df <- data_filtered()
    all_df <- data_all()
    tagList(
      tags$div(class = "mt-3",
        tags$div(class = "fw-bold", "Showing"),
        tags$div(style = "font-size:1.6rem;",
                 format(nrow(df), big.mark = ",")),
        tags$div(class = "text-muted small",
                 sprintf("of %s total",
                         format(nrow(all_df), big.mark = ",")))
      )
    )
  })

  # --- Problems table ---------------------------------------------
  output$tbl <- renderDT({
    df <- data_filtered() |>
      transmute(
        Year    = year,
        Contest = contest_label,
        `#`     = problem_num,
        Category = category,
        Link    = sprintf('<a href="%s" target="_blank">open &rarr;</a>',
                          problem_url)
      )
    datatable(
      df,
      escape   = FALSE,
      rownames = FALSE,
      options  = list(pageLength = 25,
                      order = list(list(0, "desc"),
                                   list(1, "asc"),
                                   list(2, "asc")),
                      dom = 'frtip'),
      selection = "none"
    ) |>
      formatStyle("Category",
                  backgroundColor = styleEqual(
                    names(cat_color),
                    paste0(cat_color, "33")  # add ~20% alpha
                  ))
  })

  # --- Category-by-year plot --------------------------------------
  output$plot_year <- renderPlot({
    df <- data_filtered()
    if (!nrow(df)) return(ggplot() + theme_void())
    # Primary category only (take first token for plotting)
    df <- df |>
      mutate(primary_cat = str_split_i(category, "; ", 1),
             primary_cat = factor(primary_cat, levels = CAT_LEVELS))
    ggplot(df, aes(x = year, fill = primary_cat)) +
      geom_bar() +
      scale_fill_manual(values = cat_color, drop = FALSE, name = NULL) +
      labs(x = NULL, y = "Problems") +
      theme_minimal(base_size = 13) +
      theme(legend.position = "top",
            panel.grid.minor = element_blank())
  })

  # --- Category-by-problem-position plot --------------------------
  output$plot_pos <- renderPlot({
    df <- data_filtered()
    if (!nrow(df)) return(ggplot() + theme_void())
    df <- df |>
      mutate(primary_cat = str_split_i(category, "; ", 1),
             primary_cat = factor(primary_cat, levels = CAT_LEVELS))
    ggplot(df, aes(x = problem_num, fill = primary_cat)) +
      geom_bar() +
      scale_fill_manual(values = cat_color, drop = FALSE, name = NULL) +
      scale_x_continuous(breaks = seq(1, 25, 2)) +
      labs(x = "Problem number (1 = easiest, 25 = hardest)",
           y = "Problems") +
      theme_minimal(base_size = 13) +
      theme(legend.position = "top",
            panel.grid.minor = element_blank())
  })

  # --- Counts table -----------------------------------------------
  output$tbl_counts <- renderDT({
    df <- data_filtered() |>
      mutate(primary_cat = str_split_i(category, "; ", 1))
    counts <- df |>
      count(primary_cat, name = "Problems") |>
      mutate(Share = scales::percent(Problems / sum(Problems), 0.1)) |>
      arrange(desc(Problems)) |>
      rename(Category = primary_cat)
    datatable(counts, rownames = FALSE,
              options = list(dom = 't', pageLength = 10))
  })
}

shinyApp(ui, server)
