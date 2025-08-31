# Node.js Backend (Alternative Implementation)

Express-based service for AI Video & Audio Summarizer.

## Endpoints
- POST /api/upload (multipart form-data: file)
- POST /api/transcribe/:fileId
- POST /api/summarize (JSON {fileId? transcript?})
- POST /api/qa (JSON {fileId, question})
- GET /health

## Setup
```
cd backend_node
cp .env.example .env # set GEMINI_API_KEY
npm install
npm run dev
```
Server on http://localhost:8000

## Notes
- Whisper service is placeholder; integrate whisper.cpp or OpenAI Whisper.
- In-memory storage used; replace with DB for persistence.
- Gemini JSON parsing is best-effort; enhance with strict schema validation.
