"""
AMC 10 Practice App -- Flask web app for kids.

Shows one problem at a time (embedded from AoPS wiki), lets kids
pick an answer (A-E), tracks session score, and links to solutions.
"""

import csv
import os
import random
from pathlib import Path
from flask import Flask, render_template, session, redirect, url_for, request, jsonify, make_response

app = Flask(__name__)
app.secret_key = "amc10-practice-key-change-me"

DATA_DIR = Path(__file__).resolve().parent / "data"


CATEGORY_LIST = ["Algebra", "Geometry", "Counting & Probability", "Number Theory"]
ANSWER_CHOICES = {"A", "B", "C", "D", "E"}


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
    return render_template("index.html", years=ALL_YEARS,
                           categories=CATEGORY_LIST, cat_counts=CAT_COUNTS)


@app.route("/start", methods=["POST"])
def start():
    """Apply filters, build a problem queue, redirect to first problem."""
    year_min = int(request.form.get("year_min", 2000))
    year_max = int(request.form.get("year_max", 2025))
    difficulty = request.form.get("difficulty", "all")
    category = request.form.get("category", "all")
    count = int(request.form.get("count", 10))
    timer_mode = request.form.get("timer_mode", "stopwatch")
    countdown_minutes = int(request.form.get("countdown_minutes", 30))

    pool = filter_problems(year_min, year_max, difficulty, category)
    if not pool:
        return render_template("index.html", years=ALL_YEARS,
                               categories=CATEGORY_LIST, cat_counts=CAT_COUNTS,
                               error="No problems match your filters. Try wider settings.")

    selected = random.sample(pool, min(count, len(pool)))
    session["queue"] = [p["problem_id"] for p in selected]
    session["pos"] = 0
    session["history"] = []
    session["timer"] = {
        "mode": timer_mode,
        "countdown_seconds": countdown_minutes * 60 if timer_mode == "countdown" else 0,
    }
    session["settings"] = {
        "year_min": year_min, "year_max": year_max,
        "difficulty": difficulty, "category": category, "count": count,
        "timer_mode": timer_mode, "countdown_minutes": countdown_minutes,
    }
    return redirect(url_for("practice", step=1))


@app.route("/practice")
def practice():
    queue = session.get("queue", [])
    pos = session.get("pos", 0)
    if not queue or pos >= len(queue):
        return redirect(url_for("results"))

    pid = queue[pos]
    problem = PROB_BY_ID.get(pid)
    if not problem:
        return redirect(url_for("results"))

    total = len(queue)
    history = session.get("history", [])
    correct_count = sum(1 for h in history if h.get("correct"))
    selected_choice = (request.args.get("selected") or "").strip().upper()
    if selected_choice not in {"A", "B", "C", "D", "E"}:
        selected_choice = ""

    timer = session.get("timer", {"mode": "stopwatch", "countdown_seconds": 0})

    response = make_response(render_template(
        "practice.html",
        problem=problem,
        pos=pos + 1,
        total=total,
        correct_count=correct_count,
        attempted=len(history),
        solution_url=solution_url(problem),
        selected_choice=selected_choice,
        timer_mode=timer["mode"],
        countdown_seconds=timer["countdown_seconds"],
    ))
    return no_store(response)


@app.route("/answer", methods=["POST"])
def answer():
    """Record an answer (or skip) and move to next problem."""
    choice = request.form.get("choice", "")  # A-E or "skip"
    time_spent = int(request.form.get("time_spent", 0))

    queue = session.get("queue", [])
    pos = session.get("pos", 0)

    if pos < len(queue):
        pid = queue[pos]
        history = session.get("history", [])
        history.append({
            "id": pid,
            "answer": choice if choice != "skip" else None,
            "correct": None,  # we don't have answer keys yet
            "skipped": choice == "skip",
            "time": time_spent,
        })
        session["history"] = history
        session["pos"] = pos + 1

    return redirect(url_for("practice", step=session.get("pos", 0) + 1))


@app.route("/results")
def results():
    history = session.get("history", [])
    queue = session.get("queue", [])
    settings = session.get("settings", {})

    detail = []
    total_time = 0
    for h in history:
        p = PROB_BY_ID.get(h["id"], {})
        t = h.get("time", 0)
        total_time += t
        detail.append({
            "contest": p.get("contest_label", ""),
            "num": p.get("problem_num", ""),
            "answer": h.get("answer", "-"),
            "skipped": h.get("skipped", False),
            "url": p.get("problem_url", ""),
            "solution_url": solution_url(p) if p else "",
            "time": t,
        })

    answered = sum(1 for h in history if not h.get("skipped"))
    skipped = sum(1 for h in history if h.get("skipped"))

    response = make_response(render_template(
        "results.html",
        detail=detail,
        total=len(queue),
        answered=answered,
        skipped=skipped,
        total_time=total_time,
        settings=settings,
    ))
    return no_store(response)


# ── Claude AI Assistant ───────────────────────────────────────────

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = (
    "You are a friendly math tutor helping a student practice AMC 10 problems. "
    "RULES:\n"
    "- NEVER reveal the final answer letter (A/B/C/D/E) or the numeric answer.\n"
    "- Give hints that guide the student toward the solution step by step.\n"
    "- Use simple language suitable for a middle/high school student.\n"
    "- If the student asks for the answer directly, encourage them to try first.\n"
    "- Keep responses concise (under 150 words).\n"
    "- Use plain text. For math, write it readably (e.g. x^2 + 1).\n"
)


@app.route("/ai/chat", methods=["POST"])
def ai_chat():
    if not ANTHROPIC_KEY:
        return jsonify({"error": "ANTHROPIC_API_KEY not set. Set it and restart."}), 400

    data = request.get_json()
    user_msg = (data.get("message") or "").strip()
    problem_label = data.get("problem_label", "")
    problem_url = data.get("problem_url", "")

    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    context = f"The student is working on: {problem_label}.\nProblem URL: {problem_url}\n"

    # Get chat history from session
    chat_key = f"chat_{session.get('pos', 0)}"
    chat_history = session.get(chat_key, [])

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

        messages = []
        for msg in chat_history:
            messages.append({"role": msg["role"], "content": msg["text"]})
        messages.append({"role": "user", "content": user_msg})

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=SYSTEM_PROMPT + "\n" + context,
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
