from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from arish.agent import Assistant
from arish.config import AppConfig, PROJECT_ROOT


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


def create_app(config: AppConfig | None = None) -> "FastAPI":
    if FastAPI is None:
        raise RuntimeError("FastAPI is not installed. Run: pip install -r requirements.txt")

    app_config = config or AppConfig.from_env()
    assistant = Assistant(app_config)
    app = FastAPI(
        title="A.R.I.S.H",
        description="Local-first personal assistant API",
        version="2.0.0",
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
            "owner": app_config.owner,
            "db_path": str(app_config.db_path),
            "ollama_url": app_config.ollama_url,
            "ollama_model": app_config.ollama_model,
            "ollama_effective_model": effective_model,
            "ollama_available": effective_model is not None,
            "internet_tools": app_config.enable_internet_tools,
            "desktop_tools": app_config.enable_desktop_tools,
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

    @app.get("/dashboard-file")
    def dashboard_file() -> dict[str, str]:
        return {"path": str(Path(PROJECT_ROOT / "dashboard" / "index.html"))}

    return app
