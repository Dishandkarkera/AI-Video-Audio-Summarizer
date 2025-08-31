import os, tempfile, time, asyncio, json
import threading
from typing import Callable, Optional
from concurrent.futures import ThreadPoolExecutor
from .whisper_service import get_model


class RealtimeTranscriber:
    """Naive pseudo-streaming wrapper around Whisper.

    Strategy: accumulate compressed audio bytes (e.g. webm/opus) as received.
    Throttle decoding (default every 2s) by writing current buffer to a temp file,
    invoking Whisper transcription on the full audio so far, and diffing from the
    previous emitted text. This is NOT low-latency token streaming, but provides
    incremental partials without waiting for full upload.
    """

    def __init__(self, decode_interval: float = 2.0):
        self.buffer = bytearray()
        self.last_emit_text = ""
        self.last_decode_time = 0.0
        self.decode_interval = decode_interval
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._closing = False

    def add_chunk(self, data: bytes):
        with self._lock:
            self.buffer.extend(data)

    async def maybe_decode(self, send_cb: Callable[[dict], asyncio.Future]):
        now = time.time()
        if now - self.last_decode_time < self.decode_interval:
            return
        with self._lock:
            data = bytes(self.buffer)
        if len(data) < 4000:  # wait for some audio (~few KB)
            return
        self.last_decode_time = now
        loop = asyncio.get_event_loop()
        try:
            text, segments = await loop.run_in_executor(self._executor, self._decode_bytes, data)
        except Exception as e:
            await send_cb({"type": "error", "message": f"decode_failed: {e}"})
            return
        if not text:
            return
        # diff
        if text.startswith(self.last_emit_text):
            new_text = text[len(self.last_emit_text):]
        else:
            new_text = text
        if new_text.strip():
            self.last_emit_text = text
            await send_cb({"type": "partial", "text": text, "delta": new_text, "segments": segments[-5:] if segments else []})

    def _decode_bytes(self, data: bytes):
        # Persist current buffer to a temporary file and run Whisper.
        # We assume data is webm/opus. We'll write to .webm and rely on ffmpeg (installed by whisper dependency) for decode.
        model = get_model()
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=True) as tmp:
            tmp.write(data)
            tmp.flush()
            result = model.transcribe(tmp.name, verbose=False)
        segments = []
        for seg in result.get('segments', []):
            segments.append({
                'start': seg.get('start'),
                'end': seg.get('end'),
                'text': seg.get('text')
            })
        return result.get('text'), segments

    async def finalize(self, send_cb: Callable[[dict], asyncio.Future]):
        if self._closing:
            return
        self._closing = True
        with self._lock:
            data = bytes(self.buffer)
        if not data:
            await send_cb({"type": "final", "text": self.last_emit_text})
            return
        loop = asyncio.get_event_loop()
        try:
            text, segments = await loop.run_in_executor(self._executor, self._decode_bytes, data)
        except Exception as e:
            await send_cb({"type": "error", "message": f"finalize_failed: {e}"})
            return
        self.last_emit_text = text or self.last_emit_text
        await send_cb({"type": "final", "text": self.last_emit_text, "segments": segments})
