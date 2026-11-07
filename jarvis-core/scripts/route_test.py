import argparse
import subprocess

import sounddevice as sd
from scipy.io.wavfile import write

from jarvis import config
from jarvis.core.router import route

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


def show(transcript: str) -> None:
    print(f"heard:  {transcript!r}")
    intent = route(transcript)
    print(f"intent: {intent}" if intent else "intent: None (Jarvis would say it didn't catch that)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Route typed or spoken commands.")
    parser.add_argument("text", nargs="*", help="typed command; omit to speak instead")
    parser.add_argument("--wav", help="route an existing 16 kHz WAV file")
    parser.add_argument("--seconds", type=float, default=5)
    args = parser.parse_args()

    if args.text:
        show(" ".join(args.text))
    elif args.wav:
        show(transcribe(args.wav))
    else:
        record(args.seconds)
        show(transcribe(RECORDING))


if __name__ == "__main__":
    main()
