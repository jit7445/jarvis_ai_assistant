from collections.abc import Callable
from typing import Any

from jarvis.core.intent import Intent
from jarvis.core.result import Result
from jarvis.tools import fs
from jarvis.tools.registry import InvalidIntent, check

_HANDLERS: dict[str, Callable[[dict[str, Any], bool], Result]] = {
    "fs.make_dir": lambda a, _: fs.make_dir(a["name"]),
    "fs.write_file": lambda a, confirm: fs.write_file(a["name"], a["body"], confirm),
    "fs.read_file": lambda a, _: fs.read_file(a["name"]),
    "fs.list_dir": lambda a, _: fs.list_dir(),
}


def execute(intent: Intent) -> Result:
    try:
        check(intent)
    except InvalidIntent:
        return Result(False, "I didn't understand that, so I did nothing.")
    handler = _HANDLERS.get(intent.tool)
    if handler is None:
        return Result(False, "I can't do that yet.")
    try:
        return handler(intent.args, intent.confirm)
    except PermissionError:
        return Result(False, "I can only work inside your workspace, so I did nothing.")
    except FileNotFoundError:
        return Result(False, "Your workspace folder is missing, so I did nothing.")
    except OSError:
        return Result(False, "That didn't work, and nothing was changed.")
