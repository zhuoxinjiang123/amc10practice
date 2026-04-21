import unittest
from pathlib import Path

from app import load_answer_keys


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "amc10_answers_sample.csv"


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


if __name__ == "__main__":
    unittest.main()
