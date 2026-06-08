from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from arish.agent import Assistant
from arish.config import AppConfig
from arish.llm import LLMResult, LocalLLM


class AssistantTestCase(unittest.TestCase):
    def make_assistant(self) -> Assistant:
        self.temp_dir = tempfile.TemporaryDirectory()
        config = AppConfig(
            db_path=Path(self.temp_dir.name) / "test.sqlite3",
            request_timeout=0.01,
            enable_internet_tools=False,
            enable_desktop_tools=False,
        )
        return Assistant(config)

    def tearDown(self) -> None:
        temp_dir = getattr(self, "temp_dir", None)
        if temp_dir is not None:
            temp_dir.cleanup()

    def test_memory_round_trip(self) -> None:
        assistant = self.make_assistant()

        saved = assistant.handle("remember this: my preferred local model is qwen3")
        recalled = assistant.handle("what do you remember")

        self.assertIn("Remembered memory", saved.response)
        self.assertIn("qwen3", recalled.response)

    def test_forget_memory(self) -> None:
        assistant = self.make_assistant()
        saved = assistant.handle("remember this: temporary fact")
        memory_id = int(saved.metadata["memory_id"])

        forgotten = assistant.handle(f"forget memory {memory_id}")
        recalled = assistant.handle("what do you remember")

        self.assertIn("Forgot", forgotten.response)
        self.assertNotIn("temporary fact", recalled.response)

    def test_search_returns_url_without_network(self) -> None:
        assistant = self.make_assistant()

        result = assistant.handle("search for local ai assistant")

        self.assertIn("duckduckgo.com", result.response)
        self.assertEqual(result.actions, ["web_search"])

    def test_chat_falls_back_when_ollama_is_offline(self) -> None:
        assistant = self.make_assistant()

        result = assistant.handle("tell me a short greeting")

        self.assertEqual(result.provider, "offline-fallback")
        self.assertIn("once Ollama is running", result.response)
        self.assertNotIn("Relevant memories", result.response)

    def test_greeting_does_not_leak_prompt_in_offline_mode(self) -> None:
        assistant = self.make_assistant()

        result = assistant.handle("hi")

        self.assertEqual(result.provider, "offline-fallback")
        self.assertIn("A.R.I.S.H is online locally", result.response)
        self.assertNotIn("Relevant memories", result.response)
        self.assertNotIn("User request", result.response)

    def test_ollama_uses_installed_fallback_model(self) -> None:
        config = AppConfig(db_path=Path(tempfile.gettempdir()) / "unused.sqlite3")

        class FakeLLM(LocalLLM):
            def installed_models(self) -> list[str]:
                return ["mistral:latest"]

            def _request_json(self, *args: object, **kwargs: object) -> dict[str, object]:
                return {"response": "I am A.R.I.S.H."}

        result = FakeLLM(config).generate("User request:\nwho are u")

        self.assertEqual(result.provider, "ollama")
        self.assertEqual(result.model, "mistral:latest")
        self.assertEqual(result.text, "I am A.R.I.S.H.")


if __name__ == "__main__":
    unittest.main()
