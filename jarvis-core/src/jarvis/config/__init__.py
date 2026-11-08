from pathlib import Path

CORE_DIR = Path(__file__).resolve().parents[3]
WORKSPACE = CORE_DIR / "workspace"

VOICE = "Samantha"

WHISPER_CLI = CORE_DIR / "whisper.cpp" / "build" / "bin" / "whisper-cli"
WHISPER_MODEL = CORE_DIR / "whisper.cpp" / "models" / "ggml-base.en.bin"
SAMPLE_RATE = 16000
# Without this, base.en splits "Jarvis, create" into "Jarv is created". Names in it are deliberately
# not ones the user is likely to say, so they don't bias real folder names. Tested on silence and
# noise: it never reproduces a command.
WHISPER_PROMPT = (
    "Jarvis, create a folder called Projects. Jarvis, make a note called groceries. "
    "Jarvis, read me groceries. Jarvis, what's in my workspace? Jarvis, open Safari."
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

# Used only when the router does not recognise a sentence and GEMINI_API_KEY is set.
GEMINI_MODEL = "gemini-3.5-flash-lite"
# The Gemini API rejects any deadline under 10 s with HTTP 400.
PLANNER_TIMEOUT_SECONDS = 10.0
# Earlier exchanges sent along with each new sentence, so "tell me more" works.
CHAT_MEMORY_TURNS = 6
CHAT_MEMORY_SECONDS = 300.0

# Research notes (Phase 8). Pages come only from this host; no URL from a page or a model is fetched.
WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKI_PAGE_PREFIX = "https://en.wikipedia.org/wiki/"
# Wikimedia returns 403 unless the agent carries a contact URL in this form (robot policy).
USER_AGENT = "jarvis-core/0.1 (https://github.com/jit7445/jarvis_ai_assistant)"
RESEARCH_DIR = "research"
RESEARCH_SOURCES = 2
RESEARCH_PAGE_CHARS = 6000
RESEARCH_TIMEOUT_SECONDS = 10.0
# Summarising two pages takes longer than planning a command; the card shows progress meanwhile.
SUMMARY_TIMEOUT_SECONDS = 30.0

# Video notes. Video and audio files may be read anywhere in the home folder, read-only, by these
# extensions only; the audio is transcribed on this Mac and only the text goes to Gemini.
VIDEO_DIR = "videos"
MEDIA_SUFFIXES = (".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".mp3", ".m4a", ".wav", ".aac")
MAX_VIDEO_SECONDS = 90 * 60
MAX_TRANSCRIPT_CHARS = 200_000
FFMPEG_CANDIDATES = ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg")
# Live video notes stop by themselves after this much quiet (video paused or finished).
LIVE_SILENCE_STOP_SECONDS = 5 * 60
