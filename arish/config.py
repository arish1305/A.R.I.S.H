from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_environment(project_root: Path = PROJECT_ROOT) -> None:
    """Load .env without making python-dotenv mandatory for the CLI."""
    env_file = project_root / ".env"

    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(env_file)
        return
    except Exception:
        pass

    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class AppConfig:
    project_name: str = "A.R.I.S.H"
    owner: str = "Arish Vijay"
    db_path: Path = PROJECT_ROOT / "data" / "arish.sqlite3"
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3"
    request_timeout: float = 120.0
    enable_internet_tools: bool = False
    enable_desktop_tools: bool = True
    open_browser_on_search: bool = False
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "AppConfig":
        load_environment()

        db_path = Path(os.getenv("ARISH_DB_PATH", str(cls.db_path))).expanduser()
        return cls(
            project_name=os.getenv("ARISH_PROJECT_NAME", cls.project_name),
            owner=os.getenv("ARISH_OWNER", cls.owner),
            db_path=db_path,
            ollama_url=os.getenv("ARISH_OLLAMA_URL", cls.ollama_url).rstrip("/"),
            ollama_model=os.getenv("ARISH_OLLAMA_MODEL", cls.ollama_model),
            request_timeout=_env_float("ARISH_REQUEST_TIMEOUT", cls.request_timeout),
            enable_internet_tools=_env_bool(
                "ARISH_ENABLE_INTERNET_TOOLS", cls.enable_internet_tools
            ),
            enable_desktop_tools=_env_bool(
                "ARISH_ENABLE_DESKTOP_TOOLS", cls.enable_desktop_tools
            ),
            open_browser_on_search=_env_bool(
                "ARISH_OPEN_BROWSER_ON_SEARCH", cls.open_browser_on_search
            ),
            log_level=os.getenv("ARISH_LOG_LEVEL", cls.log_level).upper(),
        )
