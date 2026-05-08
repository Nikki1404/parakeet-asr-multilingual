| Provider | Phase       | Task                               | Description                                                                            | Observation / Comments                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Outcome                               | Owner   | Status    | Priority |
| -------- | ----------- | ---------------------------------- | -------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- | ------- | --------- | -------- |
| Azure    | Setup       | ASR Config Finalization            | Lock language/locale, audio format (telephony/app), disable unnecessary auto-detection | Tested multiple combinations of locale locking, audio formats, and auto-detect configurations. Stable improvements observed when language auto-detection was restricted only to required languages (`en-US`, `es-ES`) instead of broad detection. WAV PCM 16kHz mono produced consistently better transcripts compared to MP3 direct ingestion. Disabling unnecessary detection logic reduced random word substitutions and improved transcript stability in noisy segments. | Stable, predictable recognition       | AI Team | Completed | High     |
| Azure    | Setup       | Concurrency & Quota Validation     | Validate concurrency limits, rate limits, and quotas                                   | Multiple concurrent transcription sessions were executed to identify Azure throttling thresholds. No major throttling observed within expected production load range. Minor latency spikes appeared during burst traffic scenarios. Recommended production limit and retry logic documented.                                                                                                                                                                                 | No runtime throttling                 | AI Team | Completed | High     |
| Azure    | Integration | Real-Time Socket Integration       | Implement and validate WebSocket/streaming ingestion                                   | Streaming mode was benchmarked against batch/offline mode. Real-time socket ingestion significantly improved conversational responsiveness and enabled lower perceived latency. Partial transcript stability depended heavily on chunk size and endpointing configuration. 20–30 ms chunk streaming provided best balance between responsiveness and transcript consistency.                                                                                                 | Low-latency real-time ASR             | AI Team | Completed | High     |
| Azure    | Audio       | VAD Evaluation & Tuning            | Evaluate built-in VAD behavior; tune sensitivity, silence thresholds, and endpointing  | Multiple silence timeout values (`300ms`, `500ms`, `800ms`, `1200ms`) were tested incrementally. Lower silence thresholds improved responsiveness but caused aggressive cut-offs and partial truncation. Higher thresholds reduced truncation but increased response latency. Best production balance observed around `700–900ms`. Noise-heavy audio and short-word scenarios particularly benefited from tuned endpointing.                                                 | Reduced truncation and false cut-offs | AI Team | Completed | High     |
| Azure    | Accuracy    | Word / Phrase Boosting             | Boost digits, identifiers, domain terms                                                | Phrase boosting significantly improved recognition of domain-specific terms, identifiers, numeric sequences, acronyms, and uncommon vocabulary. Multiple phrase-list weights were tested incrementally. Over-aggressive boosting occasionally introduced incorrect forced substitutions; moderate phrase weighting produced the most stable improvement. Numeric recognition improvement was especially noticeable for account numbers and identifiers.                      | Improved numeric accuracy             | AI Team | Completed | High     |
| Azure    | Accuracy    | Transcript-Based Vocabulary Tuning | Use sample transcripts to refine vocabulary/style boosting                             | Historical transcripts were analyzed to identify commonly misrecognized words and recurring terminology. Adding these domain-specific phrases into vocabulary tuning reduced repeated recognition errors across multiple test runs. Significant improvement observed for repeated organization names, technical terminology, and accented pronunciations.                                                                                                                    | Domain alignment                      | AI Team | Completed | High     |
| Azure    | Logic       | Numeric Handling Validation        | Validate digit-by-digit vs grouped digit behavior                                      | Extensive testing performed for numeric phrases, account numbers, identifiers, grouped digits, and contextual numeric speech. Validation logic was intentionally restricted to avoid unsafe conversions such as `"to"` → `2`. Spanish numeric phrases were preserved in lexical form without forced digit conversion. Context-aware validation improved downstream verification reliability without modifying original spoken transcript text.                               | Reduced verification failures         | AI Team | Completed | High     |
| Azure    | Quality     | Emotion / Tone Evaluation          | Assess ASR behavior under neutral vs stressed speech                                   | Recognition accuracy was evaluated across calm, fast, stressed, emotional, and noisy speech patterns. Elevated speaking speed and emotional tone introduced more partial instability and short-word drops. VAD tuning and phrase boosting partially mitigated these issues. Neutral speech consistently produced highest transcript stability.                                                                                                                               | Robust recognition                    | AI Team | Completed | High     |
| Azure    | Testing     | Latency & Timeout Testing          | Validate response times within conversational SLA                                      | TTFT (partial/final), end-to-end latency, and endpointing delays were benchmarked under multiple configurations. Aggressive endpointing reduced TTFT but increased truncation risk. Best conversational balance achieved using moderate silence thresholds with streaming enabled. Production SLA targets were achieved under standard network conditions.                                                                                                                   | Smooth turn-taking                    | AI Team | Completed | High     |
| Azure    | Testing     | Load & Concurrency Testing         | Validate peak concurrent real-time streams                                             | Simulated concurrent streaming sessions were executed to observe scalability behavior. System remained stable under expected load conditions with acceptable latency degradation. High concurrency mainly impacted partial response latency rather than final transcript quality. Recommended production scaling thresholds documented.                                                                                                                                      | Stable under load                     | AI Team | Completed | High     |
| Azure    | Monitoring  | Logging & Alerts Setup             | Enable error, latency, socket-drop monitoring                                          | Detailed logging was enabled for latency metrics, socket disconnects, cancellations, endpointing behavior, and recognition errors. Structured JSON logs improved troubleshooting visibility. Monitoring configuration successfully detected intermittent socket instability and long-response scenarios during testing.                                                                                                                                                      | Early issue detection                 | AI Team | Completed | High     |
| Azure    | Go-Live     | Fallback Validation                | Test re-prompt / DTMF / alternate flow                                                 | Failure scenarios including silence, low-confidence transcripts, disconnects, and recognition failures were validated. Fallback prompts and alternate handling flows reduced complete interaction failure cases. DTMF and retry mechanisms improved resilience during low-confidence recognition situations.                                                                                                                                                                 | Resilient failure handling            | AI Team | Completed | High     |




"""
Parakeet ASR – Terminal Microphone / File Streaming Client
"""

import argparse
import asyncio
import json
import logging
import sys
import threading
import time
from pathlib import Path
from queue import Empty, Queue
from typing import List, Optional

import numpy as np
import pyaudio
import websockets

# =============================================================================
# CONFIG
# =============================================================================

# CHANGE ONLY THIS WHEN SERVER CHANGES
WS_URL = "wss://cx-asr.exlservice.com/asr/ml/ws"

SAMPLE_RATE = 16_000
CHANNELS = 1
FORMAT = pyaudio.paInt16

CHUNK_MS = 30
CHUNK_SAMPLES = SAMPLE_RATE * CHUNK_MS // 1000
CHUNK_BYTES = CHUNK_SAMPLES * 2

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

BANNER = rf"""
╔══════════════════════════════════════════════════════════════╗
║        Parakeet-TDT-0.6B-v3  |  Real-Time ASR Client        ║
║          Auto language detection (EN / ES / more)           ║
║            WebSocket: {WS_URL[:52]:<52}║
╚══════════════════════════════════════════════════════════════╝
"""

HELP = """
Commands
  q         Quit
  d         List available audio input devices

Notes
  - Partial transcripts are shown while speaking.
  - Final transcript arrives after endpointing on the server.
"""

# =============================================================================
# AUDIO CAPTURE
# =============================================================================

class MicCapture:

    def __init__(self, device_index: Optional[int] = None):
        self.queue: Queue[bytes] = Queue(maxsize=512)
        self._stop = threading.Event()
        self._device = device_index
        self._thread = threading.Thread(target=self._capture, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _capture(self):

        pa = pyaudio.PyAudio()
        stream = None

        try:
            stream = pa.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                input_device_index=self._device,
                frames_per_buffer=CHUNK_SAMPLES,
            )

            while not self._stop.is_set():
                data = stream.read(
                    CHUNK_SAMPLES,
                    exception_on_overflow=False,
                )
                self.queue.put(data)

        except OSError as exc:
            print(f"\n[ERROR] Audio capture failed: {exc}", file=sys.stderr)
            self._stop.set()

        finally:
            try:
                if stream is not None:
                    stream.stop_stream()
                    stream.close()
            except Exception:
                pass

            pa.terminate()


def list_devices():

    pa = pyaudio.PyAudio()

    print("\nAvailable audio input devices:")

    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)

        if info["maxInputChannels"] > 0:
            print(
                f"  [{i}] {info['name']}  "
                f"({int(info['defaultSampleRate'])} Hz)"
            )

    pa.terminate()
    print()

# =============================================================================
# AUDIO LOADING
# =============================================================================

def load_audio_as_16k_pcm(path: str) -> bytes:

    try:
        import soundfile as sf

        data, sr = sf.read(
            path,
            dtype="float32",
            always_2d=False,
        )

        if data.ndim == 2:
            data = data.mean(axis=1)

        if sr != SAMPLE_RATE:
            data = _resample(data, sr, SAMPLE_RATE)

        return _float32_to_pcm16(data)

    except Exception as sf_err:

        try:
            from pydub import AudioSegment

            seg = AudioSegment.from_file(path)
            seg = seg.set_channels(1)
            seg = seg.set_frame_rate(SAMPLE_RATE)
            seg = seg.set_sample_width(2)

            return seg.raw_data

        except Exception as pd_err:

            raise RuntimeError(
                f"Cannot load '{path}'.\n"
                f"soundfile : {sf_err}\n"
                f"pydub     : {pd_err}\n"
                f"Tip: install ffmpeg."
            )


def _resample(data: np.ndarray, orig_sr: int, target_sr: int):

    try:
        import librosa

        return librosa.resample(
            data,
            orig_sr=orig_sr,
            target_sr=target_sr,
        )

    except ImportError:
        pass

    try:
        from scipy.signal import resample_poly
        from math import gcd

        g = gcd(orig_sr, target_sr)

        return resample_poly(
            data,
            target_sr // g,
            orig_sr // g,
        ).astype(np.float32)

    except ImportError:
        pass

    duration = len(data) / orig_sr

    old_times = np.linspace(
        0,
        duration,
        len(data),
        endpoint=False,
    )

    new_len = int(duration * target_sr)

    new_times = np.linspace(
        0,
        duration,
        new_len,
        endpoint=False,
    )

    return np.interp(
        new_times,
        old_times,
        data,
    ).astype(np.float32)


def _float32_to_pcm16(data: np.ndarray) -> bytes:

    return (
        np.clip(data, -1.0, 1.0) * 32767
    ).astype(np.int16).tobytes()

# =============================================================================
# RECEIVER
# =============================================================================

async def _receiver(ws):

    last_partial = ""

    try:
        async for raw in ws:

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")
            text = msg.get("text", "")
            t_start = msg.get("t_start")

            ts = time.strftime("%H:%M:%S")

            if msg_type == "partial":

                last_partial = text

                if t_start is not None:
                    print(
                        f"\r  ⏳ [{ts}] ({t_start} ms) {text:<100}",
                        end="",
                        flush=True,
                    )
                else:
                    print(
                        f"\r  ⏳ [{ts}] {text:<100}",
                        end="",
                        flush=True,
                    )

            elif msg_type == "transcript":

                print(f"\r{' ' * 140}\r", end="")

                if t_start is not None:
                    print(f"[{ts}] Final | first partial at {t_start} ms")
                else:
                    print(f"[{ts}] Final")

                print(f"  ✅  {text}")
                print("─" * 72)

                last_partial = ""

    except websockets.exceptions.ConnectionClosed:

        if last_partial:
            print()

        print("[Connection closed]")

# =============================================================================
# STDIN READER
# =============================================================================

def stdin_reader(cmd_queue: Queue):

    while True:
        try:
            line = sys.stdin.readline()

            if line:
                cmd_queue.put(line.strip())

        except Exception:
            break

# =============================================================================
# MIC MODE
# =============================================================================

async def run_mic(device_index: Optional[int]):

    uri = WS_URL

    print(BANNER)
    print(f"Connecting to {uri} …", end=" ", flush=True)

    try:
        async with websockets.connect(
            uri,
            ping_interval=20,
            ping_timeout=20,
            max_size=2**23,
        ) as ws:

            print("connected ✓\n")

            print("🎙  Speak now – transcriptions appear below\n")
            print("─" * 72)

            mic = MicCapture(device_index)
            mic.start()

            cmd_queue: Queue[str] = Queue()

            threading.Thread(
                target=stdin_reader,
                args=(cmd_queue,),
                daemon=True,
            ).start()

            send_task = asyncio.create_task(
                _mic_sender(ws, mic, cmd_queue)
            )

            recv_task = asyncio.create_task(
                _receiver(ws)
            )

            done, pending = await asyncio.wait(
                [send_task, recv_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

            mic.stop()

    except (OSError, websockets.exceptions.WebSocketException) as exc:

        print(f"failed ✗\n[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)


async def _mic_sender(ws, mic: MicCapture, cmd_queue: Queue):

    print(HELP)

    try:
        while True:

            try:
                cmd = cmd_queue.get_nowait()

                if cmd.lower() in ("q", "quit", "exit"):
                    print("\nBye!")
                    return

                elif cmd.lower() == "d":
                    print()
                    list_devices()

            except Empty:
                pass

            sent = 0

            while not mic.queue.empty() and sent < 50:
                frame = mic.queue.get_nowait()
                await ws.send(frame)
                sent += 1

            await asyncio.sleep(0.005)

    except websockets.exceptions.ConnectionClosed:
        print("\n[Connection closed by server]")

# =============================================================================
# FILE MODE
# =============================================================================

async def run_files(files: List[str], speed: float):

    uri = WS_URL

    print(BANNER)

    print(f"  Mode   : FILE streaming at {speed:.1f}×")
    print(f"  Server : {uri}")
    print(f"  Files  : {', '.join(Path(f).name for f in files)}\n")

    for filepath in files:

        p = Path(filepath)

        if not p.exists():
            print(f"  [SKIP] File not found: {filepath}\n")
            continue

        print(f"  Loading {p.name} …", end=" ", flush=True)

        try:
            pcm = load_audio_as_16k_pcm(str(p))
        except RuntimeError as exc:
            print(f"FAILED ✗\n  {exc}\n")
            continue

        duration_sec = len(pcm) / 2 / SAMPLE_RATE

        print(f"{duration_sec:.1f}s ✓")

        print(f"\n{'═' * 72}")
        print(f"  📄 {p.name} ({duration_sec:.1f}s)")
        print(f"{'═' * 72}\n")

        try:
            async with websockets.connect(
                uri,
                ping_interval=20,
                ping_timeout=20,
                max_size=2**23,
            ) as ws:

                recv_task = asyncio.create_task(
                    _receiver(ws)
                )

                await _file_sender(ws, pcm, speed)

                await asyncio.sleep(3.0)

                await ws.close()

                await asyncio.sleep(0.2)

                if not recv_task.done():
                    recv_task.cancel()

        except (OSError, websockets.exceptions.WebSocketException) as exc:
            print(f"\n[ERROR] WebSocket failed: {exc}")

        print()

    print("All files processed.")

# =============================================================================
# FILE SENDER
# =============================================================================

async def _file_sender(ws, pcm: bytes, speed: float):

    if speed <= 0:
        raise ValueError("--speed must be > 0")

    chunk_delay = (CHUNK_MS / 1000.0) / speed

    offset = 0

    while offset + CHUNK_BYTES <= len(pcm):

        chunk = pcm[offset: offset + CHUNK_BYTES]

        offset += CHUNK_BYTES

        await ws.send(chunk)

        await asyncio.sleep(chunk_delay)

    leftover = pcm[offset:]

    if leftover:
        await ws.send(
            leftover + bytes(CHUNK_BYTES - len(leftover))
        )

# =============================================================================
# CLI
# =============================================================================

def parse_args():

    parser = argparse.ArgumentParser(
        description="Parakeet ASR client"
    )

    parser.add_argument(
        "--device",
        type=int,
        default=None,
        metavar="INDEX",
        help="Mic device index",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List audio devices",
    )

    parser.add_argument(
        "--file",
        nargs="+",
        metavar="FILE",
        help="Audio file(s)",
    )

    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Playback speed",
    )

    return parser.parse_args()

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":

    args = parse_args()

    if args.list:
        list_devices()
        sys.exit(0)

    if args.file:
        asyncio.run(run_files(args.file, args.speed))
    else:
        asyncio.run(run_mic(args.device))
