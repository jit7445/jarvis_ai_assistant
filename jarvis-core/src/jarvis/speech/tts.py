import re
import subprocess
from functools import cache

from jarvis import config

_VOICE_LINE = re.compile(r"^(.*\S)\s+[a-z]{2,3}_[A-Za-z0-9]+\s+#")


@cache
def installed_voices() -> frozenset[str]:
    listing = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, check=True)
    return frozenset(
        m.group(1).strip() for line in listing.stdout.splitlines() if (m := _VOICE_LINE.match(line))
    )


def speak(text: str, voice: str | None = None) -> None:
    voice = voice or config.VOICE
    text = text.strip()
    if not text:
        return
    if voice not in installed_voices():
        raise ValueError(f"voice not installed: {voice!r}")
    # Text goes in on stdin, never argv: say parses a leading "-" in argv as one of its own options.
    subprocess.run(["say", "-v", voice], input=text, text=True, check=True)
