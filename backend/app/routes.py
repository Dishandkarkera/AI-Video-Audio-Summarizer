from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request, Response
from pathlib import Path
import time
import uuid, json
from pathlib import Path
from app.services import whisper_service, gemini_service, auth_service, search_service
from app.services.storage_access import transcript_path, load_transcript
from app.services.tasks import transcribe_media as celery_transcribe
import hashlib, json, os

try:
    # Optional redis-based limiter via fastapi-limiter
    from fastapi_limiter import FastAPILimiter
    from fastapi_limiter.depends import RateLimiter
    import redis.asyncio as redis
    _redis_url = os.getenv('REDIS_URL','redis://localhost:6379/0')
except Exception:  # graceful degrade
    FastAPILimiter = None
    RateLimiter = None

router = APIRouter(prefix="/media", tags=["media"])
STORAGE = Path('storage')
STORAGE.mkdir(exist_ok=True)

@router.post('/upload')
async def upload_media(file: UploadFile = File(...)):
    media_id = str(uuid.uuid4())
    ext = ''.join(Path(file.filename).suffixes)
    raw_path = STORAGE / f"{media_id}{ext}"
    with open(raw_path, 'wb') as f:
        f.write(await file.read())
    # transcribe synchronously (could async offload later)
    result = whisper_service.transcribe_to_segments(str(raw_path))
    with open(transcript_path(media_id), 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    return {"id": media_id, "filename": file.filename, "segments": len(result.get('segments', []))}

@router.get('/{media_id}/status')
async def get_status(media_id: str):
    return {"ready": transcript_path(media_id).exists()}

@router.get('/{media_id}/transcript')
async def get_transcript_primary(media_id: str):
    if not transcript_path(media_id).exists():
        raise HTTPException(status_code=404, detail='Transcript not found')
    with open(transcript_path(media_id), 'r', encoding='utf-8') as f:
        return json.load(f)

@router.get('/{media_id}/summary')
async def get_summary(media_id: str, request: Request, response: Response):
    data = await gemini_service.get_summary(media_id)
    # ETag support
    try:
        payload = json.dumps(data, sort_keys=True).encode('utf-8')
        etag = hashlib.sha1(payload).hexdigest()
        if_none = request.headers.get('if-none-match')
        response.headers['ETag'] = etag
        if if_none == etag:
            response.status_code = 304
            return None
    except Exception:
        pass
    return data

@router.delete('/{media_id}/summary')
async def invalidate_summary(media_id: str, user=Depends(auth_service.get_current_user)):
    # Remove cached summary so next call recomputes
    from pathlib import Path
    cache_file = Path('storage') / f"{media_id}_summary.json"
    if cache_file.exists():
        try: cache_file.unlink()
        except Exception: pass
    return {"status":"invalidated"}

@router.post('/{media_id}/chat')
async def chat_with_media(media_id: str, payload: dict, user=Depends(auth_service.get_current_user)):
    question = payload.get('question','')
    if RateLimiter:
        # fastapi-limiter is applied via dependency in main if initialized; fallback to manual below
        pass
    else:
        _rate_limit("chat", user.get('id'))
    return await gemini_service.chat(media_id, question, user)

@router.get('/{media_id}/search')
async def search(media_id: str, q: str):
    if RateLimiter:
        pass
    else:
        _rate_limit("search", media_id)
    return await search_service.search(media_id, q)

@router.post('/{media_id}/transcribe')
async def enqueue_transcription(media_id: str):
    # Expect raw file already uploaded via legacy or external process
    # For demo: just schedule if a raw file exists
    raw_guess = next((p for p in (Path('storage').glob(f"{media_id}.*")) if not str(p).endswith('_transcript.json')), None)
    if not raw_guess:
        raise HTTPException(status_code=404, detail='Media file not found')
    try:
        celery_transcribe.delay(media_id, str(raw_guess))  # reusing existing task signature (may mismatch int vs str in legacy)
    except Exception:
        return {"queued": False, "detail": "Celery not available"}
    return {"queued": True, "job_id": f"transcribe:{media_id}"}

@router.get('/{media_id}/transcript_poll')  # polling variant
async def get_transcript_poll(media_id: str, job_id: str | None = None):
    if not transcript_path(media_id).exists():
        return {"status":"processing", "job_id": job_id}
    with open(transcript_path(media_id), 'r', encoding='utf-8') as f:
        return json.load(f)

# ---- Simple in-memory rate limiter ----
_RL_BUCKET = {}
def _rate_limit(namespace: str, key: str, limit: int = 10, window: int = 60):
    now = time.time()
    bucket_key = f"{namespace}:{key}" if key else namespace
    window_start = now - window
    entries = _RL_BUCKET.get(bucket_key, [])
    # prune
    entries = [t for t in entries if t > window_start]
    if len(entries) >= limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    entries.append(now)
    _RL_BUCKET[bucket_key] = entries
