from __future__ import annotations

import urllib.parse
import webbrowser

from arish.config import AppConfig
from arish.tools import ToolResult


class BrowserAgent:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def open_url(self, url: str) -> ToolResult:
        clean_url = url.strip()
        if not clean_url:
            return ToolResult("open_url", False, "Tell me which URL to open.")
        if not clean_url.startswith(("http://", "https://")):
            clean_url = "https://" + clean_url
        if not self.config.enable_desktop_tools:
            return ToolResult("open_url", False, "Desktop browser launch is disabled.")
        opened = webbrowser.open(clean_url)
        return ToolResult(
            "open_url",
            opened,
            f"Opened {clean_url}." if opened else f"Could not open {clean_url}.",
            {"url": clean_url, "opened": opened},
        )

    def google_search(self, query: str) -> ToolResult:
        clean_query = query.strip()
        if not clean_query:
            return ToolResult("google_search", False, "Tell me what to search for.")
        url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(clean_query)
        opened = False
        if self.config.open_browser_on_search and self.config.enable_desktop_tools:
            opened = webbrowser.open(url)
        return ToolResult(
            "google_search",
            True,
            f"Google search ready: {url}",
            {"query": clean_query, "url": url, "opened": opened},
        )

    def status(self) -> ToolResult:
        return ToolResult(
            "browser",
            True,
            "Browser agent is ready for URL and search commands. Playwright automation is staged.",
            {
                "framework": "Playwright",
                "implemented": ["open_url", "google_search"],
                "staged": ["tab_management", "form_filling", "article_extraction"],
            },
        )
