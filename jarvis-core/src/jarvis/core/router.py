import re

from jarvis.core.intent import Intent
from jarvis.tools.registry import check

_WORKSPACE = r"(?:in|inside) (?:my|the) workspace"

_PREFIX = re.compile(
    r"^(?:(?:hey|hi|ok|okay)\s+)?jarvis\b[\s,.!:]*"
    r"|^(?:please|can you|could you|would you|will you)\s+",
    re.IGNORECASE,
)
_SUFFIX = re.compile(r"(?:[\s,]+(?:please|jarvis|thanks|thank you))+$", re.IGNORECASE)

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(
        rf"^(?:create|make) (?:a |an )?(?:new )?folder (?:{_WORKSPACE} )?(?:called|named) "
        rf"(?P<name>.+?)(?: {_WORKSPACE})?$", re.IGNORECASE),
     "fs.make_dir"),
    (re.compile(
        r"^(?:make|create|write|take) (?:a |an )?(?:new )?note (?:called|named|titled) "
        r"(?P<name>.+?)(?:,? (?:saying|that says) (?P<body>.+))?$", re.IGNORECASE),
     "fs.write_file"),
    (re.compile(
        r"^read (?:me )?(?:the |my )?(?:(?:note|file) )?(?:called |named )?(?P<name>.+)$",
        re.IGNORECASE),
     "fs.read_file"),
    (re.compile(
        rf"^(?:what's|what is|whats) (?:in|inside) (?:my|the) workspace$"
        rf"|^(?:list|show)(?: me)? (?:what's {_WORKSPACE}|(?:my|the) workspace)$", re.IGNORECASE),
     "fs.list_dir"),
    (re.compile(r"^open (?:up )?(?!(?:the )?(?:app|it|that|this)$)(?:the )?(?P<app_name>.+?)(?: app)?$",
                re.IGNORECASE),
     "app.open"),
]


def normalise(transcript: str) -> str:
    text = transcript.replace("’", "'").replace("‘", "'")
    text = " ".join(text.split())
    text = text.strip(" \"'.,!?;:")
    for _ in range(2):
        text = _PREFIX.sub("", text).strip(" ,")
    text = _SUFFIX.sub("", text)
    return text.strip(" \"'.,!?;:")


def route(transcript: str) -> Intent | None:
    if not isinstance(transcript, str):
        return None
    text = normalise(transcript)
    if not text:
        return None
    for pattern, tool in _PATTERNS:
        match = pattern.match(text)
        if not match:
            continue
        # Trailing punctuation only: stripping leading dots would turn ".env" into "env".
        args = {k: v.strip(" \"'").rstrip(".,") for k, v in match.groupdict().items()
                if v is not None}
        if tool == "fs.write_file":
            args.setdefault("body", "")
        try:
            return check(Intent(tool, args))
        except ValueError:
            return None
    return None
