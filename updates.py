 => [ 8/10] RUN pip install --no-cache-dir -r requirements.txt                                                                                                                                                                     111.2s
 => [ 9/10] COPY server.py .                                                                                                                                                                                                         5.8s
 => ERROR [10/10] RUN python -c "import nemo.collections.asr as nemo_asr; m = nemo_asr.models.ASRModel.from_pretrained('nvidia/parakeet-tdt-0.6b-v3'); print('Model cached ✓')"                                                      9.0s
------
 > [10/10] RUN python -c "import nemo.collections.asr as nemo_asr; m = nemo_asr.models.ASRModel.from_pretrained('nvidia/parakeet-tdt-0.6b-v3'); print('Model cached ✓')":
8.077 Traceback (most recent call last):
8.077   File "<string>", line 1, in <module>
8.077   File "/usr/local/lib/python3.10/dist-packages/nemo/collections/asr/__init__.py", line 15, in <module>
8.077     from nemo.collections.asr import data, losses, models, modules
8.077   File "/usr/local/lib/python3.10/dist-packages/nemo/collections/asr/models/__init__.py", line 15, in <module>
8.077     from nemo.collections.asr.models.aed_multitask_models import EncDecMultiTaskModel
8.077   File "/usr/local/lib/python3.10/dist-packages/nemo/collections/asr/models/aed_multitask_models.py", line 32, in <module>
8.077     from nemo.collections.asr.metrics import BLEU, WER
8.077   File "/usr/local/lib/python3.10/dist-packages/nemo/collections/asr/metrics/__init__.py", line 15, in <module>
8.077     from nemo.collections.asr.metrics.bleu import BLEU
8.077   File "/usr/local/lib/python3.10/dist-packages/nemo/collections/asr/metrics/bleu.py", line 22, in <module>
8.077     from nemo.collections.asr.parts.submodules.multitask_decoding import AbstractMultiTaskDecoding
8.077   File "/usr/local/lib/python3.10/dist-packages/nemo/collections/asr/parts/submodules/multitask_decoding.py", line 22, in <module>
8.077     from nemo.collections.asr.parts.submodules.multitask_beam_decoding import (
8.077   File "/usr/local/lib/python3.10/dist-packages/nemo/collections/asr/parts/submodules/multitask_beam_decoding.py", line 22, in <module>
8.077     from nemo.collections.asr.modules.transformer import (
8.077   File "/usr/local/lib/python3.10/dist-packages/nemo/collections/asr/modules/__init__.py", line 23, in <module>
8.077     from nemo.collections.asr.modules.conformer_encoder import ConformerEncoder, ConformerEncoderAdapter
8.077   File "/usr/local/lib/python3.10/dist-packages/nemo/collections/asr/modules/conformer_encoder.py", line 29, in <module>
8.077     from nemo.collections.asr.parts.submodules.conformer_modules import ConformerLayer
8.077   File "/usr/local/lib/python3.10/dist-packages/nemo/collections/asr/parts/submodules/conformer_modules.py", line 20, in <module>
8.077     from nemo.collections.asr.parts.submodules.adapters.attention_adapter_mixin import AttentionAdapterModuleMixin
8.077   File "/usr/local/lib/python3.10/dist-packages/nemo/collections/asr/parts/submodules/adapters/__init__.py", line 17, in <module>
8.077     from nemo.collections.asr.parts.submodules.adapters.multi_head_attention_adapter_module import (
8.077   File "/usr/local/lib/python3.10/dist-packages/nemo/collections/asr/parts/submodules/adapters/multi_head_attention_adapter_module.py", line 22, in <module>
8.077     from nemo.collections.asr.parts.submodules import multi_head_attention as mha
8.077   File "/usr/local/lib/python3.10/dist-packages/nemo/collections/asr/parts/submodules/multi_head_attention.py", line 41, in <module>
8.077     import torch.nn.attention
8.077 ModuleNotFoundError: No module named 'torch.nn.attention'
------
Dockerfile:41
--------------------
  40 |
  41 | >>> RUN python -c "\
  42 | >>> import nemo.collections.asr as nemo_asr; \
  43 | >>> m = nemo_asr.models.ASRModel.from_pretrained('nvidia/parakeet-tdt-0.6b-v3'); \
  44 | >>> print('Model cached ✓')"
  45 |
--------------------
ERROR: failed to build: failed to solve: process "/bin/sh -c python -c \"import nemo.collections.asr as nemo_asr; m = nemo_asr.models.ASRModel.from_pretrained('nvidia/parakeet-tdt-0.6b-v3'); print('Model cached ✓')\"" did not complete successfully: exit code: 1
