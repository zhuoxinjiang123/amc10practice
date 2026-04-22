import unittest

from app import PROBLEMS, app, slugify_topic


class QuestionPageTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.problem = next(problem for problem in PROBLEMS if problem.get("category") == "Algebra")
        self.topic_slug = slugify_topic(self.problem["category"])

    def test_question_page_renders_direct_practice_view_and_back_link(self):
        response = self.client.get(f"/question/{self.problem['problem_id']}?difficulty=hard")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.problem["contest_label"], html)
        self.assertIn(f'action="/question/{self.problem["problem_id"]}/answer"', html)
        self.assertIn("Your answer:", html)
        self.assertIn(f'href="/topic/{self.topic_slug}?difficulty=hard"', html)

    def test_question_page_preserves_selected_choice_from_query_string(self):
        response = self.client.get(f"/question/{self.problem['problem_id']}?difficulty=medium&selected=C")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Selected: C", html)
        self.assertIn('value="C"', html)
        self.assertIn("btn-answer-selected", html)


if __name__ == "__main__":
    unittest.main()
