# Local AI Interviewer

Fully local, voice-based AI mock interviewer. React frontend + FastAPI backend + Postgres, with Ollama (LLM), Faster-Whisper (STT), and pyttsx3 (TTS) — no cloud calls.

## Quickstart

Backend (PowerShell, from repo root):

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
Copy-Item .env.example .env   # then fill in DATABASE_URL
.\.venv\Scripts\alembic -c backend\alembic.ini upgrade head
$env:PYTHONPATH='backend'; .\.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

Frontend (new terminal):

```powershell
cd frontend; npm install; npm run dev -- --port 5173 --strictPort
```

Open http://localhost:5173. Needs local Postgres and Ollama (`ollama pull llama3.2:1b`, match `OLLAMA_MODEL` in `.env`).

## How an interview flows

1. New session (pick a role, or leave blank and the interviewer asks by voice).
2. The AI greets first (`POST /sessions/{id}/greet`, role-aware, auto-played).
3. Each voice turn: record → transcribe → streamed SSE reply → synthesized audio, both turns persisted.
4. Complete the session, then run `/evaluate` for a report.

## API

| Method & path | What |
|---|---|
| `GET /health` | Live Ollama + DB status |
| `POST /api/interview/chat/stream` | SSE LLM chat (role-grounded system prompt, ~200-token cap); persists turns when `interview_id` set |
| `POST /api/interview/transcribe` | Audio upload (wav/mp3/m4a/webm) → transcript |
| `POST /api/interview/synthesize` | Text → uniquely-named wav |
| `GET/DELETE /api/interview/audio/{f}` | Serve / delete audio (traversal-safe) |
| `POST /api/interview/evaluate` | Post-interview report |
| `POST/GET /api/interview/sessions…` | Sessions, history, messages, complete |
| `PATCH /api/interview/sessions/{id}` | Update target role |
| `POST /api/interview/sessions/{id}/greet` | Opening greeting + audio in one call |

Auth (JWT login, per-user session scoping) is planned, not built — sessions currently take an optional client `user_id`.

## Tests & Docker

```powershell
$env:PYTHONPATH='.'; ..\.venv\Scripts\python -m pytest tests/ -q   # from backend/
docker build -f backend/Dockerfile -t local-ai-interviewer ./backend
```
