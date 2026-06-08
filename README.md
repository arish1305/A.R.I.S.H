# A.R.I.S.H

A.R.I.S.H stands for Artificial Responsive Intelligent System Helper. This
version is a local-first assistant foundation: it runs without LiveKit, OpenAI,
Google realtime models, or other proprietary AI services.

The project now starts cleanly as a CLI, FastAPI backend, and browser dashboard.
Ollama is optional. When Ollama is not running, A.R.I.S.H still handles built-in
commands with a local fallback instead of crashing.

## What Works Now

- Local CLI chat through `python agent.py` or `python main.py`
- FastAPI API and dashboard through `python main.py api`
- SQLite short-term chat history and long-term memories
- Memory commands: remember, list, summarize, and forget
- DuckDuckGo search-link creation without sending data automatically
- Optional live weather via `wttr.in`
- Safe desktop launching for whitelisted apps
- Optional Ollama integration for local LLM responses

## Setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run The Assistant

Interactive CLI:

```powershell
python agent.py
```

One message:

```powershell
python main.py chat "remember this: my preferred model is qwen3"
python main.py chat "what do you remember"
```

API and dashboard:

```powershell
python main.py api --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

## Optional Ollama

Install Ollama, then run:

```powershell
ollama pull qwen3
ollama run qwen3
```

A.R.I.S.H talks to Ollama at `http://127.0.0.1:11434` by default.

## Environment

Copy `.env.example` to `.env` and adjust values as needed.

```text
ARISH_OLLAMA_URL=http://127.0.0.1:11434
ARISH_OLLAMA_MODEL=qwen3
ARISH_ENABLE_INTERNET_TOOLS=false
ARISH_ENABLE_DESKTOP_TOOLS=true
ARISH_OPEN_BROWSER_ON_SEARCH=false
ARISH_DB_PATH=data/arish.sqlite3
```

Set `ARISH_ENABLE_INTERNET_TOOLS=true` only when you want network-backed tools
like live weather. Search commands create a URL by default and do not fetch
results automatically.

## API

- `GET /health`
- `POST /chat` with `{ "message": "...", "session_id": "default" }`
- `GET /memories`
- `POST /memories` with `{ "content": "...", "tags": [] }`
- `DELETE /memories/{memory_id}`

## Tests

```powershell
python -m unittest discover -s tests
```

## Next Build Targets

- Whisper speech-to-text module
- Piper text-to-speech module
- OpenWakeWord wake-word listener
- ChromaDB semantic memory
- Playwright browser agent
- Vision module for webcam and screenshots
