from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from arish.config import AppConfig
from arish.tools import ToolResult


class VoiceAgent:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def status(self) -> ToolResult:
        piper_path = shutil.which(self.config.piper_executable)
        whisper_path = shutil.which("whisper")
        openwakeword_available = self._module_available("openwakeword")
        return ToolResult(
            "voice",
            True,
            "Voice pipeline status is ready.",
            {
                "wake_word": self.config.wake_word,
                "stt": {
                    "engine": "Whisper",
                    "model": self.config.whisper_model,
                    "cli_available": whisper_path is not None,
                },
                "tts": {
                    "engine": "Piper",
                    "executable": piper_path,
                    "voice": self.config.piper_voice,
                    "ready": piper_path is not None and bool(self.config.piper_voice),
                },
                "wake_word_engine": {
                    "engine": "OpenWakeWord",
                    "available": openwakeword_available,
                },
            },
        )

    def speak(self, text: str) -> ToolResult:
        piper_path = shutil.which(self.config.piper_executable)
        if not piper_path or not self.config.piper_voice:
            return ToolResult(
                "speak",
                False,
                "Piper is not configured. Set ARISH_PIPER_EXECUTABLE and ARISH_PIPER_VOICE.",
                self.status().data,
            )
        try:
            output = Path(tempfile.gettempdir()) / "arish-piper-output.wav"
            completed = subprocess.run(
                [
                    piper_path,
                    "--model",
                    self.config.piper_voice,
                    "--output_file",
                    str(output),
                ],
                input=text,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if completed.returncode != 0:
                return ToolResult("speak", False, completed.stderr.strip())
            return ToolResult(
                "speak",
                True,
                f"Speech generated: {output}",
                {"audio_path": str(output)},
            )
        except Exception as exc:
            return ToolResult("speak", False, f"Piper failed: {exc}")

    @staticmethod
    def _module_available(name: str) -> bool:
        try:
            __import__(name)
            return True
        except Exception:
            return False
