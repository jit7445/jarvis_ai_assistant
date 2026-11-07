import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from scipy.io.wavfile import write

from jarvis import config

MIN_SECONDS = 0.3
MIN_PEAK = 500

_ANNOTATION = re.compile(r"\[[^\]]*\]|\([^)]*\)|\*[^*]*\*")
# Whisper's stock output for silence and room noise.
_FILLER = {"", "you", "thank you", "thanks", "thanks for watching", "bye", "okay"}


def is_silent(audio: np.ndarray) -> bool:
    return audio.size < MIN_SECONDS * config.SAMPLE_RATE or int(np.abs(audio).max()) < MIN_PEAK


def is_noise(text: str) -> bool:
    words = _ANNOTATION.sub(" ", text)
    return " ".join(words.split()).strip(" .,!?").lower() in _FILLER


def transcribe(audio: np.ndarray) -> str:
    with tempfile.TemporaryDirectory(prefix="jarvis-") as tmp:
        wav = Path(tmp) / "command.wav"
        write(wav, config.SAMPLE_RATE, audio.astype(np.int16))
        result = subprocess.run(
            [str(config.WHISPER_CLI), "-m", str(config.WHISPER_MODEL), "-f", str(wav),
             "-t", "4", "-nt", "-np", "--prompt", config.WHISPER_PROMPT],
            capture_output=True, text=True, check=True, timeout=30,
        )
    return clean(result.stdout)


def clean(text: str) -> str:
    """Drop whisper's sound labels such as "(pop)" or "[MUSIC]", keeping the words."""
    return " ".join(_ANNOTATION.sub(" ", text).split())
