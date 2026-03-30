FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

ENV http_proxy="http://163.116.128.80:8080"
ENV https_proxy="http://163.116.128.80:8080"
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.10 \
        python3.10-dev \
        python3-pip \
        python3.10-distutils \
        build-essential \
        gcc \
        g++ \
        ffmpeg \
        libsndfile1 \
        libportaudio2 \
        portaudio19-dev \
        git \
        wget \
        curl \
        libcudnn8 \
        libcudnn8-dev \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 \
 && update-alternatives --install /usr/bin/pip    pip    /usr/bin/pip3      1

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

WORKDIR /app

RUN pip install --no-cache-dir \
    torch==2.4.0+cu121 \
    torchvision==0.19.0+cu121 \
    torchaudio==2.4.0+cu121 \
    --index-url https://download.pytorch.org/whl/cu121

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY server.py .

RUN python -c "\
import nemo.collections.asr as nemo_asr; \
m = nemo_asr.models.ASRModel.from_pretrained('nvidia/parakeet-tdt-0.6b-v3'); \
print('Model cached ✓')"

EXPOSE 8001

ENV PYTHONUNBUFFERED=1

CMD ["python", "server.py"]
