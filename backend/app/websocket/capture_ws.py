import asyncio
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from app.db.database import get_db
from app.models.media import Media

# whisper import - ensure whisper and torch are installed
import whisper

router = APIRouter()
ROOT = Path(__file__).parent.parent
REALTIMED_DIR = ROOT / "realtime_temp"
REALTIMED_DIR.mkdir(parents=True, exist_ok=True)

# Load Whisper model once at module load (choose small/base for speed)
# NOTE: change model name depending on available RAM/CPU/GPU
WHISPER_MODEL = whisper.load_model("small")


class SessionState:
    def __init__(self, session_id: str, ws: WebSocket, buffer_seconds: float = 4.0, debug: bool = False):
        self.id = session_id
        self.ws = ws
        self.dir = REALTIMED_DIR / session_id
        self.dir.mkdir(exist_ok=True, parents=True)
        self.seq = 0
        self.buffer_seconds = buffer_seconds
        self.pending_blobs = []
        self.transcribe_task: Optional[asyncio.Task] = None
        self.running = True
        self.last_full_transcript = ""
        self.debug = debug

    def push_blob(self, blob_path: Path):
        self.pending_blobs.append(str(blob_path))

    def pop_all_pending(self):
        items = list(self.pending_blobs)
        self.pending_blobs.clear()
        return items

    def cleanup(self):
        try:
            shutil.rmtree(self.dir)
        except Exception:
            pass


SESSIONS: Dict[str, SessionState] = {}
RATE_LIMIT: Dict[str, int] = {}
MAX_SESSIONS_PER_IP = 5


async def convert_and_transcribe(session: SessionState, files: list):
    if not files:
        return

    wavs = []
    for idx, f in enumerate(files):
        in_path = Path(f)
        wav_out = session.dir / f"chunk_{session.seq}_{idx}.wav"
        cmd = [
            "ffmpeg", "-y", "-i", str(in_path),
            "-ar", "16000", "-ac", "1",
            str(wav_out)
        ]
        try:
            stderr = subprocess.DEVNULL if not session.debug else None
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=stderr)
            wavs.append(str(wav_out))
        except subprocess.CalledProcessError:
            continue

    if not wavs:
        return

    list_txt = session.dir / f"wavlist_{session.seq}.txt"
    with open(list_txt, "w") as fh:
        for w in wavs:
            fh.write(f"file '{w}'\n")

    merged_wav = session.dir / f"merged_{session.seq}.wav"
    try:
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_txt),
            "-c", "copy", str(merged_wav)
        ]
        stderr = subprocess.DEVNULL if not session.debug else None
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=stderr)
    except subprocess.CalledProcessError:
        merged_wav = Path(wavs[-1])

    if session.debug:
        try:
            import wave, audioop
            with wave.open(str(merged_wav), 'rb') as wf:
                frames = wf.readframes(wf.getnframes())
                rms = audioop.rms(frames, wf.getsampwidth()) if frames else 0
                await session.ws.send_text(json.dumps({
                    "type": "debug", "message": "merged wav stats", "rms": rms, "frames": wf.getnframes(),
                    "channels": wf.getnchannels(), "rate": wf.getframerate()
                }))
        except Exception as e:
            await session.ws.send_text(json.dumps({"type": "debug", "message": f"rms failed: {e}"}))

    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, lambda: WHISPER_MODEL.transcribe(str(merged_wav), language=None, verbose=False))
    except Exception as e:
        await session.ws.send_text(json.dumps({"type": "error", "message": f"transcription failed: {str(e)}"}))
        session.seq += 1
        return

    text = result.get("text", "")
    segments = result.get("segments", [])
    payload = {"type": "partial", "text": text, "segments": segments}
    await session.ws.send_text(json.dumps(payload))

    session.last_full_transcript += " " + text
    session.seq += 1

    for p in wavs:
        try:
            os.remove(p)
        except Exception:
            pass
    try:
        os.remove(list_txt)
    except Exception:
        pass
    try:
        if merged_wav.exists():
            os.remove(merged_wav)
    except Exception:
        pass


async def session_worker(session: SessionState):
    try:
        while session.running:
            await asyncio.sleep(session.buffer_seconds)
            pending = session.pop_all_pending()
            if pending:
                await convert_and_transcribe(session, pending)
        await session.ws.send_text(json.dumps({"type": "final", "text": session.last_full_transcript}))
    except WebSocketDisconnect:
        session.running = False
    except Exception as e:
        try:
            await session.ws.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass
    finally:
        session.cleanup()


@router.websocket("/v1/ws/capture")
async def ws_capture(websocket: WebSocket, db: AsyncSession = Depends(get_db), user_id: int | None = Query(default=None), debug: bool = Query(default=False)):
    await websocket.accept()
    client_ip = websocket.client.host if websocket.client else 'unknown'
    RATE_LIMIT[client_ip] = RATE_LIMIT.get(client_ip, 0) + 1
    if RATE_LIMIT[client_ip] > MAX_SESSIONS_PER_IP:
        await websocket.send_text(json.dumps({"type": "error", "message": "rate limit exceeded"}))
        await websocket.close()
        RATE_LIMIT[client_ip] -= 1
        return
    session: Optional[SessionState] = None
    try:
        while True:
            message = await websocket.receive()
            if "text" in message and message["text"] is not None:
                try:
                    data = json.loads(message["text"])
                except json.JSONDecodeError:
                    continue
                t = data.get("type")
                if t == "start":
                    sid = data.get("session_id") or str(uuid.uuid4())
                    session = SessionState(sid, websocket, buffer_seconds=data.get("buffer_seconds", 4.0), debug=debug or data.get("debug", False))
                    SESSIONS[sid] = session
                    session.transcribe_task = asyncio.create_task(session_worker(session))
                    await websocket.send_text(json.dumps({"type": "started", "session_id": sid}))
                elif t == "stop":
                    if session:
                        session.running = False
                        await websocket.send_text(json.dumps({"type": "stopping"}))
                    else:
                        await websocket.send_text(json.dumps({"type":"error", "message":"no session"}))
                else:
                    await websocket.send_text(json.dumps({"type":"info", "message":"unknown control"}))

            elif "bytes" in message and message["bytes"] is not None:
                if not session:
                    await websocket.send_text(json.dumps({"type":"error", "message":"no active session. send start control"}))
                    continue
                data = message["bytes"]
                blob_path = session.dir / f"chunk_{session.seq}_{len(session.pending_blobs)}.webm"
                with open(blob_path, "wb") as f:
                    f.write(data)
                session.push_blob(blob_path)
                await websocket.send_text(json.dumps({"type":"ack", "file": str(blob_path.name)}))

            elif "type" in message and message["type"] == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        if session:
            session.running = False
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass
    finally:
        if session:
            session.running = False
            if session.transcribe_task:
                session.transcribe_task.cancel()
            full_text = session.last_full_transcript.strip()
            if full_text:
                try:
                    media_stmt = insert(Media).values(
                        filename=f"realtime_session_{session.id}.live",
                        original_name="Live Capture",
                        content_type="audio/webm",
                        status="transcribed",
                        transcript=full_text,
                        user_id=user_id
                    )
                    await db.execute(media_stmt)
                    await db.commit()
                except Exception:
                    pass
            try:
                del SESSIONS[session.id]
            except Exception:
                pass
    RATE_LIMIT[client_ip] = max(RATE_LIMIT.get(client_ip,1)-1, 0)