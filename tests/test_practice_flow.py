import unittest

from app import app


class LegacyRouteRedirectTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_start_redirects_to_topic_dashboard(self):
        response = self.client.post("/start", data={"count": 10}, follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get("Location"), "/")

    def test_practice_redirects_to_topic_dashboard(self):
        response = self.client.get("/practice", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get("Location"), "/")

    def test_answer_redirects_to_topic_dashboard(self):
        response = self.client.post("/answer", data={"choice": "A"}, follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get("Location"), "/")

    def test_results_redirects_to_topic_dashboard(self):
        response = self.client.get("/results", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get("Location"), "/")


if __name__ == "__main__":
    unittest.main()
