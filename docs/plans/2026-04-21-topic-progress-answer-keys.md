# Topic Progress and Answer Keys Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a real AMC 10 answer-key dataset, score submitted answers correctly, and show per-topic finished and correct counts during practice and on the results page.

**Architecture:** Keep answer keys in a dedicated CSV file and load them into the Flask app at startup, then attach each correct letter to the in-memory problem records. Compute topic summaries from the active session queue on the server and render them into the existing Jinja templates so progress stays accurate across page reloads without client-side state. Follow @test-driven-development for each behavior change and finish with @verification-before-completion.

**Tech Stack:** Python, Flask, CSV, Jinja2 templates, CSS, `unittest`

---

### Task 1: Add Answer-Key Loading Helpers

**Files:**
- Create: `tests/fixtures/amc10_answers_sample.csv`
- Create: `tests/test_answer_keys.py`
- Modify: `app.py`

**Step 1: Write the failing test**

Create `tests/fixtures/amc10_answers_sample.csv`:

```csv
problem_id,answer
1,c
2,E
```

Create `tests/test_answer_keys.py`:

```python
import unittest
from pathlib import Path

from app import load_answer_keys


class AnswerKeyTests(unittest.TestCase):
    def test_load_answer_keys_normalizes_letters_by_problem_id(self):
        keys = load_answer_keys(Path("tests/fixtures/amc10_answers_sample.csv"))
        self.assertEqual(keys["1"], "C")
        self.assertEqual(keys["2"], "E")
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_answer_keys -v`
Expected: FAIL with `ImportError` or `AttributeError` because `load_answer_keys` does not exist yet.

**Step 3: Write minimal implementation**

Add to `app.py`:

```python
ANSWER_CHOICES = {"A", "B", "C", "D", "E"}


def load_answer_keys(path):
    with open(path, newline="") as f:
        rows = csv.DictReader(f)
        answer_keys = {}
        for row in rows:
            problem_id = (row.get("problem_id") or "").strip()
            answer = (row.get("answer") or "").strip().upper()
            if not problem_id or answer not in ANSWER_CHOICES:
                raise ValueError(f"Invalid answer-key row: {row}")
            answer_keys[problem_id] = answer
    return answer_keys
```

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_answer_keys -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/fixtures/amc10_answers_sample.csv tests/test_answer_keys.py app.py
git commit -m "test: add answer key loading helper"
```

### Task 2: Merge Production Answer Keys Into Problem Records

**Files:**
- Create: `data/amc10_answers.csv`
- Modify: `app.py`
- Modify: `tests/test_answer_keys.py`

**Step 1: Write the failing test**

Extend `tests/test_answer_keys.py`:

```python
from app import attach_answer_keys


def test_attach_answer_keys_sets_answer_on_problem_records(self):
    problems = [{"problem_id": "1", "category": "Algebra"}]
    enriched = attach_answer_keys(problems, {"1": "C"})
    self.assertEqual(enriched[0]["correct_answer"], "C")
```

Add one more test:

```python
def test_production_answer_file_matches_existing_problem_ids(self):
    keys = load_answer_keys(Path("data/amc10_answers.csv"))
    self.assertIn("1", keys)
    self.assertEqual(len(keys), len(PROBLEMS))
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_answer_keys -v`
Expected: FAIL because `attach_answer_keys` does not exist and the production answer file is missing.

**Step 3: Write minimal implementation**

Create `data/amc10_answers.csv` with header:

```csv
problem_id,answer
```

Populate it with the vetted answer letter for every `problem_id` in the current AMC 10 dataset.

Add to `app.py`:

```python
ANSWER_KEY_PATH = DATA_DIR / "amc10_answers.csv"


def attach_answer_keys(problems, answer_keys):
    enriched = []
    for problem in problems:
        copied = dict(problem)
        copied["correct_answer"] = answer_keys.get(problem["problem_id"], "")
        enriched.append(copied)
    return enriched
```

Update startup loading:

```python
RAW_PROBLEMS = load_problems()
ANSWER_KEYS = load_answer_keys(ANSWER_KEY_PATH)
PROBLEMS = attach_answer_keys(RAW_PROBLEMS, ANSWER_KEYS)
PROB_BY_ID = {p["problem_id"]: p for p in PROBLEMS}
```

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_answer_keys -v`
Expected: PASS

**Step 5: Commit**

```bash
git add data/amc10_answers.csv tests/test_answer_keys.py app.py
git commit -m "feat: attach answer keys to problem records"
```

### Task 3: Score Submitted Answers and Preserve Skip Semantics

**Files:**
- Modify: `tests/test_practice_flow.py`
- Modify: `app.py`

**Step 1: Write the failing test**

Add to `tests/test_practice_flow.py`:

```python
def test_answer_route_marks_correct_answer(self):
    self.start_session(count=1)
    with self.client.session_transaction() as sess:
        first_problem = sess["queue"][0]
        correct = app.config["PROB_BY_ID"][first_problem]["correct_answer"]

    self.client.post("/answer", data={"choice": correct, "time_spent": "5"})

    with self.client.session_transaction() as sess:
        self.assertTrue(sess["history"][0]["correct"])
        self.assertFalse(sess["history"][0]["skipped"])


def test_skip_route_keeps_correct_as_none(self):
    self.start_session(count=1)
    self.client.post("/answer", data={"choice": "skip", "time_spent": "3"})

    with self.client.session_transaction() as sess:
        self.assertIsNone(sess["history"][0]["correct"])
        self.assertTrue(sess["history"][0]["skipped"])
```

If the app module is not convenient for direct access in tests, expose `PROB_BY_ID` directly from `app.py` and import it.

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_practice_flow -v`
Expected: FAIL because history currently stores `correct=None` for submitted answers.

**Step 3: Write minimal implementation**

Update `/answer` in `app.py`:

```python
problem = PROB_BY_ID.get(pid, {})
correct_answer = problem.get("correct_answer", "")
is_skip = choice == "skip"
given_answer = None if is_skip else choice

history.append({
    "id": pid,
    "answer": given_answer,
    "correct": None if is_skip else given_answer == correct_answer,
    "skipped": is_skip,
    "time": time_spent,
})
```

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_practice_flow -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_practice_flow.py app.py
git commit -m "feat: score submitted practice answers"
```

### Task 4: Add Topic Summary Aggregation for the Active Session

**Files:**
- Create: `tests/test_topic_progress.py`
- Modify: `app.py`

**Step 1: Write the failing test**

Create `tests/test_topic_progress.py`:

```python
import unittest

from app import build_topic_progress


class TopicProgressTests(unittest.TestCase):
    def test_build_topic_progress_counts_total_finished_and_correct(self):
        queue = ["1", "2", "3"]
        problems = {
            "1": {"problem_id": "1", "category": "Algebra"},
            "2": {"problem_id": "2", "category": "Algebra"},
            "3": {"problem_id": "3", "category": "Geometry"},
        }
        history = [
            {"id": "1", "correct": True, "skipped": False},
            {"id": "3", "correct": None, "skipped": True},
        ]

        topic_progress = build_topic_progress(queue, history, problems)

        self.assertEqual(topic_progress["Algebra"]["total"], 2)
        self.assertEqual(topic_progress["Algebra"]["finished"], 1)
        self.assertEqual(topic_progress["Algebra"]["correct"], 1)
        self.assertEqual(topic_progress["Geometry"]["total"], 1)
        self.assertEqual(topic_progress["Geometry"]["finished"], 1)
        self.assertEqual(topic_progress["Geometry"]["correct"], 0)
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_topic_progress -v`
Expected: FAIL because `build_topic_progress` does not exist.

**Step 3: Write minimal implementation**

Add to `app.py`:

```python
def normalize_topic(problem):
    return (problem.get("category") or "Uncategorized").strip() or "Uncategorized"


def build_topic_progress(queue, history, problems_by_id):
    summary = {}

    for problem_id in queue:
        problem = problems_by_id.get(problem_id, {})
        topic = normalize_topic(problem)
        summary.setdefault(topic, {"topic": topic, "total": 0, "finished": 0, "answered": 0, "correct": 0})
        summary[topic]["total"] += 1

    for row in history:
        problem = problems_by_id.get(row["id"], {})
        topic = normalize_topic(problem)
        summary.setdefault(topic, {"topic": topic, "total": 0, "finished": 0, "answered": 0, "correct": 0})
        summary[topic]["finished"] += 1
        if not row.get("skipped"):
            summary[topic]["answered"] += 1
        if row.get("correct") is True:
            summary[topic]["correct"] += 1

    return summary
```

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_topic_progress -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_topic_progress.py app.py
git commit -m "feat: add topic progress aggregation"
```

### Task 5: Render Topic Progress on the Practice Page

**Files:**
- Modify: `tests/test_practice_flow.py`
- Modify: `app.py`
- Modify: `templates/practice.html`
- Modify: `static/style.css`

**Step 1: Write the failing test**

Add to `tests/test_practice_flow.py`:

```python
def test_practice_page_renders_topic_progress_panel(self):
    self.start_session(count=3)

    with self.client.session_transaction() as sess:
        sess["history"] = [{"id": sess["queue"][0], "answer": "A", "correct": True, "skipped": False, "time": 4}]

    response = self.client.get("/practice")
    html = response.get_data(as_text=True)

    self.assertIn("Topic Progress", html)
    self.assertIn("finished", html.lower())
    self.assertIn("correct", html.lower())
    self.assertIn("topic-progress-card", html)
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_practice_flow -v`
Expected: FAIL because the practice template does not render topic progress yet.

**Step 3: Write minimal implementation**

In `app.py`, compute and pass the summary:

```python
topic_progress = build_topic_progress(queue, history, PROB_BY_ID)
```

Pass into `render_template(...)` as:

```python
topic_progress=topic_progress.values(),
```

In `templates/practice.html`, add a server-rendered block below the existing progress bar:

```html
<section class="topic-progress-panel">
  <h2>Topic Progress</h2>
  <div class="topic-progress-grid">
    {% for item in topic_progress %}
    <article class="topic-progress-card">
      <div class="topic-progress-title">{{ item.topic }}</div>
      <div class="topic-progress-meta">Finished {{ item.finished }} / {{ item.total }}</div>
      <div class="topic-progress-meta">Correct {{ item.correct }}</div>
      <div class="topic-progress-track">
        <div class="topic-progress-fill" style="width: {{ (item.finished / item.total * 100)|int if item.total else 0 }}%"></div>
      </div>
    </article>
    {% endfor %}
  </div>
</section>
```

Add minimal matching styles in `static/style.css` for:

- `.topic-progress-panel`
- `.topic-progress-grid`
- `.topic-progress-card`
- `.topic-progress-track`
- `.topic-progress-fill`

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_practice_flow -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_practice_flow.py app.py templates/practice.html static/style.css
git commit -m "feat: show topic progress during practice"
```

### Task 6: Render Topic Progress and Correctness State on the Results Page

**Files:**
- Create: `tests/test_results_progress.py`
- Modify: `app.py`
- Modify: `templates/results.html`
- Modify: `static/style.css`

**Step 1: Write the failing test**

Create `tests/test_results_progress.py`:

```python
import unittest

from app import app


class ResultsProgressTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_results_page_shows_topic_progress_and_correctness(self):
        self.client.post("/start", data={"count": 2})
        with self.client.session_transaction() as sess:
            first_id, second_id = sess["queue"]
            sess["history"] = [
                {"id": first_id, "answer": "A", "correct": True, "skipped": False, "time": 5},
                {"id": second_id, "answer": None, "correct": None, "skipped": True, "time": 3},
            ]
            sess["pos"] = 2

        response = self.client.get("/results")
        html = response.get_data(as_text=True)

        self.assertIn("Topic Progress", html)
        self.assertIn("badge-correct", html)
        self.assertIn("badge-skip", html)
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_results_progress -v`
Expected: FAIL because the results page does not include topic summaries or correctness badges.

**Step 3: Write minimal implementation**

Update the `detail` rows in `app.py`:

```python
"correct": h.get("correct"),
"topic": normalize_topic(p),
```

Compute and pass:

```python
topic_progress = build_topic_progress(queue, history, PROB_BY_ID)
```

Update `templates/results.html` to:

- render the same `Topic Progress` panel near the top
- show `correct`, `incorrect`, and `skipped` badges in the review table

Example badge rendering:

```html
{% if d.skipped %}
  <span class="badge badge-skip">Skipped</span>
{% elif d.correct %}
  <span class="badge badge-correct">Correct</span>
{% else %}
  <span class="badge badge-incorrect">Incorrect</span>
{% endif %}
```

Add matching styles in `static/style.css` for:

- `.badge-correct`
- `.badge-incorrect`

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_results_progress -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_results_progress.py app.py templates/results.html static/style.css
git commit -m "feat: add results topic progress and correctness badges"
```

### Task 7: Full Verification and Cleanup

**Files:**
- Modify: `README.md` only if the answer-key dataset or scoring behavior needs a short note
- Verify: `app.py`
- Verify: `templates/practice.html`
- Verify: `templates/results.html`
- Verify: `static/style.css`
- Verify: `tests/test_answer_keys.py`
- Verify: `tests/test_practice_flow.py`
- Verify: `tests/test_topic_progress.py`
- Verify: `tests/test_results_progress.py`

**Step 1: Run the focused test modules**

Run:

```bash
python3 -m unittest tests.test_answer_keys -v
python3 -m unittest tests.test_practice_flow -v
python3 -m unittest tests.test_topic_progress -v
python3 -m unittest tests.test_results_progress -v
```

Expected: PASS

**Step 2: Run the full suite**

Run: `python3 -m unittest discover -s tests -p 'test_*.py'`
Expected: PASS with all test files green.

**Step 3: Run syntax verification**

Run: `python3 -m py_compile app.py`
Expected: PASS with no output.

**Step 4: Manual smoke test**

Run the app and verify:

1. Start a mixed-topic session
2. Answer one correctly
3. Answer one incorrectly
4. Skip one
5. Confirm the practice page topic cards update between questions
6. Confirm the results page shows topic totals and correctness badges

**Step 5: Commit**

```bash
git add app.py static/style.css templates/practice.html templates/results.html tests README.md data/amc10_answers.csv
git commit -m "feat: add answer keyed topic progress"
```
