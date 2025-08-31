import os, tempfile, subprocess
import whisper
from app.core.config import get_settings

settings = get_settings()
_model = None

def get_model():
    global _model
    if _model is None:
        _model = whisper.load_model("base")
    return _model

async def transcribe_file(path: str):
    model = get_model()
    # Whisper is sync; run in thread if needed (FastAPI will handle if using run_in_threadpool)
    result = model.transcribe(path)
    return result  # includes text, segments (with timestamps), language
