# Parakeet-TDT-0.6B-v3 · Real-Time ASR

Real-time speech-to-text with auto language detection (English, Spanish + 23 more).

## Files
- `server.py` — WebSocket ASR server
- `client.py` — terminal client (mic or file mode)
- `Dockerfile` — CUDA 12.1 container
- `requirements.txt` — dependencies

## Run

```bash
# Server
docker build -t parakeet-asr .
docker run --gpus all -p 8001:8001 parakeet-asr

# Client deps
pip install pyaudio websockets soundfile numpy

# SSH tunnel (if EC2)
ssh -L 8001:localhost:8001 your_user@<ec2-ip>

# Mic
python client.py

# File
python client.py --host 0.0.0.0 --port 8001 --file audio.wav
python client.py --host 0.0.0.0 --port 8001 --file english.wav spanish.mp3
```

## Health check
```bash
curl http://localhost:8001/health
```
