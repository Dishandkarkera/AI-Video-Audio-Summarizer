import os, json, asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, select
from app.services.celery_app import celery_app
from app.services.whisper_service import transcribe_to_segments
from app.services.gemini_service import call_gemini_summarize
from app.db.database import SessionLocal, engine
from app.models.media import Media

@celery_app.task(name='transcribe.media')
def transcribe_media(media_id: int, path: str):
    """Synchronous celery task performing whisper transcription and storing results."""
    import asyncio as _asyncio
    _asyncio.run(_transcribe(media_id, path))

async def _transcribe(media_id: int, path: str):
    db: AsyncSession
    async with SessionLocal() as db:
        try:
            result = transcribe_to_segments(path)
            segments_json = json.dumps(result.get('segments', []))
            await db.execute(update(Media).where(Media.id==media_id).values(
                transcript=result.get('text'),
                language=result.get('language'),
                segments_json=segments_json,
                status='transcribed'
            ))
            await db.commit()
        except Exception:
            await db.execute(update(Media).where(Media.id==media_id).values(status='error'))
            await db.commit()

@celery_app.task(name='summarize.media')
def summarize_media(media_id: int):
    import asyncio as _asyncio
    _asyncio.run(_summarize(media_id))

async def _summarize(media_id: int):
    async with SessionLocal() as db:
        res = await db.execute(select(Media).where(Media.id==media_id))
        media = res.scalar_one_or_none()
        if not media or not media.transcript:
            return
        summary = await call_gemini_summarize(media.transcript)
        await db.execute(update(Media).where(Media.id==media.id).values(summary_json=json.dumps(summary), status='summarized'))
        await db.commit()