import unittest
from pathlib import Path

from app import RAW_PROBLEMS, PROBLEMS, attach_answer_keys, load_answer_keys


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "amc10_answers_sample.csv"
DUPLICATE_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "amc10_answers_duplicate.csv"
PRODUCTION_PATH = Path(__file__).resolve().parent.parent / "data" / "amc10_answers.csv"


class AnswerKeyLoadingTests(unittest.TestCase):
    def test_load_answer_keys_normalizes_problem_ids_and_answers(self):
        keys = load_answer_keys(FIXTURE_PATH)

        self.assertEqual(
            keys,
            {
                "1": "A",
                "2": "B",
                "3": "C",
            },
        )

    def test_load_answer_keys_raises_for_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            load_answer_keys(Path("tests/fixtures/does_not_exist.csv"))

    def test_load_answer_keys_rejects_duplicate_problem_ids(self):
        with self.assertRaises(ValueError):
            load_answer_keys(DUPLICATE_FIXTURE_PATH)

    def test_attach_answer_keys_adds_answer_key_to_problem_records(self):
        problems = [
            {"problem_id": "1", "slug": "2000_AMC_10"},
            {"problem_id": "2", "slug": "2000_AMC_10"},
            {"problem_id": "3", "slug": "2000_AMC_10"},
        ]
        keys = {"1": "A", "3": "C"}

        enriched = attach_answer_keys(problems, keys)

        self.assertEqual(enriched[0]["correct_answer"], "A")
        self.assertEqual(enriched[1]["correct_answer"], "")
        self.assertEqual(enriched[2]["correct_answer"], "C")
        self.assertNotIn("correct_answer", problems[0])

    def test_production_answer_keys_cover_all_problem_records(self):
        keys = load_answer_keys(PRODUCTION_PATH)

        self.assertEqual(len(keys), len(RAW_PROBLEMS))
        self.assertTrue(all(problem.get("correct_answer") for problem in PROBLEMS))
        self.assertEqual(
            {problem["problem_id"] for problem in RAW_PROBLEMS},
            set(keys),
        )


if __name__ == "__main__":
    unittest.main()
