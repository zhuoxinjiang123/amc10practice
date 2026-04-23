import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as app_module
from app import app, ensure_db, get_progress_map, slugify_topic, PROBLEMS


class QuestionSubmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "progress.sqlite3"
        app.config["TESTING"] = True
        app.config["PROGRESS_DB_PATH"] = self.db_path
        ensure_db(self.db_path)
        self.client = app.test_client()
        self.problem = next(problem for problem in PROBLEMS if problem.get("correct_answer"))
        self.topic_slug = slugify_topic(self.problem["category"])

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_submission_records_correct_attempt_and_returns_to_same_filter(self):
        response = self.client.post(
            f"/question/{self.problem['problem_id']}/answer",
            data={"choice": self.problem["correct_answer"], "difficulty": "medium"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers.get("Location"),
            f"/topic/{self.topic_slug}?difficulty=medium",
        )
        progress = get_progress_map(self.db_path)
        self.assertEqual(progress[self.problem["problem_id"]]["correct_count"], 1)
        self.assertEqual(progress[self.problem["problem_id"]]["wrong_count"], 0)

    def test_submission_records_wrong_attempt(self):
        wrong_answer = next(
            letter for letter in ["A", "B", "C", "D", "E"] if letter != self.problem["correct_answer"]
        )

        response = self.client.post(
            f"/question/{self.problem['problem_id']}/answer",
            data={"choice": wrong_answer, "difficulty": "easy"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        progress = get_progress_map(self.db_path)
        self.assertEqual(progress[self.problem["problem_id"]]["correct_count"], 0)
        self.assertEqual(progress[self.problem["problem_id"]]["wrong_count"], 1)

    def test_submission_normalizes_lowercase_answers(self):
        response = self.client.post(
            f"/question/{self.problem['problem_id']}/answer",
            data={"choice": self.problem["correct_answer"].lower(), "difficulty": "all"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        progress = get_progress_map(self.db_path)
        self.assertEqual(progress[self.problem["problem_id"]]["correct_count"], 1)

    def test_submission_rejects_invalid_choice_without_recording_attempt(self):
        response = self.client.post(
            f"/question/{self.problem['problem_id']}/answer",
            data={"choice": "Z", "difficulty": "hard"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers.get("Location"),
            f"/question/{self.problem['problem_id']}?difficulty=hard",
        )
        self.assertEqual(get_progress_map(self.db_path), {})

    def test_submission_uses_default_database_backend_for_progress(self):
        with patch.dict(app_module.os.environ, {"DATABASE_URL": "postgresql://render-db"}):
            with patch.object(app_module, "record_attempt") as record_attempt_mock:
                response = self.client.post(
                    f"/question/{self.problem['problem_id']}/answer",
                    data={"choice": self.problem["correct_answer"], "difficulty": "medium"},
                    follow_redirects=False,
                )

        self.assertEqual(response.status_code, 302)
        record_attempt_mock.assert_called_once()
        self.assertIsNone(record_attempt_mock.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
