import argparse
import queue
import signal
import subprocess
import threading
import time

import AppKit
import numpy as np
from ApplicationServices import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt
from PyObjCTools import AppHelper
from scipy.io.wavfile import read

from jarvis import config
from jarvis.audio.listener import Listener
from jarvis.audio.recorder import Recorder
from jarvis.core import assistant
from jarvis.core.assistant import Hooks, State
from jarvis.core.wake import is_stop, split_wake
from jarvis.speech import stt, tts
from jarvis.ui.overlay import Overlay
from jarvis import coding
from jarvis.video import live

RIGHT_OPTION_KEYCODE = 61
# Device-dependent bit for the right-hand Option key (NX_DEVICERALTKEYMASK); the public
# NSEventModifierFlagOption does not say which side is down.
RIGHT_OPTION_FLAG = 0x40
MIN_HOLD_SECONDS = 0.25
MAX_HOLD_SECONDS = 15.0
COMMAND_WAIT_SECONDS = 6.0
# Gap after Jarvis stops talking before the microphone counts again, so the tail of its own
# voice is not heard as a new utterance.
COOLDOWN_SECONDS = 0.4

SOUNDS = {
    "start": "/System/Library/Sounds/Pop.aiff",
    "stop": "/System/Library/Sounds/Bottle.aiff",
    "error": "/System/Library/Sounds/Basso.aiff",
}


def cue(name: str) -> subprocess.Popen:
    return subprocess.Popen(["afplay", SOUNDS[name]])


def cue_then_listen() -> None:
    # The microphone would otherwise record Jarvis's own chime as the start of the reply.
    try:
        cue("start").wait(timeout=1.0)
    except subprocess.TimeoutExpired:
        pass


class Jarvis:
    def __init__(self, mute: bool = False, quit_when_done: bool = False,
                 verbose: bool = False, wake: bool = False, planner=None) -> None:
        self.overlay = Overlay(on_close=self.close)
        self.recorder = Recorder(on_level=self._level)
        self.listener = Listener(on_utterance=self._utterance, on_level=self._wake_level)
        self.mute = mute
        self.quit_when_done = quit_when_done
        self.verbose = verbose
        self.wake = wake
        self.planner = planner
        self.jobs: queue.Queue[tuple[str, object]] = queue.Queue()
        self.utterances: queue.Queue[np.ndarray] = queue.Queue()
        self.awaiting_command = threading.Event()
        self.quitting = False
        self.busy = False
        self.holding = False
        self.cancelled = False
        self.pressed_at = 0.0
        self.session = 0
        live.on_auto_stop(lambda result: self.jobs.put(("announce", result)))
        coding.on_reply(lambda result: self.jobs.put(("announce", result)))
        coding.set_log(self.log)
        threading.Thread(target=self._work, daemon=True).start()

    def log(self, label: str, text: str = "") -> None:
        if self.verbose:
            print(f"{label:>10}  {text}", flush=True)

    def _level(self, value: float) -> None:
        AppHelper.callAfter(self.overlay.level, value)

    def _wake_level(self, value: float) -> None:
        if self.awaiting_command.is_set():
            self._level(value)

    def _utterance(self, audio: np.ndarray) -> None:
        if self.awaiting_command.is_set():
            self.utterances.put(audio)
        else:
            self.jobs.put(("utterance", audio))

    def _show(self, state: State, text: str) -> None:
        self.log(state.value, text)
        if state is State.FAILED:
            cue("error")
        AppHelper.callAfter(self.overlay.show, state, text)

    def _speak(self, text: str) -> None:
        if not self.mute:
            tts.speak(text)

    def _listen(self, seconds: float) -> np.ndarray:
        cue_then_listen()
        audio = self.recorder.record_for(seconds)
        cue("stop")
        return audio

    def _hooks(self) -> Hooks:
        return Hooks(show=self._show, speak=self._speak, transcribe=stt.transcribe,
                     listen=self._listen, quit=self._quit,
                     planner=self.planner, log=self.log)

    @property
    def idle_text(self) -> str:
        if live.active():
            return "Taking video notes\u2026 say \u201cJarvis, stop notes\u201d."
        return "Say \u201cJarvis\u201d to talk." if self.wake else "Hold right Option to talk."

    def settle(self, after: float = 0.0) -> None:
        """Back to the idle card while Jarvis keeps running; one-shot runs just hide."""
        if self.quit_when_done or self.quitting:
            self.overlay.hide(after)
        else:
            self.overlay.rest(self.idle_text, after)

    def close(self) -> None:
        print("Jarvis closed.", flush=True)
        self.overlay.dismiss()
        AppHelper.callLater(0.4, AppHelper.stopEventLoop)

    def _quit(self) -> None:
        self.quitting = True
        print("Jarvis stopped by voice.", flush=True)

    def _await_command(self) -> np.ndarray:
        while not self.utterances.empty():
            self.utterances.get_nowait()
        AppHelper.callAfter(self.overlay.show, State.LISTENING, "Yes?")
        cue_then_listen()
        self.awaiting_command.set()
        self.listener.enabled = True
        try:
            audio = self.utterances.get(timeout=COMMAND_WAIT_SECONDS)
            cue("stop")
            return audio
        except queue.Empty:
            return np.zeros(0, dtype=np.int16)
        finally:
            self.listener.enabled = False
            self.awaiting_command.clear()

    def _on_utterance(self, audio: np.ndarray) -> bool:
        """Handle overheard speech; True if it was meant for Jarvis."""
        if stt.is_silent(audio):
            return False
        text = stt.transcribe(audio)
        if is_stop(text):
            assistant.handle_text(text, self._hooks())
            return True
        command = None if stt.is_noise(text) else split_wake(text)
        if command is None:
            self.log("ignored", "speech without the wake word")
            return False
        self.log("wake")
        if command:
            assistant.handle_text(command, self._hooks())
        else:
            assistant.handle(self._await_command(), self._hooks())
        return True

    def _work(self) -> None:
        while True:
            kind, audio = self.jobs.get()
            self.busy = True
            self.listener.enabled = False
            shown = True
            try:
                if kind == "announce":
                    self._show(State.DONE if audio.ok else State.FAILED, audio.message)
                    self._speak(audio.message)
                elif kind == "utterance":
                    shown = self._on_utterance(audio)
                else:
                    assistant.handle(audio, self._hooks())
            except Exception:
                self.log("error", "listener job failed")
            finally:
                if shown:
                    AppHelper.callAfter(self.settle, 1.5)
                pending = []
                while not self.jobs.empty():
                    job = self.jobs.get_nowait()
                    if job[0] == "announce":
                        pending.append(job)
                for job in pending:
                    self.jobs.put(job)
                time.sleep(COOLDOWN_SECONDS)
                self.busy = False
                if self.quitting:
                    AppHelper.callLater(1.0, AppHelper.stopEventLoop)
                    return
                self.listener.enabled = self.wake
                if self.quit_when_done:
                    AppHelper.callLater(2.5, AppHelper.stopEventLoop)

    def process(self, audio: np.ndarray) -> None:
        self.busy = True
        self.jobs.put(("command", audio))

    def press(self) -> None:
        if self.busy or self.holding:
            return
        self.listener.enabled = False
        self.holding, self.cancelled = True, False
        self.pressed_at = time.monotonic()
        self.session += 1
        session = self.session
        cue("start")
        self.overlay.show(State.LISTENING, "")
        self.recorder.start()
        AppHelper.callLater(MAX_HOLD_SECONDS, lambda: self.session == session and self.release())

    def release(self) -> None:
        if not self.holding:
            return
        self.holding = False
        audio = self.recorder.stop()
        if self.cancelled or time.monotonic() - self.pressed_at < MIN_HOLD_SECONDS:
            self.settle()
            self.listener.enabled = self.wake
            return
        cue("stop")
        self.process(audio)

    def on_event(self, event) -> None:
        if event.type() != AppKit.NSEventTypeFlagsChanged:
            # Option held with a key, click, drag or scroll is a shortcut, not push-to-talk.
            if self.holding:
                self.cancelled = True
            return
        if event.keyCode() != RIGHT_OPTION_KEYCODE:
            return
        if event.modifierFlags() & RIGHT_OPTION_FLAG:
            self.press()
        else:
            self.release()

    def install_hotkey(self) -> bool:
        trusted = AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True})
        mask = (AppKit.NSEventMaskFlagsChanged | AppKit.NSEventMaskKeyDown
                | AppKit.NSEventMaskLeftMouseDown | AppKit.NSEventMaskRightMouseDown
                | AppKit.NSEventMaskOtherMouseDown | AppKit.NSEventMaskScrollWheel)
        AppKit.NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(mask, self.on_event)
        AppKit.NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
            mask, lambda e: (self.on_event(e), e)[1])
        return bool(trusted)

    def start_wake(self) -> None:
        self.listener.start()


def main() -> None:
    parser = argparse.ArgumentParser(prog="jarvis", description="Jarvis voice assistant.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="listen for 5 s now, act, then quit")
    mode.add_argument("--wav", help="run one command from a 16 kHz WAV file, then quit")
    parser.add_argument("--no-wake", action="store_true",
                        help="hotkey only; do not keep the microphone open for 'Jarvis'")
    parser.add_argument("--mute", action="store_true", help="show replies without speaking")
    parser.add_argument("--verbose", action="store_true", help="print each state to the terminal")
    parser.add_argument("--offline", action="store_true",
                        help="never ask Gemini, even when GEMINI_API_KEY is set")
    args = parser.parse_args()

    planner = None
    if not args.offline:
        from jarvis.planner import gemini
        planner = gemini.from_environment()

    config.WORKSPACE.mkdir(exist_ok=True)
    app = AppKit.NSApplication.sharedApplication()
    app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
    one_shot = bool(args.once or args.wav)
    jarvis = Jarvis(mute=args.mute, quit_when_done=one_shot, verbose=args.verbose,
                    wake=not (args.no_wake or one_shot), planner=planner)
    if planner is not None:
        print(f"Gemini fallback on ({planner.model}); only unrecognised sentences are sent.",
              flush=True)
    elif not args.offline:
        print("Gemini fallback off: GEMINI_API_KEY is not set.", flush=True)

    if args.wav:
        _, audio = read(args.wav)
        AppHelper.callLater(0.2, lambda: jarvis.process(np.asarray(audio, dtype=np.int16).ravel()))
    elif args.once:
        def listen_once():
            jarvis.overlay.show(State.LISTENING, "")
            cue("start")

            def record():
                audio = jarvis.recorder.record_for(5.0)
                cue("stop")
                jarvis.process(audio)
            threading.Thread(target=record, daemon=True).start()
        AppHelper.callLater(0.2, listen_once)
    else:
        hotkey = jarvis.install_hotkey()
        if jarvis.wake:
            jarvis.start_wake()
        lines = ["Jarvis is ready. Ctrl+C to quit."]
        if jarvis.wake:
            lines.append("  Say \"Jarvis\", \"hi Jarvis\" or \"hello Jarvis\", alone or followed by a command."
                         "\n  The microphone stays on while Jarvis runs; --no-wake turns that off.")
        if hotkey:
            lines.append("  Or hold the right Option key, speak, and let go.")
        else:
            lines.append("  The Option hotkey needs Accessibility permission for this terminal app.")
        print("\n".join(lines), flush=True)
        AppHelper.callLater(0.2, jarvis.settle)

    signal.signal(signal.SIGINT, lambda *_: AppHelper.stopEventLoop())
    signal.signal(signal.SIGTERM, lambda *_: AppHelper.stopEventLoop())
    # Python runs signal handlers only between bytecodes; while AppKit's run loop sleeps that never
    # happens, so this timer wakes the interpreter often enough for Ctrl+C to land.
    AppKit.NSTimer.scheduledTimerWithTimeInterval_repeats_block_(0.25, True, lambda timer: None)
    AppHelper.runEventLoop()
    if live.active():
        print("Saving your video notes before quitting...", flush=True)
        print(live.stop().message, flush=True)


if __name__ == "__main__":
    main()
