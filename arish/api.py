from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from arish.agent import Assistant
from arish.config import AppConfig, PROJECT_ROOT
from arish.tool_registry import ToolRegistry


try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover - exercised by CLI without API deps.
    FastAPI = None  # type: ignore
    HTTPException = None  # type: ignore
    FileResponse = None  # type: ignore
    BaseModel = object  # type: ignore

    def Field(default: object = None, **_: object) -> object:  # type: ignore
        return default


class ChatRequest(BaseModel):  # type: ignore[misc]
    message: str = Field(..., min_length=1)
    session_id: str = "default"


class MemoryCreateRequest(BaseModel):  # type: ignore[misc]
    content: str = Field(..., min_length=1)
    tags: list[str] = []


class ToolExecuteRequest(BaseModel):  # type: ignore[misc]
    name: str = Field(..., min_length=1)
    arguments: dict[str, object] = {}


class PathRequest(BaseModel):  # type: ignore[misc]
    path: str = Field(..., min_length=1)


class SpeakRequest(BaseModel):  # type: ignore[misc]
    text: str = Field(..., min_length=1)


def create_app(config: AppConfig | None = None) -> "FastAPI":
    if FastAPI is None:
        raise RuntimeError("FastAPI is not installed. Run: pip install -r requirements.txt")

    app_config = config or AppConfig.from_env()
    assistant = Assistant(app_config)
    registry = ToolRegistry(app_config)
    app = FastAPI(
        title="A.R.I.S.H",
        description="Local-first personal assistant API",
        version="3.0.0",
    )

    @app.get("/")
    def dashboard() -> FileResponse:
        index_path = PROJECT_ROOT / "dashboard" / "index.html"
        return FileResponse(index_path)

    @app.get("/health")
    def health() -> dict[str, object]:
        effective_model = assistant.llm.resolve_model()
        return {
            "ok": True,
            "project": app_config.project_name,
            "version": app_config.version,
            "owner": app_config.owner,
            "db_path": str(app_config.db_path),
            "ollama_url": app_config.ollama_url,
            "ollama_model": app_config.ollama_model,
            "ollama_effective_model": effective_model,
            "ollama_available": effective_model is not None,
            "internet_tools": app_config.enable_internet_tools,
            "desktop_tools": app_config.enable_desktop_tools,
            "wake_word": app_config.wake_word,
        }

    @app.post("/chat")
    def chat(request: ChatRequest) -> dict[str, object]:
        result = assistant.handle(request.message, session_id=request.session_id)
        return result.to_dict()

    @app.get("/memories")
    def memories(limit: int = 50) -> dict[str, object]:
        rows = assistant.memory.list_memories(limit=limit)
        return {"memories": [asdict(row) for row in rows]}

    @app.post("/memories")
    def create_memory(request: MemoryCreateRequest) -> dict[str, object]:
        memory = assistant.memory.add_memory(request.content, request.tags)
        return {"memory": asdict(memory)}

    @app.delete("/memories/{memory_id}")
    def delete_memory(memory_id: int) -> dict[str, object]:
        if not assistant.memory.delete_memory(memory_id):
            raise HTTPException(status_code=404, detail="Memory not found")
        return {"deleted": True, "memory_id": memory_id}

    @app.get("/tools")
    def tools() -> dict[str, object]:
        return {"tools": [asdict(tool) for tool in registry.list_tools()]}

    @app.post("/tools/execute")
    def execute_tool(request: ToolExecuteRequest) -> dict[str, object]:
        result = registry.execute(request.name, request.arguments)
        return asdict(result)

    @app.get("/voice/status")
    def voice_status() -> dict[str, object]:
        return asdict(registry.voice.status())

    @app.post("/voice/speak")
    def voice_speak(request: SpeakRequest) -> dict[str, object]:
        return asdict(registry.voice.speak(request.text))

    @app.get("/vision/status")
    def vision_status() -> dict[str, object]:
        return asdict(registry.vision.status())

    @app.post("/vision/screenshot")
    def vision_screenshot() -> dict[str, object]:
        return asdict(registry.vision.take_screenshot())

    @app.post("/vision/inspect")
    def vision_inspect(request: PathRequest) -> dict[str, object]:
        return asdict(registry.vision.inspect_image(request.path))

    @app.get("/documents/status")
    def documents_status() -> dict[str, object]:
        return asdict(registry.documents.status())

    @app.post("/documents/read")
    def documents_read(request: PathRequest) -> dict[str, object]:
        return asdict(registry.documents.read_document(request.path))

    @app.get("/browser/status")
    def browser_status() -> dict[str, object]:
        return asdict(registry.browser.status())

    @app.get("/desktop/system")
    def desktop_system() -> dict[str, object]:
        return asdict(registry.desktop.system_info())

    @app.get("/dashboard-file")
    def dashboard_file() -> dict[str, str]:
        return {"path": str(Path(PROJECT_ROOT / "dashboard" / "index.html"))}

    return app
