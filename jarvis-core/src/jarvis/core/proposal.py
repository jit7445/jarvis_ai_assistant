import re
from typing import Any

from jarvis.core.intent import Intent
from jarvis.tools.paths import safe_path
from jarvis.tools.registry import TOOLS, InvalidIntent, check

_PATH_ARGS = ("name",)
MAX_REPLY_CHARS = 500
_MARKUP = re.compile(r"[*_#`>|~]+|\[([^\]]*)\]\([^)]*\)")


def to_intent(proposal: Any) -> Intent | None:
    """A checked Intent from a model's reply, or None when it says no tool fits.

    Lenient about shape, strict about power: extra fields and arguments are dropped and numbers
    become text, but the tool must exist, every argument it needs must be there, names go
    through safe_path, and confirm is never taken from the model, so an overwrite or a prompt to
    Claude still needs a spoken yes. Raises InvalidIntent or PermissionError otherwise.
    """
    if not isinstance(proposal, dict):
        raise InvalidIntent("reply is not a tool call")
    tool = proposal.get("tool")
    if tool is None:
        return None
    if not isinstance(tool, str) or tool not in TOOLS:
        raise InvalidIntent("unknown tool")
    args = proposal.get("args")
    if args is None:
        # Some replies put the arguments beside "tool" instead of inside "args".
        args = {key: proposal[key] for key in TOOLS[tool] if key in proposal}
    if not isinstance(args, dict):
        raise InvalidIntent("arguments are not an object")
    kept = {}
    for key in TOOLS[tool]:
        if key not in args:
            raise InvalidIntent(f"missing {key}")
        value = args[key]
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value = str(value)
        kept[key] = value
    intent = check(Intent(tool, kept))
    for key in _PATH_ARGS:
        if key in intent.args and intent.tool.startswith("fs."):
            safe_path(intent.args[key])
    return intent


def chat_reply(proposal: Any) -> str | None:
    """The words to speak when the model answered instead of choosing a tool, or None.

    The text is only ever spoken and shown; nothing in it is acted on.
    """
    if not isinstance(proposal, dict) or proposal.get("tool") is not None:
        return None
    reply = proposal.get("reply")
    if not isinstance(reply, str):
        return None
    text = " ".join(_MARKUP.sub(lambda m: m.group(1) or "", reply).split())
    if len(text) > MAX_REPLY_CHARS:
        cut = text[:MAX_REPLY_CHARS]
        end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
        text = cut[:end + 1] if end > 0 else cut.rsplit(" ", 1)[0] + "..."
    return text or None
