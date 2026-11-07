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

## Running Jarvis

```bash
jarvis              # say "Jarvis ..." or hold the right Option key
jarvis --no-wake    # hotkey only; microphone closed until you press it
jarvis --once       # listen for 5 s now, no hotkey or permissions needed
jarvis --wav workspace/route_test.wav --mute --verbose
```

**Wake word.** Say "Jarvis", "hi Jarvis", "hello Jarvis" or "hey Jarvis", either alone (Jarvis answers "Yes?" and waits 6 s for the command) or followed by the command in one sentence. The microphone stays open while Jarvis runs: a loudness detector cuts speech into sentences, whisper transcribes each one locally, and anything not starting with the wake phrase is dropped without being shown, printed or saved. The name in the middle of a sentence ("I told Jarvis...") does not count. Jarvis stops listening while it talks, so it cannot wake itself.

**Stopping by voice.** "Close Jarvis", "stop Jarvis", "quit Jarvis", "goodbye Jarvis" or "Jarvis, stop" makes Jarvis say goodbye and exit, like Ctrl+C. Overheard speech must include the name, and the whole sentence must be the request, so "stop the music" or "we should stop Jarvis from..." do nothing. After the wake word or with the hotkey, a bare "stop" or "close" is enough.

A Siri-style overlay appears at the bottom of the screen: a spinning orb whose glow follows your voice, the transcript before anything runs, then the reply. Chimes mark start, stop and errors. Overwrites ask for a spoken yes.

The hotkey needs Accessibility permission for the app you launch Jarvis from (System Settings > Privacy & Security > Accessibility), and that app must be restarted after granting it. Pressing any other key while holding Option cancels the recording, so typing Option shortcuts never triggers Jarvis.

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

## Command router

```bash
python scripts/route_test.py create a folder called Research   # typed
python scripts/route_test.py --wav workspace/mic_test.wav       # from a recording
python scripts/route_test.py                                    # speak for 5 s
python scripts/route_test.py --run                              # speak, then act and reply aloud
```

With `--run`, the command is executed through `jarvis.tools.executor.execute` and the result is spoken. Overwriting a note asks for a spoken yes first.

## Opening apps

"Open Safari" opens only apps listed in `ALLOWED_APPS` in `src/jarvis/config/__init__.py` (Safari, Notes, Music and Calendar by default). Any other name is refused aloud and never reaches `open`. Terminal, iTerm, Script Editor, Keychain Access, System Settings and a few others sit in `BANNED_APPS` and stay refused even if added to the allowlist. To add an app, add a line such as `"slack": "Slack",` with the spoken name in lowercase. Details in `docs/phase6_results.md`.

## Workspace

Jarvis reads and writes only inside `workspace/`. Every path goes through `jarvis.tools.paths.safe_path`, which refuses `..`, absolute paths, `~`, hidden names and symlinks that lead outside. Details in `docs/phase5_results.md`.

`jarvis.core.router.route()` turns a transcript into an `Intent` with plain pattern matching, or returns `None`. Every intent is checked against the fixed tool list in `jarvis.tools.registry`. Supported phrases are listed in `docs/phase4_results.md`.

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
| `src/jarvis/` | The package: `app.py` (entry point), `core/` (intent, router, confirmation, assistant pipeline), `tools/` (registry, safe paths, file tools, app launcher, executor), `speech/` (whisper, say), `audio/` (recorder), `ui/` (overlay), `config/` | yes |
| `scripts/` | Manual hardware checks | yes |
| `tests/` | pytest suite | yes |
| `docs/` | Phase results and measurements | yes |
| `workspace/` | The only folder Jarvis may read or write | no |
| `whisper.cpp/`, `models/` | Speech-to-text engine and weights | no |
