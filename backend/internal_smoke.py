"""In-process smoke test (no external uvicorn needed).
Generates a test WAV, hits core endpoints, prints concise results.
Run:
  cd backend
  python internal_smoke.py
"""
from fastapi.testclient import TestClient
from app.main import app
from pathlib import Path
import wave, math, struct, io, json

client = TestClient(app)

def make_wav_bytes(dur=1.0, freq=440, fr=16000):
    n = int(fr*dur)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(fr)
        for i in range(n):
            val = int(16000*math.sin(2*math.pi*freq*i/fr))
            w.writeframes(struct.pack('<h', val))
    buf.seek(0)
    return buf

print('[1] ROOT')
r = client.get('/')
print(r.status_code, r.json())

print('[2] UPLOAD')
wav = make_wav_bytes()
files = {'file': ('tone.wav', wav, 'audio/wav')}
r = client.post('/media/upload', files=files)
print(r.status_code, r.text[:160])
if r.status_code != 200:
    raise SystemExit('Upload failed')
media_id = r.json()['id']

print('[3] TRANSCRIPT')
r = client.get(f'/media/{media_id}/transcript')
print(r.status_code, 'len=', len(r.text))

print('[4] SUMMARY')
r = client.get(f'/media/{media_id}/summary')
print(r.status_code)
try:
    data = r.json()
    print(json.dumps(data, indent=2)[:300])
except Exception:
    print(r.text[:300])

print('[5] SEARCH (query=tone)')
r = client.get(f'/media/{media_id}/search', params={'q':'tone'})
print(r.status_code, r.text[:160])

print('[DONE] All basic endpoint calls executed.')
