import argparse
import subprocess
import time

from jarvis.speech.tts import installed_voices, speak

SAMPLE = "Hello. I am Jarvis. I created a folder called Research in your workspace."

SAFETY_LINES = [
    'I will now read a dangerous sentence. Done. "; ls',
    "-o /tmp/should_not_exist.aiff",
]


def english_voices() -> list[tuple[str, str]]:
    listing = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, check=True).stdout
    found = []
    for name in sorted(installed_voices()):
        line = next(l for l in listing.splitlines() if l.startswith(name))
        locale = line[len(name):].split()[0]
        if locale.startswith("en_"):
            found.append((name, locale))
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description="Try Jarvis voices.")
    parser.add_argument("text", nargs="?", default=SAMPLE)
    parser.add_argument("-v", "--voice", action="append",
                        help="voice to try; repeat to compare several")
    parser.add_argument("--list", action="store_true", help="list installed English voices")
    parser.add_argument("--safety", action="store_true", help="read the injection test lines")
    args = parser.parse_args()

    if args.list:
        for name, locale in english_voices():
            print(f"{locale}  {name}")
        return

    lines = SAFETY_LINES if args.safety else [args.text]
    for voice in args.voice or ["Samantha", "Rishi"]:
        for line in lines:
            print(f"{voice}: {line}")
            start = time.perf_counter()
            speak(line, voice=voice)
            print(f"  finished in {time.perf_counter() - start:.2f} s")


if __name__ == "__main__":
    main()
