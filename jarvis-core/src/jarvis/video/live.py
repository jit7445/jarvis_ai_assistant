import shutil
import tempfile
import threading
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from jarvis import config
from jarvis.core.result import Result
from jarvis.video.source import Video

STOP_HINT = "Say “Jarvis, stop notes” when it’s done."


def _recorder(path: Path):
    from jarvis.audio.system import SystemAudioRecorder
    return SystemAudioRecorder(path)


def _front_app() -> str:
    from jarvis.video.source import _frontmost
    return _frontmost() or "your Mac"


# Replaced in tests.
make_recorder = _recorder
front_app = _front_app
clock = time.monotonic
now = datetime.now


class _Session:
    def __init__(self, recorder, folder: Path, label: str, started: float) -> None:
        self.recorder, self.folder, self.label, self.started = recorder, folder, label, started


_lock = threading.Lock()
_session: _Session | None = None
_on_auto_stop: Callable[[Result], None] = lambda result: None


def on_auto_stop(callback: Callable[[Result], None]) -> None:
    """Called with the note's result when a recording ends without being asked to."""
    global _on_auto_stop
    _on_auto_stop = callback


def active() -> bool:
    return _session is not None


def start() -> Result:
    global _session
    with _lock:
        if _session is not None:
            return Result(True, f"I'm already taking notes. {STOP_HINT}")
        folder = Path(tempfile.mkdtemp(prefix="jarvis-live-"))
        recorder = make_recorder(folder / "audio.wav")
        try:
            recorder.start()
        except Exception:
            shutil.rmtree(folder, ignore_errors=True)
            return Result(False, "I need Screen Recording permission to hear your Mac's sound. "
                                 "Allow it in System Settings, Privacy and Security, Screen "
                                 "Recording, then restart Jarvis.")
        label = f"{front_app()} {now():%H:%M}"
        _session = _Session(recorder, folder, label, clock())
    threading.Thread(target=_watch, args=(_session,), daemon=True).start()
    return Result(True, f"I'm listening to your Mac's sound and taking notes. {STOP_HINT}")


def stop() -> Result:
    session = _take()
    if session is None:
        return Result(False, "I'm not taking notes right now.")
    return _finish(session)


def _take() -> _Session | None:
    global _session
    with _lock:
        session, _session = _session, None
    return session


def _finish(session: _Session) -> Result:
    from jarvis import video
    try:
        seconds = session.recorder.stop()
        if seconds < 1:
            return Result(False, "I didn't hear anything, so I saved nothing.")
        source = Video("live", f"Sound played on this Mac ({session.label})", "")
        return video.notes_from_wav(source, f"Notes from {session.label}",
                                    session.folder / "audio.wav", seconds)
    finally:
        shutil.rmtree(session.folder, ignore_errors=True)


def _watch(session: _Session, poll: float = 5.0) -> None:
    while _session is session:
        quiet = clock() - session.recorder.last_loud
        long = clock() - session.started
        if (quiet > config.LIVE_SILENCE_STOP_SECONDS or long > config.MAX_VIDEO_SECONDS
                or session.recorder.failed):
            with _lock:
                if _session is not session:
                    return
            if _take() is session:
                _on_auto_stop(_finish(session))
            return
        time.sleep(poll)
