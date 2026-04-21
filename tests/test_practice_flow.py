import unittest

from app import app
from app import PROBLEMS


class PracticeFlowTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def start_session(self, count=2):
        response = self.client.post("/start", data={"count": count})
        self.assertEqual(response.status_code, 302)

    def set_single_problem_queue(self, problem):
        with self.client.session_transaction() as session:
            session["queue"] = [problem["problem_id"]]
            session["pos"] = 0
            session["history"] = []

    def problem_with_answer(self):
        return next(p for p in PROBLEMS if p.get("correct_answer"))

    def wrong_answer_for(self, correct_answer):
        return next(letter for letter in ["A", "B", "C", "D", "E"] if letter != correct_answer)

    def test_practice_page_renders_native_answer_form(self):
        self.start_session()

        response = self.client.get("/practice")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('<form id="answer-form"', html)
        self.assertIn('action="/answer"', html)
        self.assertIn('method="post"', html)
        self.assertIn('type="hidden" id="choice-input" name="choice"', html)
        self.assertIn("selected=A", html)
        self.assertIn("step=1", html)
        self.assertIn('name="choice"', html)
        self.assertIn('<form id="skip-form"', html)

    def test_practice_page_shows_selected_choice_from_query_param(self):
        self.start_session()

        response = self.client.get("/practice?step=1&selected=C")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Selected: C", html)
        self.assertIn('value="C"', html)
        self.assertIn("btn-answer-selected", html)

    def test_practice_page_disables_browser_caching(self):
        self.start_session()

        response = self.client.get("/practice")

        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response.headers.get("Cache-Control", ""))

    def test_answer_redirect_uses_step_cache_buster(self):
        self.start_session(count=3)

        response = self.client.post(
            "/answer",
            data={"choice": "A", "time_spent": "5"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get("Location"), "/practice?step=2")

    def test_answer_records_correct_submission_as_correct(self):
        problem = self.problem_with_answer()
        self.set_single_problem_queue(problem)

        response = self.client.post(
            "/answer",
            data={"choice": problem["correct_answer"], "time_spent": "5"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as session:
            history = session["history"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["answer"], problem["correct_answer"])
        self.assertTrue(history[0]["correct"])
        self.assertFalse(history[0]["skipped"])

    def test_answer_skip_keeps_correct_none_and_skipped_true(self):
        problem = self.problem_with_answer()
        self.set_single_problem_queue(problem)

        response = self.client.post(
            "/answer",
            data={"choice": "skip", "time_spent": "5"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as session:
            history = session["history"]
        self.assertEqual(len(history), 1)
        self.assertIsNone(history[0]["correct"])
        self.assertTrue(history[0]["skipped"])

    def test_answer_records_wrong_submission_as_incorrect(self):
        problem = self.problem_with_answer()
        self.set_single_problem_queue(problem)
        wrong_answer = self.wrong_answer_for(problem["correct_answer"])

        response = self.client.post(
            "/answer",
            data={"choice": wrong_answer, "time_spent": "5"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as session:
            history = session["history"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["answer"], wrong_answer)
        self.assertFalse(history[0]["correct"])
        self.assertFalse(history[0]["skipped"])

    def test_answer_normalizes_lowercase_choice_before_scoring(self):
        problem = self.problem_with_answer()
        self.set_single_problem_queue(problem)

        response = self.client.post(
            "/answer",
            data={"choice": problem["correct_answer"].lower(), "time_spent": "5"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as session:
            history = session["history"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["answer"], problem["correct_answer"])
        self.assertTrue(history[0]["correct"])

    def test_answer_rejects_invalid_choice_without_recording_history(self):
        problem = self.problem_with_answer()
        self.set_single_problem_queue(problem)

        response = self.client.post(
            "/answer",
            data={"choice": "Z", "time_spent": "5"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as session:
            self.assertEqual(session["pos"], 0)
            self.assertEqual(session["history"], [])


if __name__ == "__main__":
    unittest.main()
