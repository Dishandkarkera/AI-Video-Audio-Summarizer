import json, os
from pathlib import Path

STORAGE = Path('storage')
STORAGE.mkdir(exist_ok=True)

def transcript_path(media_id: str) -> Path:
    return STORAGE / f"{media_id}_transcript.json"

def media_raw_path(media_id: str, original_ext: str = '.bin') -> Path:
    return STORAGE / f"{media_id}{original_ext}"

def load_transcript(media_id: str):
    path = transcript_path(media_id)
    if not path.exists():
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
