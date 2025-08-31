# AI Summarizer Skeleton (Option A)

Minimal runnable end-to-end flow: upload -> mock processing -> summary display.

## Stack
Backend: FastAPI
Frontend: React + Vite + TailwindCSS
Docker: docker-compose for combined run

## Features Implemented
- Upload media file to /sessions
- In-memory session store
- Mock processing stages (queued -> transcribing -> summarizing -> complete)
- Auto polling in frontend until complete
- Mock summary placeholder string

## Quick Start (Local w/out Docker)

Backend:
```
cd skeleton/backend
python -m venv .venv
. .venv/Scripts/Activate.ps1  # Windows PowerShell
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:
```
cd skeleton/frontend
npm install
npm run dev
```
Open http://localhost:5173 (Vite default) and upload a small file.

## Docker Compose
```
cd skeleton
docker compose up --build
```
Frontend: http://localhost:3000  Backend: http://localhost:8000

## Environment Variables
Copy `backend/.env.example` to `backend/.env`.

- `MOCK_LATENCY_MS` (default 1200) controls simulated stage durations.
- `UPLOAD_DIR` (optional) override upload directory.

## Extending
1. Replace `mock_process` with Whisper transcription -> store transcript.
2. Add summarization call (Gemini) in place of mock summary.
3. Add database (SQLite/Postgres) for persistence.
4. Introduce auth & user sessions.
5. Expand model to include transcripts & segments.

## API
POST /sessions (multipart file) -> {id,status,...}
GET /sessions/{id} -> current state & mock summary once complete
POST /sessions/{id}/summarize -> force completion

## License
MIT (adapt as needed)
