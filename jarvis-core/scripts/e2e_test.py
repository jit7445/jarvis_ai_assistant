"""Phase 9 end-to-end run: spoken commands through the real whisper, router and tools.

    python scripts/e2e_test.py

Uses a temporary workspace, mutes replies and stubs app launching. Prints a results table and
writes nothing into your real workspace.
"""
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

import warnings

import numpy as np
from scipy.io.wavfile import read

from jarvis import config
from jarvis.core import assistant
from jarvis.core.assistant import Hooks, State
from jarvis.speech import stt
from jarvis.speech.server import WhisperServer
from jarvis.tools import apps

VOICE = "Samantha"
# say writes an extra chunk scipy does not know; the audio itself is fine.
warnings.filterwarnings("ignore", message="Chunk")


def speech(text: str, folder: Path) -> np.ndarray:
    wav = folder / "s.wav"
    subprocess.run(["say", "-v", VOICE, "--file-format=WAVE", "--data-format=LEI16@16000",
                    "-o", str(wav), text], check=True)
    _, audio = read(wav)
    pad = np.zeros(4000, dtype=np.int16)
    return np.concatenate([pad, np.asarray(audio, dtype=np.int16).ravel(), pad])


def rss_mb(pid: int) -> float:
    out = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True).stdout
    return int(out.strip() or 0) / 1024


def pressure() -> str:
    out = subprocess.run(["memory_pressure", "-Q"], capture_output=True, text=True).stdout
    return next((l.strip() for l in out.splitlines() if "free percentage" in l), "unknown")


class Run:
    def __init__(self, answers=None):
        self.shown, self.spoken, self.answers = [], [], list(answers or [])

    def hooks(self, folder: Path) -> Hooks:
        def listen(seconds):
            text = self.answers.pop(0) if self.answers else None
            return speech(text, folder) if text else np.zeros(16000, dtype=np.int16)
        return Hooks(show=lambda s, t: self.shown.append(s), speak=self.spoken.append,
                     transcribe=stt.transcribe, listen=listen, preview_seconds=0)


def main() -> int:
    launched = []
    # Only the launcher's own reference: apps.subprocess is the shared module.
    apps.subprocess = SimpleNamespace(
        run=lambda argv, **kw: launched.append(argv) or subprocess.CompletedProcess(argv, 0))
    tmp = Path(tempfile.mkdtemp(prefix="jarvis-e2e-"))
    config.WORKSPACE = tmp / "workspace"
    config.WORKSPACE.mkdir()
    audio_dir = tmp / "audio"
    audio_dir.mkdir()

    server = WhisperServer()
    t = time.monotonic()
    server.start()
    stt.server = server
    print(f"whisper-server ready in {time.monotonic() - t:.1f} s, pid {server._process.pid}\n")

    rows = []

    def check(label, audio, expect, answers=None):
        run = Run(answers)
        start = time.monotonic()
        assistant.handle(audio, run.hooks(audio_dir))
        took = time.monotonic() - start
        reply = run.spoken[-1] if run.spoken else "(silent)"
        ok = expect(run, reply)
        rows.append((label, ok, took, reply))
        print(f"{'PASS' if ok else 'FAIL'}  {took:5.2f} s  {label:38} -> {reply}")
        return ok

    print("Known commands, spoken")
    for text, expect in [
        ("Jarvis, create a folder called Research.", "Created the folder Research."),
        # Samantha's "groceries" often comes back as "grocery"; executing and confirming is the test.
        ("Make a note called groceries saying milk and eggs.", "Saved the note grocer"),
        ("Read me groceries.", "milk and eggs"),
        ("What's in my workspace?", "Research"),
        ("Open Notes.", "Opening Notes."),
    ]:
        check(text, speech(text, audio_dir), lambda r, reply, e=expect: e.lower() in reply.lower())

    print("\nEdge cases")
    check("silence after the hotkey", np.zeros(32000, dtype=np.int16),
          lambda r, reply: reply == "I didn't hear anything.")
    noise = np.random.default_rng(0).normal(0, 2500, 48000).astype(np.int16)
    before = sorted(p.name for p in config.WORKSPACE.iterdir())
    check("background noise", noise,
          lambda r, reply: sorted(p.name for p in config.WORKSPACE.iterdir()) == before
          and State.DONE not in r.shown[1:] or reply in ("I didn't hear anything.",
                                                         "Sorry, I didn't catch that."))
    check("open Terminal", speech("Open Terminal.", audio_dir),
          lambda r, reply: "isn't on my list" in reply and not any("Terminal" in a for a in launched))
    check("delete everything, answer no", speech("Delete everything in my workspace.", audio_dir),
          lambda r, reply: r.spoken[0].startswith("Move all") and reply == "Okay, I left it as it was."
          and (config.WORKSPACE / "Research").exists(), answers=["No."])
    check("offline: no Gemini planner", speech("Create a folder called Offline.", audio_dir),
          lambda r, reply: reply.lower() == "created the folder offline.")

    print("\nTwenty commands in a row")
    phrases = ["Create a folder called Run {}.", "What's in my workspace?", "Read me groceries.",
               "Make a note called log {} saying entry {}."]
    clips = [speech(phrases[i % 4].format(i, i, i), audio_dir) for i in range(20)]
    me, srv = __import__("os").getpid(), server._process.pid
    mem_start = (rss_mb(me), rss_mb(srv))
    times = []
    for i, clip in enumerate(clips):
        run = Run()
        start = time.monotonic()
        assistant.handle(clip, run.hooks(audio_dir))
        times.append(time.monotonic() - start)
    mem_end = (rss_mb(me), rss_mb(srv))
    print(f"latency first 5 avg {np.mean(times[:5]):.2f} s, last 5 avg {np.mean(times[-5:]):.2f} s, "
          f"max {max(times):.2f} s")
    print(f"memory python {mem_start[0]:.0f} -> {mem_end[0]:.0f} MB, "
          f"whisper-server {mem_start[1]:.0f} -> {mem_end[1]:.0f} MB")
    print(f"system: {pressure()}")

    t = time.monotonic()
    subprocess.run(["say", "-v", VOICE, "-o", str(audio_dir / "r.aiff"), "Created the folder Research."],
                   check=True)
    print(f"\nsay start-up and render for a short reply: {time.monotonic() - t:.2f} s")
    server.stop()
    failed = [r for r in rows if not r[1]]
    print(f"\n{len(rows) - len(failed)}/{len(rows)} scenario checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
