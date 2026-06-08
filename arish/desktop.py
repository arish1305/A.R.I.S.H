from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from arish.config import AppConfig
from arish.tools import ToolResult


@dataclass(frozen=True)
class SystemSnapshot:
    platform: str
    python: str
    cwd: str
    cpu_count: int | None
    memory_hint: str
    desktop_tools: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "platform": self.platform,
            "python": self.python,
            "cwd": self.cwd,
            "cpu_count": self.cpu_count,
            "memory_hint": self.memory_hint,
            "desktop_tools": self.desktop_tools,
        }


class DesktopAgent:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def system_info(self) -> ToolResult:
        snapshot = SystemSnapshot(
            platform=f"{platform.system()} {platform.release()}",
            python=platform.python_version(),
            cwd=str(Path.cwd()),
            cpu_count=os.cpu_count(),
            memory_hint="Use Task Manager for exact RAM/GPU/NPU telemetry.",
            desktop_tools=self.config.enable_desktop_tools,
        )
        return ToolResult(
            "system_info",
            True,
            "System information is ready.",
            snapshot.to_dict(),
        )

    def list_files(self, folder: str = ".", limit: int = 40) -> ToolResult:
        base = Path(folder).expanduser()
        if not base.is_absolute():
            base = Path.cwd() / base
        try:
            resolved = base.resolve()
            if not resolved.exists() or not resolved.is_dir():
                return ToolResult("list_files", False, f"Folder not found: {resolved}")
            items = []
            for path in sorted(resolved.iterdir(), key=lambda item: item.name.lower())[:limit]:
                items.append(
                    {
                        "name": path.name,
                        "path": str(path),
                        "type": "folder" if path.is_dir() else "file",
                    }
                )
            return ToolResult(
                "list_files",
                True,
                f"Listed {len(items)} item(s) in {resolved}.",
                {"folder": str(resolved), "items": items},
            )
        except Exception as exc:
            return ToolResult("list_files", False, f"Could not list files: {exc}")

    def open_folder(self, folder: str = ".") -> ToolResult:
        if not self.config.enable_desktop_tools:
            return ToolResult("open_folder", False, "Desktop tools are disabled.")
        path = Path(folder).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists() or not path.is_dir():
            return ToolResult("open_folder", False, f"Folder not found: {path}")
        try:
            self._open_path(path)
            return ToolResult("open_folder", True, f"Opened folder: {path}")
        except Exception as exc:
            return ToolResult("open_folder", False, f"Could not open folder: {exc}")

    def open_file(self, file_path: str) -> ToolResult:
        if not self.config.enable_desktop_tools:
            return ToolResult("open_file", False, "Desktop tools are disabled.")
        path = Path(file_path).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists() or not path.is_file():
            return ToolResult("open_file", False, f"File not found: {path}")
        try:
            self._open_path(path)
            return ToolResult("open_file", True, f"Opened file: {path}")
        except Exception as exc:
            return ToolResult("open_file", False, f"Could not open file: {exc}")

    def close_application(self, target: str, confirmed: bool = False) -> ToolResult:
        if not confirmed:
            return ToolResult(
                "close_app",
                False,
                "Closing applications needs confirmation. Repeat with confirmed=true.",
                {"requires_confirmation": True, "target": target},
            )
        if platform.system().lower() != "windows":
            return ToolResult("close_app", False, "Close app is currently implemented for Windows.")
        name = target.strip()
        if not name:
            return ToolResult("close_app", False, "Tell me which application to close.")
        if name.lower().endswith(".exe"):
            process_name = name
        else:
            process_name = f"{name}.exe"
        try:
            completed = subprocess.run(
                ["taskkill", "/IM", process_name, "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            ok = completed.returncode == 0
            message = completed.stdout.strip() or completed.stderr.strip()
            return ToolResult("close_app", ok, message or f"Closed {process_name}.")
        except Exception as exc:
            return ToolResult("close_app", False, f"Could not close {process_name}: {exc}")

    def take_screenshot(self) -> ToolResult:
        self.config.screenshots_dir.mkdir(parents=True, exist_ok=True)
        target = self.config.screenshots_dir / "latest-screenshot.png"
        try:
            import mss  # type: ignore
            import mss.tools  # type: ignore

            with mss.mss() as screen:
                monitor = screen.monitors[0]
                image = screen.grab(monitor)
                mss.tools.to_png(image.rgb, image.size, output=str(target))
            return ToolResult(
                "take_screenshot",
                True,
                f"Screenshot saved: {target}",
                {"path": str(target)},
            )
        except Exception as exc:
            return ToolResult(
                "take_screenshot",
                False,
                f"Screenshot capture needs the optional mss package or screen permission: {exc}",
                {"path": str(target)},
            )

    @staticmethod
    def _open_path(path: Path) -> None:
        system = platform.system().lower()
        if system == "windows":
            os.startfile(path)  # type: ignore[attr-defined]
        elif system == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            opener = shutil.which("xdg-open")
            if opener is None:
                raise RuntimeError("xdg-open is not available.")
            subprocess.Popen([opener, str(path)])
