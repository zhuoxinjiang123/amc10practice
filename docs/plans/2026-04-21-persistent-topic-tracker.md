# Persistent Topic Tracker Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the random session-based AMC 10 practice flow with a SQLite-backed topic checklist that persists per-question finished state plus lifetime correct and wrong counts across refreshes and tabs.

**Architecture:** Keep the AMC 10 question catalog in CSV and answer keys in memory, then layer a small SQLite persistence table on top for user progress. Build the app around three server-rendered surfaces: a topic dashboard, a topic checklist, and an explicit question practice page keyed by `problem_id`. Existing session queue behavior should be retired rather than extended. Follow @test-driven-development for each behavior change and finish with @verification-before-completion.

**Tech Stack:** Python, Flask, SQLite, CSV, Jinja2 templates, CSS, `unittest`

---

### Task 1: Clean Up Conflicting Session-Progress WIP

**Files:**
- Modify: `app.py`
- Modify: `templates/practice.html`
- Modify: `static/style.css`
- Modify: `tests/test_practice_flow.py`

**Step 1: Inspect the current dirty worktree**

Run:

```bash
git status --short
```

Expected: the current branch shows uncommitted Task 5 practice-page progress work that belongs to the old session-oriented design.

**Step 2: Revert only the uncommitted session-progress WIP**

Revert the uncommitted changes in:

- `app.py`
- `templates/practice.html`
- `static/style.css`
- `tests/test_practice_flow.py`

Do not touch the committed answer-key or topic-aggregation work already in git history.

**Step 3: Verify the worktree is clean**

Run:

```bash
git status --short
```

Expected: no output.

**Step 4: Commit**

```bash
git commit --allow-empty -m "chore: reset session progress wip for tracker redesign"
```

Only create this commit if a real revert was required.

### Task 2: Add Database Helpers and Persistence Tests

**Files:**
- Create: `tests/test_progress_db.py`
- Modify: `app.py`

**Step 1: Write the failing test**

Create `tests/test_progress_db.py` with tests for:

- initializing the SQLite database
- loading default zero-state progress for untouched questions
- upserting progress rows
- reopening a finished question without clearing counts

Example shape:

```python
import tempfile
import unittest
from pathlib import Path

from app import ensure_db, get_progress_map, record_result, reopen_question


class ProgressDbTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "progress.sqlite3"

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_untouched_question_defaults_to_open_with_zero_counts(self):
        ensure_db(self.db_path)
        progress = get_progress_map(self.db_path)
        self.assertEqual(progress.get("1"), None)

    def test_record_result_marks_finished_and_increments_correct(self):
        ensure_db(self.db_path)
        record_result(self.db_path, "1", is_correct=True)
        progress = get_progress_map(self.db_path)
        self.assertEqual(progress["1"]["finished"], 1)
        self.assertEqual(progress["1"]["correct_count"], 1)
        self.assertEqual(progress["1"]["wrong_count"], 0)

    def test_reopen_keeps_counts_but_clears_finished(self):
        ensure_db(self.db_path)
        record_result(self.db_path, "1", is_correct=False)
        reopen_question(self.db_path, "1")
        progress = get_progress_map(self.db_path)
        self.assertEqual(progress["1"]["finished"], 0)
        self.assertEqual(progress["1"]["wrong_count"], 1)
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_progress_db -v`
Expected: FAIL because the persistence helpers do not exist yet.

**Step 3: Write minimal implementation**

In `app.py`, add:

- a configured DB path
- `ensure_db(db_path=None)`
- `get_db_connection(db_path=None)`
- `get_progress_map(db_path=None)`
- `record_result(db_path, problem_id, is_correct)`
- `reopen_question(db_path, problem_id)`

Keep the table minimal:

```sql
CREATE TABLE IF NOT EXISTS question_progress (
  problem_id TEXT PRIMARY KEY,
  finished INTEGER NOT NULL DEFAULT 0,
  correct_count INTEGER NOT NULL DEFAULT 0,
  wrong_count INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
)
```

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_progress_db -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app.py tests/test_progress_db.py
git commit -m "feat: add persistent question progress store"
```

### Task 3: Build Topic Summary Helpers

**Files:**
- Create: `tests/test_topic_dashboard.py`
- Modify: `app.py`

**Step 1: Write the failing test**

Create tests that merge catalog data with DB progress and compute per-topic summary:

- total questions
- finished count
- sum of correct counts
- sum of wrong counts

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_topic_dashboard -v`
Expected: FAIL because the summary helper does not exist.

**Step 3: Write minimal implementation**

Add helpers such as:

- `merge_problem_progress(problem, progress_map)`
- `build_topic_dashboard(problems, progress_map)`
- `slugify_topic(topic_name)` or an equivalent topic-slug helper

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_topic_dashboard -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app.py tests/test_topic_dashboard.py
git commit -m "feat: add topic dashboard summary helpers"
```

### Task 4: Replace the Home Page With the Topic Dashboard

**Files:**
- Modify: `app.py`
- Modify: `templates/index.html`
- Modify: `static/style.css`
- Create: `tests/test_index_dashboard.py`

**Step 1: Write the failing test**

Create a dashboard route test asserting:

- `/` returns topic cards
- each card shows `X / total finished`
- correct and wrong totals are shown
- old random-session controls like `count` are no longer the main call to action

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_index_dashboard -v`
Expected: FAIL because `/` still renders the old start form.

**Step 3: Write minimal implementation**

Update `/` in `app.py` to:

- load progress from the DB
- build topic dashboard data
- render topic cards instead of the random session form

Update `templates/index.html` to render:

- topic cards
- topic progress summary
- open-topic links

Add matching styles in `static/style.css`.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_index_dashboard -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app.py templates/index.html static/style.css tests/test_index_dashboard.py
git commit -m "feat: replace home page with topic dashboard"
```

### Task 5: Add the Topic Checklist Page

**Files:**
- Create: `templates/topic.html`
- Create: `tests/test_topic_page.py`
- Modify: `app.py`
- Modify: `static/style.css`

**Step 1: Write the failing test**

Create route tests for `/topic/<topic_slug>` asserting:

- the correct topic page renders
- question rows appear under the topic
- each row shows `[ ]` or `[x]`
- each row shows lifetime correct and wrong counts
- open questions expose a practice action
- finished questions expose a reopen action

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_topic_page -v`
Expected: FAIL because the route and template do not exist yet.

**Step 3: Write minimal implementation**

Add to `app.py`:

- topic slug lookup helper
- `/topic/<topic_slug>` route
- merged per-question rows for the chosen topic

Create `templates/topic.html` with:

- topic summary header
- row list
- checkbox-like status indicators
- per-question counts
- buttons or links for `Practice` and `Reopen`

Add list styles in `static/style.css`.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_topic_page -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app.py templates/topic.html static/style.css tests/test_topic_page.py
git commit -m "feat: add topic checklist page"
```

### Task 6: Replace Queue-Based Practice With Explicit Question Practice

**Files:**
- Create: `tests/test_question_page.py`
- Modify: `app.py`
- Modify: `templates/practice.html`

**Step 1: Write the failing test**

Create route tests for `/question/<problem_id>` asserting:

- the page loads for a valid question
- it renders the specific problem data
- it does not depend on session queue state
- it includes answer controls and a return link to the topic page

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_question_page -v`
Expected: FAIL because the app still depends on queue/session navigation.

**Step 3: Write minimal implementation**

Refactor the practice route so the main question page becomes:

- `/question/<problem_id>`

Reuse the existing practice template where possible, but remove assumptions about:

- queue
- current position within a random session
- results-page destination

Add a `Back to Topic` link based on the question’s category.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_question_page -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app.py templates/practice.html tests/test_question_page.py
git commit -m "feat: add explicit question practice page"
```

### Task 7: Make Answer Submission Update the Database

**Files:**
- Create: `tests/test_question_submission.py`
- Modify: `app.py`

**Step 1: Write the failing test**

Create tests proving that posting to `/question/<problem_id>/answer`:

- increments `correct_count` on a correct answer
- increments `wrong_count` on an incorrect answer
- marks the question finished
- redirects back to the correct topic page
- ignores invalid answer payloads

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_question_submission -v`
Expected: FAIL because the route still writes only to session history.

**Step 3: Write minimal implementation**

Add:

- `/question/<problem_id>/answer` POST route

Use the already loaded correct answer from `PROB_BY_ID` to call `record_result(...)`.

Redirect back to `/topic/<topic_slug>`.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_question_submission -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app.py tests/test_question_submission.py
git commit -m "feat: persist answer results in database"
```

### Task 8: Add Reset/Reopen Behavior

**Files:**
- Create: `tests/test_reopen_question.py`
- Modify: `app.py`
- Modify: `templates/topic.html`

**Step 1: Write the failing test**

Create tests proving that reopening:

- sets `finished = 0`
- keeps `correct_count` unchanged
- keeps `wrong_count` unchanged
- redirects back to the topic page

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_reopen_question -v`
Expected: FAIL because the reset route does not exist.

**Step 3: Write minimal implementation**

Add:

- `/question/<problem_id>/reset` POST route

Update `templates/topic.html` so finished rows render a `Reopen` form/button.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_reopen_question -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app.py templates/topic.html tests/test_reopen_question.py
git commit -m "feat: add reopen behavior for finished questions"
```

### Task 9: Retire Legacy Session-Only Routes and Templates

**Files:**
- Modify: `app.py`
- Modify or remove: `templates/results.html`
- Modify: tests that still assume `/start` or `/results`

**Step 1: Write the failing test**

Add or update tests to define the expected legacy behavior:

- `/start` is no longer required for normal use
- `/results` is no longer part of the main checklist flow

**Step 2: Run test to verify it fails**

Run the affected test module(s).

**Step 3: Write minimal implementation**

Choose the lightest clean path:

- redirect legacy routes to `/`
- or remove them if no tests or templates rely on them anymore

Do not leave dead navigation paths in the UI.

**Step 4: Run tests to verify they pass**

Run the affected test module(s) again.

**Step 5: Commit**

```bash
git add app.py templates/results.html tests
git commit -m "refactor: retire legacy session practice flow"
```

### Task 10: Full Verification and Manual Smoke Test

**Files:**
- Verify: `app.py`
- Verify: `templates/index.html`
- Verify: `templates/topic.html`
- Verify: `templates/practice.html`
- Verify: `static/style.css`
- Verify: all new and updated `tests/*.py`

**Step 1: Run the focused test modules**

Run:

```bash
python3 -m unittest tests.test_progress_db -v
python3 -m unittest tests.test_topic_dashboard -v
python3 -m unittest tests.test_index_dashboard -v
python3 -m unittest tests.test_topic_page -v
python3 -m unittest tests.test_question_page -v
python3 -m unittest tests.test_question_submission -v
python3 -m unittest tests.test_reopen_question -v
```

Expected: PASS

**Step 2: Run the full suite**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

Expected: PASS with all tests green.

**Step 3: Run syntax verification**

Run:

```bash
python3 -m py_compile app.py
```

Expected: PASS with no output.

**Step 4: Manual smoke test**

Run the app and verify:

1. Open `/`
2. Open a topic
3. Click an open question
4. Submit one correct answer
5. Confirm the topic list now shows `[x]`
6. Confirm the lifetime correct count increased
7. Reopen that same question
8. Confirm `[ ]` returns while counts stay intact
9. Refresh the page and confirm the same state remains
10. Open another browser tab and confirm the same state appears

**Step 5: Commit**

```bash
git add app.py templates static tests
git commit -m "feat: build persistent topic checklist tracker"
```
