from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from arish.config import AppConfig


@dataclass(frozen=True)
class LLMResult:
    text: str
    provider: str
    model: str
    available: bool


class LocalLLM:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def is_available(self) -> bool:
        try:
            self._request_json(f"{self.config.ollama_url}/api/tags", timeout=2.0)
            return True
        except Exception:
            return False

    def installed_models(self) -> list[str]:
        data = self._request_json(f"{self.config.ollama_url}/api/tags", timeout=2.0)
        models = data.get("models", [])
        if not isinstance(models, list):
            return []

        names: list[str] = []
        for model in models:
            if isinstance(model, dict) and isinstance(model.get("name"), str):
                names.append(model["name"])
        return names

    def resolve_model(self) -> str | None:
        try:
            installed = self.installed_models()
        except Exception:
            return None

        configured = self.config.ollama_model
        configured_base = configured.split(":", 1)[0]
        for model in installed:
            if model == configured or model.split(":", 1)[0] == configured_base:
                return model

        preferred = ("qwen3", "llama3", "mistral", "deepseek-coder")
        for preferred_base in preferred:
            for model in installed:
                if model.split(":", 1)[0] == preferred_base:
                    return model

        return installed[0] if installed else None

    def generate(self, prompt: str, system: str | None = None) -> LLMResult:
        model = self.resolve_model()
        if model is None:
            return LLMResult(
                text=self.offline_fallback(prompt),
                provider="offline-fallback",
                model="none",
                available=False,
            )

        payload: dict[str, object] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        try:
            data = self._request_json(
                f"{self.config.ollama_url}/api/generate",
                payload=payload,
                timeout=self.config.request_timeout,
            )
            text = str(data.get("response", "")).strip()
            if not text:
                raise RuntimeError("Ollama returned an empty response.")
            return LLMResult(
                text=text,
                provider="ollama",
                model=model,
                available=True,
            )
        except Exception:
            return LLMResult(
                text=self.offline_fallback(prompt),
                provider="offline-fallback",
                model="none",
                available=False,
            )

    @staticmethod
    def offline_fallback(prompt: str) -> str:
        user_request = LocalLLM._extract_user_request(prompt)
        compact_request = " ".join(user_request.split())
        lowered = compact_request.lower().strip(" .?!")

        if lowered in {"hi", "hello", "hey", "yo", "good morning", "good evening"}:
            return (
                "Hello, Arish. A.R.I.S.H is online locally. "
                "Memory and built-in commands are ready."
            )

        if lowered in {"thanks", "thank you", "ok", "okay"}:
            return "You are welcome. A.R.I.S.H is ready."

        if len(compact_request) > 120:
            compact_request = compact_request[:117] + "..."
        if not compact_request:
            compact_request = "that"

        return (
            f"I can help with \"{compact_request}\" once Ollama is running. "
            "Right now, local commands are ready: memory, search links, weather, "
            "status, and safe desktop launching."
        )

    @staticmethod
    def _extract_user_request(prompt: str) -> str:
        marker = "User request:"
        if marker in prompt:
            return prompt.rsplit(marker, 1)[1].strip()
        return prompt.strip()

    @staticmethod
    def _request_json(
        url: str, payload: dict[str, object] | None = None, timeout: float = 10.0
    ) -> dict[str, object]:
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {body}") from exc

        decoded = json.loads(raw or "{}")
        if not isinstance(decoded, dict):
            raise RuntimeError("Expected a JSON object response.")
        return decoded
