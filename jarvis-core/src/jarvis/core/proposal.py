from typing import Any

from jarvis.core.intent import Intent
from jarvis.tools.paths import safe_path
from jarvis.tools.registry import InvalidIntent, check

_PATH_ARGS = ("name",)


def to_intent(proposal: Any) -> Intent | None:
    """A checked Intent from a model's reply, or None when it says no tool fits.

    Raises InvalidIntent or PermissionError for anything else. The model cannot set confirm, so an
    overwrite it proposes still asks for a spoken yes.
    """
    if not isinstance(proposal, dict) or not set(proposal) <= {"tool", "args"}:
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
