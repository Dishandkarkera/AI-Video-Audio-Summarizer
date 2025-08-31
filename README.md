# AI-Video-Audio-Summarizer

Full-stack project: FastAPI backend + React (Vite) frontend.

## Features
- Upload audio/video (chunk ready placeholder) and auto transcription via Whisper.
- Gemini API summarization (short & detailed, highlights, sentiment, action points).
- Chat Q&A grounded on transcript.
- JWT auth (optional use).
- SQLite default via SQLAlchemy async.
- Export PDF (TODO frontend).
- Recording + analytics placeholders TBD.

## Backend Setup

Create a `.env` (see `backend/.env.example`) and set `GEMINI_API_KEY` (replace `Your-API-Key` with your real key; never commit real keys).

```
cd backend
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 5000
```

## Frontend Setup

```
cd frontend
npm install
npm run dev
```

Visit http://localhost:3000

## Chunked Upload (WIP)
Endpoint: POST /media/upload/chunk (multipart form fields: upload_id, chunk_index, total_chunks, chunk)
Assemble occurs automatically after final chunk arrives. Returned JSON contains final_path once assembled (server not yet auto-transcribing assembled file – extend by creating a follow-up call to /media/upload using assembled file or adapting endpoint to register as Media row).

## API Quick Test (after server running)
```
GET http://localhost:5000/health
```

## Roadmap
- [x] Chunked upload endpoint (assembly only)
- [x] PDF export (transcript only)
- [ ] Word export
- [ ] Analytics endpoint (processing times, word count, sentiment score)
- [ ] Realtime recording (WebRTC)
- [x] Dark mode toggle in UI
