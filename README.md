# A.R.I.S.H

A.R.I.S.H means Artificial Responsive Intelligent System Helper. Version 3.0 is
a local-first assistant foundation for a JARVIS-inspired desktop AI assistant.
It avoids LiveKit, OpenAI APIs, Anthropic APIs, Gemini APIs, LangChain, CrewAI,
AutoGPT, and paid AI services.

## Current Status

Working now:

- Local CLI chat through `python main.py`
- FastAPI backend and dashboard at `http://127.0.0.1:8000`
- Ollama integration with Qwen preferred
- SQLite chat history and memory commands
- Native tool registry
- Desktop helpers for safe app/folder/file/system actions
- Browser URL and search helpers
- Document reader for TXT, Markdown, PDF, and DOCX
- Vision readiness plus screenshot capture through `mss`
- Voice readiness checks for Whisper, Piper, and OpenWakeWord

Staged for the next implementation pass:

- Always-listening OpenWakeWord loop
- Whisper microphone transcription
- Piper playback integration
- ChromaDB semantic long-term memory
- Playwright autonomous browser control
- Florence-2 OCR and image understanding
- Webcam capture

## Requirements

- Windows, macOS, or Linux
- Python 3.11 recommended
- Ollama installed and running locally
- A local Ollama model, preferably Qwen

This machine currently works with:

```text
qwen3:latest
```

The v3 config asks for `qwen3:4b`, and A.R.I.S.H automatically uses an installed
Qwen model if the exact tag is not present.

## Setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Start Ollama:

```powershell
ollama serve
```

Install or run Qwen:

```powershell
ollama pull qwen3
```

## Run

CLI:

```powershell
python main.py
```

One message:

```powershell
python main.py chat "who are you"
```

Dashboard/API:

```powershell
python main.py api --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## Useful Commands

```text
help
status
voice status
vision status
document status
browser status
remember this: my preferred model is qwen
what do you remember
forget memory 1
search for local AI assistants
google search Ollama Qwen
open chrome
open folder .
list files .
read document notes.txt
take screenshot
```

## API

- `GET /health`
- `POST /chat`
- `GET /memories`
- `POST /memories`
- `DELETE /memories/{memory_id}`
- `GET /tools`
- `POST /tools/execute`
- `GET /voice/status`
- `POST /voice/speak`
- `GET /vision/status`
- `POST /vision/screenshot`
- `POST /vision/inspect`
- `GET /documents/status`
- `POST /documents/read`
- `GET /browser/status`
- `GET /desktop/system`

## Configuration

Copy `.env.example` to `.env` and adjust as needed.

Important values:

```text
ARISH_OLLAMA_URL=http://127.0.0.1:11434
ARISH_OLLAMA_MODEL=qwen3:4b
ARISH_REQUEST_TIMEOUT=120
ARISH_WAKE_WORD=Arish
ARISH_DOCUMENTS_DIR=documents
ARISH_SCREENSHOTS_DIR=data/screenshots
ARISH_PIPER_EXECUTABLE=piper
ARISH_PIPER_VOICE=
```

## Tests

```powershell
python -m unittest discover -s tests
```

Expected result:

```text
10 tests OK
```
