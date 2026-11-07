# jarvis-core

The Python service that owns the machine. Requires an Apple Silicon Mac and Python 3.11.

## Setup

```bash
cd jarvis-core
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Activate `.venv` in every new terminal.

## Microphone check

```bash
python scripts/mic_test.py
```

Records 5 seconds at 16 kHz mono to `workspace/mic_test.wav`. The first run triggers the macOS microphone permission prompt; recordings made while the prompt is open come out silent.

## Layout

| Path | Contents | In git |
| --- | --- | --- |
| `scripts/` | Manual hardware checks | yes |
| `tests/` | pytest suite | yes |
| `docs/` | Phase results and measurements | yes |
| `workspace/` | The only folder Jarvis may read or write | no |
| `whisper.cpp/`, `models/` | Speech-to-text engine and weights | no |
