import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import Enum

import numpy as np

from jarvis.core.confirm import parse_answer
from jarvis.core.intent import Intent
from jarvis.core.proposal import chat_reply, to_intent
from jarvis.core.router import route
from jarvis.core.wake import is_stop
from jarvis.planner import Planner, PlannerBusy, PlannerError, PlannerSetup
from jarvis.speech.stt import is_noise, is_silent
from jarvis.tools.executor import execute
from jarvis.tools.registry import InvalidIntent

CONFIRM_SECONDS = 3.0


class State(Enum):
    IDLE = "idle"
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
    planner: Planner | None = None


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


def _ask_planner(text: str, hooks: Hooks) -> Intent | None:
    """The planner's suggestion once it passes the same checks as the router, or None after
    saying why not."""
    if hooks.planner is None:
        _reply(hooks, State.FAILED, "Sorry, I didn't catch that.")
        return None
    try:
        proposal = hooks.planner.propose(text)
    except PlannerBusy:
        _reply(hooks, State.FAILED, "Gemini is busy right now, so I did nothing.")
        return None
    except PlannerSetup:
        _reply(hooks, State.FAILED, "Gemini refused my request. Check the API key.")
        return None
    except PlannerError:
        _reply(hooks, State.FAILED, "I couldn't reach Gemini, so I did nothing.")
        return None
    try:
        intent = to_intent(proposal)
    except (InvalidIntent, PermissionError):
        _reply(hooks, State.FAILED, "Gemini suggested something I can't do, so I did nothing.")
        return None
    if intent is None:
        reply = chat_reply(proposal)
        if reply:
            _reply(hooks, State.DONE, reply)
        else:
            _reply(hooks, State.FAILED, "Sorry, I didn't catch that.")
    return intent


def _act(text: str, hooks: Hooks) -> None:
    if is_stop(text, addressed=True):
        _reply(hooks, State.DONE, "Goodbye.")
        hooks.quit()
        return
    hooks.show(State.HEARD, text)
    intent = route(text) or _ask_planner(text, hooks)
    if intent is None:
        return
    # Leave the transcript on screen long enough to spot a mishearing before anything runs.
    time.sleep(hooks.preview_seconds)
    if intent.tool == "web.research":
        hooks.show(State.THINKING, f"Looking up {intent.args['topic']}\u2026")
    elif intent.tool == "video.notes_stop":
        hooks.show(State.THINKING, "Writing your video notes\u2026")
    elif intent.tool in ("video.notes_current", "video.notes_file"):
        hooks.show(State.THINKING, "Listening to the video\u2026 this can take a few minutes.")

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
