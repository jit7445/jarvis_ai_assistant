from pathlib import Path

import sounddevice as sd
from scipy.io.wavfile import write

SAMPLE_RATE = 16000   # whisper.cpp expects 16 kHz
DURATION = 5
OUTPUT = Path(__file__).resolve().parent.parent / "workspace" / "mic_test.wav"


def main() -> None:
    print(sd.query_devices())
    print(f"\nDefault input: {sd.query_devices(kind='input')['name']}")
    print("Recording in 3 seconds...")
    sd.sleep(3000)
    print("Speak now.")

    audio = sd.rec(int(DURATION * SAMPLE_RATE),
                   samplerate=SAMPLE_RATE, channels=1, dtype="int16")
    sd.wait()

    write(OUTPUT, SAMPLE_RATE, audio)
    peak = int(abs(audio).max())
    print(f"Saved {OUTPUT} ({OUTPUT.stat().st_size} bytes, peak level {peak}/32767)")
    if peak < 500:
        print("Warning: almost silent. Check microphone permission and input device.")


# pytest collects *_test.py files, so recording must not run on import.
if __name__ == "__main__":
    main()
