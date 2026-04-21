# Topic Progress and Answer Keys Design

**Date:** 2026-04-21

**Goal:** Add reliable answer-key support so the app can track real correctness, then use that data to show per-topic progress during practice and on the results page.

## Why This Change

The current app tracks whether a question was answered or skipped, but it does not know the correct letter for any problem. Because of that, the UI can show progress through a session, but it cannot truthfully report how many answers were correct overall or within each topic.

The requested feature needs two layers:

1. A trustworthy answer-key source tied to each `problem_id`
2. A progress summary grouped by topic for the active session

## Scope

### In Scope

- Add answer-key data for AMC 10 problems in a separate file
- Load answer keys at app startup alongside the existing problem index
- Mark each submitted answer as correct or incorrect at submit time
- Aggregate per-topic totals for the current session queue
- Show topic progress during practice
- Show topic progress on the results page
- Extend tests to cover correctness and topic summaries

### Out of Scope

- Lifetime stats across multiple sessions
- User accounts or persistent history
- Live scraping of answer keys from AoPS during a session
- Reworking the full site layout or changing the core practice flow

## Chosen Approach

Use a separate answer-key dataset such as `data/amc10_answers.csv`, keyed by `problem_id`, and join it to the existing problem records in memory when the app starts.

This is preferred over storing answers in the main categorized CSV because it keeps indexing metadata, topic classification, and answer-key maintenance loosely coupled. It also avoids turning the existing problem-generation pipeline into a single fragile source of truth.

## Data Design

### New Data File

Add a CSV file with one row per problem:

```csv
problem_id,answer
1,C
2,E
3,A
```

Rules:

- `problem_id` must match the IDs already used in `data/amc10_categorized.csv`
- `answer` must be one of `A`, `B`, `C`, `D`, or `E`
- Missing or malformed rows should not crash the app; they should produce a clear startup validation error or a safe fallback

### Runtime Model

Each problem record loaded into memory should expose:

- existing metadata such as contest label, number, URL, and category
- a resolved correct answer letter, if available

Each history row stored in session should keep:

- `id`
- `answer`
- `correct`
- `skipped`
- `time`
- optional `topic` for simpler rendering, though this can also be derived later

## Backend Flow

### Startup

On startup, the app should:

1. Load the existing problem CSV
2. Load the new answer-key CSV
3. Validate answer letters and IDs
4. Attach each answer to the corresponding problem record

If an answer is missing for a queued problem, the app should degrade safely, but the preferred behavior is to catch dataset issues in tests before deployment.

### Submit Flow

When the user submits an answer:

- If the answer is `skip`, store `answer=None`, `skipped=True`, and `correct=False` or `None` depending on the chosen scoring semantics
- If the answer is `A-E`, compare it to the problem’s correct answer and store a real boolean in `correct`

Recommended scoring semantics:

- answered correct: `correct=True`
- answered incorrect: `correct=False`
- skipped: `correct=None`

This keeps “incorrect” distinct from “not attempted.”

### Session Aggregation

The topic progress view should be session-scoped and based on the active queue, not on all problems in the dataset.

For each topic in the current queue:

- `total`: number of queued questions in that topic
- `finished`: number of history entries for that topic, including skipped questions
- `answered`: number of non-skipped history entries for that topic
- `correct`: number of history entries with `correct=True`

These values should be computed on the server and passed directly into templates.

## UI Design

### Practice Page

Add a new `Topic Progress` panel under the existing thin session progress bar and above the embedded AoPS iframe.

Each topic card should show:

- topic name
- finished count out of total for this session
- correct count
- a compact visual fill bar

Behavior:

- update after each submit because the page reloads on each next problem
- reflect only the active practice set
- still render cleanly if a filtered session contains just one topic

### Results Page

Keep the current overall stats row, then add the same topic progress block near the top of the page.

Also expand the review table to show correctness state per problem:

- correct
- incorrect
- skipped

This gives the user both a summary by topic and an item-by-item review.

## Styling Direction

The new topic progress block should feel intentional and easier to scan than the current plain stats row.

Visual direction:

- use compact cards instead of a plain table
- keep the existing blue/green palette so the feature feels native to the app
- use distinct badge or accent treatment for `correct`
- keep mobile layout stacked and readable

## Error Handling

- Invalid answer-key rows should be caught during load or tests
- Missing topic labels should fall back to `Uncategorized`
- Sessions with no completed history yet should still show `0 / total` correctly
- Skipped questions should count toward `finished` but not toward `correct`

## Testing Strategy

Add tests for:

- answer-key file loading and lookup
- correctness marking in `/answer`
- skipped-answer semantics
- topic summary aggregation for mixed-topic queues
- rendering of topic progress on `/practice`
- rendering of topic progress and correctness badges on `/results`

Keep tests focused on server-rendered HTML and route behavior so regressions are easy to catch.

## Risks and Tradeoffs

- The biggest dependency is the answer-key dataset quality; bad keys would produce misleading correctness stats
- If answer keys are incomplete, progress can still render, but correctness becomes unreliable
- Per-topic counts depend on the current queue, so users may interpret them as global mastery unless the labels are clear

## Acceptance Criteria

- Submitted answers are marked correct or incorrect using a real answer key
- Skipped questions remain distinguishable from incorrect answers
- The practice page shows per-topic finished and correct counts for the current session
- The results page shows the same per-topic summary plus per-question correctness state
- Automated tests cover the new scoring and aggregation behavior
