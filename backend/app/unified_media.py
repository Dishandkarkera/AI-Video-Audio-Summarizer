from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request, Response, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import time, uuid, json, hashlib, os
from app.services import whisper_service, gemini_service, search_service
from app.services.storage_access import transcript_path
from app.services.tasks import transcribe_media as celery_transcribe
from fastapi.responses import PlainTextResponse
from io import BytesIO

try:  # optional heavy dependency already in requirements
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except Exception:  # pragma: no cover
    letter = None  # type: ignore
    canvas = None  # type: ignore

try:
    from fastapi_limiter import FastAPILimiter  # noqa: F401
    from fastapi_limiter.depends import RateLimiter
except Exception:
    RateLimiter = None  # type: ignore

router = APIRouter(prefix="/media", tags=["media"])
STORAGE = Path('storage')
STORAGE.mkdir(exist_ok=True)

@router.get('/{media_id}')
def get_media_meta(media_id: str):
    """Return metadata for a media item (status, filename, segments count, language).

    This endpoint was added to satisfy frontend polling that expected /media/{id}.
    """
    # Identify raw/original file (exclude generated _transcript/_summary files)
    raw = next((p for p in STORAGE.glob(f"{media_id}.*")
                if not p.name.endswith('_transcript.json') and not p.name.endswith('_summary.json')),
               None)
    transcript_file = transcript_path(media_id)
    transcript_data = None
    if transcript_file.exists():
        try:
            import json as _json
            with open(transcript_file, 'r', encoding='utf-8') as f:
                transcript_data = _json.load(f)
        except Exception:
            transcript_data = None
    if not raw and not transcript_data:
        raise HTTPException(status_code=404, detail='Media not found')
    segments_list = transcript_data.get('segments', []) if isinstance(transcript_data, dict) else []
    language = transcript_data.get('language') if isinstance(transcript_data, dict) else None
    # Provide a concise transcript string only if small (avoid huge payloads each poll)
    transcript_text = None
    if segments_list and len(segments_list) <= 200:  # arbitrary safety limit
        try:
            transcript_text = ' '.join(s.get('text','') for s in segments_list)[:2000]
        except Exception:
            transcript_text = None
    status = 'done' if transcript_data else 'processing'
    return {
        'id': media_id,
        'filename': raw.name if raw else None,
        'status': status,
        'segments': len(segments_list),
        'language': language,
        'transcript': transcript_text
    }

@router.get('/{media_id}/raw')
def get_media_file(media_id: str):
    """Stream the original uploaded media file (video/audio) for playback.

    Looks up a file named {media_id}.* in storage excluding generated transcript/summary artifacts.
    """
    raw = next((p for p in STORAGE.glob(f"{media_id}.*")
                if not p.name.endswith('_transcript.json') and not p.name.endswith('_summary.json')),
               None)
    if not raw:
        raise HTTPException(status_code=404, detail='Media file not found')
    import mimetypes
    mt, _ = mimetypes.guess_type(str(raw))
    return FileResponse(str(raw), media_type=mt or 'application/octet-stream', filename=raw.name)

@router.post('/upload')
async def upload_media(file: UploadFile = File(...), background: BackgroundTasks = None):
    """Upload a media file.

    Small files (<= SYNC_TRANSCRIBE_MAX_MB, default 8MB) are transcribed synchronously so
    the client immediately receives segments.
    Larger files return quickly with status=processing and are transcribed in a background task.
    """
    media_id = str(uuid.uuid4())
    ext = ''.join(Path(file.filename).suffixes)
    raw_path = STORAGE / f"{media_id}{ext}"
    data = await file.read()
    with open(raw_path, 'wb') as f:
        f.write(data)
    size_mb = len(data) / (1024*1024)
    sync_limit_mb = float(os.getenv('SYNC_TRANSCRIBE_MAX_MB', '8'))

    def _do_transcribe(mid: str, path: str):  # background safe function
        try:
            result_local = whisper_service.transcribe_to_segments(path)
            with open(transcript_path(mid), 'w', encoding='utf-8') as tf:
                json.dump(result_local, tf, indent=2)
        except Exception as e:  # write minimal error marker
            try:
                with open(transcript_path(mid), 'w', encoding='utf-8') as tf:
                    json.dump({"error": str(e)}, tf)
            except Exception:
                pass

    if size_mb <= sync_limit_mb:
        # synchronous (keeps test behavior for tiny fixtures)
        result = whisper_service.transcribe_to_segments(str(raw_path))
        with open(transcript_path(media_id), 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
        return {"id": media_id, "filename": file.filename, "segments": len(result.get('segments', [])), "status": "done"}
    else:
        if background is not None:
            background.add_task(_do_transcribe, media_id, str(raw_path))
        else:  # fallback run inline if background not provided
            _do_transcribe(media_id, str(raw_path))
        return {"id": media_id, "filename": file.filename, "segments": 0, "status": "processing", "detail": "Transcription queued"}

@router.post('/summarize')
async def summarize_media(payload: dict):
    """Generate (or return cached) summary for a media id.

    Frontend calls POST /media/summarize with {media_id}. We map to gemini_service.get_summary.
    """
    media_id = (payload or {}).get('media_id') or (payload or {}).get('id')
    if not media_id:
        raise HTTPException(status_code=400, detail='media_id required')
    # Ensure transcript exists first
    t_file = transcript_path(media_id)
    if not t_file.exists():
        return JSONResponse({'status': 'processing', 'detail': 'Transcript not ready'}, status_code=202)
    data = await gemini_service.get_summary(media_id)
    # Normalize fields
    if 'key_highlights' in data and 'highlights' not in data:
        data['highlights'] = data['key_highlights']
    data.setdefault('highlights', [])
    data.setdefault('action_points', [])
    return data

@router.get('/{media_id}/status')
async def get_status(media_id: str):
    return {"ready": transcript_path(media_id).exists()}

@router.get('/{media_id}/transcript')
async def get_transcript_primary(media_id: str):
    """Return transcript JSON or a processing placeholder.

    Previous behavior: 404 until file existed (caused frontend error bursts).
    New behavior: 202 Accepted with {status: processing} while waiting, 404 only if
    neither transcript nor raw media file exists anymore (invalid id).
    """
    t_path = transcript_path(media_id)
    if t_path.exists():
        with open(t_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Ensure a status field for consistency
        if isinstance(data, dict) and 'status' not in data:
            data['status'] = 'done'
        return data
    # Determine if raw file exists (any extension except generated *_transcript/_summary)
    raw = next((p for p in STORAGE.glob(f"{media_id}.*")
                if not p.name.endswith('_transcript.json') and not p.name.endswith('_summary.json')),
               None)
    if raw:
        return JSONResponse({"id": media_id, "status": "processing"}, status_code=202)
    raise HTTPException(status_code=404, detail='Media not found')

@router.get('/{media_id}/transcript/translate')
async def translate_transcript_api(media_id: str, target: str = 'hi'):
    """Translate existing transcript to target language (default Hindi 'hi')."""
    t_path = transcript_path(media_id)
    if not t_path.exists():
        raise HTTPException(status_code=404, detail='Transcript not ready')
    try:
        with open(t_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        raise HTTPException(status_code=500, detail='Cannot read transcript')
    text = data.get('text') or ' '.join(s.get('text','') for s in data.get('segments', []))
    translated = await gemini_service.translate_transcript(text, target)
    return {"media_id": media_id, "target": target, "translated_text": translated}

@router.post('/{media_id}/transcript/inline')
def force_inline_transcription(media_id: str):
    """Force an inline (synchronous) transcription if transcript missing.

    Use when background task / celery queue did not process a large file yet. This will block the request
    until transcription is complete, so ONLY use for debugging or small/medium files.
    """
    t_path = transcript_path(media_id)
    if t_path.exists():
        return {"status": "already_done"}
    raw = next((p for p in STORAGE.glob(f"{media_id}.*")
                if not p.name.endswith('_transcript.json') and not p.name.endswith('_summary.json')),
               None)
    if not raw:
        raise HTTPException(status_code=404, detail='Raw media not found')
    try:
        result = whisper_service.transcribe_to_segments(str(raw))
        with open(t_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
        return {"status": "done", "segments": len(result.get('segments', []))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inline transcription failed: {e}")

@router.get('/{media_id}/summary')
async def get_summary(media_id: str, request: Request, response: Response):
    data = await gemini_service.get_summary(media_id)
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

@router.get('/{media_id}/summary')
async def get_summary(media_id: str, request: Request, response: Response):
    """Return (and cache) AI summary; if transcript not ready, report processing.

    Mirrors legacy route behavior so both GET and POST flows work.
    """
    transcript_file = transcript_path(media_id)
    if not transcript_file.exists():
        return JSONResponse({"status": "processing", "detail": "Transcript not ready"}, status_code=202)
    data = await gemini_service.get_summary(media_id)
    # ETag for caching
    try:
        payload = json.dumps(data, sort_keys=True).encode('utf-8')  # type: ignore
        etag = hashlib.sha1(payload).hexdigest()
        if_none = request.headers.get('if-none-match')
        response.headers['ETag'] = etag
        if if_none == etag:
            response.status_code = 304
            return None
    except Exception:
        pass
    if 'key_highlights' in data and 'highlights' not in data:
        data['highlights'] = data['key_highlights']
    data.setdefault('highlights', [])
    data.setdefault('action_points', [])
    return data

@router.delete('/{media_id}/summary')
async def invalidate_summary(media_id: str):
    cache_file = Path('storage') / f"{media_id}_summary.json"
    if cache_file.exists():
        try:
            cache_file.unlink()
        except Exception:
            pass
    return {"status": "invalidated"}

@router.post('/{media_id}/chat')
async def chat_with_media(media_id: str, payload: dict):
    question = payload.get('question','')
    if RateLimiter is None:
        _rate_limit("chat", media_id)
    mode = payload.get('mode') or 'agent'
    if mode == 'agent':
        return await gemini_service.chat_agent(media_id, question, {"id":"anon"})
    if mode == 'gpt':
        return await gemini_service.chat_gpt(media_id, question, {"id":"anon"})
    # fallback simple retrieval grounded
    return await gemini_service.chat(media_id, question, {"id":"anon"})

@router.delete('/{media_id}/chat/history')
async def clear_chat_history(media_id: str):
    ok = gemini_service.clear_history(media_id, 'anon')
    return {"cleared": ok}

@router.get('/{media_id}/chat/history')
async def get_chat_history(media_id: str):
    hist = gemini_service.list_history(media_id, 'anon')
    return {"history": hist[-50:]}

@router.get('/{media_id}/search')
async def search(media_id: str, q: str):
    if RateLimiter is None:
        _rate_limit("search", media_id)
    return await search_service.search(media_id, q)

@router.post('/{media_id}/transcribe')
async def enqueue_transcription(media_id: str):
    raw_guess = next((p for p in (Path('storage').glob(f"{media_id}.*")) if not str(p).endswith('_transcript.json')), None)
    if not raw_guess:
        raise HTTPException(status_code=404, detail='Media file not found')
    try:
        celery_transcribe.delay(media_id, str(raw_guess))
    except Exception:
        return {"queued": False, "detail": "Celery not available"}
    return {"queued": True, "job_id": f"transcribe:{media_id}"}

@router.get('/{media_id}/transcript_poll')
async def get_transcript_poll(media_id: str, job_id: str | None = None):
    if not transcript_path(media_id).exists():
        return {"status": "processing", "job_id": job_id}
    with open(transcript_path(media_id), 'r', encoding='utf-8') as f:
        return json.load(f)

_RL_BUCKET = {}
def _rate_limit(namespace: str, key: str, limit: int = 10, window: int = 60):
    now = time.time()
    bucket_key = f"{namespace}:{key}" if key else namespace
    entries = [t for t in _RL_BUCKET.get(bucket_key, []) if t > now - window]
    if len(entries) >= limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    entries.append(now)
    _RL_BUCKET[bucket_key] = entries

# ---------------------------------------------------------------------------
# Export endpoints (PDF / TXT / SRT) to mirror legacy API used by frontend
# ---------------------------------------------------------------------------
@router.get('/{media_id}/export/txt')
def export_txt(media_id: str):
    t_path = transcript_path(media_id)
    if not t_path.exists():
        raise HTTPException(status_code=404, detail='Transcript not found')
    try:
        with open(t_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        text = data.get('text') or ' '.join(s.get('text','') for s in data.get('segments', []))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Could not read transcript: {e}')
    return PlainTextResponse(text, headers={"Content-Disposition": f"attachment; filename=transcript_{media_id}.txt"})

@router.get('/{media_id}/export/srt')
def export_srt(media_id: str):
    t_path = transcript_path(media_id)
    if not t_path.exists():
        raise HTTPException(status_code=404, detail='Transcript not found')
    try:
        with open(t_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Could not read transcript: {e}')
    segments = data.get('segments') or []
    def fmt(sec: float):
        h = int(sec//3600); m = int((sec%3600)//60); s = int(sec%60); ms = int((sec-int(sec))*1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"
    if segments:
        lines = []
        for idx, seg in enumerate(segments, start=1):
            lines.append(str(idx))
            lines.append(f"{fmt(seg.get('start',0.0))} --> {fmt(seg.get('end', seg.get('start',0.0)+2))}")
            lines.append((seg.get('text') or '').strip())
            lines.append("")
        content = "\n".join(lines)
    else:
        # Fallback: single block with whole text
        full = data.get('text','')
        content = f"1\n00:00:00,000 --> 00:10:00,000\n{full}\n"
    return PlainTextResponse(content, headers={"Content-Disposition": f"attachment; filename=transcript_{media_id}.srt"})

@router.get('/{media_id}/export/pdf')
def export_pdf(media_id: str):
    t_path = transcript_path(media_id)
    if not t_path.exists():
        raise HTTPException(status_code=404, detail='Transcript not found')
    if canvas is None or letter is None:
        raise HTTPException(status_code=500, detail='PDF generation library missing')
    try:
        with open(t_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        text = data.get('text') or ' '.join(s.get('text','') for s in data.get('segments', []))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Could not read transcript: {e}')
    # Build nicely formatted lines
    from datetime import datetime, timezone
    import textwrap
    segments = data.get('segments') or []
    lines: list[str] = []
    lines.append('Transcript Export')
    lines.append(f'Media ID: {media_id}')
    if data.get('language'): lines.append(f'Language: {data.get("language")}')
    lines.append(f'Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}')
    if segments:
        lines.append(f'Segments: {len(segments)}')
    lines.append('')
    def fmt_ts(sec: float):
        h = int(sec//3600); m = int((sec%3600)//60); s = int(sec%60); ms = int((sec-int(sec))*1000)
        if h:
            return f"{h:02}:{m:02}:{s:02}.{ms:03}"
        return f"{m:02}:{s:02}.{ms:03}"
    if segments:
        for seg in segments:
            start = fmt_ts(seg.get('start',0.0)); end = fmt_ts(seg.get('end', seg.get('start',0.0)))
            header = f"[{start} - {end}]"
            body = (seg.get('text') or '').strip()
            if not body:
                continue
            wrap_width = 100
            wrapped = textwrap.wrap(body, width=wrap_width) or ['']
            lines.append(header + ' ' + wrapped[0])
            for cont in wrapped[1:]:
                lines.append(' '*(len(header)+1) + cont)
            lines.append('')
            if len(lines) > 12000:  # safety cutoff to avoid huge PDFs
                lines.append('... (truncated)')
                break
    else:
        # Fallback to raw text splitting by paragraphs
        for para in (text[:60000]).split('\n'):
            para = para.strip()
            if not para:
                continue
            for w in textwrap.wrap(para, width=100):
                lines.append(w)
            lines.append('')
    # Generate PDF in-memory with wrapped lines
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter
    text_obj = c.beginText(40, height - 50)
    text_obj.setFont('Helvetica', 10)
    for line in lines:
        # Page break handling
        if text_obj.getY() < 50:
            c.drawText(text_obj); c.showPage(); text_obj = c.beginText(40, height - 50); text_obj.setFont('Helvetica', 10)
        text_obj.textLine(line if line is not None else '')
    c.drawText(text_obj)
    c.save(); buf.seek(0)
    headers = {"Content-Disposition": f"attachment; filename=transcript_{media_id}.pdf"}
    return Response(content=buf.read(), media_type='application/pdf', headers=headers)
