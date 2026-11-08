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

# whisper writes VS Code as "BS code", "V.S. code", "vscode"; Claude as "cloud" or "Claud".
_VSCODE = r"(?:(?:v\.? ?s\.?|b\.? ?s\.?|visual studio|visual) ?code|vscode|code)"
_CLAUDE = r"(?:claude|claud|cloud|clod|clawed)(?: code)?"
_VIDEO = r"(?:youtube |yt )?video"
_NOTES = r"(?:make|take|write|create|save|give|get)(?: me)? (?:some |a |the )?(?:notes?|summary)"

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # coding with Claude Code in VS Code
    (rf"^open (?:up )?(?:the |my )?(?:project |repo |repository |folder )?(?P<name>.+?)"
     rf"(?: project| repo| repository| folder)? (?:in|with|on|using) {_VSCODE}$"
     rf"|^open {_VSCODE} (?:with|for|in|on) (?:the |my )?"
     rf"(?:project |repo |repository |folder )?(?P<name2>.+?)(?: project| repo| repository)?$"
     rf"|^(?:find|search for|look for|open)(?: the| my)? (?:repo|repository|project|folder),?"
     rf" (?:call|called|named) (?P<name3>.+?)(?:,? and open it)?(?: in {_VSCODE})?$",
     "code.open_repo"),
    (rf"^(?:review (?:the |my |this )?(?:code|changes)|do a code review|code review"
     rf"|(?:ask|tell) {_CLAUDE} to review (?:the |my |this )?(?:code|changes))$", "code.review"),
    (rf"^(?:what did {_CLAUDE} say|what (?:was|is) {_CLAUDE}'?s? (?:answer|reply)"
     rf"|(?:read|repeat|tell)(?: me)? (?:the |{_CLAUDE}'?s? )?(?:answer|reply|response)(?: again)?"
     rf"|(?:read|repeat) (?:what )?{_CLAUDE} (?:said|wrote)(?: again)?)$", "code.last_reply"),
    (r"^(?:accept|approve|keep) (?:the |these |those |all )?(?:changes?|edits?|diff|code)$",
     "code.accept"),
    (r"^(?:reject|decline|discard|undo) (?:the |these |those |all )?(?:changes?|edits?|diff)$",
     "code.reject"),
    (r"^(?P<prompt4>(?:explain|describe|summari[sz]e|walk me through|go through|read|analy[sz]e)"
     r"(?: me| to me)? (?:the |this |my |that )?(?:code|codebase|source code|source|repo|repository)"
     r"(?: (?:of|in|for|from) .+)?)$"
     r"|^(?P<prompt5>(?:what does|how does) (?:the |this |my )?(?:code|codebase|project|repo|app)"
     r" .+)$", "code.ask_claude"),
    (rf"^(?:tell|ask|have|let|get|make|use) {_CLAUDE}(?: to)?[,:]? (?P<prompt>.+)$"
     rf"|^(?:send|give) (?:this |that )?to {_CLAUDE}[,:]? (?P<prompt2>.+)$"
     rf"|^{_CLAUDE}[,:] (?P<prompt3>.+)$", "code.ask_claude"),
    # live video notes: stop, then explicit start
    (r"^(?:stop|end|finish|done with|wrap up|save)(?: (?:taking|making|the|my|video|recording|those))*"
     r" (?:notes?|recording)(?: now)?$"
     r"|^(?:stop listening to|i'm done with|i am done with|i finished) (?:the |this )?(?:video|movie|lecture)$"
     r"|^(?:the )?video (?:is )?(?:done|over|finished)$", "video.notes_stop"),
    (r"^(?:start )?(?:take|taking|make|making) notes (?:while i watch|as i watch|on what's playing)$"
     r"|^start (?:taking |making )?(?:video )?notes$"
     r"|^listen (?:to (?:the |my )?(?:video|sound|audio|mac) )?and (?:take|make) notes$",
     "video.notes_live"),
    # video notes: the one playing now, then a file by name
    (rf"^(?:{_NOTES} (?:from|on|of|about|for)|summari[sz]e|transcribe|take notes on|make notes on"
     rf"|note down|listen to) (?:this|the|that|my|the current|my current) {_VIDEO}"
     rf"(?: (?:i'm|i am|that's|that is) (?:watching|playing|on))?(?: (?:now|right now))?$",
     "video.notes_current"),
    (rf"^(?:{_NOTES} (?:from|on|of|about|for)|summari[sz]e|transcribe|take notes on|make notes on"
     rf"|listen to) (?:the |my )?{_VIDEO} (?:file )?(?:called |named |titled )?(?P<query>.+)$",
     "video.notes_file"),
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
    # deleting: everything, then one item (both always ask first)
    (rf"^(?:delete|remove|clear|empty|wipe|erase|trash|clean)(?: out)? (?:all|everything"
     rf"|the whole workspace|my whole workspace|my workspace|the workspace)"
     rf"(?: {_WS}| from (?:my |the )?workspace)?$"
     rf"|^(?:clear|empty|wipe|clean)(?: out)? (?:my |the )?workspace$", "fs.delete_all"),
    (r"^(?:delete|remove|trash|erase|get rid of|throw away) (?!all\b)(?:the |my )?(?:folder |note |file )?"
     r"(?:called |named )?(?P<name>.+?)(?: folder| note| file)?(?: from (?:my |the )?workspace)?$",
     "fs.delete"),
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


# whisper repeats a false start: "open, Jarvis, open, demo repo".
_STUTTER = re.compile(r"^(\w+)[\s,.]+(?:jarvis[\s,.]+)?\1\b[\s,.]*", re.IGNORECASE)


def normalise(transcript: str) -> str:
    text = transcript.replace("’", "'").replace("‘", "'")
    text = " ".join(text.split())
    text = _STUTTER.sub(r"\1 ", text.strip(" \"'.,!?;:"))
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
        groups = {k.rstrip("2345"): v for k, v in match.groupdict().items() if v is not None}
        # Trailing punctuation only: stripping leading dots would turn ".env" into "env".
        args = {k: v.strip(" \"'").rstrip(".,") for k, v in groups.items()}
        if tool == "fs.write_file":
            args.setdefault("body", "")
        if tool == "app.open" and not _known_app(args.get("app_name", "")):
            # "open livedoc": not an app, but maybe a project.
            from jarvis.coding import repos
            name = args.get("app_name", "")
            if repos.find(name) is not None:
                return check(Intent("code.open_repo", {"name": name}))
            return None
        try:
            return check(Intent(tool, args))
        except ValueError:
            return None
    return None
