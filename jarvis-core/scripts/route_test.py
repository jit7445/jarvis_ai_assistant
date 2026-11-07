import argparse
import subprocess
from dataclasses import replace

import sounddevice as sd
from scipy.io.wavfile import write

from jarvis import config
from jarvis.core.confirm import parse_answer
from jarvis.core.router import route
from jarvis.speech.tts import speak
from jarvis.tools.executor import execute

RECORDING = config.WORKSPACE / "route_test.wav"


def record(seconds: float) -> None:
    print(f"Speak now ({seconds:.0f} s)...")
    audio = sd.rec(int(seconds * config.SAMPLE_RATE), samplerate=config.SAMPLE_RATE,
                   channels=1, dtype="int16")
    sd.wait()
    write(RECORDING, config.SAMPLE_RATE, audio)


def transcribe(wav) -> str:
    result = subprocess.run(
        [str(config.WHISPER_CLI), "-m", str(config.WHISPER_MODEL), "-f", str(wav),
         "-t", "4", "-nt", "-np", "--prompt", config.WHISPER_PROMPT],
        capture_output=True, text=True, check=True, timeout=30,
    )
    return " ".join(result.stdout.split())


def listen(seconds: float) -> str:
    record(seconds)
    return transcribe(RECORDING)


def say(text: str) -> None:
    print(f"jarvis: {text}")
    speak(text)


def handle(transcript: str, run: bool, voice: bool) -> None:
    print(f"heard:  {transcript!r}")
    intent = route(transcript)
    print(f"intent: {intent}" if intent else "intent: None")
    if not run:
        return
    if intent is None:
        say("Sorry, I didn't catch that.")
        return
    result = execute(intent)
    say(result.message)
    if not result.needs_confirmation:
        return
    answer = listen(3) if voice else input("answer> ")
    print(f"answer: {answer!r}")
    if parse_answer(answer) is True:
        say(execute(replace(intent, confirm=True)).message)
    else:
        say("Okay, I left it as it was.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Route, and optionally run, a command.")
    parser.add_argument("text", nargs="*", help="typed command; omit to speak instead")
    parser.add_argument("--wav", help="route an existing 16 kHz WAV file")
    parser.add_argument("--seconds", type=float, default=5)
    parser.add_argument("--run", action="store_true", help="execute the command and speak the result")
    args = parser.parse_args()

    config.WORKSPACE.mkdir(exist_ok=True)
    if args.text:
        handle(" ".join(args.text), args.run, voice=False)
    elif args.wav:
        handle(transcribe(args.wav), args.run, voice=False)
    else:
        handle(listen(args.seconds), args.run, voice=True)


if __name__ == "__main__":
    main()
