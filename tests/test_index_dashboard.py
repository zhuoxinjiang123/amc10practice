import tempfile
import unittest
from pathlib import Path

from app import app, ensure_db, record_attempt


class IndexDashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "progress.sqlite3"
        app.config["TESTING"] = True
        app.config["PROGRESS_DB_PATH"] = self.db_path
        ensure_db(self.db_path)
        self.client = app.test_client()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_index_renders_topic_dashboard_with_persistent_counts(self):
        record_attempt(self.db_path, "1", is_correct=True)
        record_attempt(self.db_path, "4", is_correct=False)

        response = self.client.get("/")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("AMC 10 Topics", html)
        self.assertIn("Algebra", html)
        self.assertIn("Answered 2 / 541", html)
        self.assertIn("Correct 1", html)
        self.assertIn("Wrong 1", html)

    def test_index_replaces_random_session_setup_as_primary_ui(self):
        response = self.client.get("/")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("How many problems?", html)
        self.assertNotIn("Start Practice", html)

    def test_index_uses_versioned_stylesheet_url_for_cache_busting(self):
        response = self.client.get("/")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('/static/style.css?v=', html)

    def test_index_renders_learning_cockpit_design_hooks(self):
        response = self.client.get("/")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('class="dashboard-shell"', html)
        self.assertIn('class="dashboard-hero"', html)
        self.assertIn('class="topic-progress-track"', html)


if __name__ == "__main__":
    unittest.main()
