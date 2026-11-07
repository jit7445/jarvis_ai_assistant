# jarvis-core

The Python service that owns the machine. Requires an Apple Silicon Mac and Python 3.11.

## Setup

```bash
cd jarvis-core
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest
```

Activate `.venv` in every new terminal. Dependencies are pinned in `pyproject.toml`; `dev` adds pytest and the arm64 cmake.

## Speech output

```python
from jarvis.speech.tts import speak
speak("Your assistant is ready.")
```

Wraps macOS `say`. Text goes in on stdin, never as an argument, so a sentence like `-o file` or `"; ls` is read aloud rather than parsed. The voice comes from `jarvis.config.VOICE` and must be installed (`say -v '?'`). `python scripts/speak_test.py` plays sample lines in Samantha and Rishi.

## Speech-to-text engine

whisper.cpp is built from source, pinned to v1.9.1, using the venv's arm64 cmake. If Homebrew lives in `/usr/local`, its cmake is x86_64 and builds without Metal.

```bash
git clone --depth 1 --branch v1.9.1 https://github.com/ggml-org/whisper.cpp.git
cd whisper.cpp
cmake -B build -DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF
cmake --build build -j 4 --config Release --target whisper-cli
sh ./models/download-ggml-model.sh base.en
```

Static linking keeps the binary working if the folder moves. The first run takes about 14 s while Metal compiles its shaders; later runs take about 0.4 s for a 5 s clip.

## Transcription benchmark

```bash
scripts/bench_whisper.sh
```

Refuses to run while the network is reachable. Runs five transcriptions of `workspace/mic_test.wav` and writes timings to `docs/phase2_offline.log`.

## Microphone check

```bash
python scripts/mic_test.py
```

Records 5 seconds at 16 kHz mono to `workspace/mic_test.wav`. The first run triggers the macOS microphone permission prompt; recordings made while the prompt is open come out silent.

## Layout

| Path | Contents | In git |
| --- | --- | --- |
| `src/jarvis/` | The package: `speech/`, `config/` | yes |
| `scripts/` | Manual hardware checks | yes |
| `tests/` | pytest suite | yes |
| `docs/` | Phase results and measurements | yes |
| `workspace/` | The only folder Jarvis may read or write | no |
| `whisper.cpp/`, `models/` | Speech-to-text engine and weights | no |
