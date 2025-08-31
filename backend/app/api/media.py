from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.db.database import get_db
from app.models.media import Media
from app.schemas.media import MediaOut, SummaryRequest, ChatRequest, SummaryResponse, AnalyticsOut, ChatResponse
from app.utils.file import save_upload
from app.services.whisper_service import transcribe_to_segments
from app.services.gemini_service import call_gemini_summarize
from app.services.tasks import transcribe_media, summarize_media
from app.ai.gemini import chat_with_context, call_gemini
from app.api.deps import get_current_user
import os, json, asyncio, uuid
from fastapi.responses import FileResponse
from fastapi.responses import PlainTextResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

router = APIRouter(prefix="/media", tags=["media"])

async def process_transcription(media_id: int, path: str, db: AsyncSession):
    # fallback local inline (if Celery not running)
    try:
        transcribe_media.delay(media_id, path)
    except Exception:
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: transcribe_to_segments(path))
            transcript = result['text']
            language = result.get('language')
            segments_json = json.dumps(result.get('segments', []))
            await db.execute(update(Media).where(Media.id==media_id).values(transcript=transcript, language=language, segments_json=segments_json, status='transcribed'))
            await db.commit()
        except Exception:
            await db.execute(update(Media).where(Media.id==media_id).values(status='error'))
            await db.commit()

@router.post('/upload', response_model=MediaOut)
async def upload(file: UploadFile = File(...), db: AsyncSession = Depends(get_db), user=Depends(get_current_user), background_tasks: BackgroundTasks = None):
    try:
        stored = save_upload(file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    media = Media(filename=stored, original_name=file.filename, content_type=file.content_type, status='processing', user_id=int(user) if user else None)
    db.add(media)
    await db.commit()
    await db.refresh(media)
    path = os.path.join('uploads', stored)
    background_tasks.add_task(process_transcription, media.id, path, db)
    return media

@router.post('/upload/chunk')
async def upload_chunk(chunk: UploadFile = File(...), chunk_index: int = Form(...), total_chunks: int = Form(...), upload_id: str = Form(...)):
    os.makedirs('uploads/chunks', exist_ok=True)
    temp_dir = os.path.join('uploads', 'chunks', upload_id)
    os.makedirs(temp_dir, exist_ok=True)
    # save chunk
    chunk_path = os.path.join(temp_dir, f"{chunk_index}.part")
    with open(chunk_path, 'wb') as f:
        f.write(await chunk.read())
    # if last chunk, assemble
    assembled = None
    if len(os.listdir(temp_dir)) == total_chunks:
        final_name = f"{upload_id}.bin"
        assembled = os.path.join('uploads', final_name)
        with open(assembled, 'wb') as out:
            for i in range(total_chunks):
                p = os.path.join(temp_dir, f"{i}.part")
                with open(p, 'rb') as inp:
                    out.write(inp.read())
        # cleanup
        for fpart in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, fpart))
        os.rmdir(temp_dir)
    return {"received": chunk_index, "assembled": bool(assembled), "upload_id": upload_id, "final_path": assembled}

@router.get('/{media_id}', response_model=MediaOut)
async def get_media(media_id: int, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Media).where(Media.id==media_id))
    media = q.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=404, detail="Not found")
    return media

@router.get('/{media_id}/analytics', response_model=AnalyticsOut)
async def analytics(media_id: int, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Media).where(Media.id==media_id))
    media = q.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=404, detail="Not found")
    wc = len((media.transcript or '').split()) if media.transcript else 0
    sentiment = None
    if media.summary_json:
        try:
            sentiment = json.loads(media.summary_json).get('sentiment')
        except Exception:
            pass
    return AnalyticsOut(media_id=media.id, word_count=wc, sentiment=sentiment, processing_seconds=None)

@router.post('/summarize', response_model=SummaryResponse)
async def summarize(req: SummaryRequest, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Media).where(Media.id==req.media_id))
    media = q.scalar_one_or_none()
    if not media or not media.transcript:
        raise HTTPException(status_code=400, detail="Transcript not ready")
    try:
        summarize_media.delay(media.id)
        return {"summary_short":"queued", "summary_detailed":"queued", "highlights":[], "sentiment":"neutral", "action_points":[]}
    except Exception:
        summary = await call_gemini_summarize(media.transcript)
        await db.execute(update(Media).where(Media.id==media.id).values(summary_json=json.dumps(summary), status='summarized'))
        await db.commit()
        return summary

@router.post('/chat', response_model=ChatResponse)
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Media).where(Media.id==req.media_id))
    media = q.scalar_one_or_none()
    if not media or not media.transcript:
        raise HTTPException(status_code=400, detail="Transcript not ready")

    # Retrieval: simple scoring by term frequency overlap
    context_segments = []
    refs = []
    if media.segments_json:
        try:
            segments = json.loads(media.segments_json)
            terms = [t for t in req.message.lower().split() if len(t) > 2]
            scored = []
            for seg in segments:
                text = seg.get('text','')
                lt = text.lower()
                score = sum(lt.count(t) for t in terms)
                if score:
                    scored.append((score, seg))
            scored.sort(key=lambda x: x[0], reverse=True)
            top = [s for _, s in scored[:8]]
            context_segments = top
            refs = [{"start": s.get('start'), "end": s.get('end'), "text": s.get('text','')} for s in top[:5]]
        except Exception:
            context_segments = []

    context_text = "\n".join([f"[{seg.get('start'):.1f}-{seg.get('end'):.1f}] {seg.get('text')}" for seg in context_segments])
    prompt = f"You are an assistant answering a question about an audio/video transcript. Use only the provided context segments. Cite timestamps in brackets.\nQuestion: {req.message}\nContext Segments:\n{context_text if context_text else media.transcript[:4000]}\nAnswer:"  # fallback to truncated whole transcript
    answer = await call_gemini(prompt)
    return {"answer": answer, "refs": refs}

@router.get('/{media_id}/export/pdf')
async def export_pdf(media_id: int, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Media).where(Media.id==media_id))
    media = q.scalar_one_or_none()
    if not media or not media.transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    pdf_path = os.path.join('uploads', f"media_{media_id}.pdf")
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    text_obj = c.beginText(40, height - 50)
    text_obj.setFont("Helvetica", 10)
    for line in (media.transcript[:30000]).splitlines():
        text_obj.textLine(line[:120])
        if text_obj.getY() < 50:
            c.drawText(text_obj)
            c.showPage()
            text_obj = c.beginText(40, height - 50)
            text_obj.setFont("Helvetica", 10)
    c.drawText(text_obj)
    c.save()
    return FileResponse(pdf_path, filename=f"transcript_{media_id}.pdf")

@router.get('/{media_id}/export/txt')
async def export_txt(media_id: int, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Media).where(Media.id==media_id))
    media = q.scalar_one_or_none()
    if not media or not media.transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return PlainTextResponse(media.transcript, headers={"Content-Disposition": f"attachment; filename=transcript_{media_id}.txt"})

@router.get('/{media_id}/export/srt')
async def export_srt(media_id: int, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Media).where(Media.id==media_id))
    media = q.scalar_one_or_none()
    if not media or not media.transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    segments = []
    if media.segments_json:
        try:
            segments = json.loads(media.segments_json)
        except Exception:
            pass
    def format_ts(sec: float):
        h = int(sec//3600); m = int((sec%3600)//60); s = int(sec%60); ms = int((sec-int(sec))*1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"
    lines = []
    for idx, seg in enumerate(segments or []):
        lines.append(str(idx+1))
        lines.append(f"{format_ts(seg.get('start',0))} --> {format_ts(seg.get('end',0))}")
        lines.append(seg.get('text','').strip())
        lines.append("")
    content = "\n".join(lines) if lines else media.transcript
    return PlainTextResponse(content, headers={"Content-Disposition": f"attachment; filename=transcript_{media_id}.srt"})

@router.get('/{media_id}/transcript')
async def get_transcript(media_id: int, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Media).where(Media.id==media_id))
    media = q.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=404, detail="Not found")
    if not media.transcript:
        return {"status": media.status}
    segments = []
    if media.segments_json:
        try:
            segments = json.loads(media.segments_json)
        except Exception:
            segments = []
    return {"status": media.status, "language": media.language, "text": media.transcript, "segments": segments}

@router.get('/{media_id}/summary')
async def get_full_summary(media_id: int, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Media).where(Media.id==media_id))
    media = q.scalar_one_or_none()
    if not media or not media.transcript:
        raise HTTPException(status_code=404, detail="Transcript not ready")
    # if summary JSON stored reuse, else generate minimal one
    summary_data = {}
    if media.summary_json:
        try:
            summary_data = json.loads(media.summary_json)
        except Exception:
            summary_data = {}
    if not summary_data:
        summary_data = await call_gemini_summarize(media.transcript)
    # Derive extended fields
    topics_prompt = f"Extract a concise bullet list (max 8) of key topics covered in this transcript.\nTranscript:\n{media.transcript[:12000]}"[:16000]
    action_prompt = f"Extract action items with responsible (if inferable) and due hints if mentioned as JSON array of objects with fields: text, owner, due. If none, return empty array. Transcript:\n{media.transcript[:12000]}"[:16000]
    try:
        topics_raw = await call_gemini(topics_prompt)
        action_raw = await call_gemini(action_prompt)
    except Exception:
        topics_raw, action_raw = "", "[]"
    return {
        "summary": summary_data,
        "topics_raw": topics_raw,
        "action_items_raw": action_raw,
        "language": media.language
    }
