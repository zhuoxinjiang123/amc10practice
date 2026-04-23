import tempfile
import unittest
from pathlib import Path

from app import PROBLEMS, app, ensure_db, record_attempt, slugify_topic


class TopicPageTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "progress.sqlite3"
        app.config["TESTING"] = True
        app.config["PROGRESS_DB_PATH"] = self.db_path
        ensure_db(self.db_path)
        self.client = app.test_client()
        self.topic = "Algebra"
        self.topic_slug = slugify_topic(self.topic)

    def tearDown(self):
        self.tmpdir.cleanup()

    def problem_in_topic(self, predicate):
        return next(
            problem
            for problem in PROBLEMS
            if problem.get("category") == self.topic and predicate(int(problem["problem_num"]))
        )

    def problem_label_snippet(self, problem):
        return f">{problem['contest_label']} - Problem {problem['problem_num']}<"

    def test_topic_page_renders_filters_and_history_based_status_labels(self):
        practiced = self.problem_in_topic(lambda num: num <= 7)
        untouched = self.problem_in_topic(lambda num: 11 <= num <= 15)

        record_attempt(self.db_path, practiced["problem_id"], is_correct=True)
        record_attempt(self.db_path, practiced["problem_id"], is_correct=False)

        response = self.client.get(f"/topic/{self.topic_slug}")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("All", html)
        self.assertIn("Easy", html)
        self.assertIn("Medium", html)
        self.assertIn("Hard", html)
        self.assertIn(self.problem_label_snippet(practiced), html)
        self.assertIn(self.problem_label_snippet(untouched), html)
        self.assertIn("Correct: 1", html)
        self.assertIn("Wrong: 1", html)
        self.assertIn("Not answered yet", html)

    def test_topic_page_filters_visible_rows_by_current_difficulty_rules(self):
        easy_problem = self.problem_in_topic(lambda num: num <= 7)
        medium_problem = self.problem_in_topic(lambda num: 11 <= num <= 15)
        hard_problem = self.problem_in_topic(lambda num: num >= 19)

        easy_html = self.client.get(f"/topic/{self.topic_slug}?difficulty=easy").get_data(as_text=True)
        medium_html = self.client.get(f"/topic/{self.topic_slug}?difficulty=medium").get_data(as_text=True)
        hard_html = self.client.get(f"/topic/{self.topic_slug}?difficulty=hard").get_data(as_text=True)

        self.assertIn(self.problem_label_snippet(easy_problem), easy_html)
        self.assertNotIn(self.problem_label_snippet(medium_problem), easy_html)
        self.assertNotIn(self.problem_label_snippet(hard_problem), easy_html)

        self.assertNotIn(self.problem_label_snippet(easy_problem), medium_html)
        self.assertIn(self.problem_label_snippet(medium_problem), medium_html)
        self.assertNotIn(self.problem_label_snippet(hard_problem), medium_html)

        self.assertNotIn(self.problem_label_snippet(easy_problem), hard_html)
        self.assertNotIn(self.problem_label_snippet(medium_problem), hard_html)
        self.assertIn(self.problem_label_snippet(hard_problem), hard_html)

    def test_topic_page_returns_404_for_unknown_topic(self):
        response = self.client.get("/topic/not-a-real-topic")
        self.assertEqual(response.status_code, 404)

    def test_topic_page_renders_learning_cockpit_design_hooks(self):
        response = self.client.get(f"/topic/{self.topic_slug}")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('class="topic-shell"', html)
        self.assertIn('class="topic-command-bar"', html)
        self.assertIn('class="question-status-pill', html)


if __name__ == "__main__":
    unittest.main()
