import re
from typing import Any

from jarvis.core.intent import Intent
from jarvis.tools.paths import safe_path
from jarvis.tools.registry import InvalidIntent, check

_PATH_ARGS = ("name",)
MAX_REPLY_CHARS = 500
_MARKUP = re.compile(r"[*_#`>|~]+|\[([^\]]*)\]\([^)]*\)")


def to_intent(proposal: Any) -> Intent | None:
    """A checked Intent from a model's reply, or None when it says no tool fits.

    Raises InvalidIntent or PermissionError for anything else. The model cannot set confirm, so an
    overwrite it proposes still asks for a spoken yes.
    """
    if not isinstance(proposal, dict) or not set(proposal) <= {"tool", "args", "reply"}:
        raise InvalidIntent("reply is not a tool call")
    tool, args = proposal.get("tool"), proposal.get("args", {})
    if tool is None:
        return None
    if not isinstance(tool, str):
        raise InvalidIntent("tool must be a string")
    intent = check(Intent(tool, args))
    for key in _PATH_ARGS:
        if key in intent.args:
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
