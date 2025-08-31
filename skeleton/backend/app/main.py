from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, uuid, asyncio, time

UPLOAD_DIR = os.getenv('UPLOAD_DIR', 'uploads')
LAT_MS = int(os.getenv('MOCK_LATENCY_MS', '1200'))
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="AI Media Summarizer Skeleton")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store
SESSIONS = {}

class SessionOut(BaseModel):
    id: str
    original_filename: str
    status: str
    summary: str | None = None

@app.get('/health')
async def health():
    return {"ok": True}

async def mock_process(session_id: str, path: str):
    # simulate transcription & summarization pipeline
    await asyncio.sleep(LAT_MS/1000)
    sess = SESSIONS.get(session_id)
    if not sess: return
    sess['status'] = 'transcribing'
    await asyncio.sleep(LAT_MS/1000)
    sess['status'] = 'summarizing'
    await asyncio.sleep(LAT_MS/1000)
    sess['summary'] = f"Mock summary for {sess['original_filename']} (size={sess['size']} bytes). Replace with Gemini output."
    sess['status'] = 'complete'

@app.post('/sessions', response_model=SessionOut)
async def create_session(file: UploadFile = File(...), background: BackgroundTasks = None):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename")
    ext = os.path.splitext(file.filename)[1].lower()
    new_id = uuid.uuid4().hex
    stored_name = f"{new_id}{ext}"
    dest = os.path.join(UPLOAD_DIR, stored_name)
    with open(dest, 'wb') as f:
        f.write(await file.read())
    SESSIONS[new_id] = {
        'id': new_id,
        'original_filename': file.filename,
        'stored_name': stored_name,
        'status': 'queued',
        'summary': None,
        'size': os.path.getsize(dest)
    }
    background.add_task(mock_process, new_id, dest)
    return SessionOut(**SESSIONS[new_id])

@app.get('/sessions/{session_id}', response_model=SessionOut)
async def get_session(session_id: str):
    sess = SESSIONS.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Not found")
    return SessionOut(**sess)

@app.post('/sessions/{session_id}/summarize', response_model=SessionOut)
async def force_summarize(session_id: str):
    sess = SESSIONS.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Not found")
    if sess['status'] != 'complete':
        # fast-forward
        sess['summary'] = f"(Forced) Mock summary for {sess['original_filename']}."
        sess['status'] = 'complete'
    return SessionOut(**sess)
