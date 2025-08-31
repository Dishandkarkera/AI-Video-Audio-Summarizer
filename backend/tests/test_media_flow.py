import json, io, wave, math, struct, pytest

@pytest.mark.anyio
async def test_upload_and_summary(client):
    # generate 0.5s tone
    fr=16000; dur=0.5; n=int(fr*dur)
    buf=io.BytesIO()
    with wave.open(buf,'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(fr)
        for i in range(n):
            val=int(10000*math.sin(2*math.pi*440*i/fr))
            w.writeframes(struct.pack('<h', val))
    buf.seek(0)
    files={'file':('tone.wav', buf, 'audio/wav')}
    r = await client.post('/media/upload', files=files)
    assert r.status_code==200, r.text
    media_id = r.json()['id']
    r2 = await client.get(f'/media/{media_id}/transcript')
    assert r2.status_code==200
    r3 = await client.get(f'/media/{media_id}/summary')
    assert r3.status_code==200
