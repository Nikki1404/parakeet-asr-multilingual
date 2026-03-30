(base) root@EC03-E01-AICOE1:/home/CORP/re_nikitav/parakeet-asr-multilingual# docker build -t parakeet_asr_realtime .
[+] Building 236.7s (13/15)                                                                                                                                                                                                docker:default
 => [internal] load build definition from Dockerfile                                                                                                                                                                                 0.0s
 => => transferring dockerfile: 2.34kB                                                                                                                                                                                               0.0s
 => [internal] load metadata for nvcr.io/nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04                                                                                                                                               1.2s
 => [auth] nvidia/cuda:pull token for nvcr.io                                                                                                                                                                                        0.0s
 => [internal] load .dockerignore                                                                                                                                                                                                    0.0s
 => => transferring context: 2B                                                                                                                                                                                                      0.0s
 => CACHED [ 1/10] FROM nvcr.io/nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04@sha256:85fb7ac694079fff1061a0140fd5b5a641997880e12112d92589c3bbb1e8b7ca                                                                                0.0s
 => [internal] load build context                                                                                                                                                                                                    0.0s
 => => transferring context: 9.59kB                                                                                                                                                                                                  0.0s
 => [ 2/10] RUN apt-get update && apt-get install -y --no-install-recommends         python3.10         python3.10-dev         python3-pip         python3.10-distutils         build-essential         gcc         g++         f  103.9s
 => [ 3/10] RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1  && update-alternatives --install /usr/bin/pip    pip    /usr/bin/pip3      1                                                             0.4s
 => [ 4/10] RUN pip install --no-cache-dir --upgrade pip setuptools wheel                                                                                                                                                            3.5s
 => [ 5/10] WORKDIR /app                                                                                                                                                                                                             0.2s
 => [ 6/10] RUN pip install --no-cache-dir     torch==2.1.2+cu118     torchvision==0.16.2+cu118     torchaudio==2.1.2+cu118     --index-url https://download.pytorch.org/whl/cu118                                                 113.5s
 => [ 7/10] COPY requirements.txt .                                                                                                                                                                                                 11.9s
 => ERROR [ 8/10] RUN pip install --no-cache-dir -r requirements.txt                                                                                                                                                                 2.0s
------
 > [ 8/10] RUN pip install --no-cache-dir -r requirements.txt:
1.085 Collecting nemo_toolkit==2.4.0 (from nemo_toolkit[asr]==2.4.0->-r requirements.txt (line 1))
1.235   Downloading nemo_toolkit-2.4.0-py3-none-any.whl.metadata (91 kB)
1.512 Collecting fastapi==0.115.0 (from -r requirements.txt (line 2))
1.526   Downloading fastapi-0.115.0-py3-none-any.whl.metadata (27 kB)
1.565 Collecting uvicorn==0.30.6 (from uvicorn[standard]==0.30.6->-r requirements.txt (line 3))
1.579   Downloading uvicorn-0.30.6-py3-none-any.whl.metadata (6.6 kB)
1.701 Collecting websockets==12.0 (from -r requirements.txt (line 4))
1.748   Downloading websockets-12.0-cp310-cp310-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (6.6 kB)
1.798 ERROR: Could not find a version that satisfies the requirement webrtcvad-wheels==2.0.10.post0 (from versions: 2.0.10.post2, 2.0.11, 2.0.11.post1, 2.0.12, 2.0.13, 2.0.14)
1.968 ERROR: No matching distribution found for webrtcvad-wheels==2.0.10.post0
------
Dockerfile:41
--------------------
  39 |
  40 |     COPY requirements.txt .
  41 | >>> RUN pip install --no-cache-dir -r requirements.txt
  42 |
  43 |     # ── App ───────────────────────────────────────────────────────────────────────
--------------------
ERROR: failed to build: failed to solve: process "/bin/sh -c pip install --no-cache-dir -r requirements.txt" did not complete successfully: exit code: 1
