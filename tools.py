from __future__ import annotations

from arish.config import AppConfig
from arish.tools import AssistantTools, ToolResult, send_email_via_smtp


_tools: AssistantTools | None = None


def _get_tools() -> AssistantTools:
    global _tools
    if _tools is None:
        _tools = AssistantTools(AppConfig.from_env())
    return _tools


async def get_weather(context: object = None, city: str = "") -> str:
    return _get_tools().weather(city).message


async def search_web(context: object = None, query: str = "") -> str:
    return _get_tools().web_search(query).message


async def send_email(
    context: object = None,
    to_email: str = "",
    subject: str = "",
    message: str = "",
    cc_email: str | None = None,
) -> str:
    return send_email_via_smtp(to_email, subject, message, cc_email).message


__all__ = [
    "AssistantTools",
    "ToolResult",
    "get_weather",
    "search_web",
    "send_email",
    "send_email_via_smtp",
]
