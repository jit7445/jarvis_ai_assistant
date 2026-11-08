import os
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parents[3]
WORKSPACE = CORE_DIR / "workspace"

VOICE = "Samantha"

WHISPER_CLI = CORE_DIR / "whisper.cpp" / "build" / "bin" / "whisper-cli"
# Kept running with the model loaded, so a command does not pay the load cost each time.
WHISPER_SERVER = CORE_DIR / "whisper.cpp" / "build" / "bin" / "whisper-server"
WHISPER_SERVER_START_SECONDS = 60.0
WHISPER_MODEL = CORE_DIR / "whisper.cpp" / "models" / "ggml-base.en.bin"
SAMPLE_RATE = 16000
# Without this, base.en splits "Jarvis, create" into "Jarv is created". Names in it are deliberately
# not ones the user is likely to say, so they don't bias real folder names. Tested on silence and
# noise: it never reproduces a command.
WHISPER_PROMPT = (
    "Jarvis, create a folder called Projects. Jarvis, make a note called groceries. "
    "Jarvis, read me groceries. Jarvis, what's in my workspace? Jarvis, open Safari. "
    "Jarvis, open the demo repo in VS Code. Jarvis, tell Claude to add tests."
)

# Spoken name (lowercase) to the macOS app it opens. Only you edit this; no command can change it.
ALLOWED_APPS = {
    "safari": "Safari",
    "notes": "Notes",
    "music": "Music",
    "calendar": "Calendar",
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "google": "Google Chrome",
    "crome": "Google Chrome",
}
# Refused even if added above: any of these gives a voice command shell or system access.
BANNED_APPS = {"terminal", "iterm", "iterm2", "script editor", "keychain access", "system settings",
               "system preferences", "automator", "shortcuts", "console", "activity monitor"}

# Two local services (Phase 10). Core owns the Mac and makes no internet request; the gateway
# owns the network (Gemini, Wikipedia, YouTube) and the browser UI. Both bind to 127.0.0.1 and
# share a secret from the environment, created fresh by scripts/dev.sh.
LOCALHOST = "127.0.0.1"
CORE_PORT = int(os.environ.get("JARVIS_CORE_PORT", "8765"))
GATEWAY_PORT = int(os.environ.get("JARVIS_GATEWAY_PORT", "4300"))
TOKEN_ENV = "JARVIS_CORE_TOKEN"
TOKEN_HEADER = "X-Jarvis-Token"
MAX_UPLOAD_BYTES = 400 * 1024 * 1024
# Waits for the gateway's answers. Gemini itself rejects deadlines under 10 s.
PLANNER_TIMEOUT_SECONDS = 20.0
SUMMARY_TIMEOUT_SECONDS = 120.0
DOWNLOAD_TIMEOUT_SECONDS = 600.0

# Research notes are written here; the sources must be Wikipedia pages.
RESEARCH_DIR = "research"
WIKI_PAGE_PREFIX = "https://en.wikipedia.org/wiki/"

# Video notes. Video and audio files may be read anywhere in the home folder, read-only, by these
# extensions only; the audio is transcribed on this Mac and only the text goes to the gateway.
VIDEO_DIR = "videos"
MEDIA_SUFFIXES = (".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".mp3", ".m4a", ".wav", ".aac")
MAX_VIDEO_SECONDS = 90 * 60
MAX_TRANSCRIPT_CHARS = 200_000
FFMPEG_CANDIDATES = ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg")
# Live video notes stop by themselves after this much quiet (video paused or finished).
LIVE_SILENCE_STOP_SECONDS = 5 * 60

# Coding by voice: any git repository in the home folder can be opened in VS Code, and prompts go
# to the Claude Code extension through its own link, filled in but not sent until a spoken yes.
VSCODE_APP = "Visual Studio Code"
# The code command focuses a folder's existing window; open -a makes an untitled workspace.
VSCODE_CLI_CANDIDATES = ("/usr/local/bin/code", "/opt/homebrew/bin/code",
                         "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code")
VSCODE_PROCESS = "Code"
CLAUDE_CODE_URI = "vscode://anthropic.claude-code/open"
REPO_SEARCH_DEPTH = 5
REPO_SKIP = {"Library", "Applications", "node_modules", "venv", "dist", "build", "target",
             "Pictures", "Music", "Movies", "whisper.cpp", "site-packages", "__pycache__"}
MAX_PROMPT_CHARS = 2000
REVIEW_PROMPT = (
    "Review the uncommitted changes in this repository (git diff, plus any new files). "
    "List bugs, risky code and missing tests, most important first, with file and line. "
    "Do not change any files."
)
# Claude Code writes each conversation to ~/.claude/projects/<folder with non-alphanumerics as ->/.
CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"
CLAUDE_REPLY_WAIT_SECONDS = 15 * 60
SPOKEN_REPLY_CHARS = 700
