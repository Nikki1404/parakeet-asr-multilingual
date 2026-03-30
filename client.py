"""
Parakeet ASR – Terminal Microphone Client
Captures microphone audio, sends it to the WebSocket server in real time,
and prints transcriptions as they arrive. Works for English & Spanish
(parakeet-tdt-0.6b-v3 auto-detects the language).

Usage:
    python client.py [--host HOST] [--port PORT] [--device DEVICE_INDEX]

Dependencies:
    pip install pyaudio websockets
"""

import argparse
import asyncio
import json
import logging
import sys
import threading
import time
from queue import Empty, Queue
from typing import Optional

import pyaudio
import websockets

# ── Config ────────────────────────────────────────────────────────────────────
SAMPLE_RATE = 16_000
CHANNELS = 1
FORMAT = pyaudio.paInt16
CHUNK_MS = 30                          # send 30 ms frames – matches server VAD
CHUNK_SAMPLES = SAMPLE_RATE * CHUNK_MS // 1000   # 480 samples
CHUNK_BYTES = CHUNK_SAMPLES * 2        # int16 → 2 bytes per sample

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║        Parakeet-TDT-0.6B-v3  |  Real-Time ASR Client        ║
║          English & Spanish auto-detection                    ║
║          WebSocket: ws://localhost:8001/ws                   ║
╚══════════════════════════════════════════════════════════════╝
"""

HELP = """
Commands
  [Enter]   Manual flush – force transcription of buffered audio
  q         Quit
  d         List available audio input devices

Test phrases
  EN: "The quick brown fox jumps over the lazy dog"
  ES: "El zorro marrón rápido salta sobre el perro perezoso"
"""


# ── Audio capture thread ───────────────────────────────────────────────────────

class MicCapture:
    """Captures microphone audio into a thread-safe queue."""

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
                data = stream.read(CHUNK_SAMPLES, exception_on_overflow=False)
                self.queue.put(data)
        except OSError as exc:
            print(f"\n[ERROR] Audio capture failed: {exc}", file=sys.stderr)
            self._stop.set()
        finally:
            try:
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
            print(f"  [{i}] {info['name']}  ({int(info['defaultSampleRate'])} Hz)")
    pa.terminate()
    print()


# ── stdin reader (non-blocking) ────────────────────────────────────────────────

def stdin_reader(cmd_queue: Queue):
    """Reads lines from stdin in a background thread."""
    while True:
        try:
            line = sys.stdin.readline()
            if line:
                cmd_queue.put(line.strip())
        except Exception:
            break


# ── WebSocket sender ───────────────────────────────────────────────────────────

async def run(host: str, port: int, device_index: Optional[int]):
    uri = f"ws://{host}:{port}/ws"
    print(BANNER)
    print(f"Connecting to {uri} …", end=" ", flush=True)

    try:
        async with websockets.connect(uri, ping_interval=20, ping_timeout=20) as ws:
            print("connected ✓\n")
            print("🎙  Speak now – transcriptions appear below\n")
            print("─" * 64)

            mic = MicCapture(device_index)
            mic.start()

            cmd_queue: Queue[str] = Queue()
            cmd_thread = threading.Thread(
                target=stdin_reader, args=(cmd_queue,), daemon=True
            )
            cmd_thread.start()

            send_task = asyncio.create_task(_sender(ws, mic, cmd_queue))
            recv_task = asyncio.create_task(_receiver(ws))

            done, pending = await asyncio.wait(
                [send_task, recv_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for t in pending:
                t.cancel()
            mic.stop()

    except (OSError, websockets.exceptions.WebSocketException) as exc:
        print(f"failed ✗\n[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)


async def _sender(ws, mic: MicCapture, cmd_queue: Queue):
    """Reads from microphone queue and sends frames to server."""
    print(HELP)
    try:
        while True:
            # Check for user commands
            try:
                cmd = cmd_queue.get_nowait()
                if cmd.lower() in ("q", "quit", "exit"):
                    print("\nBye!")
                    return
                elif cmd == "":
                    # Enter → manual flush
                    await ws.send(json.dumps({"cmd": "flush"}).encode())
                    print("[flushed]\n", flush=True)
                elif cmd.lower() == "d":
                    list_devices()
            except Empty:
                pass

            # Drain the audio queue and send frames
            sent = 0
            while not mic.queue.empty() and sent < 50:
                frame = mic.queue.get_nowait()
                await ws.send(frame)
                sent += 1

            await asyncio.sleep(0.005)

    except websockets.exceptions.ConnectionClosed:
        print("\n[Connection closed by server]")


async def _receiver(ws):
    """Receives transcription messages from server and prints them."""
    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")
            text     = msg.get("text", "")
            dur_ms   = msg.get("duration_ms", 0)
            ts       = time.strftime("%H:%M:%S")

            if msg_type == "partial":
                # Overwrite same line with carriage return so it feels live
                print(f"\r  ⏳ [{ts}] {text:<80}", end="", flush=True)

            elif msg_type == "transcript":
                rtf = msg.get("rtf", 0)
                # Move to new line first to clear any partial still on screen
                print(f"\r{' ' * 90}\r", end="")   # clear partial line
                print(f"[{ts}] ({dur_ms/1000:.1f}s | RTF {rtf:.2f}x)")
                print(f"  ✅  {text}")
                print("─" * 64)

    except websockets.exceptions.ConnectionClosed:
        print("\n[Connection closed]")


# ── Entry point ────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Parakeet ASR terminal client")
    p.add_argument("--host", default="localhost", help="Server host (default: localhost)")
    p.add_argument("--port", type=int, default=8001, help="Server port (default: 8001)")
    p.add_argument(
        "--device",
        type=int,
        default=None,
        metavar="INDEX",
        help="Microphone device index (use --list to see options)",
    )
    p.add_argument("--list", action="store_true", help="List audio input devices and exit")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.list:
        list_devices()
        sys.exit(0)
    asyncio.run(run(args.host, args.port, args.device))
