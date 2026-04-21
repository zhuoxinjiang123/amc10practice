import unittest

from app import app


class PracticeFlowTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def start_session(self, count=2):
        response = self.client.post("/start", data={"count": count})
        self.assertEqual(response.status_code, 302)

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


if __name__ == "__main__":
    unittest.main()
