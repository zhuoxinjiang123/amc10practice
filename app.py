"""
AMC 10 Practice App -- Flask web app for kids.

Shows one problem at a time (embedded from AoPS wiki), lets kids
pick an answer (A-E), tracks session score, and links to solutions.
"""

import csv
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, abort, render_template, session, redirect, url_for, request, jsonify, make_response

app = Flask(__name__)
app.secret_key = "amc10-practice-key-change-me"

APP_ROOT = Path(__file__).resolve().parent
DATA_DIR = APP_ROOT / "data"
ENV_FILE_PATH = APP_ROOT / ".env"
PROGRESS_DB_PATH = Path(app.instance_path) / "amc10_progress.sqlite3"
app.config.setdefault("PROGRESS_DB_PATH", PROGRESS_DB_PATH)


CATEGORY_LIST = ["Algebra", "Geometry", "Counting & Probability", "Number Theory"]
ANSWER_CHOICES = {"A", "B", "C", "D", "E"}
DIFFICULTY_ORDER = ("all", "easy", "medium", "hard")
DIFFICULTY_LABELS = {
    "all": "All",
    "easy": "Easy",
    "medium": "Medium",
    "hard": "Hard",
}


def load_local_env(path=None):
    env_path = Path(path) if path is not None else ENV_FILE_PATH
    loaded = {}
    if not env_path.exists():
        return loaded

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        os.environ[key] = value
        loaded[key] = value

    return loaded


load_local_env()


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def resolve_db_path(db_path=None):
    path = Path(db_path) if db_path is not None else Path(app.config["PROGRESS_DB_PATH"])
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def ensure_db(db_path=None):
    path = resolve_db_path(db_path)
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS question_progress (
              problem_id TEXT PRIMARY KEY,
              correct_count INTEGER NOT NULL DEFAULT 0,
              wrong_count INTEGER NOT NULL DEFAULT 0,
              updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()
    return path


def get_db_connection(db_path=None):
    path = ensure_db(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def get_progress_map(db_path=None):
    conn = get_db_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT problem_id, correct_count, wrong_count, updated_at FROM question_progress"
        ).fetchall()
    finally:
        conn.close()
    return {
        row["problem_id"]: {
            "problem_id": row["problem_id"],
            "correct_count": row["correct_count"],
            "wrong_count": row["wrong_count"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    }


def record_attempt(db_path, problem_id, is_correct):
    correct_inc = 1 if is_correct else 0
    wrong_inc = 0 if is_correct else 1
    updated_at = utc_now_iso()
    conn = get_db_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO question_progress (problem_id, correct_count, wrong_count, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(problem_id) DO UPDATE SET
              correct_count = correct_count + excluded.correct_count,
              wrong_count = wrong_count + excluded.wrong_count,
              updated_at = excluded.updated_at
            """,
            (problem_id, correct_inc, wrong_inc, updated_at),
        )
        conn.commit()
    finally:
        conn.close()


def load_problems():
    # Prefer categorized file; fall back to plain index
    path = DATA_DIR / "amc10_categorized.csv"
    if not path.exists():
        path = DATA_DIR / "amc10_index.csv"
    with open(path, newline="") as f:
        return list(csv.DictReader(f))

RAW_PROBLEMS = load_problems()


def load_answer_keys(path=None):
    """Load answer keys from CSV and normalize identifiers/answers."""
    if path is None:
        path = DATA_DIR / "amc10_answers.csv"
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Answer key file not found: {path}")

    keys = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            problem_id = (row.get("problem_id") or row.get("id") or "").strip()
            answer = (row.get("answer") or row.get("correct") or "").strip().upper()
            if not problem_id or answer not in ANSWER_CHOICES:
                raise ValueError(f"Invalid answer key row: {row}")
            if problem_id in keys:
                raise ValueError(f"Duplicate answer key for problem_id {problem_id}")
            keys[problem_id] = answer
    return keys


def attach_answer_keys(problems, keys):
    """Return copied problem records with the matching correct answer attached."""
    enriched = []
    for problem in problems:
        enriched_problem = dict(problem)
        enriched_problem["correct_answer"] = keys.get(problem["problem_id"], "")
        enriched.append(enriched_problem)
    return enriched


def normalize_topic(problem):
    """Return a stable topic label for a problem record."""
    if isinstance(problem, dict):
        raw_topic = problem.get("category") or problem.get("topic") or ""
    else:
        raw_topic = problem or ""
    topic = str(raw_topic).strip()
    return topic or "Uncategorized"


def slugify_topic(topic_name):
    cleaned = normalize_topic(topic_name).lower()
    cleaned = cleaned.replace("&", "")
    cleaned = cleaned.replace("/", " ")
    parts = cleaned.split()
    return "-".join(parts)


def difficulty_matches(problem, difficulty):
    difficulty = (difficulty or "all").strip().lower()
    if difficulty == "all":
        return True
    problem_num = int(problem["problem_num"])
    if difficulty == "easy":
        return problem_num <= 10
    if difficulty == "medium":
        return 8 <= problem_num <= 18
    if difficulty == "hard":
        return problem_num >= 16
    return True


def normalize_difficulty(value):
    difficulty = (value or "all").strip().lower()
    if difficulty in DIFFICULTY_ORDER:
        return difficulty
    return "all"


def sort_catalog_problems(problems):
    return sorted(
        problems,
        key=lambda problem: (
            int(problem.get("year") or 0),
            (problem.get("version") or "").strip(),
            int(problem.get("problem_num") or 0),
            int(problem.get("problem_id") or 0),
        ),
    )


def topic_status_text(correct_count, wrong_count):
    if correct_count == 0 and wrong_count == 0:
        return "Not answered yet"
    return f"Correct: {correct_count} / Wrong: {wrong_count}"


def merge_problem_progress(problem, progress_map):
    progress = progress_map.get(problem["problem_id"], {})
    correct_count = int(progress.get("correct_count", 0))
    wrong_count = int(progress.get("wrong_count", 0))
    answered = (correct_count + wrong_count) > 0

    merged = dict(problem)
    merged["correct_count"] = correct_count
    merged["wrong_count"] = wrong_count
    merged["answered"] = answered
    merged["status_text"] = topic_status_text(correct_count, wrong_count)
    merged["status_marker"] = "[x]" if answered else "[ ]"
    return merged


def find_topic_by_slug(topic_slug):
    for topic in sorted({normalize_topic(problem) for problem in PROBLEMS}, key=str.lower):
        if slugify_topic(topic) == topic_slug:
            return topic
    return None


def get_topic_problem_rows(topic_name, progress_map, difficulty="all"):
    filtered = []
    for problem in PROBLEMS:
        if normalize_topic(problem) != topic_name:
            continue
        if not difficulty_matches(problem, difficulty):
            continue
        filtered.append(merge_problem_progress(problem, progress_map))
    return sort_catalog_problems(filtered)


def build_topic_summary(topic_name, progress_map):
    merged_problems = [
        merge_problem_progress(problem, progress_map)
        for problem in PROBLEMS
        if normalize_topic(problem) == topic_name
    ]
    return {
        "topic": topic_name,
        "slug": slugify_topic(topic_name),
        "total": len(merged_problems),
        "answered": sum(1 for problem in merged_problems if problem["answered"]),
        "correct_total": sum(problem["correct_count"] for problem in merged_problems),
        "wrong_total": sum(problem["wrong_count"] for problem in merged_problems),
    }


def build_topic_dashboard(problems, progress_map):
    summary = {}

    for problem in problems:
        topic = normalize_topic(problem)
        if topic not in summary:
            summary[topic] = {
                "topic": topic,
                "slug": slugify_topic(topic),
                "total": 0,
                "answered": 0,
                "correct_total": 0,
                "wrong_total": 0,
            }

        merged_problem = merge_problem_progress(problem, progress_map)
        bucket = summary[topic]
        bucket["total"] += 1
        if merged_problem["answered"]:
            bucket["answered"] += 1
        bucket["correct_total"] += merged_problem["correct_count"]
        bucket["wrong_total"] += merged_problem["wrong_count"]

    return sorted(summary.values(), key=lambda item: item["topic"].lower())


def build_topic_progress(queue, history, problems_by_id):
    """Aggregate queue-scoped progress by topic from the active session."""
    progress = {}
    topic_by_problem_id = {}

    for problem_id in queue:
        topic = normalize_topic(problems_by_id.get(problem_id, {}))
        topic_by_problem_id[problem_id] = topic
        if topic not in progress:
            progress[topic] = {
                "topic": topic,
                "total": 0,
                "finished": 0,
                "answered": 0,
                "correct": 0,
            }
        progress[topic]["total"] += 1

    for item in history:
        topic = topic_by_problem_id.get(item.get("id"))
        if not topic:
            continue
        bucket = progress[topic]
        bucket["finished"] += 1
        if not item.get("skipped"):
            bucket["answered"] += 1
        if item.get("correct") is True:
            bucket["correct"] += 1

    return progress


ANSWER_KEYS = load_answer_keys()
PROBLEMS = attach_answer_keys(RAW_PROBLEMS, ANSWER_KEYS)

# Build lookup: problem_id -> problem dict
PROB_BY_ID = {p["problem_id"]: p for p in PROBLEMS}

# Unique years
ALL_YEARS = sorted({int(p["year"]) for p in PROBLEMS})

# Count problems per category for display
CAT_COUNTS = {}
for _p in PROBLEMS:
    _cat = (_p.get("category") or "").strip()
    for _c in CATEGORY_LIST:
        if _c.lower() in _cat.lower():
            CAT_COUNTS[_c] = CAT_COUNTS.get(_c, 0) + 1


def filter_problems(year_min, year_max, difficulty, category):
    """Filter problems by year range, difficulty tier, and category."""
    results = []
    for p in PROBLEMS:
        y = int(p["year"])
        n = int(p["problem_num"])
        if y < year_min or y > year_max:
            continue
        # Difficulty tiers based on problem number
        if difficulty == "easy" and n > 10:
            continue
        if difficulty == "medium" and (n < 8 or n > 18):
            continue
        if difficulty == "hard" and n < 16:
            continue
        # Category filter
        if category and category != "all":
            cat = (p.get("category") or "").lower()
            if category.lower() not in cat:
                continue
        results.append(p)
    return results


def get_session_data():
    """Get or initialize session tracking data."""
    if "history" not in session:
        session["history"] = []  # list of {id, correct, answer}
    return session


def solution_url(problem):
    """Build the AoPS solution page URL."""
    return problem["problem_url"].replace("/Problem_", "_Solution")


def no_store(response):
    """Prevent browsers from reusing stale HTML for dynamic practice pages."""
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ── Routes ──────────────────────────────────────────────────────────


@app.route("/")
def index():
    topic_dashboard = build_topic_dashboard(PROBLEMS, get_progress_map())
    return render_template("index.html", topic_dashboard=topic_dashboard)


@app.route("/topic/<topic_slug>")
def topic_page(topic_slug):
    topic_name = find_topic_by_slug(topic_slug)
    if not topic_name:
        abort(404)

    difficulty = normalize_difficulty(request.args.get("difficulty"))
    progress_map = get_progress_map()
    topic_summary = build_topic_summary(topic_name, progress_map)
    problems = get_topic_problem_rows(topic_name, progress_map, difficulty=difficulty)

    response = make_response(render_template(
        "topic.html",
        topic_summary=topic_summary,
        problems=problems,
        difficulty_options=[{"value": value, "label": DIFFICULTY_LABELS[value]} for value in DIFFICULTY_ORDER],
        selected_difficulty=difficulty,
    ))
    return no_store(response)


@app.route("/question/<problem_id>")
def question_page(problem_id):
    problem = PROB_BY_ID.get(problem_id)
    if not problem:
        abort(404)

    difficulty = normalize_difficulty(request.args.get("difficulty"))
    selected_choice = (request.args.get("selected") or "").strip().upper()
    if selected_choice not in ANSWER_CHOICES:
        selected_choice = ""

    progress_map = get_progress_map()
    problem_with_progress = merge_problem_progress(problem, progress_map)
    topic_name = normalize_topic(problem)
    topic_slug = slugify_topic(topic_name)
    back_to_topic_url = url_for("topic_page", topic_slug=topic_slug, difficulty=difficulty)
    session["active_problem_id"] = problem_id

    response = make_response(render_template(
        "practice.html",
        problem=problem_with_progress,
        selected_choice=selected_choice,
        solution_url=solution_url(problem),
        selected_difficulty=difficulty,
        topic_name=topic_name,
        topic_slug=topic_slug,
        back_to_topic_url=back_to_topic_url,
        ai_tutor_modes=AI_TUTOR_MODES,
        default_ai_tutor_mode=DEFAULT_AI_TUTOR_MODE,
    ))
    return no_store(response)


@app.route("/question/<problem_id>/answer", methods=["POST"])
def submit_question_answer(problem_id):
    problem = PROB_BY_ID.get(problem_id)
    if not problem:
        abort(404)

    difficulty = normalize_difficulty(request.form.get("difficulty"))
    raw_choice = (request.form.get("choice", "") or "").strip().upper()
    if raw_choice not in ANSWER_CHOICES:
        return redirect(url_for("question_page", problem_id=problem_id, difficulty=difficulty))

    correct_answer = (problem.get("correct_answer") or "").strip().upper()
    if correct_answer in ANSWER_CHOICES:
        record_attempt(resolve_db_path(), problem_id, raw_choice == correct_answer)

    return redirect(url_for("topic_page", topic_slug=slugify_topic(problem), difficulty=difficulty))


@app.route("/start", methods=["POST"])
def start():
    return redirect(url_for("index"))


@app.route("/practice")
def practice():
    return redirect(url_for("index"))


@app.route("/answer", methods=["POST"])
def answer():
    return redirect(url_for("index"))


@app.route("/results")
def results():
    return redirect(url_for("index"))


# ── Claude AI Assistant ───────────────────────────────────────────

AI_HINT_MODEL = "claude-opus-4-1-20250805"
AI_TUTOR_MODES = {
    "hint": {
        "label": "Hint",
        "instruction": "Give a gentle hint that nudges the student toward the next useful idea without outlining the full solution.",
        "intro": "Hint mode is on. I will give you a small push without spoiling the path.",
        "placeholder": "Ask for a hint...",
    },
    "socratic": {
        "label": "Socratic",
        "instruction": "Use a Socratic tutoring style: ask guiding questions, reveal as little as possible, and help the student discover the next step themselves.",
        "intro": "Socratic mode is on. I will mostly respond with guiding questions.",
        "placeholder": "Ask for a guiding question...",
    },
    "step_by_step": {
        "label": "Step-by-step",
        "instruction": "Give a clearer step-by-step walkthrough, but still do not reveal the final answer letter or numeric answer.",
        "intro": "Step-by-step mode is on. I will explain the path more directly without giving the final answer.",
        "placeholder": "Ask for a step-by-step explanation...",
    },
    "challenge": {
        "label": "Challenge",
        "instruction": "Be extra concise and challenging: offer only a very short nudge or a checkpoint to test the student's thinking.",
        "intro": "Challenge mode is on. I will keep hints very short so you do more of the work.",
        "placeholder": "Ask for a tiny nudge...",
    },
}
DEFAULT_AI_TUTOR_MODE = "hint"


def get_ai_hint_model():
    return os.environ.get("AI_HINT_MODEL", AI_HINT_MODEL).strip() or AI_HINT_MODEL


def get_anthropic_key():
    return os.environ.get("ANTHROPIC_API_KEY", "").strip()

SYSTEM_PROMPT = (
    "You are a friendly math tutor helping a student practice AMC 10 problems. "
    "RULES:\n"
    "- NEVER reveal the final answer letter (A/B/C/D/E) or the numeric answer.\n"
    "- Give hints that guide the student toward the solution step by step.\n"
    "- Use simple language suitable for a middle/high school student.\n"
    "- If the student asks for the answer directly, encourage them to try first.\n"
    "- Keep responses concise (under 150 words).\n"
    "- Use LaTeX-style math formatting for mathematical expressions within otherwise plain text explanations.\n"
    "- For inline math use \\( ... \\). For displayed equations use \\[ ... \\].\n"
    "- Prefer nicely formatted fractions, exponents, radicals, sums, and aligned equations when helpful.\n"
)


def normalize_ai_tutor_mode(value):
    candidate = (value or DEFAULT_AI_TUTOR_MODE).strip().lower()
    if candidate in AI_TUTOR_MODES:
        return candidate
    return DEFAULT_AI_TUTOR_MODE


def build_ai_system_prompt(tutor_mode):
    mode = normalize_ai_tutor_mode(tutor_mode)
    return SYSTEM_PROMPT + "\n" + AI_TUTOR_MODES[mode]["instruction"]


@app.route("/ai/chat", methods=["POST"])
def ai_chat():
    anthropic_key = get_anthropic_key()
    if not anthropic_key:
        return jsonify({"error": "ANTHROPIC_API_KEY not set. Add it to your environment or a local .env file, then restart."}), 400

    data = request.get_json()
    user_msg = (data.get("message") or "").strip()
    problem_label = data.get("problem_label", "")
    problem_url = data.get("problem_url", "")
    problem_id = str(data.get("problem_id") or session.get("active_problem_id") or "").strip()
    tutor_mode = normalize_ai_tutor_mode(data.get("tutor_mode"))

    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    context = f"The student is working on: {problem_label}.\nProblem URL: {problem_url}\n"

    # Get chat history from session
    chat_key_base = problem_id if problem_id else str(session.get("pos", 0))
    chat_key = f"chat_{chat_key_base}_{tutor_mode}"
    chat_history = session.get(chat_key, [])

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=anthropic_key)

        messages = []
        for msg in chat_history:
            messages.append({"role": msg["role"], "content": msg["text"]})
        messages.append({"role": "user", "content": user_msg})

        response = client.messages.create(
            model=get_ai_hint_model(),
            max_tokens=300,
            system=build_ai_system_prompt(tutor_mode) + "\n" + context,
            messages=messages,
        )
        reply = response.content[0].text

        # Save to session
        chat_history.append({"role": "user", "text": user_msg})
        chat_history.append({"role": "assistant", "text": reply})
        session[chat_key] = chat_history

        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/reset")
def reset():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, port=5050)
