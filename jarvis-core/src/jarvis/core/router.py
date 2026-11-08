import re

from jarvis import config
from jarvis.core.intent import Intent
from jarvis.tools import apps
from jarvis.tools.registry import check

_WS = r"(?:in|inside|to|into) (?:my |the )?workspace"
_MAKE = r"(?:create|make|add|set up|start|build|give me|i need|i want)"
_A = r"(?:me )?(?:a |an |the |one )?(?:new )?"
_DIR = r"(?:folder|directory)"
_NAMED = r"(?:called|named|titled|with the name|by the name|for)"
_BODY = (r"(?:,? (?:saying|that says|which says|with the text|containing|with|that reads|reading)[,:]? "
         r"|: )")
# A name that is really the start of a body or a filler word, as in "make a note saying hi".
_NOT_NAME = (r"(?!(?:saying|that|which|with|containing|about|reading|new|a|an|the|my|called|named"
             r"|titled|for)\b)")

_PREFIX = re.compile(
    r"^(?:(?:hey|hi|hello|ok|okay)\s+)?jarvis\b[\s,.!:]*"
    r"|^(?:please|can you|could you|would you|will you|go ahead and|i want you to|i'd like you to"
    r"|i would like you to|let's|lets|kindly)\s+",
    re.IGNORECASE,
)
_SUFFIX = re.compile(r"(?:[\s,]+(?:please|jarvis|thanks|thank you|for me|now|right now))+$",
                     re.IGNORECASE)

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # folders
    (rf"^{_MAKE} {_A}{_DIR} (?:{_WS} )?(?:{_NAMED} )?{_NOT_NAME}(?P<name>.+?)(?: {_WS})?$",
     "fs.make_dir"),
    (rf"^{_MAKE} {_A}{_NOT_NAME}(?P<name>.+?) {_DIR}(?: {_WS})?$", "fs.make_dir"),
    (rf"^new {_DIR} (?:{_NAMED} )?{_NOT_NAME}(?P<name>.+)$", "fs.make_dir"),
    # notes
    (rf"^(?:{_MAKE}|write|take|save|jot down) {_A}note (?:{_WS} )?(?:{_NAMED} )?{_NOT_NAME}"
     rf"(?P<name>.+?)(?:{_BODY}(?P<body>.+))?$", "fs.write_file"),
    (rf"^(?:{_MAKE}|write|take|save) {_A}{_NOT_NAME}(?P<name>.+?) note(?:{_BODY}(?P<body>.+))?$",
     "fs.write_file"),
    (rf"^new note (?:{_NAMED} )?{_NOT_NAME}(?P<name>.+?)(?:{_BODY}(?P<body>.+))?$",
     "fs.write_file"),
    # listing
    (rf"^(?:what's|what is|whats) (?:in|inside) (?:my |the )?workspace$"
     rf"|^(?:list|show|tell)(?: me)? (?:all )?(?:of )?(?:what's {_WS}|what i have(?: {_WS})?"
     rf"|everything(?: {_WS})?|(?:my |the )?(?:workspace|files|notes|folders|stuff|things)"
     rf"(?: {_WS})?)$"
     rf"|^what (?:files |notes |folders |things |stuff )?(?:do i have|have i got|are there|is there)"
     rf"(?: {_WS})?$", "fs.list_dir"),
    # reading
    (r"^read (?:me |out |aloud )?(?:out )?(?:the |my )?(?:(?:note|file) )?(?:called |named )?"
     r"(?P<name>.+?)(?: (?:note|file))?(?: (?:aloud|out loud|to me))?$", "fs.read_file"),
    (r"^(?:what's|what is|whats) (?:in|on) (?:the |my )?(?:note|file) (?:called |named )?(?P<name>.+)$"
     r"|^what does (?:the |my )?(?:note )?(?:called |named )?(?P<name2>.+?)(?: note)? say$"
     r"|^(?:show|open) (?:me )?(?:the |my )?note (?:called |named )?(?P<name3>.+)$",
     "fs.read_file"),
    # research
    (r"^(?:look up|research|find out about|find out|read up on|look into|search for"
     r"|search (?:the web|online|wikipedia) for|google)"
     r" (?P<topic>.+?)(?:,? and (?:save|make|write|take|put|give)(?: me)? (?:it in |it as )?"
     r"(?:a |an )?(?:research )?(?:note|it)(?: (?:on|about) it)?)?$", "web.research"),
    (r"^(?:make|write|save|give|create)(?: me)? (?:a |an )?research note (?:on|about|for) "
     r"(?P<topic>.+)$", "web.research"),
    # apps
    (r"^(?:open|launch|start|run|fire up|bring up|switch to|load) (?:up )?"
     r"(?!(?:the |my )?(?:app|it|that|this|application)$)(?:the |my )?(?P<app_name>.+?)"
     r"(?: app| application)?$", "app.open"),
]
_COMPILED = [(re.compile(p, re.IGNORECASE), tool) for p, tool in _PATTERNS]


def normalise(transcript: str) -> str:
    text = transcript.replace("’", "'").replace("‘", "'")
    text = " ".join(text.split())
    text = text.strip(" \"'.,!?;:")
    for _ in range(3):
        text = _PREFIX.sub("", text).strip(" ,")
    text = _SUFFIX.sub("", text)
    return text.strip(" \"'.,!?;:")


def _known_app(name: str) -> bool:
    """Allowlisted or banned: both are answered here. Anything else is left to the planner, which
    may know that "my browser" means Safari."""
    try:
        apps.resolve(name)
        return True
    except PermissionError:
        key = " ".join(name.split()).lower().removesuffix(" browser")
        return key in config.BANNED_APPS


def route(transcript: str) -> Intent | None:
    if not isinstance(transcript, str):
        return None
    text = normalise(transcript)
    if not text:
        return None
    for pattern, tool in _COMPILED:
        match = pattern.match(text)
        if not match:
            continue
        groups = {k.rstrip("23"): v for k, v in match.groupdict().items() if v is not None}
        # Trailing punctuation only: stripping leading dots would turn ".env" into "env".
        args = {k: v.strip(" \"'").rstrip(".,") for k, v in groups.items()}
        if tool == "fs.write_file":
            args.setdefault("body", "")
        if tool == "app.open" and not _known_app(args.get("app_name", "")):
            return None
        try:
            return check(Intent(tool, args))
        except ValueError:
            return None
    return None
