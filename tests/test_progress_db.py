import tempfile
import unittest
from pathlib import Path

from app import ensure_db, get_progress_map, record_attempt


class ProgressDbTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "progress.sqlite3"

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_ensure_db_creates_sqlite_file(self):
        ensure_db(self.db_path)

        self.assertTrue(self.db_path.exists())

    def test_untouched_questions_have_no_progress_row(self):
        ensure_db(self.db_path)

        progress = get_progress_map(self.db_path)

        self.assertIsNone(progress.get("1"))

    def test_record_attempt_increments_correct_count(self):
        ensure_db(self.db_path)

        record_attempt(self.db_path, "1", is_correct=True)
        progress = get_progress_map(self.db_path)

        self.assertEqual(progress["1"]["correct_count"], 1)
        self.assertEqual(progress["1"]["wrong_count"], 0)

    def test_record_attempt_increments_wrong_count(self):
        ensure_db(self.db_path)

        record_attempt(self.db_path, "1", is_correct=False)
        progress = get_progress_map(self.db_path)

        self.assertEqual(progress["1"]["correct_count"], 0)
        self.assertEqual(progress["1"]["wrong_count"], 1)


if __name__ == "__main__":
    unittest.main()
