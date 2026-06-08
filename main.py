from __future__ import annotations

import argparse
import sys

from arish.agent import Assistant
from arish.config import AppConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arish",
        description="Run the local-first A.R.I.S.H assistant.",
    )
    subparsers = parser.add_subparsers(dest="command")

    chat = subparsers.add_parser("chat", help="Send one message or start chat mode.")
    chat.add_argument("message", nargs="*", help="Message to send.")
    chat.add_argument("--session", default="default", help="Conversation session id.")

    api = subparsers.add_parser("api", help="Start the FastAPI dashboard/API.")
    api.add_argument("--host", default="127.0.0.1", help="API host.")
    api.add_argument("--port", default=8000, type=int, help="API port.")
    api.add_argument("--reload", action="store_true", help="Reload on code changes.")

    subparsers.add_parser("health", help="Check assistant health.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "api":
        return run_api(host=args.host, port=args.port, reload=args.reload)

    config = AppConfig.from_env()
    assistant = Assistant(config)

    if args.command == "health":
        result = assistant.handle("status")
        print(result.response)
        return 0

    if args.command == "chat" and args.message:
        result = assistant.handle(" ".join(args.message), session_id=args.session)
        print(result.response)
        return 0

    return repl(assistant)


def repl(assistant: Assistant) -> int:
    print("A.R.I.S.H is running locally. Type 'help' for commands or 'exit' to quit.")
    while True:
        try:
            message = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if message.lower() in {"exit", "quit"}:
            return 0
        if not message:
            continue

        result = assistant.handle(message)
        print(f"A.R.I.S.H> {result.response}")


def run_api(host: str, port: int, reload: bool = False) -> int:
    try:
        import uvicorn

        from arish.api import create_app
    except Exception as exc:
        print(f"API dependencies are missing: {exc}", file=sys.stderr)
        print("Run: python -m pip install -r requirements.txt", file=sys.stderr)
        return 1

    app = create_app()
    uvicorn.run(app, host=host, port=port, reload=reload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
