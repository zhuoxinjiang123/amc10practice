# Persistent Topic Tracker Design

**Date:** 2026-04-21

**Goal:** Replace the random session-based AMC 10 practice flow with a database-backed topic checklist where users can browse questions by topic, track persistent completion state across tabs and refreshes, and accumulate lifetime correct and wrong counts per question.

## Why This Change

The current app is built around temporary practice sessions:

- it chooses a random queue
- it tracks progress only in the current session
- it does not treat topics as first-class study spaces

Your updated requirements change the product into a study tracker:

- questions must be listed under each topic
- each question needs a persistent finished state
- progress must survive refreshes and future visits
- stats must be shared across tabs because they live in a server-side database
- users must be able to reopen finished questions later without losing lifetime correct and wrong counts

That means the core architecture should move from session-first to question-first persistence.

## Scope

### In Scope

- Replace the random practice-session flow with a topic checklist flow
- Add database-backed persistent progress shared across tabs
- Show question lists grouped by topic
- Show topic-level completion summaries
- Track per-question lifetime `correct_count` and `wrong_count`
- Track per-question `finished` status
- Allow reset/reopen without clearing lifetime counts
- Let the user click any unanswered or reopened question to practice

### Out of Scope

- Multi-user accounts or login
- Cloud sync across machines
- Spaced repetition scheduling
- Tagging, notes, bookmarking, or favorites
- Importing new contest sets beyond the current AMC 10 catalog

## Chosen Approach

Use the existing CSV files as the question catalog and add a small SQLite database to persist user progress.

Why this is the best fit:

- the catalog is already stable and loaded in memory
- SQLite is lightweight, local, and shared across browser tabs because it is server-side
- it avoids over-engineering with a larger ORM or service layer
- it keeps the app fast and easy to run locally

## Product Model

The app should become a persistent topic tracker with three main surfaces:

1. `Topic Dashboard` at `/`
2. `Topic Checklist` at `/topic/<topic_slug>`
3. `Question Practice` at `/question/<problem_id>`

This replaces the old idea of “start a random session with N questions.”

## Data Model

### Question Catalog

Keep using the existing CSV-backed problem catalog as the source of truth for:

- `problem_id`
- contest label
- problem number
- topic/category
- problem URL
- correct answer

No question metadata needs to be duplicated into the database.

### Progress Database

Add a SQLite database file, preferably under an app-owned local path such as:

- `instance/amc10_progress.sqlite3`

Add one table:

```sql
CREATE TABLE question_progress (
  problem_id TEXT PRIMARY KEY,
  finished INTEGER NOT NULL DEFAULT 0,
  correct_count INTEGER NOT NULL DEFAULT 0,
  wrong_count INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);
```

### Semantics

- `finished = 1` means the question is currently marked complete
- `finished = 0` means it is open or reopened
- `correct_count` is the lifetime number of correct submissions
- `wrong_count` is the lifetime number of incorrect submissions
- `reset/reopen` changes only `finished` back to open; it does not change counts

### Untouched Questions

Questions that have never been interacted with do not need database rows yet.

The app can treat missing rows as:

- `finished = 0`
- `correct_count = 0`
- `wrong_count = 0`

This keeps the database small and allows lazy creation of rows only when a question is answered or reopened.

## Route Design

### `/`

Render the topic dashboard.

For each topic card show:

- topic name
- total questions in that topic
- finished count, for example `2 / 541 finished`
- total lifetime correct count across that topic
- total lifetime wrong count across that topic

Clicking a topic opens the checklist page for that topic.

### `/topic/<topic_slug>`

Render the topic checklist page.

This page shows all questions in that topic, ordered consistently, for example by:

1. year
2. contest version
3. problem number

Each row shows:

- `[ ]` for open / unanswered / reopened questions
- `[x]` for finished questions
- contest label and problem number
- lifetime `correct_count`
- lifetime `wrong_count`
- a `Practice` action for open questions
- a `Reopen` action for finished questions

This page should also show topic-level summary text at the top.

### `/question/<problem_id>`

Render a single question practice page.

This page should reuse as much of the current problem-practice UI as makes sense:

- problem iframe
- answer choices
- submit action
- AI hint
- optional timer if it still feels useful

But the navigation model changes:

- there is no random queue
- there is no “next random question”
- after answer submission, the user returns to the topic checklist

### `/question/<problem_id>/answer`

Handle answer submission.

Behavior:

- normalize and validate the submitted choice
- compare to the question’s correct answer
- increment `correct_count` or `wrong_count`
- set `finished = 1`
- update `updated_at`
- redirect back to the source topic checklist

### `/question/<problem_id>/reset`

Handle reset/reopen.

Behavior:

- set `finished = 0`
- keep lifetime correct/wrong counts unchanged
- update `updated_at`
- redirect back to the topic checklist

## UI Design

### Topic Dashboard

The home page should stop asking the user to pick “how many random problems.”

Instead it should feel like a study map:

- one card per topic
- persistent summary per card
- clear call to action to open a topic

### Topic Checklist

This is the center of the product.

Each topic page should feel like a structured worksheet:

- clear summary at the top
- scannable question rows
- visible `[ ]` or `[x]` state
- lifetime right/wrong counters visible without extra clicks

The row status indicator should be visually obvious, but it does not have to be a real HTML checkbox input. A styled checkbox-like badge is enough if that keeps the behavior clearer.

### Practice Page

The practice page should feel focused:

- one selected question
- answer submission
- return to the checklist after completion

Because the user chooses the question from the checklist, the app no longer needs to pretend that the next step is random or queue-driven.

## Persistence Flow

### Answering a Question

1. User opens a topic page
2. User clicks an open question
3. User submits an answer
4. The app updates the database row
5. The app marks the question finished
6. The app returns to the topic checklist
7. The checklist and topic dashboard now reflect the new totals

### Reopening a Question

1. User visits a finished question row
2. User clicks `Reopen`
3. The app changes only `finished = 0`
4. Lifetime stats remain unchanged
5. The row returns to `[ ]`

## Transition From Current App

The app currently has partial work for session-scoped progress and random practice flow. That is no longer the target product.

Implementation should treat the following as legacy behavior to replace:

- `/start`
- random queue creation
- session-based `history` as the primary source of progress
- `/results` as the main summary surface

Some pieces can still be reused:

- question catalog loading
- answer-key loading
- correctness comparison logic
- problem iframe UI
- AI hint support

## Error Handling

- Invalid `problem_id` should return a clean redirect or 404-style response
- Invalid answer payloads should not mutate progress
- Missing database file should be auto-created
- Missing progress rows should default to zero stats
- Reset on an untouched question should be harmless and leave counts at zero

## Testing Strategy

Tests should cover:

- database initialization
- default zero-state progress for untouched questions
- answer submission increments correct or wrong counts appropriately
- answer submission marks finished
- reset/reopen clears only finished state
- topic dashboard summaries
- topic checklist row rendering and status markers
- explicit question selection flow

## Risks and Tradeoffs

- Replacing the random flow is a larger product shift than adding a panel
- The current templates and route structure are session-oriented, so some existing code will be retired
- SQLite is perfect for local single-user use, but not intended for many simultaneous remote users

## Acceptance Criteria

- The home page shows topic progress based on persistent database data
- Each topic page lists all questions in that topic with `[ ]` or `[x]`
- Users can click a question from the list to practice it
- Answering a question marks it finished and increments lifetime correct or wrong counts
- Reopening a question resets only the finished state
- Progress persists across refreshes and future visits
- Progress is shared across browser tabs because it is stored server-side
