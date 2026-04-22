import sys
import types
import unittest
from unittest.mock import patch

import app as app_module
from app import app


class AiChatModelTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        app_module.ANTHROPIC_KEY = "test-anthropic-key"

    def post_ai_chat(self):
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
                    "problem_id": "1",
                    "problem_label": "2000 AMC 10 Problem 1",
                    "problem_url": "https://example.com/problem",
                },
            )

        return response, record

    def test_ai_hint_uses_latest_claude_model_by_default(self):
        response, record = self.post_ai_chat()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(app_module.AI_HINT_MODEL, "claude-opus-4-1-20250805")
        self.assertEqual(record["model"], "claude-opus-4-1-20250805")
        self.assertEqual(record["api_key"], "test-anthropic-key")

    def test_ai_hint_model_can_be_overridden_with_env_var(self):
        with patch.dict(app_module.os.environ, {"AI_HINT_MODEL": "claude-sonnet-4-5-20250929"}):
            response, record = self.post_ai_chat()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(record["model"], "claude-sonnet-4-5-20250929")


if __name__ == "__main__":
    unittest.main()
