"""
Parakeet-TDT-0.6B-v3 Real-Time ASR Server
WebSocket server that receives raw PCM audio chunks and streams back transcriptions.
Uses VAD (Voice Activity Detection) + chunked NeMo inference for pseudo-streaming.

Fixes vs v1:
  - webrtcvad imported via webrtcvad-wheels (same namespace, explicit try/fallback)
  - Python 3.10-safe type hints (no X | Y union syntax)
  - json imported at top level (not inside hot loop)
  - asyncio.get_event_loop() → asyncio.get_running_loop() (deprecation fix)
  - NamedTemporaryFile delete=False + manual cleanup (avoids Windows/NeMo race)
  - Robust result unpacking for NeMo Hypothesis / plain string returns
  - Startup/shutdown lifespan events (FastAPI best practice)
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

# webrtcvad-wheels installs under the same 'webrtcvad' namespace
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
SAMPLE_RATE      = 16_000   # Hz  – parakeet-tdt expects 16 kHz mono
FRAME_MS         = 30       # VAD frame size must be 10 / 20 / 30 ms
FRAME_SAMPLES    = SAMPLE_RATE * FRAME_MS // 1000   # 480 samples
BYTES_PER_SAMPLE = 2        # int16 LE

VAD_MODE          = 3       # 0–3; 3 = most aggressive noise rejection
SILENCE_TIMEOUT_MS = 700    # ms of silence before flushing the buffer
SILENCE_FRAMES    = SILENCE_TIMEOUT_MS // FRAME_MS   # 23 frames
MIN_CHUNK_MS      = 300     # skip clips shorter than this (noise burst)
MAX_CHUNK_SEC     = 28      # hard cap; model supports up to ~24 min

MODEL_NAME = "nvidia/parakeet-tdt-0.6b-v3"

# ── Model (loaded once at startup) ───────────────────────────────────────────
asr_model = None
device: str = "cpu"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global asr_model, device
    logger.info("Loading ASR model %s …", MODEL_NAME)
    import nemo.collections.asr as nemo_asr  # heavy import – keep inside lifespan

    asr_model = nemo_asr.models.ASRModel.from_pretrained(model_name=MODEL_NAME)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    asr_model = asr_model.to(device)
    asr_model.eval()
    logger.info("Model ready on %s", device.upper())
    yield
    # Teardown (nothing needed for NeMo)
    logger.info("Server shutting down.")


app = FastAPI(title="Parakeet ASR", version="2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def pcm_to_wav_bytes(pcm: bytes, sample_rate: int = SAMPLE_RATE) -> bytes:
    """Wrap raw int16 PCM in a WAV container (in-memory)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(BYTES_PER_SAMPLE)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def _extract_text(result) -> str:
    """
    NeMo returns different types depending on version:
      - nemo >= 1.18: Hypothesis object with .text attribute
      - older: plain string
    """
    if hasattr(result, "text"):
        return result.text or ""
    return str(result)


def transcribe_pcm(pcm: bytes) -> str:
    """
    Write PCM to a temp WAV file and run NeMo inference.
    Uses delete=False + manual unlink to avoid race conditions on Linux
    when NeMo re-opens the file by path.
    """
    tmp_path: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(pcm_to_wav_bytes(pcm))

        results = asr_model.transcribe([tmp_path])
        if not results:
            return ""
        return _extract_text(results[0]).strip()

    except Exception as exc:
        logger.error("Transcription error: %s", exc, exc_info=True)
        return ""
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ── WebSocket handler ─────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    client = ws.client
    logger.info("Client connected: %s:%s", client.host, client.port)

    vad = webrtcvad.Vad(VAD_MODE)

    audio_buffer: Deque[bytes] = deque()  # one entry = one 30 ms VAD frame
    silent_frames: int = 0
    in_speech: bool = False

    async def flush_and_transcribe(label: str = "") -> None:
        nonlocal audio_buffer, silent_frames, in_speech

        pcm = b"".join(audio_buffer)
        duration_ms = len(pcm) / BYTES_PER_SAMPLE / SAMPLE_RATE * 1000
        audio_buffer.clear()
        silent_frames = 0
        in_speech = False

        if duration_ms < MIN_CHUNK_MS:
            logger.debug("Skipping %.0f ms clip (too short)", duration_ms)
            return

        logger.info("[%s] Transcribing %.2f s …", label or "flush", duration_ms / 1000)
        t0 = time.perf_counter()

        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, transcribe_pcm, pcm)

        elapsed = time.perf_counter() - t0

        if text:
            rtf = elapsed / (duration_ms / 1000)
            logger.info("  → \"%s\"  [%.2fs, RTF %.2fx]", text, elapsed, rtf)
            await ws.send_json({
                "type":        "transcript",
                "text":        text,
                "duration_ms": round(duration_ms),
                "rtf":         round(rtf, 3),
            })

    # ── Main receive loop ──────────────────────────────────────────────────
    try:
        remainder = b""
        frame_bytes = FRAME_SAMPLES * BYTES_PER_SAMPLE  # 960

        while True:
            raw = await ws.receive_bytes()

            # ── Control messages (sent as JSON, always < frame_bytes) ──────
            if len(raw) < frame_bytes:
                try:
                    msg = json.loads(raw)
                    if msg.get("cmd") == "flush":
                        await flush_and_transcribe("manual-flush")
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass  # not JSON – ignore tiny incomplete frames
                continue

            # ── Audio frames ──────────────────────────────────────────────
            data = remainder + raw
            remainder = b""
            offset = 0

            while offset + frame_bytes <= len(data):
                frame = data[offset: offset + frame_bytes]
                offset += frame_bytes

                try:
                    is_speech = vad.is_speech(frame, SAMPLE_RATE)
                except Exception:
                    is_speech = True   # VAD error → assume speech

                if is_speech:
                    silent_frames = 0
                    in_speech = True
                    audio_buffer.append(frame)
                else:
                    silent_frames += 1
                    if in_speech:
                        audio_buffer.append(frame)   # keep trailing silence

                    if in_speech and silent_frames >= SILENCE_FRAMES:
                        await flush_and_transcribe("vad-silence")

                # Safety cap
                buffered_secs = len(audio_buffer) * FRAME_SAMPLES / SAMPLE_RATE
                if buffered_secs >= MAX_CHUNK_SEC:
                    await flush_and_transcribe("max-length")

            remainder = data[offset:]

    except WebSocketDisconnect:
        logger.info("Client disconnected: %s:%s", client.host, client.port)
        if audio_buffer:
            await flush_and_transcribe("disconnect-flush")

    except Exception as exc:
        logger.error("Unexpected WebSocket error: %s", exc, exc_info=True)
        try:
            await ws.close(code=1011)
        except Exception:
            pass


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model":  MODEL_NAME,
        "device": device,
    }


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8001, log_level="info")
