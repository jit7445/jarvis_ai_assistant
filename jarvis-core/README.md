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
jarvis --offline     # never ask Gemini, even with a key set
```

**Wake word.** Say "Jarvis", "hi Jarvis", "hello Jarvis" or "hey Jarvis", either alone (Jarvis answers "Yes?" and waits 6 s for the command) or followed by the command in one sentence. The microphone stays open while Jarvis runs: a loudness detector cuts speech into sentences, whisper transcribes each one locally, and anything not starting with the wake phrase is dropped without being shown, printed or saved. The name in the middle of a sentence ("I told Jarvis...") does not count. Jarvis stops listening while it talks, so it cannot wake itself.

**Stopping by voice.** "Close Jarvis", "stop Jarvis", "quit Jarvis", "goodbye Jarvis" or "Jarvis, stop" makes Jarvis say goodbye and exit, like Ctrl+C. Overheard speech must include the name, and the whole sentence must be the request, so "stop the music" or "we should stop Jarvis from..." do nothing. After the wake word or with the hotkey, a bare "stop" or "close" is enough.

Whisper stays loaded in a local `whisper-server` (127.0.0.1 only), so a command transcribes in about 0.2 s; replies start well under a second after you stop speaking. "Delete X" and "delete everything" move items to the Trash after a spoken yes.

A compact HUD card appears at the bottom of the screen: a reactor of counter-rotating cyan rings whose glow follows your voice and whose colour shows the state, the transcript before anything runs, then the reply. The card stays on screen while Jarvis runs, resting on "Say Jarvis to talk" between commands; drag it anywhere, and its X button closes Jarvis like "close Jarvis" does. Chimes mark start, stop and errors. Overwrites ask for a spoken yes.

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
cmake --build build -j 4 --config Release --target whisper-cli whisper-server
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

## Services

Jarvis core serves a small API on `127.0.0.1:8765` (FastAPI) for `jarvis-gateway`: `/health`, `/tools`, `/transcribe`, `/execute` (after the policy gate, never confirming) and `/command`. Every request needs the shared secret from `JARVIS_CORE_TOKEN` and a localhost `Host`. Without the secret the API stays off and Jarvis works offline. Details in `docs/phase10_results.md`.

## Gemini fallback

When the router does not recognise a sentence, Jarvis asks Gemini to map it onto one of the same tools. Gemini runs in `jarvis-gateway`, not here: core makes no internet request and never sees the key. Put a key from aistudio.google.com/apikey in your shell profile (`~/.zshrc`), never in the repo, and start both services from the repository root:

```bash
export GEMINI_API_KEY="..."            # in ~/.zshrc
../scripts/dev.sh --verbose            # gateway + Jarvis, with a fresh shared secret
```

`scripts/plan_test.py` shows a proposal without running it; it needs `JARVIS_CORE_TOKEN` from a running `dev.sh` session.

It also chats: questions and small talk get a short spoken answer ("how are you", "tell me a joke", "explain it"), with the last 6 exchanges remembered for 5 minutes. A chat reply is only ever spoken, never acted on.

Only the sentence, recent exchanges and the tool list are sent. The reply is checked like any untrusted input: known tool, exact arguments, `safe_path` on names, allowlist for apps, spoken yes for overwrites. No network, a rate limit or a bad reply each get a spoken answer and change nothing. On the free tier Google may use requests to improve its products. Details in `docs/phase7_results.md`.

## Research notes

"Look up black holes and save me a note", "research the Roman Empire" or "find out about whisper.cpp" fetches up to two Wikipedia articles, has Gemini summarise them in a separate call with no tools, and saves `workspace/research/YYYY-MM-DD-topic.md` with the sources and the date they were fetched. Page text is treated as data: it is never sent to the planner and never acted on. Needs `GEMINI_API_KEY`. Details in `docs/phase8_results.md`.

## Video notes

"Make notes from this video" works for whatever you are watching. A YouTube tab (Safari, Chrome, Brave, Edge, Arc) or a QuickTime file is read whole. Anything else (any site, any app) is heard live from the Mac's own sound output until you say "Jarvis, stop notes", 5 minutes of quiet pass, or 90 minutes are up; this needs Screen Recording permission. "Make notes from the video called lecture 3" finds a video or audio file anywhere in your home folder by name (Spotlight). Jarvis extracts the audio, transcribes it on this Mac with whisper, has Gemini write a summary in a separate call with no tools, and saves `workspace/videos/YYYY-MM-DD-title.md` with the source, the summary and the full transcript. Without a key the transcript is still saved.

The first time, macOS asks to let your terminal control the browser or QuickTime (Automation); allow it. Files are read only, only by media extension (mp4, mov, m4v, mkv, webm, avi, mp3, m4a, wav, aac), never in hidden folders or `~/Library`. Videos over 90 minutes are refused. whisper `base.en` is English only. ffmpeg is used when installed, macOS `afconvert` otherwise. Details in `docs/video_notes.md`.

## Coding by voice

"Open jarvis ai assistant in VS Code" opens any git repository in your home folder. "Tell Claude to add a login page" fills the prompt into Claude Code in that window, reads it back and sends it only on your spoken yes. "Review the code" asks Claude for a review; "accept the changes" / "reject the changes" answer its proposed edits. Needs Accessibility for the app Jarvis runs in. Details and safety notes in `docs/coding_by_voice.md`.

## Opening apps

"Open Safari" opens only apps listed in `ALLOWED_APPS` in `src/jarvis/config/__init__.py` (Safari, Notes, Music, Calendar and Chrome). Any other name is refused aloud and never reaches `open`. Terminal, iTerm, Script Editor, Keychain Access, System Settings and a few others sit in `BANNED_APPS` and stay refused even if added to the allowlist. To add an app, add a line such as `"slack": "Slack",` with the spoken name in lowercase. Details in `docs/phase6_results.md`.

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
| `src/jarvis/` | The package: `app.py` (entry point), `core/` (intent, router, confirmation, assistant pipeline), `tools/` (registry, safe paths, file tools, app launcher, executor), `speech/` (whisper, say), `audio/` (recorder), `ui/` (overlay), `planner/` (Gemini fallback), `research/` (Wikipedia notes), `video/` (video notes), `coding/` (VS Code and Claude Code), `config/` | yes |
| `scripts/` | Manual hardware checks | yes |
| `tests/` | pytest suite | yes |
| `docs/` | Phase results and measurements | yes |
| `workspace/` | The only folder Jarvis may read or write | no |
| `whisper.cpp/`, `models/` | Speech-to-text engine and weights | no |
