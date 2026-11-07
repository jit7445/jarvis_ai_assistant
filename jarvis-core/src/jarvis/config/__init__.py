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
