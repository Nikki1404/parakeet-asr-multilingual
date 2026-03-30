# ── Parakeet-TDT-0.6B-v3 Real-Time ASR Server ────────────────────────────────
# Base: NVIDIA CUDA runtime (Ampere-compatible, CUDA 11.8)
# Switch to nvcr.io/nvidia/cuda:12.1.0-runtime-ubuntu22.04 for Ada/Hopper GPUs.
FROM nvcr.io/nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# ── System deps ───────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.10 \
        python3.10-dev \
        python3-pip \
        python3.10-distutils \
        ffmpeg \
        libsndfile1 \
        libportaudio2 \
        portaudio19-dev \
        git \
        wget \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Make python3.10 the default python
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 \
 && update-alternatives --install /usr/bin/pip    pip    /usr/bin/pip3      1

# ── Python deps ───────────────────────────────────────────────────────────────
WORKDIR /app

# Install PyTorch with CUDA 11.8 support BEFORE nemo_toolkit
# (nemo_toolkit will try to pull CPU-only torch otherwise)
RUN pip install --no-cache-dir \
    torch==2.1.2+cu118 \
    torchvision==0.16.2+cu118 \
    torchaudio==2.1.2+cu118 \
    --index-url https://download.pytorch.org/whl/cu118

COPY requirements.txt .

# Install remaining deps (torch is already satisfied, so pip won't downgrade it)
RUN pip install --no-cache-dir \
    nemo_toolkit[asr]==2.4.0 \
    fastapi==0.115.0 \
    "uvicorn[standard]==0.30.6" \
    websockets==12.0 \
    webrtcvad==2.0.10 \
    numpy>=1.24.0 \
    soundfile>=0.12.1

# ── App ───────────────────────────────────────────────────────────────────────
COPY server.py .

# Pre-download model weights at build time so container starts fast
# Comment this out if you want to pull on first run instead.
RUN python -c "\
import nemo.collections.asr as nemo_asr; \
m = nemo_asr.models.ASRModel.from_pretrained('nvidia/parakeet-tdt-0.6b-v3'); \
print('Model cached ✓')"

EXPOSE 8765

# ── Runtime ───────────────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1

CMD ["python", "server.py"]
