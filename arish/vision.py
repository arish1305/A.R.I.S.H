from __future__ import annotations

from pathlib import Path

from arish.config import AppConfig
from arish.desktop import DesktopAgent
from arish.tools import ToolResult


class VisionAgent:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.desktop = DesktopAgent(config)

    def status(self) -> ToolResult:
        return ToolResult(
            "vision",
            True,
            "Vision agent is staged for screenshots and image analysis. Florence-2 is not bundled yet.",
            {
                "model": "Florence-2",
                "implemented": ["take_screenshot", "image_file_probe"],
                "staged": ["ocr", "object_detection", "webcam_capture"],
            },
        )

    def take_screenshot(self) -> ToolResult:
        return self.desktop.take_screenshot()

    def inspect_image(self, image_path: str) -> ToolResult:
        path = Path(image_path).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists() or not path.is_file():
            return ToolResult("inspect_image", False, f"Image not found: {path}")
        return ToolResult(
            "inspect_image",
            True,
            f"Image file is ready for local vision analysis: {path.name}",
            {
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "model_required": "Florence-2",
            },
        )
