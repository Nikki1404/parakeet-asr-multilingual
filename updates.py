 => [5/9] RUN pip install --no-cache-dir     torch==2.1.2+cu118     torchvision==0.16.2+cu118     torchaudio==2.1.2+cu118     --index-url https://download.pytorch.org/whl/cu118                                                   129.6s
 => [6/9] COPY requirements.txt .                                                                                                                                                                                                   11.2s
 => ERROR [7/9] RUN pip install --no-cache-dir     nemo_toolkit[asr]==2.4.0     fastapi==0.115.0     "uvicorn[standard]==0.30.6"     websockets==12.0     webrtcvad==2.0.10     numpy>=1.24.0     soundfile>=0.12.1                 62.4s
------
 > [7/9] RUN pip install --no-cache-dir     nemo_toolkit[asr]==2.4.0     fastapi==0.115.0     "uvicorn[standard]==0.30.6"     websockets==12.0     webrtcvad==2.0.10     numpy>=1.24.0     soundfile>=0.12.1:
55.48   error: subprocess-exited-with-error
55.48
55.48   × python setup.py bdist_wheel did not run successfully.
55.48   │ exit code: 1
55.48   ╰─> [16 lines of output]
55.48       running bdist_wheel
55.48       running build
55.48       running build_py
55.48       creating build
55.48       creating build/lib.linux-x86_64-3.10
55.48       copying webrtcvad.py -> build/lib.linux-x86_64-3.10
55.48       running build_ext
55.48       building '_webrtcvad' extension
55.48       creating build/temp.linux-x86_64-3.10
55.48       creating build/temp.linux-x86_64-3.10/cbits
55.48       creating build/temp.linux-x86_64-3.10/cbits/webrtc
55.48       creating build/temp.linux-x86_64-3.10/cbits/webrtc/common_audio
55.48       creating build/temp.linux-x86_64-3.10/cbits/webrtc/common_audio/signal_processing
55.48       creating build/temp.linux-x86_64-3.10/cbits/webrtc/common_audio/vad
55.48       x86_64-linux-gnu-gcc -Wno-unused-result -Wsign-compare -DNDEBUG -g -fwrapv -O2 -Wall -g -fstack-protector-strong -Wformat -Werror=format-security -g -fwrapv -O2 -g -fstack-protector-strong -Wformat -Werror=format-security -Wdate-time -D_FORTIFY_SOURCE=2 -fPIC -DWEBRTC_POSIX -Icbits -I/usr/include/python3.10 -c cbits/pywebrtcvad.c -o build/temp.linux-x86_64-3.10/cbits/pywebrtcvad.o
55.48       error: command 'x86_64-linux-gnu-gcc' failed: No such file or directory
55.48       [end of output]
55.48
55.48   note: This error originates from a subprocess, and is likely not a problem with pip.
55.48   ERROR: Failed building wheel for webrtcvad
56.44   error: subprocess-exited-with-error
56.44
56.44   × python setup.py bdist_wheel did not run successfully.
56.44   │ exit code: 1
56.44   ╰─> [48 lines of output]
56.44       /usr/lib/python3/dist-packages/setuptools/installer.py:27: SetuptoolsDeprecationWarning: setuptools.installer is deprecated. Requirements should be satisfied by a PEP 517 installer.
56.44         warnings.warn(
56.44       running bdist_wheel
56.44       running build
56.44       running build_py
56.44       creating build
56.44       creating build/lib.linux-x86_64-3.10
56.44       creating build/lib.linux-x86_64-3.10/texterrors
56.44       copying texterrors/__init__.py -> build/lib.linux-x86_64-3.10/texterrors
56.44       copying texterrors/texterrors.py -> build/lib.linux-x86_64-3.10/texterrors
56.44       running build_ext
56.44       creating tmp
56.44       x86_64-linux-gnu-gcc -Wno-unused-result -Wsign-compare -DNDEBUG -g -fwrapv -O2 -Wall -g -fstack-protector-strong -Wformat -Werror=format-security -g -fwrapv -O2 -g -fstack-protector-strong -Wformat -Werror=format-security -Wdate-time -D_FORTIFY_SOURCE=2 -fPIC -I/usr/include/python3.10 -c /tmp/tmpjeh6ku0k.cpp -o tmp/tmpjeh6ku0k.o -std=c++14
56.44       x86_64-linux-gnu-gcc -Wno-unused-result -Wsign-compare -DNDEBUG -g -fwrapv -O2 -Wall -g -fstack-protector-strong -Wformat -Werror=format-security -g -fwrapv -O2 -g -fstack-protector-strong -Wformat -Werror=format-security -Wdate-time -D_FORTIFY_SOURCE=2 -fPIC -I/usr/include/python3.10 -c /tmp/tmpxjm4o8jx.cpp -o tmp/tmpxjm4o8jx.o -std=c++11
56.44       Traceback (most recent call last):
56.44         File "<string>", line 2, in <module>
56.44         File "<pip-setuptools-caller>", line 34, in <module>
56.44         File "/tmp/pip-install-p_9zw7a2/texterrors_de992c6e153f4dbcb83919fde2bceb7c/setup.py", line 101, in <module>
56.44           setup(
56.44         File "/usr/lib/python3/dist-packages/setuptools/__init__.py", line 153, in setup
56.44           return distutils.core.setup(**attrs)
56.44         File "/usr/lib/python3.10/distutils/core.py", line 148, in setup
56.44           dist.run_commands()
56.44         File "/usr/lib/python3.10/distutils/dist.py", line 966, in run_commands
56.44           self.run_command(cmd)
56.44         File "/usr/lib/python3.10/distutils/dist.py", line 985, in run_command
56.44           cmd_obj.run()
56.44         File "/usr/lib/python3/dist-packages/wheel/bdist_wheel.py", line 299, in run
56.44           self.run_command('build')
56.44         File "/usr/lib/python3.10/distutils/cmd.py", line 313, in run_command
56.44           self.distribution.run_command(command)
56.44         File "/usr/lib/python3.10/distutils/dist.py", line 985, in run_command
56.44           cmd_obj.run()
56.44         File "/usr/lib/python3.10/distutils/command/build.py", line 135, in run
56.44           self.run_command(cmd_name)
56.44         File "/usr/lib/python3.10/distutils/cmd.py", line 313, in run_command
56.44           self.distribution.run_command(command)
56.44         File "/usr/lib/python3.10/distutils/dist.py", line 985, in run_command
56.44           cmd_obj.run()
56.44         File "/usr/lib/python3/dist-packages/setuptools/command/build_ext.py", line 79, in run
56.44           _build_ext.run(self)
56.44         File "/usr/lib/python3.10/distutils/command/build_ext.py", line 340, in run
56.44           self.build_extensions()
56.44         File "/tmp/pip-install-p_9zw7a2/texterrors_de992c6e153f4dbcb83919fde2bceb7c/setup.py", line 80, in build_extensions
56.44           opts.append(cpp_flag(self.compiler))
56.44         File "/tmp/pip-install-p_9zw7a2/texterrors_de992c6e153f4dbcb83919fde2bceb7c/setup.py", line 62, in cpp_flag
56.44           raise RuntimeError(
56.44       RuntimeError: Unsupported compiler -- at least C++11 support is needed!
56.44       [end of output]
56.44
56.44   note: This error originates from a subprocess, and is likely not a problem with pip.
56.44   ERROR: Failed building wheel for texterrors
60.71   error: subprocess-exited-with-error
60.71
60.71   × Running setup.py install for webrtcvad did not run successfully.
60.71   │ exit code: 1
60.71   ╰─> [18 lines of output]
60.71       running install
60.71       /usr/lib/python3/dist-packages/setuptools/command/install.py:34: SetuptoolsDeprecationWarning: setup.py install is deprecated. Use build and pip and other standards-based tools.
60.71         warnings.warn(
60.71       running build
60.71       running build_py
60.71       creating build
60.71       creating build/lib.linux-x86_64-3.10
60.71       copying webrtcvad.py -> build/lib.linux-x86_64-3.10
60.71       running build_ext
60.71       building '_webrtcvad' extension
60.71       creating build/temp.linux-x86_64-3.10
60.71       creating build/temp.linux-x86_64-3.10/cbits
60.71       creating build/temp.linux-x86_64-3.10/cbits/webrtc
60.71       creating build/temp.linux-x86_64-3.10/cbits/webrtc/common_audio
60.71       creating build/temp.linux-x86_64-3.10/cbits/webrtc/common_audio/signal_processing
60.71       creating build/temp.linux-x86_64-3.10/cbits/webrtc/common_audio/vad
60.71       x86_64-linux-gnu-gcc -Wno-unused-result -Wsign-compare -DNDEBUG -g -fwrapv -O2 -Wall -g -fstack-protector-strong -Wformat -Werror=format-security -g -fwrapv -O2 -g -fstack-protector-strong -Wformat -Werror=format-security -Wdate-time -D_FORTIFY_SOURCE=2 -fPIC -DWEBRTC_POSIX -Icbits -I/usr/include/python3.10 -c cbits/pywebrtcvad.c -o build/temp.linux-x86_64-3.10/cbits/pywebrtcvad.o
60.71       error: command 'x86_64-linux-gnu-gcc' failed: No such file or directory
60.71       [end of output]
60.71
60.71   note: This error originates from a subprocess, and is likely not a problem with pip.
60.71 error: legacy-install-failure
60.71
60.71 × Encountered error while trying to install package.
60.71 ╰─> webrtcvad
60.71
60.71 note: This is an issue with the package mentioned above, not pip.
60.71 hint: See above for output from the failure.
------
Dockerfile:39
--------------------
  38 |     # Install remaining deps (torch is already satisfied, so pip won't downgrade it)
  39 | >>> RUN pip install --no-cache-dir \
  40 | >>>     nemo_toolkit[asr]==2.4.0 \
  41 | >>>     fastapi==0.115.0 \
  42 | >>>     "uvicorn[standard]==0.30.6" \
  43 | >>>     websockets==12.0 \
  44 | >>>     webrtcvad==2.0.10 \
  45 | >>>     numpy>=1.24.0 \
  46 | >>>     soundfile>=0.12.1
  47 |
--------------------
ERROR: failed to build: failed to solve: process "/bin/sh -c pip install --no-cache-dir     nemo_toolkit[asr]==2.4.0     fastapi==0.115.0     \"uvicorn[standard]==0.30.6\"     websockets==12.0     webrtcvad==2.0.10     numpy>=1.24.0     soundfile>=0.12.1" did not complete successfully: exit code: 1
