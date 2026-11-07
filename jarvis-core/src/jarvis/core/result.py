from dataclasses import dataclass


@dataclass(frozen=True)
class Result:
    ok: bool
    message: str
    needs_confirmation: bool = False
