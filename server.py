"""
Parakeet-TDT-0.6B-v3 Real-Time ASR Server  (v3 – partial transcripts)
======================================================================
Message types sent to client:
  {"type": "partial",    "text": "...", "duration_ms": N}   – interim result while speaking
  {"type": "transcript", "text": "...", "duration_ms": N, "rtf": N}  – final on silence

Partial strategy:
  - While speech is active, run inference on the growing buffer every
    PARTIAL_INTERVAL_SEC seconds (runs in thread pool, non-blocking).
  - A lock prevents two inference jobs from running simultaneously.
  - On silence flush the full buffer is transcribed as final and partials reset.
"""

import asyncio
import io
import json
import logging
import os
import tempfile
import time
import wave
from collections import deque
from contextlib import asynccontextmanager
from typing import Deque, Optional

import torch
import uvicorn

try:
    import webrtcvad
except ImportError as exc:
    raise SystemExit(
        "webrtcvad not found. Install with: pip install webrtcvad-wheels"
    ) from exc

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
SAMPLE_RATE       = 16_000
FRAME_MS          = 30
FRAME_SAMPLES     = SAMPLE_RATE * FRAME_MS // 1000   # 480
BYTES_PER_SAMPLE  = 2

VAD_MODE           = 3
SILENCE_TIMEOUT_MS = 700
SILENCE_FRAMES     = SILENCE_TIMEOUT_MS // FRAME_MS
MIN_CHUNK_MS       = 300
MAX_CHUNK_SEC      = 28

# How often to emit a partial transcript while speech is ongoing (seconds)
PARTIAL_INTERVAL_SEC = 1.0

MODEL_NAME = "nvidia/parakeet-tdt-0.6b-v3"

# ── Model ─────────────────────────────────────────────────────────────────────
asr_model = None
device: str = "cpu"

# Global model lock: mandatory for NeMo RNNT/TDT repeated inference stability
MODEL_LOCK = asyncio.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global asr_model, device
    logger.info("Loading ASR model %s …", MODEL_NAME)
    import nemo.collections.asr as nemo_asr

    asr_model = nemo_asr.models.ASRModel.from_pretrained(model_name=MODEL_NAME)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    asr_model = asr_model.to(device)
    asr_model.eval()

    # Critical fix for repeated transcribe() stability
    try:
        asr_model.freeze()
        logger.info("Model frozen for inference stability")
    except Exception:
        logger.warning("Model freeze() not available or failed; continuing", exc_info=True)

    logger.info("Model ready on %s", device.upper())
    yield
    logger.info("Server shutting down.")


app = FastAPI(title="Parakeet ASR", version="3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def pcm_to_wav_bytes(pcm: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(BYTES_PER_SAMPLE)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm)
    return buf.getvalue()


def _extract_text(result) -> str:
    if hasattr(result, "text"):
        return result.text or ""
    return str(result)


def transcribe_pcm(pcm: bytes) -> str:
    """Synchronous NeMo inference — runs in executor thread."""
    tmp_path: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(pcm_to_wav_bytes(pcm))

        # Critical fix: safer inference context
        with torch.inference_mode():
            results = asr_model.transcribe([tmp_path])

        if not results:
            return ""
        return _extract_text(results[0]).strip()

    except Exception as exc:
        logger.error("Transcription error: %s", exc, exc_info=True)
        return ""

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                logger.warning("Failed to delete temp file: %s", tmp_path, exc_info=True)


# ── WebSocket handler ─────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    client = ws.client
    logger.info("Client connected: %s:%s", client.host, client.port)

    vad            = webrtcvad.Vad(VAD_MODE)
    loop           = asyncio.get_running_loop()

    # Keep connection-level lock too, but actual model safety uses global lock
    infer_lock     = asyncio.Lock()

    audio_buffer  : Deque[bytes] = deque()
    silent_frames : int  = 0
    in_speech     : bool = False
    last_partial  : float = 0.0
    closed        : bool = False

    # ── helpers ───────────────────────────────────────────────────────────

    async def safe_send_json(payload: dict) -> bool:
        nonlocal closed
        if closed:
            return False
        try:
            await ws.send_json(payload)
            return True
        except Exception:
            closed = True
            logger.info("WebSocket send failed; marking connection closed", exc_info=True)
            return False

    async def run_inference(pcm: bytes) -> str:
        """
        Run transcribe_pcm in thread pool.
        Uses both connection lock and global model lock.
        """
        async with infer_lock:
            async with MODEL_LOCK:
                return await loop.run_in_executor(None, transcribe_pcm, pcm)

    async def send_partial() -> None:
        """Transcribe current buffer and send a partial message (non-destructive)."""
        nonlocal last_partial, closed

        if closed:
            return

        # If either this connection or global model is busy, skip this partial
        if infer_lock.locked() or MODEL_LOCK.locked():
            return

        pcm = b"".join(audio_buffer)
        duration_ms = len(pcm) / BYTES_PER_SAMPLE / SAMPLE_RATE * 1000
        if duration_ms < MIN_CHUNK_MS:
            return

        last_partial = time.monotonic()
        text = await run_inference(pcm)
        if text and not closed:
            logger.debug("[partial] %s", text)
            await safe_send_json({
                "type":        "partial",
                "text":        text,
                "duration_ms": round(duration_ms),
            })

    async def flush_final(label: str = "") -> None:
        """Transcribe buffer as final, clear state, send transcript message."""
        nonlocal audio_buffer, silent_frames, in_speech, last_partial, closed

        pcm = b"".join(audio_buffer)
        duration_ms = len(pcm) / BYTES_PER_SAMPLE / SAMPLE_RATE * 1000

        audio_buffer.clear()
        silent_frames = 0
        in_speech     = False
        last_partial  = 0.0

        if duration_ms < MIN_CHUNK_MS:
            return

        logger.info("[%s] Final transcription %.2f s …", label or "flush", duration_ms / 1000)
        t0   = time.perf_counter()
        text = await run_inference(pcm)
        elapsed = time.perf_counter() - t0

        if text and not closed:
            rtf = elapsed / (duration_ms / 1000)
            logger.info("  → FINAL \"%s\"  [%.2fs RTF %.2fx]", text, elapsed, rtf)
            await safe_send_json({
                "type":        "transcript",
                "text":        text,
                "duration_ms": round(duration_ms),
                "rtf":         round(rtf, 3),
            })

    # ── main receive loop ─────────────────────────────────────────────────
    try:
        remainder   = b""
        frame_bytes = FRAME_SAMPLES * BYTES_PER_SAMPLE   # 960

        while True:
            # Safe receive: handles bytes/text/disconnect cleanly
            message = await ws.receive()

            msg_type = message.get("type")
            if msg_type == "websocket.disconnect":
                closed = True
                logger.info("Client disconnected: %s:%s", client.host, client.port)
                break

            raw = message.get("bytes")

            if raw is None:
                text_payload = message.get("text")
                if text_payload is not None:
                    raw = text_payload.encode()
                else:
                    continue

            # Control messages (JSON blobs, always shorter than a full frame)
            if len(raw) < frame_bytes:
                try:
                    msg = json.loads(raw)
                    if msg.get("cmd") == "flush":
                        await flush_final("manual-flush")
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
                continue

            # Audio frames
            data      = remainder + raw
            remainder = b""
            offset    = 0

            while offset + frame_bytes <= len(data):
                frame   = data[offset: offset + frame_bytes]
                offset += frame_bytes

                try:
                    is_speech = vad.is_speech(frame, SAMPLE_RATE)
                except Exception:
                    is_speech = True

                if is_speech:
                    silent_frames = 0
                    in_speech     = True
                    audio_buffer.append(frame)

                    # emit partial every PARTIAL_INTERVAL_SEC
                    now = time.monotonic()
                    if now - last_partial >= PARTIAL_INTERVAL_SEC:
                        asyncio.create_task(send_partial())

                else:
                    silent_frames += 1
                    if in_speech:
                        audio_buffer.append(frame)   # keep trailing silence

                    if in_speech and silent_frames >= SILENCE_FRAMES:
                        await flush_final("vad-silence")

                # Safety cap
                if len(audio_buffer) * FRAME_SAMPLES / SAMPLE_RATE >= MAX_CHUNK_SEC:
                    await flush_final("max-length")

            remainder = data[offset:]

    except WebSocketDisconnect:
        closed = True
        logger.info("Client disconnected: %s:%s", client.host, client.port)

    except Exception as exc:
        closed = True
        logger.error("Unexpected error: %s", exc, exc_info=True)
        try:
            await ws.close(code=1011)
        except Exception:
            pass

    finally:
        # Keep disconnect flush behavior, but never send after connection is closed
        if audio_buffer:
            try:
                pcm = b"".join(audio_buffer)
                duration_ms = len(pcm) / BYTES_PER_SAMPLE / SAMPLE_RATE * 1000
                if duration_ms >= MIN_CHUNK_MS:
                    logger.info("[disconnect-flush-local] Final transcription %.2f s …", duration_ms / 1000)
                    t0 = time.perf_counter()
                    text = await run_inference(pcm)
                    elapsed = time.perf_counter() - t0
                    if text:
                        rtf = elapsed / (duration_ms / 1000)
                        logger.info("  → FINAL \"%s\"  [%.2fs RTF %.2fx]", text, elapsed, rtf)
            except Exception:
                logger.warning("Disconnect flush inference failed", exc_info=True)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "model": MODEL_NAME, "device": device}


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, log_level="info")
