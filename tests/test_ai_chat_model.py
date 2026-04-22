import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import app as app_module
from app import AI_TUTOR_MODES, app, load_local_env


class AiChatModelTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.key_patcher = patch.dict(app_module.os.environ, {"ANTHROPIC_API_KEY": "test-anthropic-key"})
        self.key_patcher.start()
        self.addCleanup(self.key_patcher.stop)

    def post_ai_chat(self, tutor_mode=None, problem_id="1"):
        record = {}

        class FakeMessages:
            def create(self, **kwargs):
                record.update(kwargs)
                return types.SimpleNamespace(
                    content=[types.SimpleNamespace(text="Try simplifying the expression first.")]
                )

        class FakeAnthropicClient:
            def __init__(self, api_key):
                record["api_key"] = api_key
                self.messages = FakeMessages()

        fake_module = types.SimpleNamespace(Anthropic=FakeAnthropicClient)

        with patch.dict(sys.modules, {"anthropic": fake_module}):
            response = self.client.post(
                "/ai/chat",
                json={
                    "message": "Can I have a hint?",
                    "problem_id": problem_id,
                    "problem_label": "2000 AMC 10 Problem 1",
                    "problem_url": "https://example.com/problem",
                    "tutor_mode": tutor_mode,
                },
            )

        return response, record

    def test_ai_hint_uses_latest_claude_model_by_default(self):
        response, record = self.post_ai_chat()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(app_module.AI_HINT_MODEL, "claude-opus-4-1-20250805")
        self.assertEqual(record["model"], "claude-opus-4-1-20250805")
        self.assertEqual(record["api_key"], "test-anthropic-key")
        self.assertIn("Use LaTeX-style math formatting", record["system"])

    def test_ai_hint_includes_exact_problem_text_when_available(self):
        with patch.object(
            app_module,
            "get_problem_text",
            return_value="When the mean, median, and mode are arranged in increasing order, they form an arithmetic progression.",
        ):
            response, record = self.post_ai_chat(problem_id="999")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Exact problem text:", record["system"])
        self.assertIn("mean, median, and mode", record["system"])

    def test_ai_hint_marks_problem_text_as_unavailable_when_missing(self):
        with patch.object(app_module, "get_problem_text", return_value=""):
            response, record = self.post_ai_chat(problem_id="999")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Exact problem text: unavailable", record["system"])

    def test_ai_hint_model_can_be_overridden_with_env_var(self):
        with patch.dict(app_module.os.environ, {"AI_HINT_MODEL": "claude-sonnet-4-5-20250929"}):
            response, record = self.post_ai_chat()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(record["model"], "claude-sonnet-4-5-20250929")

    def test_ai_hint_uses_selected_tutor_mode_in_system_prompt(self):
        response, record = self.post_ai_chat(tutor_mode="step_by_step")

        self.assertEqual(response.status_code, 200)
        self.assertIn(AI_TUTOR_MODES["step_by_step"]["instruction"], record["system"])

    def test_ai_hint_falls_back_to_hint_mode_for_invalid_tutor_mode(self):
        response, record = self.post_ai_chat(tutor_mode="not-real")

        self.assertEqual(response.status_code, 200)
        self.assertIn(AI_TUTOR_MODES["hint"]["instruction"], record["system"])

    def test_ai_chat_returns_helpful_error_when_key_missing(self):
        with patch.dict(app_module.os.environ, {}, clear=True):
            response = self.client.post(
                "/ai/chat",
                json={
                    "message": "Can I have a hint?",
                    "problem_id": "1",
                    "problem_label": "2000 AMC 10 Problem 1",
                    "problem_url": "https://example.com/problem",
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn(".env", response.get_data(as_text=True))


class LocalEnvLoadingTests(unittest.TestCase):
    def test_load_local_env_sets_missing_values_from_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text('ANTHROPIC_API_KEY="from-dotenv"\nAI_HINT_MODEL=claude-test\n')

            with patch.dict(app_module.os.environ, {}, clear=True):
                loaded = load_local_env(env_path)

                self.assertEqual(app_module.os.environ["ANTHROPIC_API_KEY"], "from-dotenv")
                self.assertEqual(app_module.os.environ["AI_HINT_MODEL"], "claude-test")
                self.assertEqual(loaded["ANTHROPIC_API_KEY"], "from-dotenv")

    def test_load_local_env_does_not_override_existing_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("ANTHROPIC_API_KEY=from-dotenv\n")

            with patch.dict(app_module.os.environ, {"ANTHROPIC_API_KEY": "from-shell"}, clear=True):
                loaded = load_local_env(env_path)

                self.assertEqual(app_module.os.environ["ANTHROPIC_API_KEY"], "from-shell")
                self.assertEqual(loaded, {})


if __name__ == "__main__":
    unittest.main()
