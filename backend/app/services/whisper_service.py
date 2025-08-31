import os
from typing import List, Dict
import warnings

try:
    import whisper  # type: ignore
except ImportError:
    whisper = None  # type: ignore

_model = None

def get_model():
    global _model
    if _model is None and whisper is not None:
        size = os.getenv('WHISPER_MODEL','base')
        try:
            # Suppress torch.load future warning emitted inside whisper
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=r"You are using `torch.load` with `weights_only=False`.*",
                    category=FutureWarning,
                )
                _model = whisper.load_model(size)
        except Exception:
            _model = None
    return _model

def transcribe_to_segments(path: str) -> Dict:
    model = get_model()
    if model is None:
        # Fallback placeholder if whisper not installed
        return {
            'language': 'en',
            'text': '[transcription unavailable – whisper not installed]',
            'segments': [
                {'start': 0.0, 'end': 0.1, 'text': '[transcription unavailable]'}
            ]
        }
    result = model.transcribe(path, verbose=False)
    segments = []
    for seg in result.get('segments', []):
        segments.append({
            'start': seg.get('start'),
            'end': seg.get('end'),
            'text': seg.get('text')
        })
    return {
        'language': result.get('language'),
        'text': result.get('text'),
        'segments': segments
    }