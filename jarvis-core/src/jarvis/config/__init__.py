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
