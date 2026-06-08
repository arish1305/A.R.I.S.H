from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from arish.config import AppConfig
from arish.llm import LocalLLM
from arish.memory import MemoryStore
from arish.tool_registry import ToolRegistry
from arish.tools import AssistantTools, ToolResult


SYSTEM_PROMPT = """
You are A.R.I.S.H, the Artificial Responsive Intelligent System Helper.
You run locally, respect privacy, avoid destructive actions, and answer clearly.
When a task can be handled by a local tool, prefer the tool. Keep replies concise.
""".strip()


@dataclass(frozen=True)
class ChatResponse:
    response: str
    session_id: str
    actions: list[str] = field(default_factory=list)
    provider: str = "local"
    model: str = "built-in"
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class Assistant:
    def __init__(
        self,
        config: AppConfig | None = None,
        memory: MemoryStore | None = None,
        llm: LocalLLM | None = None,
        tools: AssistantTools | None = None,
    ) -> None:
        self.config = config or AppConfig.from_env()
        self.memory = memory or MemoryStore(self.config.db_path)
        self.llm = llm or LocalLLM(self.config)
        self.tools = tools or AssistantTools(self.config)
        self.registry = ToolRegistry(self.config)

    def handle(self, message: str, session_id: str = "default") -> ChatResponse:
        clean_message = self._strip_wake_word(message).strip()
        if not clean_message:
            return ChatResponse(
                response="I am listening.",
                session_id=session_id,
                actions=["idle"],
            )

        self.memory.add_message(session_id, "user", clean_message)

        tool_result = self._handle_command(clean_message)
        if tool_result is not None:
            response = tool_result.message
            self.memory.add_message(session_id, "assistant", response)
            return ChatResponse(
                response=response,
                session_id=session_id,
                actions=[tool_result.name],
                metadata=tool_result.data,
            )

        llm_result = self.llm.generate(
            prompt=self._build_prompt(clean_message, session_id),
            system=SYSTEM_PROMPT,
        )
        self.memory.add_message(session_id, "assistant", llm_result.text)
        return ChatResponse(
            response=llm_result.text,
            session_id=session_id,
            actions=["chat"],
            provider=llm_result.provider,
            model=llm_result.model,
            metadata={"llm_available": llm_result.available},
        )

    def _handle_command(self, message: str) -> ToolResult | None:
        lowered = message.lower().strip()

        if lowered in {"help", "commands", "what can you do"}:
            return ToolResult("help", True, self.help_text())

        if lowered in {"status", "health", "system status"}:
            result = self.tools.health()
            effective_model = self.llm.resolve_model()
            availability = (
                f"available with {effective_model}"
                if effective_model
                else "not reachable"
            )
            data = dict(result.data)
            data["ollama_available"] = effective_model is not None
            data["ollama_effective_model"] = effective_model
            return ToolResult(
                "health",
                True,
                f"{result.message} Ollama is {availability}.",
                data,
            )

        if lowered in {"voice status", "voice system", "wake word status"}:
            return self.registry.voice.status()

        if lowered in {"vision status", "camera status", "screenshot status"}:
            return self.registry.vision.status()

        if lowered in {"browser status", "browser agent status"}:
            return self.registry.browser.status()

        if lowered in {"document status", "documents status", "document agent status"}:
            return self.registry.documents.status()

        if lowered in {"system info", "system information", "monitor system"}:
            return self.registry.desktop.system_info()

        if "what do you remember" in lowered or lowered in {
            "list memories",
            "show memories",
            "show memory",
        }:
            return ToolResult("memory", True, self._format_memories())

        if "summarize my memories" in lowered:
            memories = self.memory.list_memories(limit=10)
            if not memories:
                return ToolResult("memory", True, "I do not have saved memories yet.")
            summary = "; ".join(memory.content for memory in memories)
            return ToolResult("memory", True, f"Memory summary: {summary}")

        forget_match = re.match(
            r"^(?:forget|delete memory|remove memory)\s+(?:memory\s+)?(?P<id>\d+)$",
            message,
            flags=re.IGNORECASE,
        )
        if forget_match:
            memory_id = int(forget_match.group("id"))
            deleted = self.memory.delete_memory(memory_id)
            if deleted:
                return ToolResult("memory", True, f"Forgot memory {memory_id}.")
            return ToolResult("memory", False, f"I could not find memory {memory_id}.")

        remember_match = re.match(
            r"^remember(?:\s+this|\s+that)?(?::|\s)\s*(?P<content>.+)$",
            message,
            flags=re.IGNORECASE,
        )
        if remember_match and not lowered.startswith("remember what"):
            content = remember_match.group("content").strip()
            if not content:
                return ToolResult("memory", False, "Tell me what to remember.")
            memory = self.memory.add_memory(content)
            return ToolResult(
                "memory",
                True,
                f"Remembered memory {memory.id}: {memory.content}",
                {"memory_id": memory.id},
            )

        weather_match = re.search(
            r"weather(?:\s+(?:in|for|at))?\s+(?P<city>[a-zA-Z .,'-]+)$",
            message,
            flags=re.IGNORECASE,
        )
        if weather_match:
            return self.tools.weather(weather_match.group("city"))

        search_match = re.match(
            r"^(?:search(?:\s+the\s+web)?(?:\s+for)?|google|look\s+up)\s+(?P<query>.+)$",
            message,
            flags=re.IGNORECASE,
        )
        if search_match:
            return self.tools.web_search(search_match.group("query"))

        google_match = re.match(
            r"^google\s+search\s+(?P<query>.+)$",
            message,
            flags=re.IGNORECASE,
        )
        if google_match:
            return self.registry.browser.google_search(google_match.group("query"))

        open_url_match = re.match(
            r"^open\s+(?:url|website|site)\s+(?P<url>.+)$",
            message,
            flags=re.IGNORECASE,
        )
        if open_url_match:
            return self.registry.browser.open_url(open_url_match.group("url"))

        list_files_match = re.match(
            r"^list\s+files(?:\s+in)?\s*(?P<folder>.*)$",
            message,
            flags=re.IGNORECASE,
        )
        if list_files_match:
            folder = list_files_match.group("folder").strip() or "."
            return self.registry.desktop.list_files(folder)

        open_folder_match = re.match(
            r"^open\s+folder\s+(?P<folder>.+)$",
            message,
            flags=re.IGNORECASE,
        )
        if open_folder_match:
            return self.registry.desktop.open_folder(open_folder_match.group("folder"))

        open_file_match = re.match(
            r"^open\s+file\s+(?P<file>.+)$",
            message,
            flags=re.IGNORECASE,
        )
        if open_file_match:
            return self.registry.desktop.open_file(open_file_match.group("file"))

        if lowered in {"take screenshot", "capture screenshot", "screenshot"}:
            return self.registry.vision.take_screenshot()

        read_document_match = re.match(
            r"^(?:read|load)\s+(?:document|pdf|file)\s+(?P<path>.+)$",
            message,
            flags=re.IGNORECASE,
        )
        if read_document_match:
            return self.registry.documents.read_document(read_document_match.group("path"))

        open_match = re.match(
            r"^(?:open|launch|start)\s+(?P<target>.+)$",
            message,
            flags=re.IGNORECASE,
        )
        if open_match:
            return self.tools.open_application(open_match.group("target"))

        return None

    def _build_prompt(self, message: str, session_id: str) -> str:
        memories = self.memory.search_memories(message, limit=5)
        recent = self.memory.recent_messages(session_id, limit=8)

        memory_block = "\n".join(f"- {memory.content}" for memory in memories)
        history_block = "\n".join(
            f"{record.role}: {record.content}" for record in recent
        )

        return (
            f"Relevant memories:\n{memory_block or '- none'}\n\n"
            f"Recent conversation:\n{history_block or '- none'}\n\n"
            f"User request:\n{message}"
        )

    def _format_memories(self) -> str:
        memories = self.memory.list_memories(limit=20)
        if not memories:
            return "I do not have saved memories yet."
        return "\n".join(f"{memory.id}. {memory.content}" for memory in memories)

    @staticmethod
    def help_text() -> str:
        return (
            "Commands: remember this: <fact>; what do you remember; forget memory <id>; "
            "search for <query>; google search <query>; weather in <city>; "
            "open <browser|calculator|notepad|terminal|vscode|chrome|spotify>; "
            "open folder <path>; list files <path>; read document <path>; "
            "take screenshot; voice status; vision status; document status; browser status; "
            "status. General chat uses local Ollama."
        )

    @staticmethod
    def _strip_wake_word(message: str) -> str:
        return re.sub(r"^\s*arish[\s,:\-]+", "", message, flags=re.IGNORECASE)
