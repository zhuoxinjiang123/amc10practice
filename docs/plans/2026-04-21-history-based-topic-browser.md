# History-Based Topic Browser Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the random session-based AMC 10 practice flow with a SQLite-backed topic browser where users pick questions directly from topic lists and see persistent lifetime correct/wrong history per question.

**Architecture:** Keep the question catalog and answer keys in CSV-backed memory, then add a SQLite database that stores only per-question attempt counts. Build three server-rendered surfaces: topic dashboard, topic browser with difficulty filter tabs, and explicit question practice pages keyed by `problem_id`. Retire session queue flow instead of extending it. Follow @test-driven-development for each behavior change and finish with @verification-before-completion.

**Tech Stack:** Python, Flask, SQLite, CSV, Jinja2 templates, CSS, `unittest`

---

### Task 1: Remove Conflicting Session-Progress WIP

**Files:**
- Modify: `app.py`
- Modify: `templates/practice.html`
- Modify: `static/style.css`
- Modify: `tests/test_practice_flow.py`

**Step 1: Confirm the current dirty worktree**

Run:

```bash
git status --short
```

Expected: uncommitted practice-page topic-progress changes from the old session-oriented direction.

**Step 2: Revert only the uncommitted session-progress WIP**

Revert the uncommitted changes in:

- `app.py`
- `templates/practice.html`
- `static/style.css`
- `tests/test_practice_flow.py`

Do not revert the already committed answer-key, scoring, or topic-aggregation commits.

**Step 3: Verify the worktree is clean**

Run:

```bash
git status --short
```

Expected: no output.

**Step 4: Commit**

```bash
git commit --allow-empty -m "chore: clear session progress wip for topic browser redesign"
```

Only create this commit if an actual revert was required.

### Task 2: Add Persistent Attempt-History Database Helpers

**Files:**
- Create: `tests/test_progress_db.py`
- Modify: `app.py`

**Step 1: Write the failing test**

Create tests for:

- database initialization
- untouched-question default zero state
- correct-answer increment
- wrong-answer increment

Example shape:

```python
import tempfile
import unittest
from pathlib import Path

from app import ensure_db, get_progress_map, record_attempt


class ProgressDbTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "progress.sqlite3"

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_record_attempt_increments_correct_count(self):
        ensure_db(self.db_path)
        record_attempt(self.db_path, "1", is_correct=True)
        progress = get_progress_map(self.db_path)
        self.assertEqual(progress["1"]["correct_count"], 1)
        self.assertEqual(progress["1"]["wrong_count"], 0)

    def test_record_attempt_increments_wrong_count(self):
        ensure_db(self.db_path)
        record_attempt(self.db_path, "1", is_correct=False)
        progress = get_progress_map(self.db_path)
        self.assertEqual(progress["1"]["correct_count"], 0)
        self.assertEqual(progress["1"]["wrong_count"], 1)
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_progress_db -v`
Expected: FAIL because the DB helpers do not exist yet.

**Step 3: Write minimal implementation**

Add to `app.py`:

- configured DB path
- `ensure_db(db_path=None)`
- `get_db_connection(db_path=None)`
- `get_progress_map(db_path=None)`
- `record_attempt(db_path, problem_id, is_correct)`

Use a table like:

```sql
CREATE TABLE IF NOT EXISTS question_progress (
  problem_id TEXT PRIMARY KEY,
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
git commit -m "feat: add persistent attempt history store"
```

### Task 3: Build Progress Merge and Topic Summary Helpers

**Files:**
- Create: `tests/test_topic_dashboard.py`
- Modify: `app.py`

**Step 1: Write the failing test**

Create tests for helpers that:

- merge catalog questions with progress rows
- compute topic dashboard summaries
- count `answered` as questions with any attempts
- sum topic `correct` and `wrong` totals

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_topic_dashboard -v`
Expected: FAIL because the helper functions do not exist.

**Step 3: Write minimal implementation**

Add helpers such as:

- `merge_problem_progress(problem, progress_map)`
- `build_topic_dashboard(problems, progress_map)`
- `slugify_topic(topic_name)`
- `difficulty_matches(problem, difficulty)`

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_topic_dashboard -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app.py tests/test_topic_dashboard.py
git commit -m "feat: add topic browser summary helpers"
```

### Task 4: Replace the Home Page With the Topic Dashboard

**Files:**
- Create: `tests/test_index_dashboard.py`
- Modify: `app.py`
- Modify: `templates/index.html`
- Modify: `static/style.css`

**Step 1: Write the failing test**

Create tests for `/` asserting:

- topic cards render
- each card shows `Answered X / Total`
- each card shows aggregated `Correct` and `Wrong`
- the old random-session controls are no longer the main UI

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_index_dashboard -v`
Expected: FAIL because `/` still renders the old practice setup form.

**Step 3: Write minimal implementation**

Update `/` to:

- load DB progress
- build topic summaries
- render topic dashboard cards

Update `templates/index.html` to remove the random queue setup as the primary experience.

Add minimal styles for dashboard cards.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_index_dashboard -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app.py templates/index.html static/style.css tests/test_index_dashboard.py
git commit -m "feat: replace home page with topic dashboard"
```

### Task 5: Add the Topic Browser Page With Difficulty Filters

**Files:**
- Create: `templates/topic.html`
- Create: `tests/test_topic_page.py`
- Modify: `app.py`
- Modify: `static/style.css`

**Step 1: Write the failing test**

Create tests for `/topic/<topic_slug>` asserting:

- the topic page renders
- difficulty filter values `all`, `easy`, `medium`, and `hard` are supported
- the filtered question list matches the current problem-number rules
- question rows show `Not answered yet` when untouched
- practiced rows show `Correct: N` and `Wrong: M`

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_topic_page -v`
Expected: FAIL because the route and template do not exist yet.

**Step 3: Write minimal implementation**

Add `/topic/<topic_slug>` to:

- resolve the topic
- read `difficulty` from the query string
- filter rows using the existing overlapping rules
- merge progress into the visible row list

Create `templates/topic.html` with:

- topic summary header
- filter tabs/chips
- question rows
- status text
- practice links

Add minimal topic-page styles.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_topic_page -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app.py templates/topic.html static/style.css tests/test_topic_page.py
git commit -m "feat: add topic browser with difficulty filters"
```

### Task 6: Replace Queue-Based Practice With Explicit Question Pages

**Files:**
- Create: `tests/test_question_page.py`
- Modify: `app.py`
- Modify: `templates/practice.html`

**Step 1: Write the failing test**

Create tests for `/question/<problem_id>` asserting:

- it renders a specific question without session queue setup
- it includes answer controls
- it includes a link back to the topic page
- it preserves the current difficulty filter in that link when present

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_question_page -v`
Expected: FAIL because the practice route still depends on queue/session flow.

**Step 3: Write minimal implementation**

Refactor the main practice route into:

- `/question/<problem_id>`

Reuse the current question UI where helpful, but remove assumptions about:

- random queue
- session position
- results-page navigation

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_question_page -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app.py templates/practice.html tests/test_question_page.py
git commit -m "feat: add explicit question practice page"
```

### Task 7: Persist Answer Submission and Return to the Same Filtered Topic View

**Files:**
- Create: `tests/test_question_submission.py`
- Modify: `app.py`

**Step 1: Write the failing test**

Create tests proving that posting to `/question/<problem_id>/answer`:

- increments `correct_count` on a correct answer
- increments `wrong_count` on an incorrect answer
- leaves untouched rows alone on invalid input
- redirects back to the same topic page and selected difficulty filter

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_question_submission -v`
Expected: FAIL because the route still writes only to session history.

**Step 3: Write minimal implementation**

Add:

- `/question/<problem_id>/answer` POST route

Behavior:

- normalize and validate choice
- compare against `correct_answer`
- call `record_attempt(...)`
- redirect to `/topic/<topic_slug>?difficulty=<value>`

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_question_submission -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app.py tests/test_question_submission.py
git commit -m "feat: persist question attempts"
```

### Task 8: Retire Legacy Session Routes and Results Flow

**Files:**
- Modify: `app.py`
- Modify or remove: `templates/results.html`
- Update: older tests that still assume `/start` or `/results`

**Step 1: Write the failing test**

Update or add tests to define the legacy behavior we now want:

- `/start` should no longer be part of the main flow
- `/results` should no longer be the primary progress surface

**Step 2: Run tests to verify they fail**

Run the affected test module(s).

**Step 3: Write minimal implementation**

Choose the simplest clean path:

- redirect legacy routes to `/`
- or remove them if nothing still depends on them

Do not leave dead primary-navigation paths in the UI.

**Step 4: Run tests to verify they pass**

Run the affected test module(s) again.

**Step 5: Commit**

```bash
git add app.py templates/results.html tests
git commit -m "refactor: retire legacy session flow"
```

### Task 9: Full Verification and Manual Smoke Test

**Files:**
- Verify: `app.py`
- Verify: `templates/index.html`
- Verify: `templates/topic.html`
- Verify: `templates/practice.html`
- Verify: `static/style.css`
- Verify: all updated and new `tests/*.py`

**Step 1: Run focused test modules**

Run:

```bash
python3 -m unittest tests.test_progress_db -v
python3 -m unittest tests.test_topic_dashboard -v
python3 -m unittest tests.test_index_dashboard -v
python3 -m unittest tests.test_topic_page -v
python3 -m unittest tests.test_question_page -v
python3 -m unittest tests.test_question_submission -v
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
2. Open a topic card
3. Switch between `All`, `Easy`, `Medium`, and `Hard`
4. Confirm untouched questions show `Not answered yet`
5. Open a question and answer it correctly
6. Confirm the row now shows `Correct: 1 • Wrong: 0`
7. Answer it incorrectly later
8. Confirm the row now shows `Correct: 1 • Wrong: 1`
9. Refresh the topic page and confirm the same state remains
10. Open another browser tab and confirm the same state appears

**Step 5: Commit**

```bash
git add app.py templates static tests
git commit -m "feat: build history-based topic browser"
```
