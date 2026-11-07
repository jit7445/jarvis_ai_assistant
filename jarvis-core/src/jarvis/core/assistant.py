import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import Enum

import numpy as np

from jarvis.core.confirm import parse_answer
from jarvis.core.router import route
from jarvis.core.wake import is_stop
from jarvis.speech.stt import is_noise, is_silent
from jarvis.tools.executor import execute

CONFIRM_SECONDS = 3.0


class State(Enum):
    LISTENING = "listening"
    THINKING = "thinking"
    HEARD = "heard"
    CONFIRMING = "confirming"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Hooks:
    show: Callable[[State, str], None]
    speak: Callable[[str], None]
    transcribe: Callable[[np.ndarray], str]
    listen: Callable[[float], np.ndarray]
    preview_seconds: float = 0.6
    quit: Callable[[], None] = lambda: None


def _reply(hooks: Hooks, state: State, message: str) -> None:
    hooks.show(state, message)
    hooks.speak(message)


def _hear(hooks: Hooks, audio: np.ndarray) -> str | None:
    if is_silent(audio):
        return None
    hooks.show(State.THINKING, "")
    text = hooks.transcribe(audio)
    return None if is_noise(text) else text


def handle(audio: np.ndarray, hooks: Hooks) -> None:
    try:
        text = _hear(hooks, audio)
        if text is None:
            _reply(hooks, State.FAILED, "I didn't hear anything.")
            return
        _act(text, hooks)
    except Exception:
        _reply(hooks, State.FAILED, "Something went wrong, so I did nothing.")


def handle_text(text: str, hooks: Hooks) -> None:
    try:
        _act(text, hooks)
    except Exception:
        _reply(hooks, State.FAILED, "Something went wrong, so I did nothing.")


def _act(text: str, hooks: Hooks) -> None:
    if is_stop(text, addressed=True):
        _reply(hooks, State.DONE, "Goodbye.")
        hooks.quit()
        return
    hooks.show(State.HEARD, text)
    intent = route(text)
    if intent is None:
        _reply(hooks, State.FAILED, "Sorry, I didn't catch that.")
        return
    # Leave the transcript on screen long enough to spot a mishearing before anything runs.
    time.sleep(hooks.preview_seconds)

    result = execute(intent)
    if not result.needs_confirmation:
        _reply(hooks, State.DONE if result.ok else State.FAILED, result.message)
        return

    _reply(hooks, State.CONFIRMING, result.message)
    hooks.show(State.LISTENING, "Say yes or no.")
    answer = _hear(hooks, hooks.listen(CONFIRM_SECONDS))
    if answer is not None and parse_answer(answer) is True:
        confirmed = execute(replace(intent, confirm=True))
        _reply(hooks, State.DONE if confirmed.ok else State.FAILED, confirmed.message)
    else:
        _reply(hooks, State.DONE, "Okay, I left it as it was.")
