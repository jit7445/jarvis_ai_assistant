from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Intent:
    tool: str
    args: dict[str, Any]
    confirm: bool = False
