import asyncio
import websockets
import json
import pyaudio
import numpy as np
import sys

print('''After you are done with dev work please test the following:
1. test for backend = "nemotron"
2. test for backend = "google"
3. test for backend = "whisper"
4. test for the combination: backend = "nemotron" and TARGET_SR = 16000
5. test for the combination: backend = "nemotron" and TARGET_SR = 8000

---------------------
STARTING TESTING
---------------------

''')

# CONFIG
WEBSOCKET_ADDRESS = "ws://127.0.0.1:8002/asr/realtime-custom-vad"
#WEBSOCKET_ADDRESS = "wss://cx-asr.exlservice.com/asr/realtime-custom-vad"

TARGET_SR = 16000
CHANNELS = 1

CHUNK_MS = 80
CHUNK_FRAMES = int(TARGET_SR * CHUNK_MS / 1000)
SLEEP_SEC = CHUNK_MS / 1000.0

# Whisper flush tuning
WHISPER_FLUSH_INTERVAL_SEC = 0.35
WHISPER_FLUSH_SILENCE_MS = 80

websocket = None
stream = None
is_recording = False

# NEW: track session start time for t_final
session_start_time = None


# RECEIVE LOOP
async def receive_data():
    global session_start_time

    try:
        async for msg in websocket:
            if isinstance(msg, str):
                obj = json.loads(msg)
                typ = obj.get("type")

                if typ == "partial":
                    txt = obj.get("text", "")
                    t_start = obj.get("t_start")

                    print(
                        f"\r[PARTIAL] {txt[:120]} (t_start={t_start} ms)",
                        end="",
                        flush=True,
                    )

                elif typ == "final":
                    txt = obj.get("text", "")
                    t_start = obj.get("t_start")

                    print(f"\n[FINAL] {txt}")

                    now = asyncio.get_event_loop().time()

                    if t_start is not None:
                        # Nemotron metric
                        latency_ms = t_start
                        metric_name = "t_start"
                    else:
                        # Whisper / Google metric
                        latency_ms = int((now - session_start_time) * 1000)
                        metric_name = "t_final"

                    print(f"[CLIENT] {metric_name}={latency_ms} ms")

                else:
                    print("[SERVER EVENT]", obj)

    except websockets.exceptions.ConnectionClosed:
        print("\nWebSocket closed")


# CONNECT
async def connect_websocket():
    global websocket

    websocket = await websockets.connect(
        WEBSOCKET_ADDRESS,
        max_size=None,
    )

    print(f"Connected to {WEBSOCKET_ADDRESS}")


# SEND BACKEND CONFIG
async def send_audio_config(backend: str):

    audio_config = {
        "backend": backend,
        "sample_rate": TARGET_SR,
    }

    await websocket.send(json.dumps(audio_config))
    print(f"Sent backend config: {backend}")


# MIC START
async def start_recording():
    global stream, is_recording, session_start_time

    p = pyaudio.PyAudio()

    stream = p.open(
        format=pyaudio.paInt16,
        channels=CHANNELS,
        rate=TARGET_SR,
        input=True,
        frames_per_buffer=CHUNK_FRAMES,
    )

    # NEW: start timer
    session_start_time = asyncio.get_event_loop().time()

    is_recording = True
    print("Recording started (Ctrl+C to stop)")


# MIC STOP + EOS
async def stop_recording():
    global stream, is_recording

    is_recording = False

    try:
        # trailing silence
        await websocket.send(b"\x00\x00" * int(TARGET_SR * 0.6))
        await asyncio.sleep(0.5)

        # explicit EOS
        await websocket.send(b"")

    except Exception:
        pass

    if stream:
        stream.stop_stream()
        stream.close()

    print("Recording stopped")


# MAIN LOOP
async def main():

    backend = "nemotron"

    if len(sys.argv) > 1:
        backend = sys.argv[1]

    if backend not in ("nemotron", "whisper", "google"):
        print("Usage: python client.py [nemotron|whisper|google]")
        return

    await connect_websocket()

    await send_audio_config(backend)

    await start_recording()

    recv_task = asyncio.create_task(receive_data())

    last_flush_time = asyncio.get_event_loop().time()

    try:
        while True:

            data = stream.read(CHUNK_FRAMES, exception_on_overflow=False)

            pcm = np.frombuffer(data, dtype=np.int16)

            await websocket.send(pcm.tobytes())

            # Whisper flush logic
            if backend == "whisper":

                now = asyncio.get_event_loop().time()

                if now - last_flush_time >= WHISPER_FLUSH_INTERVAL_SEC:

                    silence_frames = int(
                        TARGET_SR * (WHISPER_FLUSH_SILENCE_MS / 1000.0)
                    )

                    silence = b"\x00\x00" * silence_frames

                    await websocket.send(silence)

                    last_flush_time = now

            await asyncio.sleep(SLEEP_SEC)

    except KeyboardInterrupt:
        print("\nKeyboard interrupt")

    finally:
        await stop_recording()

        recv_task.cancel()

        try:
            await websocket.close()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())



us-central1-docker.pkg.dev/emr-dgt-autonomous-uctr1-snbx/asr-parakeet-es
gcloud auth configure-docker us-central1-docker.pkg.dev
docker tag nvcr.io/nim/nvidia/parakeet-ctc-0.6b-es:latest us-central1-docker.pkg.dev/emr-dgt-autonomous-uctr1-snbx/asr-parakeet-es/parakeet-ctc-0.6b-es:0.0.1
docker push us-central1-docker.pkg.dev/emr-dgt-autonomous-uctr1-snbx/asr-parakeet-es/parakeet-ctc-0.6b-es:0.0.1



how to use this cloud run url https://parakeet-custom-vad-150916788856.us-central1.run.app
for websocket testing of this script 
in this 
import asyncio
import json
import logging
import websockets
import soundfile as sf
import numpy as np

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# CONFIG
WEBSOCKET_ADDRESS = "ws://192.168.4.38:8001/ws"
TARGET_SR = 16000
CHUNK_MS = 30
CHUNK_SAMPLES = TARGET_SR * CHUNK_MS // 1000
CHUNK_BYTES = CHUNK_SAMPLES * 2


# AUDIO LOADER
def load_audio(filepath: str):
    audio, sr = sf.read(filepath, dtype="float32")

    if audio.ndim == 2:
        audio = audio.mean(axis=1)

    if sr != TARGET_SR:
        import librosa
        audio = librosa.resample(
            audio,
            orig_sr=sr,
            target_sr=TARGET_SR
        )

    pcm = (
        np.clip(audio, -1.0, 1.0) * 32767
    ).astype(np.int16)

    return pcm.tobytes()


# MAIN STREAM FUNCTION
async def stream_parakeet(audio_file: str):
    event_queue = asyncio.Queue()

    pcm_audio = load_audio(audio_file)

    async with websockets.connect(
        WEBSOCKET_ADDRESS,
        max_size=None,
        ping_interval=20,
        ping_timeout=20
    ) as ws:

        logger.info("Connected to websocket")

        async def receive_task():
            """
            Listen for partial + final transcripts
            throughout the full audio stream.
            """
            try:
                async for msg in ws:
                    if isinstance(msg, str):
                        obj = json.loads(msg)

                        typ = obj.get("type")
                        txt = obj.get("text", "")

                        logger.info(
                            f"Websocket received msg: {txt}, type: {typ}"
                        )

                        if typ == "partial":
                            await event_queue.put({
                                "type": "INTERIM_TRANSCRIPT",
                                "text": txt
                            })

                        elif typ in ["transcript", "final"]:
                            await event_queue.put({
                                "type": "FINAL_TRANSCRIPT",
                                "text": txt
                            })

            except websockets.exceptions.ConnectionClosed:
                logger.info("Connection closed by server")

        async def send_task():
            """
            Stream complete audio file chunk by chunk.
            """
            try:
                offset = 0
                total_chunks = 0

                while offset < len(pcm_audio):
                    chunk = pcm_audio[
                        offset: offset + CHUNK_BYTES
                    ]
                    offset += CHUNK_BYTES

                    if len(chunk) < CHUNK_BYTES:
                        chunk += bytes(
                            CHUNK_BYTES - len(chunk)
                        )

                    await ws.send(chunk)
                    total_chunks += 1

                    if total_chunks % 1000 == 0:
                        logger.info(
                            f"Sent {total_chunks} chunks"
                        )

                    await asyncio.sleep(
                        CHUNK_MS / 1000
                    )

                logger.info("Finished sending full audio")

                # final flush
                await asyncio.sleep(0.5)

                await ws.send(
                    json.dumps({"cmd": "flush"})
                )

                logger.info("Flush sent")

                # wait for last transcript
                await asyncio.sleep(10)

                await event_queue.put(None)

            except Exception as e:
                logger.info(f"Error occurred: {e}")
                await event_queue.put(None)

        # start background tasks
        stask = asyncio.create_task(send_task())
        rtask = asyncio.create_task(receive_task())

        try:
            while True:
                event = await event_queue.get()

                if event is None:
                    break

                yield event

        finally:
            stask.cancel()
            rtask.cancel()
 
