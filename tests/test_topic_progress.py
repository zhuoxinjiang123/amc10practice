import unittest

from app import build_topic_progress


class TopicProgressTests(unittest.TestCase):
    def test_build_topic_progress_counts_total_finished_and_correct(self):
        queue = ["1", "2", "3", "4"]
        problems_by_id = {
            "1": {"problem_id": "1", "category": "Algebra"},
            "2": {"problem_id": "2", "category": "Geometry"},
            "3": {"problem_id": "3", "category": "Algebra"},
            "4": {"problem_id": "4", "category": ""},
        }
        history = [
            {"id": "1", "answer": "C", "correct": True, "skipped": False, "time": 12},
            {"id": "2", "answer": None, "correct": None, "skipped": True, "time": 4},
            {"id": "3", "answer": "A", "correct": False, "skipped": False, "time": 9},
        ]

        topic_progress = build_topic_progress(queue, history, problems_by_id)

        self.assertEqual(list(topic_progress.keys()), ["Algebra", "Geometry", "Uncategorized"])
        self.assertEqual(topic_progress["Algebra"], {
            "topic": "Algebra",
            "total": 2,
            "finished": 2,
            "answered": 2,
            "correct": 1,
        })
        self.assertEqual(topic_progress["Geometry"], {
            "topic": "Geometry",
            "total": 1,
            "finished": 1,
            "answered": 0,
            "correct": 0,
        })
        self.assertEqual(topic_progress["Uncategorized"], {
            "topic": "Uncategorized",
            "total": 1,
            "finished": 0,
            "answered": 0,
            "correct": 0,
        })


if __name__ == "__main__":
    unittest.main()
