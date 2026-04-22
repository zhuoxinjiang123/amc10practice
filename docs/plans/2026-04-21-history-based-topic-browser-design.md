# History-Based Topic Browser Design

**Date:** 2026-04-21

**Goal:** Replace the random session-based AMC 10 practice flow with a database-backed topic browser where users select questions directly from topic lists, filter by difficulty, and see persistent per-question attempt history across refreshes and tabs.

## Why This Change

The current app is centered on temporary practice sessions:

- it picks a random queue
- it tracks progress in session state
- it treats topics mostly as filters instead of destinations

Your updated requirements change the product into a persistent study browser:

- questions should be shown in a list under each topic
- the user should click any question to practice it
- each question row should show attempt history
- question status should come entirely from that history
- progress must persist across refreshes and future visits
- progress must be shared across tabs because it is stored server-side

This means the app should move from queue-first behavior to question-first navigation.

## Scope

### In Scope

- Replace random session flow with a persistent topic browser
- Add server-side persistence using SQLite
- Show topic dashboard summaries on the home page
- Show topic question lists with difficulty filters
- Let the user select any question from the list
- Track lifetime `correct_count` and `wrong_count` per question
- Derive question status from attempt history only
- Preserve progress across refreshes and across browser tabs

### Out of Scope

- Multi-user accounts
- Cloud sync across machines
- Separate “finished” or “reopen” state
- Spaced repetition or scheduling
- Notes, tags, favorites, or bookmarks

## Chosen Approach

Use the existing CSV files as the question catalog and a small SQLite database as the persistent attempt-history store.

Why this is the best fit:

- the catalog already exists and is stable
- SQLite is lightweight and shared across tabs because it is server-side
- it avoids over-engineering while giving us durable local persistence
- it lets the UI stay server-rendered and simple

## Product Model

The app should have three main surfaces:

1. `Topic Dashboard` at `/`
2. `Topic Browser` at `/topic/<topic_slug>`
3. `Question Practice` at `/question/<problem_id>`

This replaces the old “start a random session” idea.

## Data Model

### Question Catalog

Keep using the CSV-backed problem catalog for:

- `problem_id`
- contest label
- problem number
- topic/category
- problem URL
- correct answer

No question metadata needs to move into the database.

### Progress Database

Add a SQLite database file under an app-owned path such as:

- `instance/amc10_progress.sqlite3`

Add one table:

```sql
CREATE TABLE question_progress (
  problem_id TEXT PRIMARY KEY,
  correct_count INTEGER NOT NULL DEFAULT 0,
  wrong_count INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);
```

### Status Semantics

Question row status comes only from attempt history:

- if `correct_count = 0` and `wrong_count = 0`, show `Not answered yet`
- otherwise show `Correct: N • Wrong: M`

There is no separate `finished` column and no reopen behavior.

### Untouched Questions

Questions that have never been attempted do not need database rows yet.

Missing rows should be treated as:

- `correct_count = 0`
- `wrong_count = 0`

This keeps the database small and easy to maintain.

## Difficulty Model

Keep the current difficulty rules exactly:

- `Easy`: problem `#1-10`
- `Medium`: problem `#8-18`
- `Hard`: problem `#16-25`

These ranges overlap, so the topic page should use difficulty filter tabs instead of fixed difficulty sections. That preserves the current rule without forcing duplicate rows in the visible list.

## Route Design

### `/`

Render the topic dashboard.

Each topic card should show:

- topic name
- total number of questions in the topic
- `Answered X / Total`
- aggregated `Correct` count
- aggregated `Wrong` count

Where `Answered` means the number of questions with any non-zero attempt history, not the total number of attempts.

### `/topic/<topic_slug>`

Render the topic browser page for one topic.

This page should show:

- a topic summary header
- difficulty filter tabs or chips: `All`, `Easy`, `Medium`, `Hard`
- a single question list filtered by the chosen difficulty

Each row should show:

- a checkbox-like status indicator or label
- contest label and problem number
- status text:
  - `Not answered yet`
  - or `Correct: N • Wrong: M`
- a link or button to practice that question

### `/question/<problem_id>`

Render one selected problem for practice.

This page should reuse useful parts of the current question page:

- embedded AoPS problem
- answer choices
- AI hint

But the navigation model changes:

- there is no random queue
- there is no “next problem” session flow
- after submitting an answer, the app returns to the topic browser page

### `/question/<problem_id>/answer`

Handle answer submission.

Behavior:

- normalize and validate the choice
- compare with the known correct answer
- increment `correct_count` or `wrong_count`
- update `updated_at`
- redirect back to the same topic page and the same difficulty filter

### Query Parameter for Difficulty

Use a query parameter such as `?difficulty=easy` on the topic page.

This makes it easy to:

- preserve the user’s selected filter
- return them to the same filtered view after answering a question

## UI Design

### Topic Dashboard

The home page should feel like a study map, not a setup form.

Instead of asking how many random questions to generate, it should show:

- one card per topic
- persistent summary numbers
- a clear action to open that topic

### Topic Browser

This becomes the main study surface.

It should feel like a structured question browser:

- topic summary at the top
- difficulty filter controls
- scannable rows
- immediate visibility into whether a question has never been attempted
- lifetime correct/wrong history on every practiced question

### Practice Page

This page should stay focused:

- one chosen question
- one answer action
- one clear path back to the same topic browser state

## Persistence Flow

### First Attempt

1. User opens a topic page
2. User selects a difficulty filter
3. User clicks a question
4. User submits an answer
5. The app increments the appropriate lifetime counter
6. The app redirects back to the same topic and difficulty view
7. The row now shows `Correct: N` and `Wrong: M`

### Repeating a Question

1. User clicks a question that already has history
2. User practices it again
3. The app increments the correct or wrong counter again
4. The row remains available in the list, now with updated lifetime totals

## Transition From Current App

The app already has committed work for:

- answer-key loading
- scoring logic
- topic aggregation helpers

Those pieces can still be reused where they fit.

The parts that should be treated as legacy and replaced:

- `/start`
- random queue creation
- session history as the primary persistence model
- `/results` as the main progress surface
- the idea of “finished/open” session progress

## Error Handling

- Invalid `problem_id` should redirect cleanly or return a 404-style page
- Invalid answer payloads should not change counts
- Missing database file should be auto-created
- Missing progress rows should render as `Not answered yet`
- Unknown difficulty filters should fall back to `all`

## Testing Strategy

Tests should cover:

- database initialization
- default zero-state for untouched questions
- answer submission increments correct or wrong counts
- topic dashboard summaries
- difficulty filter behavior on topic pages
- row status rendering for untouched vs practiced questions
- returning to the same topic and difficulty filter after submission

## Risks and Tradeoffs

- Replacing the old random flow is a larger behavioral shift than adding a panel
- Some current session-oriented route logic will become dead code and should be retired
- SQLite is ideal for local use but not for large multi-user deployments
- Overlapping difficulty ranges require careful UI so users do not think rows are missing when they switch filters

## Acceptance Criteria

- The home page shows persistent topic summaries
- Each topic page lists questions and supports `All / Easy / Medium / Hard` filtering
- Users can click any question from the list to practice it
- Question row status is based only on attempt history
- Untouched questions show `Not answered yet`
- Practiced questions show `Correct: N • Wrong: M`
- Progress persists across refreshes and future visits
- Progress is shared across browser tabs because it is stored server-side
