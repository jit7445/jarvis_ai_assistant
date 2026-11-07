import re

# Spellings base.en produces for "Jarvis"; a fixed list, not fuzzy matching.
_NAME = r"(?:jarvis|jarviss|jarvish|jervis|javis|jarv is)"
_WAKE = re.compile(
    rf"^[\s\"'.,!?-]*(?:(?:hi|hello|hey|ok|okay)[\s,.!-]+)?{_NAME}\b[\s,.!?:;-]*",
    re.IGNORECASE,
)


def split_wake(transcript: str) -> str | None:
    """The command after a leading wake phrase ("" if there is none), or None without one."""
    if not isinstance(transcript, str):
        return None
    match = _WAKE.match(transcript)
    if match is None:
        return None
    return transcript[match.end():].strip()


_STOP_WORD = (r"(?:stop|close|quit|exit|goodbye|good bye|bye|bye bye|shut down|shutdown|turn off"
              r"|go to sleep)")
_GREETING = r"(?:(?:hi|hello|hey|ok|okay) )?"
_NAMED_STOP = re.compile(
    rf"^(?:{_GREETING}{_NAME} (?:please )?{_STOP_WORD}"
    rf"|(?:please )?{_STOP_WORD} (?:the )?{_NAME})(?: please)?$")
_BARE_STOP = re.compile(rf"^(?:please )?{_STOP_WORD}(?: please)?$")


def is_stop(transcript: str, addressed: bool = False) -> bool:
    """Whether the whole sentence asks Jarvis to shut down.

    Overheard speech must name Jarvis; once addressed (after the wake word or the hotkey) the bare
    word is enough.
    """
    if not isinstance(transcript, str):
        return False
    text = " ".join(re.sub(r"[^\w\s']", " ", transcript.lower()).split())
    if _NAMED_STOP.match(text):
        return True
    return addressed and bool(_BARE_STOP.match(text))
