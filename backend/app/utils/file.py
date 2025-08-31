import os, shutil, uuid
from app.core.config import get_settings

settings = get_settings()

ALLOWED_EXT = {'.mp4', '.mp3', '.wav', '.avi', '.mov', '.mkv', '.m4a', '.webm'}

def ensure_upload_dir():
    os.makedirs(settings.upload_dir, exist_ok=True)


def save_upload(file) -> str:
    ensure_upload_dir()
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        raise ValueError(f"Unsupported file type: {ext}")
    new_name = f"{uuid.uuid4().hex}{ext}"
    dest = os.path.join(settings.upload_dir, new_name)
    with open(dest, 'wb') as f:
        shutil.copyfileobj(file.file, f)
    return new_name
