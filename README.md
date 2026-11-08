# Jarvis

A voice assistant for macOS on Apple Silicon. Say "Jarvis" (or hold the right Option key), speak, and Jarvis acts on your Mac and answers out loud. Speech is transcribed on your Mac; only sentences Jarvis does not understand on its own go to Gemini.

## Features

| Feature | Try saying |
| --- | --- |
| Wake word and push-to-talk | "Jarvis", "hi Jarvis", or hold the right Option key |
| Folders and notes in your workspace | "Create a folder called Research", "make a note called groceries saying milk and eggs", "read me groceries", "what's in my workspace" |
| Delete, after asking (to the Trash) | "Delete groceries", "delete everything in my workspace" |
| Open allowlisted apps | "Open Safari", "open my Chrome browser" |
| Chat | "How are you?", "tell me a joke", "explain it" |
| Research notes with sources (Wikipedia) | "Look up black holes and save me a note" |
| Notes from videos | "Make notes from this video" (YouTube, QuickTime, or any app by listening to the Mac's sound), "make notes from the video called lecture 3", "Jarvis, stop notes" |
| Coding with Claude Code in VS Code | "Open code mining project in VS Code", "explain this code", "tell Claude to add tests", "review the code", "accept the changes", "what did Claude say" |
| Stop by voice | "Close Jarvis", "stop Jarvis" |

A small card at the bottom of the screen shows what Jarvis heard and what it is doing. A browser dashboard at http://127.0.0.1:4300 shows the same live, and accepts typed commands.

## How it is built

| Folder | Runtime | Owns |
| --- | --- | --- |
| [jarvis-core](jarvis-core/) | Python | The Mac: microphone, wake word, whisper.cpp, speech output, workspace and app tools, VS Code, and the policy gate that checks every action |
| [jarvis-gateway](jarvis-gateway/) | Node.js | The network: Gemini, Wikipedia, YouTube downloads, and the dashboard |

Core makes no internet requests and never sees the Gemini key. Both services listen on `127.0.0.1` only, and every request to core carries a secret created fresh each time you start them.

## Requirements

- A Mac with Apple Silicon (M1 or later)
- Python 3.11
- Node.js 22
- Optional: a Gemini API key from https://aistudio.google.com/apikey (for chat, unknown sentences, research and video summaries)
- Optional: `ffmpeg` and `yt-dlp` (`brew install ffmpeg yt-dlp`) for video notes

## Set up

**1. Jarvis core**

```bash
cd jarvis-core
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

**2. Speech-to-text (whisper.cpp)**

```bash
cd jarvis-core
git clone --depth 1 --branch v1.9.1 https://github.com/ggml-org/whisper.cpp.git
cd whisper.cpp
cmake -B build -DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF
cmake --build build -j 4 --config Release --target whisper-cli whisper-server
sh ./models/download-ggml-model.sh base.en
```

Use the `cmake` from the virtual environment (it is arm64). If Homebrew lives in `/usr/local`, its `cmake` is x86_64 and builds without Metal.

**3. Gateway**

```bash
cd jarvis-gateway
npm ci --ignore-scripts
```

**4. Gemini key (optional)**

Add it to your shell profile, never to the repository:

```bash
echo 'export GEMINI_API_KEY="your-key"' >> ~/.zshrc
```

Then open a new terminal.

## Run

From the repository root:

```bash
scripts/dev.sh --verbose
```

This starts the gateway, then Jarvis. Say "Jarvis" and a command. Ctrl+C, "close Jarvis" or the card's X button stops both. Open http://127.0.0.1:4300 for the dashboard.

To start Jarvis core on its own (no gateway, so no Gemini, research or YouTube):

```bash
cd jarvis-core && source .venv/bin/activate
jarvis                 # wake word and right Option key
jarvis --no-wake       # right Option key only
jarvis --offline       # never use Gemini
```

## macOS permissions

Grant these to the app you run Jarvis from (Terminal, iTerm or VS Code) in System Settings > Privacy & Security, then quit and reopen that app:

| Permission | Needed for |
| --- | --- |
| Microphone | Hearing you |
| Accessibility | The right Option key, and pressing Enter in Claude Code after your "yes" |
| Screen Recording | Notes from any video by listening to the Mac's sound |
| Automation (System Events, your browser, QuickTime) | Finding the video you are watching and bringing VS Code forward; macOS asks the first time |

## Your workspace

Jarvis reads and writes only inside `jarvis-core/workspace/`. Research notes go to `workspace/research/`, video notes to `workspace/videos/`. Deleting moves items to the Trash after a spoken yes.

To let Jarvis open more apps, add a line to `ALLOWED_APPS` in `jarvis-core/src/jarvis/config/__init__.py`, for example `"slack": "Slack",`. Terminal, Keychain Access, System Settings and similar apps are always refused.

## Tests

```bash
cd jarvis-core && source .venv/bin/activate && python -m pytest
cd jarvis-gateway && npm test
cd jarvis-core && python scripts/e2e_test.py      # spoken commands through the real pipeline
```

## Privacy

- Your voice is transcribed on your Mac by whisper.cpp.
- Sentences Jarvis understands by itself never leave your Mac.
- Other sentences, the last few exchanges, research topics and video transcripts go to Gemini through the gateway. On the free tier Google may use them to improve its products. `jarvis --offline` turns this off.
- Video audio is transcribed locally; only the text is summarised by Gemini.
- Nothing you say is written to disk except the notes you ask for.
