import json
from fastapi.testclient import TestClient
from app.main import app

def test_root():
    client = TestClient(app)
    r = client.get('/')
    assert r.status_code == 200
    assert 'Video-Audio Insight' in r.json().get('message','')

def test_upload_and_summary():
    client = TestClient(app)
    # generate small wav
    import io, wave, math, struct
    buf = io.BytesIO()
    fr=16000; dur=0.5; amp=12000; freq=440; n=int(fr*dur)
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(fr)
        for i in range(n):
            val=int(amp*math.sin(2*math.pi*freq*i/fr))
            w.writeframes(struct.pack('<h', val))
    buf.seek(0)
    r = client.post('/media/upload', files={'file':('tone.wav', buf, 'audio/wav')})
    assert r.status_code == 200, r.text
    media_id = r.json()['id']
    r_t = client.get(f'/media/{media_id}/transcript')
    assert r_t.status_code == 200
    r_s = client.get(f'/media/{media_id}/summary')
    assert r_s.status_code == 200
