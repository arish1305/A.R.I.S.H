from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from arish.config import AppConfig


try:
    from fastapi.testclient import TestClient

    from arish.api import create_app
except Exception:  # pragma: no cover
    TestClient = None  # type: ignore
    create_app = None  # type: ignore


@unittest.skipIf(TestClient is None, "FastAPI test dependencies are not installed")
class ApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        config = AppConfig(
            db_path=Path(self.temp_dir.name) / "api.sqlite3",
            request_timeout=0.01,
            enable_internet_tools=False,
            enable_desktop_tools=False,
        )
        self.client = TestClient(create_app(config))  # type: ignore[arg-type]

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_health(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_chat_memory(self) -> None:
        response = self.client.post(
            "/chat",
            json={"message": "remember this: dashboard works", "session_id": "test"},
        )
        memories = self.client.get("/memories").json()["memories"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["actions"], ["memory"])
        self.assertEqual(memories[0]["content"], "dashboard works")


if __name__ == "__main__":
    unittest.main()
