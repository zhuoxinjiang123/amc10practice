import unittest

from app import build_topic_dashboard, difficulty_matches, slugify_topic


class TopicDashboardTests(unittest.TestCase):
    def test_build_topic_dashboard_counts_answered_correct_and_wrong(self):
        problems = [
            {"problem_id": "1", "category": "Algebra", "problem_num": "1"},
            {"problem_id": "2", "category": "Algebra", "problem_num": "12"},
            {"problem_id": "3", "category": "Geometry", "problem_num": "20"},
        ]
        progress_map = {
            "1": {"correct_count": 2, "wrong_count": 1},
            "3": {"correct_count": 0, "wrong_count": 3},
        }

        dashboard = build_topic_dashboard(problems, progress_map)

        self.assertEqual(
            dashboard,
            [
                {
                    "topic": "Algebra",
                    "slug": "algebra",
                    "total": 2,
                    "answered": 1,
                    "correct_total": 2,
                    "wrong_total": 1,
                },
                {
                    "topic": "Geometry",
                    "slug": "geometry",
                    "total": 1,
                    "answered": 1,
                    "correct_total": 0,
                    "wrong_total": 3,
                },
            ],
        )

    def test_slugify_topic_matches_expected_path_format(self):
        self.assertEqual(slugify_topic("Counting & Probability"), "counting-probability")

    def test_difficulty_matches_keeps_current_overlapping_rules(self):
        easy_problem = {"problem_num": "9"}
        medium_problem = {"problem_num": "9"}
        hard_problem = {"problem_num": "17"}

        self.assertTrue(difficulty_matches(easy_problem, "easy"))
        self.assertTrue(difficulty_matches(medium_problem, "medium"))
        self.assertTrue(difficulty_matches(hard_problem, "medium"))
        self.assertTrue(difficulty_matches(hard_problem, "hard"))
        self.assertFalse(difficulty_matches({"problem_num": "24"}, "easy"))


if __name__ == "__main__":
    unittest.main()
