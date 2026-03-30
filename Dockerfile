FROM nvcr.io/nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

ENV http_proxy="http://163.116.128.80:8080"
ENV https_proxy="http://163.116.128.80:8080"
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.10 \
        python3.10-dev \
        python3-pip \
        python3.10-distutils \
        # C/C++ compiler – required by webrtcvad, texterrors, and other native exts
        build-essential \
        gcc \
        g++ \
        # Audio / media
        ffmpeg \
        libsndfile1 \
        libportaudio2 \
        portaudio19-dev \
        git \
        wget \
        curl \
    && rm -rf /var/lib/apt/lists/*
 
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 \
 && update-alternatives --install /usr/bin/pip    pip    /usr/bin/pip3      1
 
# Upgrade pip + wheel so legacy setup.py packages build cleanly
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
 
# ── Python deps ───────────────────────────────────────────────────────────────
WORKDIR /app
 
# Install PyTorch with CUDA 11.8 BEFORE nemo_toolkit
RUN pip install --no-cache-dir \
    torch==2.1.2+cu118 \
    torchvision==0.16.2+cu118 \
    torchaudio==2.1.2+cu118 \
    --index-url https://download.pytorch.org/whl/cu118
 
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
 
# ── App ───────────────────────────────────────────────────────────────────────
COPY server.py .
 
# Pre-download model weights at build time so container starts fast
# Comment this out if you want to pull on first run instead.
RUN python -c "\
import nemo.collections.asr as nemo_asr; \
m = nemo_asr.models.ASRModel.from_pretrained('nvidia/parakeet-tdt-0.6b-v3'); \
print('Model cached ✓')"
 
EXPOSE 8001
 
# ── Runtime ───────────────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1
 
CMD ["python", "server.py"]
