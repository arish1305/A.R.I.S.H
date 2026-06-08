from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from arish.browser_agent import BrowserAgent
from arish.config import AppConfig
from arish.desktop import DesktopAgent
from arish.documents import DocumentAgent
from arish.tools import AssistantTools, ToolResult
from arish.vision import VisionAgent
from arish.voice import VoiceAgent


ToolHandler = Callable[[dict[str, object]], ToolResult]


@dataclass(frozen=True)
class RegisteredTool:
    name: str
    description: str
    parameters: list[str]


class ToolRegistry:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.assistant_tools = AssistantTools(config)
        self.desktop = DesktopAgent(config)
        self.browser = BrowserAgent(config)
        self.documents = DocumentAgent(config)
        self.vision = VisionAgent(config)
        self.voice = VoiceAgent(config)

        self._handlers: dict[str, ToolHandler] = {
            "open_app": lambda args: self.assistant_tools.open_application(
                str(args.get("target", ""))
            ),
            "close_app": lambda args: self.desktop.close_application(
                str(args.get("target", "")), bool(args.get("confirmed", False))
            ),
            "open_url": lambda args: self.browser.open_url(str(args.get("url", ""))),
            "google_search": lambda args: self.browser.google_search(
                str(args.get("query", ""))
            ),
            "read_pdf": lambda args: self.documents.read_document(
                str(args.get("path", ""))
            ),
            "read_document": lambda args: self.documents.read_document(
                str(args.get("path", ""))
            ),
            "take_screenshot": lambda args: self.vision.take_screenshot(),
            "remember": lambda args: ToolResult(
                "remember",
                False,
                "Use the memory API or command syntax: remember this: <fact>.",
            ),
            "forget": lambda args: ToolResult(
                "forget",
                False,
                "Use the memory API or command syntax: forget memory <id>.",
            ),
            "webcam_capture": lambda args: ToolResult(
                "webcam_capture",
                False,
                "Webcam capture is staged; local camera permission and backend capture are next.",
            ),
            "system_info": lambda args: self.desktop.system_info(),
            "list_files": lambda args: self.desktop.list_files(
                str(args.get("folder", ".")), int(args.get("limit", 40))
            ),
            "open_folder": lambda args: self.desktop.open_folder(
                str(args.get("folder", "."))
            ),
            "play_music": lambda args: self.assistant_tools.open_application("spotify"),
        }

    def list_tools(self) -> list[RegisteredTool]:
        return [
            RegisteredTool("open_app", "Open a whitelisted local application.", ["target"]),
            RegisteredTool("close_app", "Close an application after confirmation.", ["target", "confirmed"]),
            RegisteredTool("open_url", "Open a URL in the default browser.", ["url"]),
            RegisteredTool("google_search", "Create or open a Google search URL.", ["query"]),
            RegisteredTool("read_pdf", "Read a PDF document.", ["path"]),
            RegisteredTool("read_document", "Read PDF, DOCX, TXT, or Markdown.", ["path"]),
            RegisteredTool("take_screenshot", "Capture a local screenshot.", []),
            RegisteredTool("remember", "Store a memory through the assistant memory system.", ["content"]),
            RegisteredTool("forget", "Forget a memory by id.", ["id"]),
            RegisteredTool("webcam_capture", "Capture from webcam when configured.", []),
            RegisteredTool("system_info", "Return local system information.", []),
            RegisteredTool("list_files", "List files in a local folder.", ["folder", "limit"]),
            RegisteredTool("open_folder", "Open a local folder.", ["folder"]),
            RegisteredTool("play_music", "Open Spotify when installed.", []),
        ]

    def execute(self, name: str, arguments: dict[str, object]) -> ToolResult:
        handler = self._handlers.get(name)
        if handler is None:
            return ToolResult("tool", False, f"Unknown tool: {name}")
        return handler(arguments)
