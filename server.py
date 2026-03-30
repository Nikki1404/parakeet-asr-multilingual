"""
Parakeet-TDT-0.6B-v3 Real-Time ASR Server
WebSocket server that receives raw PCM audio chunks and streams back transcriptions.
Uses VAD (Voice Activity Detection) + chunked NeMo inference for pseudo-streaming.
"""

import asyncio
import io
import logging
import tempfile
import time
import wave
from collections import deque

import numpy as np
import torch
import uvicorn
import webrtcvad
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
SAMPLE_RATE = 16_000          # Hz – model expects 16 kHz
FRAME_MS = 30                 # VAD frame size (10 / 20 / 30 ms)
FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000   # 480 samples per VAD frame
BYTES_PER_SAMPLE = 2          # int16

VAD_MODE = 3                  # 0–3, 3 = most aggressive noise rejection
SILENCE_TIMEOUT_MS = 700      # flush after this many ms of silence
SILENCE_FRAMES = SILENCE_TIMEOUT_MS // FRAME_MS  # number of silent frames before flush
MIN_CHUNK_MS = 300            # don't transcribe clips shorter than this
MAX_CHUNK_SEC = 28            # safety cap – model handles up to 24 min, keep well under

MODEL_NAME = "nvidia/parakeet-tdt-0.6b-v3"

# ── Model loading ─────────────────────────────────────────────────────────────
logger.info("Loading ASR model %s …", MODEL_NAME)
import nemo.collections.asr as nemo_asr  # noqa: E402 – heavy import after banner

asr_model = nemo_asr.models.ASRModel.from_pretrained(model_name=MODEL_NAME)
device = "cuda" if torch.cuda.is_available() else "cpu"
asr_model = asr_model.to(device)
asr_model.eval()
logger.info("Model ready on %s", device.upper())

app = FastAPI(title="Parakeet ASR", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def pcm_to_wav_bytes(pcm: bytes, sample_rate: int = SAMPLE_RATE) -> bytes:
    """Wrap raw int16 PCM bytes in a valid WAV container (in-memory)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(BYTES_PER_SAMPLE)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def transcribe_pcm(pcm: bytes) -> str:
    """Write PCM to a temp WAV file and run NeMo inference."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
        tmp.write(pcm_to_wav_bytes(pcm))
        tmp.flush()
        try:
            results = asr_model.transcribe([tmp.name])
            text = results[0].text if hasattr(results[0], "text") else str(results[0])
            return text.strip()
        except Exception as exc:
            logger.error("Transcription error: %s", exc)
            return ""


# ── WebSocket handler ─────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    client = ws.client
    logger.info("Client connected: %s:%s", client.host, client.port)

    vad = webrtcvad.Vad(VAD_MODE)

    # Ring buffer: accumulates *all* audio since last flush (speech + context)
    audio_buffer: deque[bytes] = deque()   # each element = one VAD frame (30 ms)
    speech_frames = 0
    silent_frames = 0
    in_speech = False

    async def flush_and_transcribe(label: str = ""):
        nonlocal audio_buffer, speech_frames, silent_frames, in_speech
        pcm = b"".join(audio_buffer)
        duration_ms = len(pcm) / BYTES_PER_SAMPLE / SAMPLE_RATE * 1000
        audio_buffer.clear()
        speech_frames = 0
        silent_frames = 0
        in_speech = False

        if duration_ms < MIN_CHUNK_MS:
            return  # too short – skip

        logger.info("[%s] Transcribing %.1f s …", label or client.host, duration_ms / 1000)
        t0 = time.perf_counter()
        # Run in thread pool so the event loop isn't blocked
        text = await asyncio.get_event_loop().run_in_executor(None, transcribe_pcm, pcm)
        elapsed = time.perf_counter() - t0

        if text:
            logger.info("[%.2fs] %s", elapsed, text)
            await ws.send_json({
                "type": "transcript",
                "text": text,
                "duration_ms": round(duration_ms),
                "rtf": round(elapsed / (duration_ms / 1000), 3),
            })

    try:
        remainder = b""  # leftover bytes that didn't fill a complete VAD frame

        while True:
            raw = await ws.receive_bytes()

            # Handle control message embedded as tiny JSON blob (< 8 bytes)
            # Real 30ms frame = 480 samples × 2 bytes = 960 bytes minimum
            if len(raw) < 10:
                # Could be a flush signal from client
                try:
                    import json
                    msg = json.loads(raw)
                    if msg.get("cmd") == "flush":
                        await flush_and_transcribe("manual-flush")
                except Exception:
                    pass
                continue

            # Accumulate bytes and split into exact VAD frames
            data = remainder + raw
            remainder = b""
            frame_bytes = FRAME_SAMPLES * BYTES_PER_SAMPLE  # 960

            offset = 0
            while offset + frame_bytes <= len(data):
                frame = data[offset: offset + frame_bytes]
                offset += frame_bytes

                # VAD decision
                try:
                    is_speech = vad.is_speech(frame, SAMPLE_RATE)
                except Exception:
                    is_speech = True  # if VAD fails, assume speech

                if is_speech:
                    speech_frames += 1
                    silent_frames = 0
                    in_speech = True
                    audio_buffer.append(frame)
                else:
                    silent_frames += 1
                    if in_speech:
                        # Keep trailing silence for natural endings
                        audio_buffer.append(frame)

                    if silent_frames >= SILENCE_FRAMES and in_speech:
                        await flush_and_transcribe("vad-silence")

                # Safety cap: flush if buffer grows too large
                total_samples = len(audio_buffer) * FRAME_SAMPLES
                if total_samples / SAMPLE_RATE >= MAX_CHUNK_SEC:
                    await flush_and_transcribe("max-length")

            remainder = data[offset:]

    except WebSocketDisconnect:
        logger.info("Client disconnected: %s:%s", client.host, client.port)
        # Flush any remaining audio
        if audio_buffer:
            await flush_and_transcribe("disconnect-flush")
    except Exception as exc:
        logger.error("Unexpected error: %s", exc, exc_info=True)
        await ws.close(code=1011)


@app.get("/health")
async def health():
    return {"status": "ok", "device": device, "model": MODEL_NAME}


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8765, log_level="info")
