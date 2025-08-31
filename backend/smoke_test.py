"""Simple smoke test for the FastAPI media endpoints.

Run the API server first in another terminal:
  uvicorn app.main:app --port 8000

Then run:
  python smoke_test.py
"""

import time
import json
import requests
from pathlib import Path
import wave, math, struct

BASE = "http://127.0.0.1:8000"

def ensure_test_wav(path: Path):
    if path.exists():
        return path
    fr=16000; dur=1.0; amp=16000; freq=440; n=int(fr*dur)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'w') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(fr)
        for i in range(n):
            val=int(amp*math.sin(2*math.pi*freq*i/fr))
            w.writeframes(struct.pack('<h', val))
    return path

def main():
    # Root health
    r = requests.get(BASE + "/")
    print("ROOT", r.status_code, r.text)
    # Prepare wav
    wav = ensure_test_wav(Path("storage/test_tone.wav"))
    with open(wav, 'rb') as f:
        r = requests.post(BASE + "/media/upload", files={'file':(wav.name,f,'audio/wav')})
    print("UPLOAD", r.status_code, r.text)
    if r.status_code != 200:
        return
    media_id = r.json()["id"]
    # Transcript
    r = requests.get(f"{BASE}/media/{media_id}/transcript")
    print("TRANSCRIPT", r.status_code, len(r.text))
    # Summary
    r = requests.get(f"{BASE}/media/{media_id}/summary")
    print("SUMMARY", r.status_code)
    try:
        print(json.dumps(r.json(), indent=2)[:400])
    except Exception:
        print(r.text[:400])

if __name__ == "__main__":
    main()
