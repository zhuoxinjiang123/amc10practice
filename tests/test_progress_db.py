import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as app_module
from app import ensure_db, get_progress_map, record_attempt


class FakePostgresCursor:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, params=None):
        self.connection.queries.append((query, params))

    def fetchall(self):
        return self.connection.rows

    def close(self):
        pass


class FakePostgresConnection:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.queries = []
        self.commits = 0
        self.closed = False

    def cursor(self):
        return FakePostgresCursor(self)

    def commit(self):
        self.commits += 1

    def close(self):
        self.closed = True


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

    def test_get_progress_map_uses_postgres_when_database_url_is_set(self):
        create_conn = FakePostgresConnection()
        read_conn = FakePostgresConnection(rows=[("1", 2, 1, "2026-04-22T20:00:00+00:00")])

        with patch.dict(app_module.os.environ, {"DATABASE_URL": "postgresql://render-db"}):
            with patch.object(
                app_module,
                "get_postgres_connection",
                side_effect=[create_conn, read_conn],
                create=True,
            ):
                progress = get_progress_map()

        self.assertEqual(progress["1"]["correct_count"], 2)
        self.assertEqual(progress["1"]["wrong_count"], 1)
        self.assertTrue(create_conn.closed)
        self.assertTrue(read_conn.closed)

    def test_record_attempt_uses_postgres_when_database_url_is_set(self):
        create_conn = FakePostgresConnection()
        write_conn = FakePostgresConnection()

        with patch.dict(app_module.os.environ, {"DATABASE_URL": "postgresql://render-db"}):
            with patch.object(
                app_module,
                "get_postgres_connection",
                side_effect=[create_conn, write_conn],
                create=True,
            ):
                record_attempt(None, "1", is_correct=True)

        self.assertEqual(write_conn.queries[-1][1][0], "1")
        self.assertEqual(write_conn.queries[-1][1][1], 1)
        self.assertEqual(write_conn.queries[-1][1][2], 0)
        self.assertEqual(write_conn.commits, 1)


if __name__ == "__main__":
    unittest.main()
