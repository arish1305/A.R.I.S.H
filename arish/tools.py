from __future__ import annotations

import os
import platform
import smtplib
import subprocess
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass, field
from email.message import EmailMessage

from arish.config import AppConfig


@dataclass(frozen=True)
class ToolResult:
    name: str
    ok: bool
    message: str
    data: dict[str, object] = field(default_factory=dict)


class AssistantTools:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def weather(self, city: str) -> ToolResult:
        clean_city = city.strip(" ?.!,")
        if not clean_city:
            return ToolResult("weather", False, "Tell me the city name first.")

        if not self.config.enable_internet_tools:
            return ToolResult(
                "weather",
                False,
                (
                    "Internet tools are disabled. Set ARISH_ENABLE_INTERNET_TOOLS=true "
                    f"to fetch live weather for {clean_city}."
                ),
                {"city": clean_city},
            )

        url = f"https://wttr.in/{urllib.parse.quote(clean_city)}?format=3"
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "ARISH/2.0"})
            with urllib.request.urlopen(request, timeout=self.config.request_timeout) as response:
                text = response.read().decode("utf-8", errors="replace").strip()
            return ToolResult("weather", True, text, {"city": clean_city})
        except Exception as exc:
            return ToolResult(
                "weather",
                False,
                f"I could not retrieve weather for {clean_city}: {exc}",
                {"city": clean_city},
            )

    def web_search(self, query: str) -> ToolResult:
        clean_query = query.strip(" ?.!,")
        if not clean_query:
            return ToolResult("web_search", False, "Tell me what to search for first.")

        url = "https://duckduckgo.com/?q=" + urllib.parse.quote_plus(clean_query)
        opened = False
        if self.config.open_browser_on_search and self.config.enable_desktop_tools:
            opened = webbrowser.open(url)

        if opened:
            message = f"Opened a DuckDuckGo search for: {clean_query}"
        else:
            message = f"Search ready: {url}"

        return ToolResult(
            "web_search",
            True,
            message,
            {"query": clean_query, "url": url, "opened": opened},
        )

    def open_application(self, target: str) -> ToolResult:
        clean_target = target.strip().lower()
        if not clean_target:
            return ToolResult("desktop", False, "Tell me what application to open first.")

        if not self.config.enable_desktop_tools:
            return ToolResult(
                "desktop",
                False,
                "Desktop tools are disabled. Set ARISH_ENABLE_DESKTOP_TOOLS=true to enable them.",
            )

        if clean_target in {"browser", "web browser", "internet"}:
            opened = webbrowser.open("https://duckduckgo.com")
            return ToolResult(
                "desktop",
                opened,
                "Opened your browser." if opened else "I could not open the browser.",
                {"target": clean_target},
            )

        command = self._application_command(clean_target)
        if command is None:
            return ToolResult(
                "desktop",
                False,
                (
                    "I can safely open: browser, calculator, notepad, terminal, "
                    "file explorer, and vscode."
                ),
                {"target": clean_target},
            )

        try:
            subprocess.Popen(command)
            return ToolResult(
                "desktop",
                True,
                f"Opened {clean_target}.",
                {"target": clean_target, "command": command},
            )
        except Exception as exc:
            return ToolResult(
                "desktop",
                False,
                f"I could not open {clean_target}: {exc}",
                {"target": clean_target, "command": command},
            )

    def health(self) -> ToolResult:
        return ToolResult(
            "health",
            True,
            "A.R.I.S.H core is running.",
            {
                "internet_tools": self.config.enable_internet_tools,
                "desktop_tools": self.config.enable_desktop_tools,
                "db_path": str(self.config.db_path),
                "ollama_url": self.config.ollama_url,
                "ollama_model": self.config.ollama_model,
            },
        )

    @staticmethod
    def _application_command(target: str) -> list[str] | None:
        system = platform.system().lower()

        if system == "windows":
            apps = {
                "calculator": ["calc.exe"],
                "calc": ["calc.exe"],
                "notepad": ["notepad.exe"],
                "terminal": ["powershell.exe"],
                "powershell": ["powershell.exe"],
                "cmd": ["cmd.exe"],
                "file explorer": ["explorer.exe"],
                "explorer": ["explorer.exe"],
                "vscode": ["code.cmd"],
                "vs code": ["code.cmd"],
                "chrome": ["cmd.exe", "/c", "start", "", "chrome"],
                "discord": ["cmd.exe", "/c", "start", "", "discord"],
                "spotify": ["cmd.exe", "/c", "start", "", "spotify"],
                "steam": ["cmd.exe", "/c", "start", "", "steam"],
            }
        elif system == "darwin":
            apps = {
                "calculator": ["open", "-a", "Calculator"],
                "notepad": ["open", "-a", "TextEdit"],
                "terminal": ["open", "-a", "Terminal"],
                "file explorer": ["open", "."],
                "finder": ["open", "."],
                "vscode": ["code"],
                "vs code": ["code"],
                "chrome": ["open", "-a", "Google Chrome"],
                "discord": ["open", "-a", "Discord"],
                "spotify": ["open", "-a", "Spotify"],
                "steam": ["open", "-a", "Steam"],
            }
        else:
            apps = {
                "calculator": ["gnome-calculator"],
                "notepad": ["gedit"],
                "terminal": ["x-terminal-emulator"],
                "file explorer": ["xdg-open", "."],
                "files": ["xdg-open", "."],
                "vscode": ["code"],
                "vs code": ["code"],
                "chrome": ["google-chrome"],
                "discord": ["discord"],
                "spotify": ["spotify"],
                "steam": ["steam"],
            }

        return apps.get(target)


def send_email_via_smtp(
    to_email: str,
    subject: str,
    message: str,
    cc_email: str | None = None,
) -> ToolResult:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM", username or "")

    if not host or not username or not password or not sender:
        return ToolResult(
            "email",
            False,
            (
                "Email is not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USER, "
                "SMTP_PASSWORD, and SMTP_FROM in your environment."
            ),
        )

    email = EmailMessage()
    email["From"] = sender
    email["To"] = to_email
    email["Subject"] = subject
    if cc_email:
        email["Cc"] = cc_email
    email.set_content(message)

    recipients = [to_email]
    if cc_email:
        recipients.append(cc_email)

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(email, from_addr=sender, to_addrs=recipients)
        return ToolResult("email", True, f"Email sent to {to_email}.")
    except Exception as exc:
        return ToolResult("email", False, f"Email failed: {exc}")
